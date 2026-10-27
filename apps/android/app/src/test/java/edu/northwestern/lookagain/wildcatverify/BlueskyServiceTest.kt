package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.data.BlueskyFeedService
import edu.northwestern.lookagain.wildcatverify.data.BlueskyService
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import edu.northwestern.lookagain.wildcatverify.data.HttpClient
import edu.northwestern.lookagain.wildcatverify.model.CheckException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.IOException

private fun stub(status: Int, body: String) = HttpClient { status to body.toByteArray() }

private const val POST_JSON = """
{"thread":{"post":{"uri":"at://did:plc:abc/app.bsky.feed.post/3k","author":{"handle":"alice.bsky.social"},
"record":{"text":"Storm over the lake\nsecond line"},
"embed":{"${'$'}type":"app.bsky.embed.images#view","images":[{"thumb":"https://cdn/t.jpg","fullsize":"https://cdn/full.jpg"}]}}}}
"""

class BlueskyLinkTest {
    @Test fun parsesPostLinks() {
        assertEquals("alice.bsky.social" to "3k", BlueskyService.parse("https://bsky.app/profile/alice.bsky.social/post/3k"))
        assertEquals("did:plc:abc" to "xyz", BlueskyService.parse("  bsky.app/profile/did:plc:abc/post/xyz?ref=1 "))
        assertEquals("a" to "b", BlueskyService.parse("https://staging.bsky.app/profile/a/post/b"))
    }

    @Test fun rejectsOtherLinks() {
        assertNull(BlueskyService.parse("https://example.com/profile/a/post/b"))
        assertNull(BlueskyService.parse("https://bsky.app/profile/alice.bsky.social"))
        assertNull(BlueskyService.parse("https://bsky.app/profile/a/feed/b"))
        assertNull(BlueskyService.parse("not a link"))
        assertNull(BlueskyService.parse("https://notbsky.app/profile/a/post/b"))
    }

    @Test fun findsLinkInSharedText() {
        assertEquals(
            "https://bsky.app/profile/a/post/b",
            BlueskyService.linkIn("Look at this (https://bsky.app/profile/a/post/b)."),
        )
        assertEquals("bsky.app/profile/a/post/b", BlueskyService.linkIn("bsky.app/profile/a/post/b"))
        assertNull(BlueskyService.linkIn("nothing to see https://example.com"))
    }

    @Test fun findsLinksRunTogetherWithText() {
        assertEquals("https://bsky.app/profile/a/post/b", BlueskyService.linkIn("look:https://bsky.app/profile/a/post/b!"))
        assertEquals("https://bsky.app/profile/a/post/b", BlueskyService.linkIn("Is this real?https://bsky.app/profile/a/post/b?"))
        assertEquals("https://staging.bsky.app/profile/a/post/b", BlueskyService.linkIn("see https://staging.bsky.app/profile/a/post/b."))
        assertNull(BlueskyService.linkIn("https://notbsky.app/profile/a/post/b"))
    }

    @Test fun titleIsFirstLineTrimmed() {
        assertEquals("Storm over the lake", CheckPipeline.title("Storm over the lake\nsecond"))
        assertEquals("Bluesky post", CheckPipeline.title(""))
        val long = "x".repeat(80)
        assertEquals("x".repeat(59) + "…", CheckPipeline.title(long))
    }
}

class BlueskyServiceTest {
    @Test fun fetchesPost() = runTest {
        val post = BlueskyService(stub(200, POST_JSON)).fetchPost("https://bsky.app/profile/alice.bsky.social/post/3k")
        assertEquals("alice.bsky.social", post.authorHandle)
        assertEquals("https://cdn/full.jpg", post.imageUrl)
        assertEquals("https://bsky.app/profile/alice.bsky.social/post/3k", post.postUrl)
    }

    @Test fun readsEveryImageInAPost() = runTest {
        val json = """{"thread":{"post":{"author":{"handle":"a"},"record":{},"embed":{"images":[{"fullsize":"https://cdn/1.jpg"},{"fullsize":"https://cdn/2.jpg"},{"fullsize":"https://cdn/3.jpg"}]}}}}"""
        val post = BlueskyService(stub(200, json)).fetchPost("bsky.app/profile/a/post/b")
        assertEquals(listOf("https://cdn/1.jpg", "https://cdn/2.jpg", "https://cdn/3.jpg"), post.imageUrls)
    }

    @Test fun readsQuotePostMedia() = runTest {
        val json = """{"thread":{"post":{"author":{"handle":"a"},"record":{},"embed":{"media":{"images":[{"fullsize":"https://cdn/m.jpg"}]}}}}}"""
        assertEquals("https://cdn/m.jpg", BlueskyService(stub(200, json)).fetchPost("bsky.app/profile/a/post/b").imageUrl)
    }

    @Test fun invalidLink() = runTest { expect(CheckException.InvalidLink) { BlueskyService(stub(200, POST_JSON)).fetchPost("hello") } }

    @Test fun notFound() = runTest { expect(CheckException.PostNotFound) { BlueskyService(stub(400, "{}")).fetchPost("bsky.app/profile/a/post/b") } }

    @Test fun serverError() = runTest { expect(CheckException.PostNotFound) { BlueskyService(stub(500, "")).fetchPost("bsky.app/profile/a/post/b") } }

    @Test fun badJson() = runTest { expect(CheckException.PostNotFound) { BlueskyService(stub(200, "<html>")).fetchPost("bsky.app/profile/a/post/b") } }

    @Test fun deletedPost() = runTest {
        expect(CheckException.PostNotFound) { BlueskyService(stub(200, """{"thread":{"${'$'}type":"app.bsky.feed.defs#notFoundPost"}}""")).fetchPost("bsky.app/profile/a/post/b") }
    }

    @Test fun textOnlyPost() = runTest {
        val json = """{"thread":{"post":{"author":{"handle":"a"},"record":{"text":"hi"}}}}"""
        expect(CheckException.NoImage) { BlueskyService(stub(200, json)).fetchPost("bsky.app/profile/a/post/b") }
    }

    @Test fun offline() = runTest {
        expect(CheckException.Network) { BlueskyService { throw IOException("offline") }.fetchPost("bsky.app/profile/a/post/b") }
    }

    private suspend fun expect(expected: CheckException, block: suspend () -> Unit) {
        try {
            block()
            fail("Expected $expected")
        } catch (e: CheckException) {
            assertEquals(expected, e)
        }
    }
}

class BlueskyFeedServiceTest {
    private val feedJson = """
    {"cursor":"next","feed":[
      {"post":{"uri":"at://did:plc:a/app.bsky.feed.post/one","author":{"handle":"a.bsky.social","displayName":"Alice"},
        "record":{"text":"photo"},"indexedAt":"2026-10-14T12:00:15.455Z",
        "embed":{"images":[{"thumb":"https://cdn/1.jpg","alt":"a dog","aspectRatio":{"width":1200,"height":800}},{"thumb":"https://cdn/2.jpg"}]}}},
      {"post":{"uri":"at://did:plc:b/app.bsky.feed.post/two","author":{"handle":"b"},"record":{"text":"no image"}}},
      {"post":{"uri":"at://did:plc:c/app.bsky.feed.post/three","author":{"handle":"c"},"record":{},"labels":[{"val":"porn"}],
        "embed":{"images":[{"thumb":"https://cdn/3.jpg"}]}}},
      {"post":{"uri":"at://did:plc:d/app.bsky.feed.post/four","author":{"handle":"d","labels":[{"val":"!hide"}]},"record":{},
        "embed":{"images":[{"thumb":"https://cdn/4.jpg"}]}}}
    ]}
    """

    @Test fun keepsOnlyUnlabelledImagePosts() = runTest {
        val page = BlueskyFeedService(stub(200, feedJson)).fetchPage(null)
        assertEquals("next", page.cursor)
        assertEquals(1, page.posts.size)
        val post = page.posts[0]
        assertEquals("Alice", post.authorName)
        assertEquals("https://bsky.app/profile/a.bsky.social/post/one", post.postUrl)
        assertEquals(1.5, post.aspectRatio!!, 1e-9)
        assertEquals(2, post.imageCount)
        assertEquals(listOf("https://cdn/1.jpg", "https://cdn/2.jpg"), post.imageUrls)
        assertEquals("did:plc:a", post.authorDid)
        assertEquals("a dog", post.imageAlt)
        assertTrue(post.postedAt != null)
    }

    @Test fun failureIsNetworkError() = runTest {
        try {
            BlueskyFeedService(stub(503, "")).fetchPage(null)
            fail()
        } catch (e: CheckException) {
            assertEquals(CheckException.Network, e)
        }
    }
}
