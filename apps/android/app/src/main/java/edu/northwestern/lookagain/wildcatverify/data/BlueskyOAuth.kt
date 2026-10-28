package edu.northwestern.lookagain.wildcatverify.data

import kotlinx.coroutines.CancellationException
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.math.BigInteger
import java.net.URI
import java.net.URLDecoder
import java.net.URLEncoder
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.SecureRandom
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

/**
 * Look Again's identity as an AT Protocol OAuth client, shared with the iOS
 * app. The client ID is the public address of `oauth-client-metadata.json`
 * (GitHub Pages, from the repository's `docs/` folder); the redirect scheme is
 * that host reversed, as the AT Protocol requires for native apps.
 */
object BlueskyOAuthConfig {
    const val CLIENT_ID = "https://vinnyt456.github.io/Look-Again/oauth-client-metadata.json"
    const val CALLBACK_SCHEME = "io.github.vinnyt456"
    const val REDIRECT_URI = "$CALLBACK_SCHEME:/oauth/callback"
    /** Broad scope, because Bluesky's servers don't list read-only scopes yet. Only `getTimeline` is ever called. */
    const val SCOPE = "atproto transition:generic"
    /** Bluesky's sign-in server for accounts hosted by Bluesky (most people). */
    const val ENTRYWAY = "https://bsky.social"
    /** Asks the user's server to forward timeline reads to Bluesky's AppView. */
    const val APP_VIEW_PROXY = "did:web:api.bsky.app#bsky_appview"
    const val TIMELINE_PAGE_SIZE = 30
}

/** Sign-in failures, with copy the user can act on. */
/** `detail` is the OAuth error code from the server, when there is one. */
class BlueskyAuthException(val reason: Reason, val detail: String? = null) : Exception(reason.message(detail)) {
    enum class Reason {
        CANCELLED, ACCOUNT_NOT_FOUND, SERVER_REJECTED, BAD_RESPONSE, STATE_MISMATCH, WRONG_ISSUER, SIGNED_OUT, SESSION_EXPIRED;

        fun message(detail: String?): String = when (this) {
            CANCELLED -> "Sign-in was cancelled."
            ACCOUNT_NOT_FOUND -> "Couldn't find that Bluesky account. Check the handle and try again."
            SERVER_REJECTED -> "Bluesky didn't accept the sign-in (${detail ?: "unknown reason"}). Please try again."
            BAD_RESPONSE -> "Couldn't reach Bluesky to sign in. Check your connection and try again."
            STATE_MISMATCH, WRONG_ISSUER -> "The sign-in reply didn't match this request, so it was ignored for safety. Please try again."
            SIGNED_OUT -> "Sign in with Bluesky to see your Following feed."
            SESSION_EXPIRED -> "Your Bluesky sign-in expired. Sign in again to see your Following feed."
        }
    }
}

private fun fail(reason: BlueskyAuthException.Reason, detail: String? = null): Nothing = throw BlueskyAuthException(reason, detail)

/** Base64 without padding, using `-` and `_` (RFC 7515). */
internal fun ByteArray.base64Url(): String = java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(this)

internal fun randomBytes(count: Int): ByteArray = ByteArray(count).also { SecureRandom().nextBytes(it) }

private fun sha256(bytes: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(bytes)

/**
 * Proof Key for Code Exchange (RFC 7636, S256 only): a fresh secret per
 * sign-in, so an intercepted authorization code is useless on its own.
 */
class Pkce(val verifier: String = randomBytes(32).base64Url()) {
    val challenge: String = sha256(verifier.toByteArray()).base64Url()
}

/**
 * Signs DPoP proofs (RFC 9449) with a per-session P-256 key, so Bluesky's
 * tokens only work from this device.
 */
class DPoPSigner(private val keys: KeyPair = generate()) {
    /** Restores a key saved with [encoded]. */
    constructor(encoded: String) : this(decode(encoded))

    /** The key pair, for keeping with the session (which is itself encrypted). */
    val encoded: String get() = keys.private.encoded.base64Url() + "." + keys.public.encoded.base64Url()

    /** The public key as a JWK, embedded in every proof's header. */
    val publicJwk get() = buildJsonObject {
        val point = (keys.public as ECPublicKey).w
        put("kty", "EC")
        put("crv", "P-256")
        put("x", point.affineX.fixed32().base64Url())
        put("y", point.affineY.fixed32().base64Url())
    }

    /**
     * A proof for one request. `url` is reduced to scheme, host and path;
     * `accessToken` adds the `ath` claim for resource requests.
     */
    fun proof(method: String, url: String, nonce: String?, accessToken: String? = null, nowSeconds: Long = System.currentTimeMillis() / 1000): String {
        val header = buildJsonObject {
            put("alg", "ES256")
            put("typ", "dpop+jwt")
            put("jwk", publicJwk)
        }
        val payload = buildJsonObject {
            put("jti", UUID.randomUUID().toString())
            put("htm", method)
            put("htu", htu(url))
            put("iat", nowSeconds)
            nonce?.let { put("nonce", it) }
            accessToken?.let { put("ath", sha256(it.toByteArray()).base64Url()) }
        }
        val signingInput = header.toString().toByteArray().base64Url() + "." + payload.toString().toByteArray().base64Url()
        val der = Signature.getInstance("SHA256withECDSA").run {
            initSign(keys.private)
            update(signingInput.toByteArray())
            sign()
        }
        return signingInput + "." + derToJose(der).base64Url()
    }

    companion object {
        fun generate(): KeyPair = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()

        private fun decode(encoded: String): KeyPair {
            val (private, public) = encoded.split('.').map { java.util.Base64.getUrlDecoder().decode(it) }
            val factory = KeyFactory.getInstance("EC")
            return KeyPair(factory.generatePublic(X509EncodedKeySpec(public)), factory.generatePrivate(PKCS8EncodedKeySpec(private)))
        }

        /** The target URI without query or fragment. */
        fun htu(url: String): String = url.substringBefore('#').substringBefore('?')

        /** Java signs ECDSA as DER; JWS ES256 wants the two 32-byte numbers back to back. */
        internal fun derToJose(der: ByteArray): ByteArray {
            var i = 2
            if (der[1].toInt() and 0x80 != 0) i += der[1].toInt() and 0x7f
            fun integer(): ByteArray {
                require(der[i] == 0x02.toByte()) { "Not a DER integer" }
                val length = der[i + 1].toInt()
                val value = der.copyOfRange(i + 2, i + 2 + length)
                i += 2 + length
                return BigInteger(1, value).fixed32()
            }
            return integer() + integer()
        }

        private fun BigInteger.fixed32(): ByteArray {
            val bytes = toByteArray()
            return when {
                bytes.size == 32 -> bytes
                bytes.size > 32 -> bytes.copyOfRange(bytes.size - 32, bytes.size)
                else -> ByteArray(32 - bytes.size) + bytes
            }
        }
    }
}

/**
 * The latest DPoP nonce each server handed out, keyed by origin. Servers
 * rotate them every few minutes; a stale one just costs one retry.
 */
class DPoPNonceStore {
    private val nonces = ConcurrentHashMap<String, String>()

    fun nonce(url: String): String? = nonces[origin(url)]

    fun remember(nonce: String, url: String) {
        nonces[origin(url)] = nonce
    }

    companion object {
        fun origin(url: String): String = runCatching {
            val uri = URI(url)
            "${uri.scheme ?: "https"}://${uri.host.orEmpty()}${if (uri.port != -1) ":${uri.port}" else ""}"
        }.getOrDefault(url)
    }
}

/** Sends requests with a DPoP proof, retrying once when the server asks for a fresh nonce. */
class DPoPHttp(private val http: HttpSender, private val nonces: DPoPNonceStore = DPoPNonceStore()) {
    suspend fun send(
        method: String,
        url: String,
        signer: DPoPSigner,
        headers: Map<String, String> = emptyMap(),
        body: ByteArray? = null,
        accessToken: String? = null,
    ): HttpReply {
        var attempt = 0
        while (true) {
            val signed = headers.toMutableMap()
            signed["DPoP"] = signer.proof(method, url, nonces.nonce(url), accessToken)
            if (accessToken != null) signed["Authorization"] = "DPoP $accessToken"
            val reply = try {
                http.send(method, url, signed, body)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                fail(BlueskyAuthException.Reason.BAD_RESPONSE)
            }
            reply.header("DPoP-Nonce")?.let { nonces.remember(it, url) }
            if (attempt == 0 && asksForNonce(reply)) {
                attempt++
                continue
            }
            return reply
        }
    }

    companion object {
        /** Token endpoints say so in the body (400); resource servers in `WWW-Authenticate` (401). */
        fun asksForNonce(reply: HttpReply): Boolean = when (reply.status) {
            400 -> runCatching { lenientJson.decodeFromString<OAuthErrorBody>(reply.body.decodeToString()).error }.getOrNull() == "use_dpop_nonce"
            401 -> reply.header("WWW-Authenticate")?.contains("use_dpop_nonce") == true
            else -> false
        }
    }
}

/** `/.well-known/oauth-authorization-server` (RFC 8414), the fields used. */
@Serializable
data class AuthServerMetadata(
    val issuer: String,
    @SerialName("authorization_endpoint") val authorizationEndpoint: String,
    @SerialName("token_endpoint") val tokenEndpoint: String,
    @SerialName("pushed_authorization_request_endpoint") val pushedAuthorizationRequestEndpoint: String,
    @SerialName("dpop_signing_alg_values_supported") val dpopSigningAlgValuesSupported: List<String>? = null,
)

/** `/.well-known/oauth-protected-resource` (RFC 9728) on the user's server. */
@Serializable
private data class ProtectedResourceMetadata(@SerialName("authorization_servers") val authorizationServers: List<String>)

@Serializable
private data class TokenResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("token_type") val tokenType: String? = null,
    @SerialName("expires_in") val expiresIn: Long? = null,
    val scope: String? = null,
    val sub: String,
)

@Serializable
private data class OAuthErrorBody(val error: String)

@Serializable
private data class ResolvedHandle(val did: String)

@Serializable
private data class ParReply(@SerialName("request_uri") val requestUri: String)

/** A DID document: where the account's data lives and which handle it claims. */
@Serializable
data class DidDocument(
    val id: String,
    val alsoKnownAs: List<String>? = null,
    val service: List<Service>? = null,
) {
    @Serializable
    data class Service(val id: String, val type: String, val serviceEndpoint: String)

    /** The account's Personal Data Server. */
    val pdsEndpoint: String?
        get() = service?.firstOrNull { it.id.endsWith("#atproto_pds") && it.type == "AtprotoPersonalDataServer" }?.serviceEndpoint?.trimEnd('/')

    /** The handle the DID claims, from `at://handle`. */
    val handle: String?
        get() = alsoKnownAs?.firstOrNull { it.startsWith("at://") }?.removePrefix("at://")
}

/** Turns a handle into a DID and a DID into its document. */
class BlueskyIdentity(private val http: HttpSender) {
    suspend fun resolveHandle(handle: String): String {
        val reply = get("https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=${URLEncoder.encode(handle, "UTF-8")}")
        if (reply.status != 200) fail(BlueskyAuthException.Reason.ACCOUNT_NOT_FOUND)
        return runCatching { lenientJson.decodeFromString<ResolvedHandle>(reply.body.decodeToString()).did }
            .getOrElse { fail(BlueskyAuthException.Reason.ACCOUNT_NOT_FOUND) }
    }

    suspend fun document(did: String): DidDocument {
        val url = documentUrl(did) ?: fail(BlueskyAuthException.Reason.ACCOUNT_NOT_FOUND)
        val reply = get(url)
        val document = runCatching { lenientJson.decodeFromString<DidDocument>(reply.body.decodeToString()) }.getOrNull()
        if (reply.status != 200 || document?.id != did) fail(BlueskyAuthException.Reason.ACCOUNT_NOT_FOUND)
        return document
    }

    private suspend fun get(url: String): HttpReply = try {
        http.send("GET", url, emptyMap(), null)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        fail(BlueskyAuthException.Reason.BAD_RESPONSE)
    }

    companion object {
        /** did:plc lives in the PLC directory; did:web on its own host. */
        fun documentUrl(did: String): String? = when {
            did.startsWith("did:plc:") -> "https://plc.directory/$did"
            did.startsWith("did:web:") -> "https://${did.removePrefix("did:web:").replace("%3A", ":")}/.well-known/did.json"
            else -> null
        }

        /** "@Alice.bsky.social " → "alice.bsky.social". */
        fun normalize(handle: String): String = handle.trim().lowercase().removePrefix("@")
    }
}

/**
 * The AT Protocol OAuth flow for a native app: discovery, a pushed
 * authorization request (PAR) with PKCE and DPoP, the code exchange, and
 * refresh. Nothing goes through a Look Again server; there isn't one.
 */
class BlueskyOAuthClient(
    private val http: HttpSender = UrlConnectionHttpClient,
    nonces: DPoPNonceStore = DPoPNonceStore(),
    private val now: () -> Long = System::currentTimeMillis,
) {
    /** Everything needed between opening Bluesky's sign-in page and its reply. */
    class PendingSignIn(
        val authorizeUrl: String,
        val state: String,
        val pkce: Pkce,
        val signer: DPoPSigner,
        val metadata: AuthServerMetadata,
        /** Set when the user typed a handle; the result must be that account. */
        val expectedDid: String?,
    )

    private val dpop = DPoPHttp(http, nonces)
    private val identity = BlueskyIdentity(http)

    /**
     * With no handle, signs in through Bluesky's own server, which covers
     * accounts hosted by Bluesky. With a handle, finds that account's server.
     */
    suspend fun beginSignIn(handle: String?): PendingSignIn {
        var expectedDid: String? = null
        var authServer = BlueskyOAuthConfig.ENTRYWAY
        val loginHint = handle?.let(BlueskyIdentity::normalize)?.takeIf { it.isNotEmpty() }

        if (loginHint != null) {
            val did = identity.resolveHandle(loginHint)
            val document = identity.document(did)
            val pds = document.pdsEndpoint
            if (document.handle?.lowercase() != loginHint || pds == null) fail(BlueskyAuthException.Reason.ACCOUNT_NOT_FOUND)
            expectedDid = did
            authServer = authorizationServer(pds)
        }

        val metadata = serverMetadata(authServer)
        val pkce = Pkce()
        val state = randomBytes(16).base64Url()
        val signer = DPoPSigner()

        val form = mutableMapOf(
            "client_id" to BlueskyOAuthConfig.CLIENT_ID,
            "response_type" to "code",
            "redirect_uri" to BlueskyOAuthConfig.REDIRECT_URI,
            "scope" to BlueskyOAuthConfig.SCOPE,
            "state" to state,
            "code_challenge" to pkce.challenge,
            "code_challenge_method" to "S256",
        )
        if (loginHint != null) form["login_hint"] = loginHint

        val reply = postForm(metadata.pushedAuthorizationRequestEndpoint, form, signer)
        val par = runCatching { lenientJson.decodeFromString<ParReply>(reply.body.decodeToString()) }.getOrNull()
        if (reply.status !in 200..299 || par == null) throw rejection(reply)

        val separator = if ('?' in metadata.authorizationEndpoint) "&" else "?"
        val authorizeUrl = metadata.authorizationEndpoint + separator + formBody(
            mapOf("client_id" to BlueskyOAuthConfig.CLIENT_ID, "request_uri" to par.requestUri),
        )
        return PendingSignIn(authorizeUrl, state, pkce, signer, metadata, expectedDid)
    }

    /** Checks Bluesky's reply to the sign-in page and exchanges its code for tokens. */
    suspend fun finishSignIn(pending: PendingSignIn, callback: String): BlueskySession {
        val query = queryOf(callback)

        query["error"]?.let { error ->
            if (error == "access_denied") fail(BlueskyAuthException.Reason.CANCELLED)
            fail(BlueskyAuthException.Reason.SERVER_REJECTED, error)
        }
        if (query["state"] != pending.state) fail(BlueskyAuthException.Reason.STATE_MISMATCH)
        if (query["iss"] != pending.metadata.issuer) fail(BlueskyAuthException.Reason.WRONG_ISSUER)
        val code = query["code"] ?: fail(BlueskyAuthException.Reason.BAD_RESPONSE)

        val token = tokenRequest(
            pending.metadata.tokenEndpoint,
            pending.signer,
            mapOf(
                "grant_type" to "authorization_code",
                "code" to code,
                "redirect_uri" to BlueskyOAuthConfig.REDIRECT_URI,
                "code_verifier" to pending.pkce.verifier,
                "client_id" to BlueskyOAuthConfig.CLIENT_ID,
            ),
        )
        if (token.tokenType?.equals("DPoP", ignoreCase = true) == false) fail(BlueskyAuthException.Reason.SERVER_REJECTED, "token not DPoP-bound")
        if (token.scope?.split(' ')?.contains("atproto") != true) fail(BlueskyAuthException.Reason.SERVER_REJECTED, "missing atproto scope")
        if (pending.expectedDid != null && token.sub != pending.expectedDid) fail(BlueskyAuthException.Reason.WRONG_ISSUER)

        // The account's server must use this same sign-in server.
        val document = identity.document(token.sub)
        val pds = document.pdsEndpoint ?: fail(BlueskyAuthException.Reason.ACCOUNT_NOT_FOUND)
        val server = authorizationServer(pds)
        if (server.trimEnd('/') != pending.metadata.issuer.trimEnd('/')) fail(BlueskyAuthException.Reason.WRONG_ISSUER)

        return BlueskySession(
            did = token.sub,
            handle = verifiedHandle(document) ?: token.sub,
            pds = pds,
            issuer = pending.metadata.issuer,
            tokenEndpoint = pending.metadata.tokenEndpoint,
            accessToken = token.accessToken,
            refreshToken = token.refreshToken,
            expiresAt = now() + (token.expiresIn ?: 300) * 1000,
            dpopKey = pending.signer.encoded,
        )
    }

    suspend fun refresh(current: BlueskySession): BlueskySession {
        val refreshToken = current.refreshToken ?: fail(BlueskyAuthException.Reason.SESSION_EXPIRED)
        val token = try {
            tokenRequest(
                current.tokenEndpoint,
                DPoPSigner(current.dpopKey),
                mapOf(
                    "grant_type" to "refresh_token",
                    "refresh_token" to refreshToken,
                    "client_id" to BlueskyOAuthConfig.CLIENT_ID,
                ),
            )
        } catch (e: BlueskyAuthException) {
            // Only a refused refresh token means signing in again; clock skew,
            // nonce churn or a server hiccup leaves the session for next time.
            if (e.reason == BlueskyAuthException.Reason.SERVER_REJECTED && e.detail == "invalid_grant") fail(BlueskyAuthException.Reason.SESSION_EXPIRED)
            if (e.reason == BlueskyAuthException.Reason.SERVER_REJECTED) fail(BlueskyAuthException.Reason.BAD_RESPONSE)
            throw e
        }
        if (token.sub != current.did) fail(BlueskyAuthException.Reason.WRONG_ISSUER)
        return current.copy(
            accessToken = token.accessToken,
            refreshToken = token.refreshToken ?: refreshToken,
            expiresAt = now() + (token.expiresIn ?: 300) * 1000,
        )
    }

    /**
     * One page of the user's Following timeline, read through their own
     * server, which forwards it to Bluesky's AppView. 401 means the access
     * token needs refreshing.
     */
    suspend fun timeline(current: BlueskySession, cursor: String?): HttpReply {
        var url = "${current.pds}/xrpc/app.bsky.feed.getTimeline?limit=${BlueskyOAuthConfig.TIMELINE_PAGE_SIZE}"
        if (cursor != null) url += "&cursor=${URLEncoder.encode(cursor, "UTF-8")}"
        return dpop.send(
            "GET",
            url,
            DPoPSigner(current.dpopKey),
            headers = mapOf("atproto-proxy" to BlueskyOAuthConfig.APP_VIEW_PROXY),
            accessToken = current.accessToken,
        )
    }

    /** The handle the DID document claims, only if that handle points back to the same DID. */
    private suspend fun verifiedHandle(document: DidDocument): String? {
        val handle = document.handle ?: return null
        return try {
            handle.takeIf { identity.resolveHandle(it) == document.id }
        } catch (e: BlueskyAuthException) {
            null
        }
    }

    private suspend fun authorizationServer(pds: String): String {
        val reply = get("${pds.trimEnd('/')}/.well-known/oauth-protected-resource")
        val resource = runCatching { lenientJson.decodeFromString<ProtectedResourceMetadata>(reply.body.decodeToString()) }.getOrNull()
        if (reply.status != 200) fail(BlueskyAuthException.Reason.BAD_RESPONSE)
        return resource?.authorizationServers?.firstOrNull() ?: fail(BlueskyAuthException.Reason.BAD_RESPONSE)
    }

    private suspend fun serverMetadata(server: String): AuthServerMetadata {
        val reply = get("${server.trimEnd('/')}/.well-known/oauth-authorization-server")
        val metadata = runCatching { lenientJson.decodeFromString<AuthServerMetadata>(reply.body.decodeToString()) }.getOrNull()
        if (reply.status != 200 || metadata == null) fail(BlueskyAuthException.Reason.BAD_RESPONSE)
        // The document must describe the server it came from, exactly.
        if (metadata.issuer.trimEnd('/') != server.trimEnd('/')) fail(BlueskyAuthException.Reason.WRONG_ISSUER)
        if (metadata.dpopSigningAlgValuesSupported?.contains("ES256") == false) fail(BlueskyAuthException.Reason.SERVER_REJECTED, "ES256 unsupported")
        return metadata
    }

    private suspend fun tokenRequest(endpoint: String, signer: DPoPSigner, form: Map<String, String>): TokenResponse {
        val reply = postForm(endpoint, form, signer)
        val token = runCatching { lenientJson.decodeFromString<TokenResponse>(reply.body.decodeToString()) }.getOrNull()
        if (reply.status != 200 || token == null) throw rejection(reply)
        return token
    }

    private suspend fun postForm(url: String, form: Map<String, String>, signer: DPoPSigner): HttpReply =
        dpop.send(
            "POST",
            url,
            signer,
            headers = mapOf("Content-Type" to "application/x-www-form-urlencoded"),
            body = formBody(form).toByteArray(),
        )

    private suspend fun get(url: String): HttpReply = try {
        http.send("GET", url, emptyMap(), null)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        fail(BlueskyAuthException.Reason.BAD_RESPONSE)
    }

    private fun rejection(reply: HttpReply): BlueskyAuthException {
        val error = runCatching { lenientJson.decodeFromString<OAuthErrorBody>(reply.body.decodeToString()).error }.getOrNull()
        return if (error != null) BlueskyAuthException(BlueskyAuthException.Reason.SERVER_REJECTED, error) else BlueskyAuthException(BlueskyAuthException.Reason.BAD_RESPONSE)
    }

    companion object {
        /** `application/x-www-form-urlencoded`, keys sorted, only unreserved characters left bare. */
        fun formBody(form: Map<String, String>): String = form.entries
            .sortedBy { it.key }
            .joinToString("&") { "${it.key}=${percentEncode(it.value)}" }

        private fun percentEncode(value: String): String = buildString {
            for (byte in value.toByteArray()) {
                val c = byte.toInt() and 0xff
                if (c.toChar().isLetterOrDigit() && c < 0x80 || c.toChar() in "-._~") append(c.toChar()) else append("%%%02X".format(c))
            }
        }

        /** The query of the redirect back to the app, decoded. */
        fun queryOf(callback: String): Map<String, String> {
            val raw = runCatching { URI(callback).rawQuery }.getOrNull() ?: return emptyMap()
            return raw.split('&').filter { it.isNotEmpty() }.associate { part ->
                val name = part.substringBefore('=')
                val value = part.substringAfter('=', "")
                URLDecoder.decode(name, "UTF-8") to URLDecoder.decode(value, "UTF-8")
            }
        }
    }
}
