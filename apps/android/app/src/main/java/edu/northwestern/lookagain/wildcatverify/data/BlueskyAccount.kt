package edu.northwestern.lookagain.wildcatverify.data

import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.edit
import edu.northwestern.lookagain.wildcatverify.model.CheckException
import edu.northwestern.lookagain.wildcatverify.model.FeedPage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.Serializable
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.net.URLEncoder
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** A signed-in Bluesky session. Tokens only; the password is never stored. */
@Serializable
data class BlueskySession(
    val did: String,
    val handle: String,
    val accessJwt: String,
    val refreshJwt: String,
    /** The user's PDS, where their timeline is read from. */
    val service: String,
)

/** Sign-in failures with copy the user can act on. */
class SignInException(message: String) : Exception(message)

/** Keeps the session encrypted with a key that never leaves the Android Keystore. */
class SessionVault(private val prefs: SharedPreferences) {
    fun load(): BlueskySession? = try {
        prefs.getString(KEY, null)?.let { decrypt(it) }?.let { Json.decodeFromString<BlueskySession>(it) }
    } catch (e: Exception) {
        null
    }

    fun save(session: BlueskySession?) {
        prefs.edit {
            if (session == null) remove(KEY) else putString(KEY, encrypt(Json.encodeToString(BlueskySession.serializer(), session)))
        }
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(
                KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .build(),
            )
        }.generateKey()
    }

    private fun encrypt(plain: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION).apply { init(Cipher.ENCRYPT_MODE, key()) }
        val sealed = cipher.iv + cipher.doFinal(plain.toByteArray())
        return Base64.encodeToString(sealed, Base64.NO_WRAP)
    }

    private fun decrypt(stored: String): String {
        val sealed = Base64.decode(stored, Base64.NO_WRAP)
        val cipher = Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, sealed, 0, 12))
        }
        return String(cipher.doFinal(sealed, 12, sealed.size - 12))
    }

    private companion object {
        const val KEY = "bluesky.session"
        const val ALIAS = "wildcatverify.session"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}

/**
 * Signs in with a Bluesky app password and reads the user's Following
 * timeline. Requests go straight to Bluesky; nothing passes through a server
 * of ours.
 */
class BlueskyAccount(
    private val vault: SessionVault?,
    private val http: HttpSender = UrlConnectionHttpClient,
) {
    var session by mutableStateOf(vault?.load())
        private set

    private val refreshLock = Mutex()

    suspend fun signIn(identifier: String, appPassword: String) {
        val handle = identifier.trim().removePrefix("@")
        val body = """{"identifier":${quote(handle)},"password":${quote(appPassword.trim())}}"""
        val (status, response) = try {
            http.send("POST", "$ENTRYWAY/xrpc/com.atproto.server.createSession", JSON_HEADERS, body.toByteArray())
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            throw SignInException("Couldn't reach Bluesky. Check your connection and try again.")
        }
        val json = runCatching { lenientJson.parseToJsonElement(response.decodeToString()).jsonObject }.getOrNull()
        if (status != 200 || json == null) {
            val error = json?.get("error")?.jsonPrimitive?.content
            throw SignInException(
                when (error) {
                    "AuthFactorTokenRequired" -> "Your account uses two-factor sign-in. Use an app password instead."
                    "AuthenticationRequired" -> "That handle and app password don't match."
                    "RateLimitExceeded" -> "Too many attempts. Wait a few minutes and try again."
                    else -> "Couldn't sign in. Check your handle and app password."
                },
            )
        }
        update(sessionFrom(json, fallbackService = ENTRYWAY))
    }

    suspend fun signOut() {
        val current = session ?: return
        update(null)
        // Revoke the tokens too; signing out locally works even if this fails.
        runCatching {
            http.send("POST", "${current.service}/xrpc/com.atproto.server.deleteSession", mapOf("Authorization" to "Bearer ${current.refreshJwt}"), null)
        }
    }

    /** Forgets the session without contacting Bluesky (Erase All Data). */
    fun forget() = update(null)

    /** One page of the signed-in user's Following timeline (image posts only). */
    suspend fun timeline(cursor: String?): FeedPage {
        var url = "/xrpc/app.bsky.feed.getTimeline?limit=${BlueskyFeedService.PAGE_SIZE}"
        if (cursor != null) url += "&cursor=${URLEncoder.encode(cursor, "UTF-8")}"
        val body = authorizedGet(url)
        return try {
            BlueskyFeedService.page(body)
        } catch (e: Exception) {
            throw CheckException.Network
        }
    }

    private suspend fun authorizedGet(path: String, retried: Boolean = false): ByteArray {
        val current = session ?: throw CheckException.Network
        val (status, body) = try {
            http.send("GET", current.service + path, mapOf("Authorization" to "Bearer ${current.accessJwt}"), null)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            throw CheckException.Network
        }
        if (status == 200) return body
        if (!retried && (status == 400 || status == 401) && body.decodeToString().contains("ExpiredToken")) {
            refresh(current)
            return authorizedGet(path, retried = true)
        }
        if (status == 401) update(null)
        throw CheckException.Network
    }

    /** Access tokens last minutes; the refresh token gets a new pair. */
    private suspend fun refresh(stale: BlueskySession) = refreshLock.withLock {
        if (session?.accessJwt != stale.accessJwt) return@withLock // Someone else already refreshed.
        val (status, body) = http.send("POST", "${stale.service}/xrpc/com.atproto.server.refreshSession", mapOf("Authorization" to "Bearer ${stale.refreshJwt}"), null)
        val json = runCatching { lenientJson.parseToJsonElement(body.decodeToString()).jsonObject }.getOrNull()
        if (status != 200 || json == null) {
            update(null)
            throw CheckException.Network
        }
        update(sessionFrom(json, fallbackService = stale.service))
    }

    private fun update(new: BlueskySession?) {
        session = new
        vault?.save(new)
    }

    companion object {
        /** Bluesky's sign-in entryway; it hands back the account's own PDS. */
        const val ENTRYWAY = "https://bsky.social"
        const val APP_PASSWORDS_URL = "https://bsky.app/settings/app-passwords"
        private val JSON_HEADERS = mapOf("Content-Type" to "application/json")

        private fun quote(value: String) = Json.encodeToString(String.serializer(), value)

        /** Reads tokens and the PDS endpoint from a createSession/refreshSession response. */
        fun sessionFrom(json: JsonObject, fallbackService: String): BlueskySession {
            val service = runCatching {
                json["didDoc"]!!.jsonObject["service"]!!.jsonArray
                    .map { it.jsonObject }
                    .first { it["id"]?.jsonPrimitive?.content?.endsWith("#atproto_pds") == true }["serviceEndpoint"]!!
                    .jsonPrimitive.content.trimEnd('/')
            }.getOrDefault(fallbackService)
            return BlueskySession(
                did = json["did"]!!.jsonPrimitive.content,
                handle = json["handle"]!!.jsonPrimitive.content,
                accessJwt = json["accessJwt"]!!.jsonPrimitive.content,
                refreshJwt = json["refreshJwt"]!!.jsonPrimitive.content,
                service = service,
            )
        }
    }
}
