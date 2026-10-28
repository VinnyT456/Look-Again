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
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** A signed-in Bluesky account, from OAuth. Kept encrypted on this device only. */
@Serializable
data class BlueskySession(
    val did: String,
    val handle: String,
    /** The account's own server, where timeline requests go. */
    val pds: String,
    val issuer: String,
    val tokenEndpoint: String,
    val accessToken: String,
    val refreshToken: String? = null,
    /** Epoch milliseconds. */
    val expiresAt: Long,
    /** The DPoP key pair the tokens are bound to ([DPoPSigner.encoded]). */
    val dpopKey: String,
) {
    /** Refresh a minute early so a request never races the expiry. */
    fun needsRefresh(now: Long): Boolean = expiresAt - 60_000 <= now
}

/** Keeps the session encrypted with a key that never leaves the Android Keystore. */
class SessionVault(private val prefs: SharedPreferences) {
    fun load(): BlueskySession? = try {
        // Sessions from the old app-password sign-in no longer decode, so they read as signed out.
        prefs.getString(KEY, null)?.let { decrypt(it) }?.let { lenientJson.decodeFromString<BlueskySession>(it) }
    } catch (e: Exception) {
        null
    }

    fun save(session: BlueskySession?) {
        prefs.edit {
            if (session == null) remove(KEY) else putString(KEY, encrypt(lenientJson.encodeToString(BlueskySession.serializer(), session)))
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
 * The optional Bluesky sign-in, through Bluesky's own sign-in page (OAuth),
 * so no password is ever typed into Look Again. Only used to read the
 * user's Following timeline; requests go straight to Bluesky.
 */
class BlueskyAccount(
    private val vault: SessionVault?,
    private val client: BlueskyOAuthClient = BlueskyOAuthClient(),
    private val now: () -> Long = System::currentTimeMillis,
) {
    sealed interface State {
        data object SignedOut : State
        data object SigningIn : State
        data class SignedIn(val handle: String) : State
    }

    private var session: BlueskySession? = vault?.load()

    var state by mutableStateOf<State>(session?.let { State.SignedIn(it.handle) } ?: State.SignedOut)
        private set

    /** Why the last sign-in failed, or that it expired; shown once. */
    var lastError by mutableStateOf<String?>(null)

    val isSignedIn: Boolean get() = state is State.SignedIn
    val handle: String? get() = (state as? State.SignedIn)?.handle

    private val refreshLock = Mutex()
    /** Bumped on every sign-in and sign-out, so a slow refresh can't undo either. */
    private var generation = 0

    /**
     * Opens Bluesky's sign-in page with [authenticate] (a browser tab that
     * returns the redirect back to the app; it gets the page and the `state`
     * the redirect must carry) and keeps the result. `handle` is only for
     * accounts hosted outside Bluesky.
     */
    suspend fun signIn(handle: String? = null, authenticate: suspend (url: String, state: String) -> String) {
        if (state == State.SigningIn) return
        val previous = state
        state = State.SigningIn
        lastError = null
        try {
            val pending = client.beginSignIn(handle)
            val callback = authenticate(pending.authorizeUrl, pending.state)
            val signedIn = client.finishSignIn(pending, callback)
            generation++
            update(signedIn)
            state = State.SignedIn(signedIn.handle)
        } catch (e: CancellationException) {
            state = previous
            throw e
        } catch (e: Exception) {
            state = previous
            if ((e as? BlueskyAuthException)?.reason != BlueskyAuthException.Reason.CANCELLED) {
                lastError = (e as? BlueskyAuthException)?.message ?: "Couldn't sign in. Please try again."
            }
        }
    }

    /** Forgets the session on this device. */
    fun signOut() {
        generation++
        update(null)
        state = State.SignedOut
    }

    /** One page of the signed-in user's Following timeline (image posts only). */
    suspend fun timeline(cursor: String?): FeedPage {
        var current = session ?: throw BlueskyAuthException(BlueskyAuthException.Reason.SIGNED_OUT)
        try {
            if (current.needsRefresh(now())) current = refreshed(current)
            var reply = client.timeline(current, cursor)
            if (reply.status == 401) {
                current = refreshed(current)
                reply = client.timeline(current, cursor)
            }
            if (reply.status == 401) {
                expire()
                throw BlueskyAuthException(BlueskyAuthException.Reason.SESSION_EXPIRED)
            }
            if (reply.status != 200) throw CheckException.Network
            return BlueskyFeedService.page(reply.body)
        } catch (e: BlueskyAuthException) {
            // Anything but a lost sign-in reads as a network problem on the Feed.
            if (e.reason == BlueskyAuthException.Reason.SESSION_EXPIRED) throw e
            throw CheckException.Network
        } catch (e: CancellationException) {
            throw e
        } catch (e: CheckException) {
            throw e
        } catch (e: Exception) {
            throw CheckException.Network
        }
    }

    /** One refresh at a time: refresh tokens are single-use. */
    private suspend fun refreshed(stale: BlueskySession): BlueskySession = refreshLock.withLock {
        val current = session ?: throw BlueskyAuthException(BlueskyAuthException.Reason.SIGNED_OUT)
        if (current.accessToken != stale.accessToken) return@withLock current // Someone else already refreshed.
        val started = generation
        try {
            val next = client.refresh(current)
            // Signed out (or into another account) meanwhile: drop it.
            if (generation != started) throw BlueskyAuthException(BlueskyAuthException.Reason.SIGNED_OUT)
            next.also(::update)
        } catch (e: BlueskyAuthException) {
            if (e.reason == BlueskyAuthException.Reason.SESSION_EXPIRED && generation == started) expire()
            throw e
        }
    }

    private fun expire() {
        signOut()
        lastError = BlueskyAuthException.Reason.SESSION_EXPIRED.message(null)
    }

    private fun update(new: BlueskySession?) {
        session = new
        vault?.save(new)
    }
}
