package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.data.BlueskyAccount
import edu.northwestern.lookagain.wildcatverify.data.HttpSender
import edu.northwestern.lookagain.wildcatverify.data.SignInException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

private fun session(access: String) = """
{"did":"did:plc:me","handle":"me.bsky.social","accessJwt":"$access","refreshJwt":"r-$access",
 "didDoc":{"service":[{"id":"#atproto_pds","type":"AtprotoPersonalDataServer","serviceEndpoint":"https://pds.example.com/"}]}}
"""

private const val TIMELINE = """
{"cursor":"c2","feed":[{"post":{"uri":"at://did:plc:a/app.bsky.feed.post/one","author":{"handle":"a"},"record":{"text":"hi"},
 "embed":{"images":[{"thumb":"https://cdn/t.jpg","fullsize":"https://cdn/f.jpg"}]}}}]}
"""

/** Records requests and answers from a script keyed by path. */
private class FakeBluesky(val answer: (method: String, url: String, auth: String?) -> Pair<Int, String>) : HttpSender {
    val calls = mutableListOf<String>()
    override suspend fun send(method: String, url: String, headers: Map<String, String>, body: ByteArray?): Pair<Int, ByteArray> {
        calls += "$method $url"
        val (status, text) = answer(method, url, headers["Authorization"])
        return status to text.toByteArray()
    }
}

class BlueskyAccountTest {
    @Test fun signInFindsTheAccountsPds() = runTest {
        val account = BlueskyAccount(null, FakeBluesky { _, _, _ -> 200 to session("a1") })
        account.signIn("@me.bsky.social", "abcd-efgh-ijkl-mnop")
        assertEquals("me.bsky.social", account.session?.handle)
        assertEquals("https://pds.example.com", account.session?.service)
    }

    @Test fun wrongPasswordExplains() = runTest {
        val account = BlueskyAccount(null, FakeBluesky { _, _, _ -> 401 to """{"error":"AuthenticationRequired"}""" })
        try {
            account.signIn("me", "nope")
            fail()
        } catch (e: SignInException) {
            assertTrue(e.message!!.contains("don't match"))
        }
        assertNull(account.session)
    }

    @Test fun twoFactorAccountsAreToldToUseAppPasswords() = runTest {
        val account = BlueskyAccount(null, FakeBluesky { _, _, _ -> 401 to """{"error":"AuthFactorTokenRequired"}""" })
        try {
            account.signIn("me", "main-password")
            fail()
        } catch (e: SignInException) {
            assertTrue(e.message!!.contains("app password"))
        }
    }

    @Test fun timelineRefreshesAnExpiredToken() = runTest {
        val fake = FakeBluesky { method, url, auth ->
            when {
                url.endsWith("createSession") -> 200 to session("old")
                url.endsWith("refreshSession") -> 200 to session("new")
                url.contains("getTimeline") && auth == "Bearer old" -> 400 to """{"error":"ExpiredToken"}"""
                url.contains("getTimeline") && auth == "Bearer new" -> 200 to TIMELINE
                else -> 500 to "unexpected $method $url"
            }
        }
        val account = BlueskyAccount(null, fake)
        account.signIn("me", "app-pass")
        val page = account.timeline(null)
        assertEquals(1, page.posts.size)
        assertEquals("https://cdn/f.jpg", page.posts[0].fullsizeUrl)
        assertEquals("new", account.session?.accessJwt)
        assertTrue(fake.calls.any { it.startsWith("GET https://pds.example.com/xrpc/app.bsky.feed.getTimeline") })
    }

    @Test fun signOutForgetsTheSession() = runTest {
        val account = BlueskyAccount(null, FakeBluesky { _, _, _ -> 200 to session("a1") })
        account.signIn("me", "app-pass")
        account.signOut()
        assertNull(account.session)
    }
}

class HiddenFeedTest {
    private val post = edu.northwestern.lookagain.wildcatverify.model.FeedPost(
        id = "at://did:plc:abc/app.bsky.feed.post/1", authorHandle = "abc.bsky.social", authorName = "A", avatarUrl = null,
        text = "", postUrl = "https://bsky.app/profile/abc.bsky.social/post/1", thumbUrl = "t", fullsizeUrl = "f",
        imageAlt = "", aspectRatio = null, postedAt = null, imageCount = 1,
    )

    @Test fun authorDidComesFromTheUri() {
        assertEquals("did:plc:abc", post.authorDid)
    }
}
