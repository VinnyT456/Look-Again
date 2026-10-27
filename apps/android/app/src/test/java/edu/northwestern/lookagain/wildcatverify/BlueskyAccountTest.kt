package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.data.BlueskyAccount
import edu.northwestern.lookagain.wildcatverify.data.BlueskyAuthException
import edu.northwestern.lookagain.wildcatverify.data.BlueskyOAuthClient
import edu.northwestern.lookagain.wildcatverify.data.BlueskyOAuthConfig
import edu.northwestern.lookagain.wildcatverify.data.DPoPSigner
import edu.northwestern.lookagain.wildcatverify.data.HttpReply
import edu.northwestern.lookagain.wildcatverify.data.HttpSender
import edu.northwestern.lookagain.wildcatverify.data.Pkce
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.math.BigInteger
import java.net.URLEncoder
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECPoint
import java.security.spec.ECPublicKeySpec
import java.util.Base64

private const val TIMELINE = """
{"cursor":"c2","feed":[{"post":{"uri":"at://did:plc:a/app.bsky.feed.post/one","author":{"handle":"a"},"record":{"text":"hi"},
 "embed":{"images":[{"thumb":"https://cdn/t.jpg","fullsize":"https://cdn/f.jpg"}]}}}]}
"""

private fun b64(text: String): ByteArray = Base64.getUrlDecoder().decode(text)

/** JWS ES256 (r || s) back to the DER form Java verifies. */
private fun joseToDer(jose: ByteArray): ByteArray {
    fun integer(bytes: ByteArray): ByteArray {
        val value = BigInteger(1, bytes).toByteArray()
        return byteArrayOf(0x02, value.size.toByte()) + value
    }
    val body = integer(jose.copyOfRange(0, 32)) + integer(jose.copyOfRange(32, 64))
    return byteArrayOf(0x30, body.size.toByte()) + body
}

private val p256 = (KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair().public as ECPublicKey).params

/** Checks a DPoP proof's signature against the key in its own header; returns its claims. */
private fun verifiedClaims(proof: String): JsonObject {
    val (header, payload, signature) = proof.split('.')
    val headerJson = Json.parseToJsonElement(b64(header).decodeToString()).jsonObject
    assertEquals("dpop+jwt", headerJson["typ"]!!.jsonPrimitive.content)
    assertEquals("ES256", headerJson["alg"]!!.jsonPrimitive.content)
    val jwk = headerJson["jwk"]!!.jsonObject
    val point = ECPoint(BigInteger(1, b64(jwk["x"]!!.jsonPrimitive.content)), BigInteger(1, b64(jwk["y"]!!.jsonPrimitive.content)))
    val key = KeyFactory.getInstance("EC").generatePublic(ECPublicKeySpec(point, p256))
    val ok = Signature.getInstance("SHA256withECDSA").run {
        initVerify(key)
        update("$header.$payload".toByteArray())
        verify(joseToDer(b64(signature)))
    }
    assertTrue("DPoP signature verifies", ok)
    return Json.parseToJsonElement(b64(payload).decodeToString()).jsonObject
}

private fun formOf(body: ByteArray?): Map<String, String> =
    BlueskyOAuthClient.queryOf("x:/?" + body!!.decodeToString())

/**
 * A pretend Bluesky: discovery documents, PAR and token endpoints that insist
 * on a DPoP nonce first, the PLC directory and a PDS timeline.
 */
private class FakeBluesky : HttpSender {
    val calls = mutableListOf<String>()
    var parState: String? = null
    var parChallenge: String? = null
    var validAccess = "a1"
    var refreshWorks = true
    var refreshError: String? = null
    var duringRefresh: () -> Unit = {}
    var handleInDocument = "me.bsky.social"
    /** A handle the DID document claims but that belongs to someone else. */
    var impostorHandle = "famous.bsky.social"
    private var nonceSent = false

    override suspend fun send(method: String, url: String, headers: Map<String, String>, body: ByteArray?): HttpReply {
        calls += "$method $url"
        val claims = headers["DPoP"]?.let(::verifiedClaims)
        if (claims != null) {
            assertEquals(method, claims["htm"]!!.jsonPrimitive.content)
            assertEquals(url.substringBefore('?'), claims["htu"]!!.jsonPrimitive.content)
        }
        // Token endpoints want a nonce, and say so once.
        if (url.startsWith("https://bsky.social/oauth/") && claims?.get("nonce")?.jsonPrimitive?.content != "n1") {
            nonceSent = true
            return HttpReply(400, """{"error":"use_dpop_nonce"}""".toByteArray(), mapOf("DPoP-Nonce" to "n1"))
        }
        return when {
            url == "https://bsky.social/.well-known/oauth-authorization-server" -> json(
                """{"issuer":"https://bsky.social","authorization_endpoint":"https://bsky.social/oauth/authorize",
                "token_endpoint":"https://bsky.social/oauth/token","pushed_authorization_request_endpoint":"https://bsky.social/oauth/par",
                "dpop_signing_alg_values_supported":["ES256"]}""",
            )
            url == "https://bsky.social/oauth/par" -> {
                val form = formOf(body)
                assertEquals(BlueskyOAuthConfig.CLIENT_ID, form["client_id"])
                assertEquals(BlueskyOAuthConfig.REDIRECT_URI, form["redirect_uri"])
                assertEquals("S256", form["code_challenge_method"])
                parState = form["state"]
                parChallenge = form["code_challenge"]
                json("""{"request_uri":"urn:ietf:params:oauth:request_uri:req-1","expires_in":90}""", 201)
            }
            url == "https://bsky.social/oauth/token" -> {
                val form = formOf(body)
                when (form["grant_type"]) {
                    "authorization_code" -> {
                        assertEquals("c1", form["code"])
                        // The verifier must match the challenge sent with PAR.
                        assertEquals(parChallenge, Pkce(form["code_verifier"]!!).challenge)
                        token("a1", "r1")
                    }
                    "refresh_token" -> {
                        duringRefresh()
                        when {
                            refreshError != null -> json("""{"error":"$refreshError"}""", 400)
                            refreshWorks && form["refresh_token"] == "r1" -> token("a2", "r2")
                            else -> json("""{"error":"invalid_grant"}""", 400)
                        }
                    }
                    else -> json("""{"error":"unsupported_grant_type"}""", 400)
                }
            }
            url == "https://plc.directory/did:plc:me" -> json(
                """{"id":"did:plc:me","alsoKnownAs":["at://$handleInDocument"],
                "service":[{"id":"#atproto_pds","type":"AtprotoPersonalDataServer","serviceEndpoint":"https://pds.example.com"}]}""",
            )
            url.startsWith("https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle=") ->
                if (url.endsWith("=$impostorHandle")) json("""{"did":"did:plc:someone"}""") else json("""{"did":"did:plc:me"}""")
            url == "https://pds.example.com/.well-known/oauth-protected-resource" ->
                json("""{"authorization_servers":["https://bsky.social"]}""")
            url.startsWith("https://pds.example.com/xrpc/app.bsky.feed.getTimeline") -> {
                assertEquals(BlueskyOAuthConfig.APP_VIEW_PROXY, headers["atproto-proxy"])
                val access = headers["Authorization"]?.removePrefix("DPoP ")
                // The proof is bound to the access token.
                val ath = Base64.getUrlEncoder().withoutPadding().encodeToString(MessageDigest.getInstance("SHA-256").digest(access!!.toByteArray()))
                assertEquals(ath, claims!!["ath"]!!.jsonPrimitive.content)
                if (access == validAccess) json(TIMELINE) else HttpReply(401, ByteArray(0), mapOf("WWW-Authenticate" to """DPoP error="invalid_token""""))
            }
            else -> json("""{"error":"unexpected $method $url"}""", 500)
        }
    }

    private fun token(access: String, refresh: String) = json(
        """{"access_token":"$access","refresh_token":"$refresh","token_type":"DPoP","expires_in":300,
        "scope":"atproto transition:generic","sub":"did:plc:me"}""",
    )

    private fun json(text: String, status: Int = 200) = HttpReply(status, text.toByteArray())
}

private fun account(fake: FakeBluesky) = BlueskyAccount(null, BlueskyOAuthClient(fake, now = { 1_000_000L }), now = { 1_000_000L })

/** Plays Bluesky's sign-in page: the user taps Authorize. */
private fun approve(fake: FakeBluesky, state: () -> String? = { fake.parState }, iss: String = "https://bsky.social"): suspend (String, String) -> String = { authorizeUrl, expected ->
    assertEquals(fake.parState, expected)
    assertTrue(authorizeUrl.startsWith("https://bsky.social/oauth/authorize?"))
    assertTrue(authorizeUrl.contains("request_uri=urn%3Aietf%3Aparams%3Aoauth%3Arequest_uri%3Areq-1"))
    "${BlueskyOAuthConfig.REDIRECT_URI}?state=${state()}&iss=${URLEncoder.encode(iss, "UTF-8")}&code=c1"
}

class BlueskyAccountTest {
    @Test fun signsInWithOAuthAndReadsTheTimeline() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        assertNull(account.lastError)
        assertEquals("me.bsky.social", account.handle)

        val page = account.timeline(null)
        assertEquals(1, page.posts.size)
        assertEquals("https://cdn/f.jpg", page.posts[0].fullsizeUrl)
        assertTrue(fake.calls.any { it.startsWith("GET https://pds.example.com/xrpc/app.bsky.feed.getTimeline?limit=30") })
    }

    @Test fun replyForAnotherRequestIsIgnored() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake, state = { "someone-elses-state" }))
        assertFalse(account.isSignedIn)
        assertTrue(account.lastError!!.contains("didn't match"))
    }

    @Test fun replyFromAnotherServerIsIgnored() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake, iss = "https://evil.example"))
        assertFalse(account.isSignedIn)
        assertTrue(account.lastError!!.contains("didn't match"))
    }

    @Test fun closingTheSignInPageIsQuiet() = runTest {
        val account = account(FakeBluesky())
        account.signIn { _, _ -> throw BlueskyAuthException(BlueskyAuthException.Reason.CANCELLED) }
        assertEquals(BlueskyAccount.State.SignedOut, account.state)
        assertNull(account.lastError)
    }

    @Test fun deniedOnBlueskysPageIsQuiet() = runTest {
        val account = account(FakeBluesky())
        account.signIn { _, _ -> "${BlueskyOAuthConfig.REDIRECT_URI}?error=access_denied" }
        assertFalse(account.isSignedIn)
        assertNull(account.lastError)
    }

    @Test fun handleSignInMustBeThatAccount() = runTest {
        val fake = FakeBluesky().apply { handleInDocument = "someone.else" }
        val account = account(fake)
        account.signIn("@Me.Example.com ", approve(fake))
        assertFalse(account.isSignedIn)
        assertTrue(account.lastError!!.contains("Couldn't find"))
    }

    @Test fun handleSignInFindsTheAccountsServer() = runTest {
        val fake = FakeBluesky().apply { handleInDocument = "me.example.com" }
        val account = account(fake)
        account.signIn("@Me.Example.com ", approve(fake))
        assertEquals("me.example.com", account.handle)
        assertTrue(fake.calls.contains("GET https://pds.example.com/.well-known/oauth-protected-resource"))
    }

    @Test fun expiredAccessTokenIsRefreshed() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        fake.validAccess = "a2"
        assertEquals(1, account.timeline(null).posts.size)
        assertTrue(fake.calls.count { it == "POST https://bsky.social/oauth/token" } >= 2)
    }

    @Test fun rejectedRefreshSignsOutAndSaysSo() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        fake.validAccess = "a2"
        fake.refreshWorks = false
        try {
            account.timeline(null)
            fail()
        } catch (e: BlueskyAuthException) {
            assertEquals(BlueskyAuthException.Reason.SESSION_EXPIRED, e.reason)
        }
        assertFalse(account.isSignedIn)
        assertTrue(account.lastError!!.contains("expired"))
    }

    @Test fun claimedHandleThatIsntTheirsShowsTheDid() = runTest {
        val fake = FakeBluesky().apply { handleInDocument = "famous.bsky.social" }
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        assertEquals("did:plc:me", account.handle)
    }

    @Test fun refreshHiccupKeepsTheSession() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        fake.validAccess = "a2"
        fake.refreshError = "server_error"
        try {
            account.timeline(null)
            fail()
        } catch (e: Exception) {
            // Reads as a network problem.
        }
        assertTrue(account.isSignedIn)
        assertNull(account.lastError)
    }

    @Test fun signingOutDuringARefreshStaysSignedOut() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        fake.validAccess = "a2"
        fake.duringRefresh = { account.signOut() }
        try {
            account.timeline(null)
            fail()
        } catch (e: Exception) {
            // The timeline isn't read for an account that just signed out.
        }
        assertFalse(account.isSignedIn)
        assertNull(account.lastError)
    }

    @Test fun signOutForgets() = runTest {
        val fake = FakeBluesky()
        val account = account(fake)
        account.signIn(authenticate = approve(fake))
        account.signOut()
        assertFalse(account.isSignedIn)
        try {
            account.timeline(null)
            fail()
        } catch (e: BlueskyAuthException) {
            assertEquals(BlueskyAuthException.Reason.SIGNED_OUT, e.reason)
        }
    }
}

class OAuthPiecesTest {
    @Test fun pkceChallengeIsSha256OfTheVerifier() {
        // Worked out separately with Python's hashlib.
        assertEquals("xyV6EN1Au6gj_Hhaws2OOaNT2DOjSBcSFR-6rpFHn7g", Pkce("dBjftJeZ4CVP-mJ92K1qUcmGNoBn1-Yj0b9u_vM6YiE").challenge)
        assertEquals(43, Pkce().verifier.length)
    }

    @Test fun dpopProofSurvivesSavingTheKey() {
        val saved = DPoPSigner().encoded
        val claims = verifiedClaims(DPoPSigner(saved).proof("GET", "https://pds.example.com/xrpc/x?y=1#z", nonce = "n", accessToken = "t", nowSeconds = 42))
        assertEquals("https://pds.example.com/xrpc/x", claims["htu"]!!.jsonPrimitive.content)
        assertEquals("42", claims["iat"]!!.jsonPrimitive.content)
        assertEquals("n", claims["nonce"]!!.jsonPrimitive.content)
    }

    @Test fun formBodyEncodesEverythingButUnreserved() {
        assertEquals(
            "a=x%20y%2Bz~&b=io.github.vinnyt456%3A%2Foauth%2Fcallback",
            BlueskyOAuthClient.formBody(mapOf("b" to "io.github.vinnyt456:/oauth/callback", "a" to "x y+z~")),
        )
    }

    @Test fun callbackQueryIsDecoded() {
        val query = BlueskyOAuthClient.queryOf("io.github.vinnyt456:/oauth/callback?state=s%2B1&iss=https%3A%2F%2Fbsky.social&code=c")
        assertEquals(mapOf("state" to "s+1", "iss" to "https://bsky.social", "code" to "c"), query)
    }
}
