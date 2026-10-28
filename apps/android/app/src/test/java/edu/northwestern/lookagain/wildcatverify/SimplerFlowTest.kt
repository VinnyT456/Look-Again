package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.data.BlueskyService
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import edu.northwestern.lookagain.wildcatverify.data.ClipboardProbe
import edu.northwestern.lookagain.wildcatverify.data.HistoryStore
import edu.northwestern.lookagain.wildcatverify.data.ImageRepository
import edu.northwestern.lookagain.wildcatverify.data.ImageClassifier
import edu.northwestern.lookagain.wildcatverify.model.ClassificationResult
import edu.northwestern.lookagain.wildcatverify.model.FeedPost
import edu.northwestern.lookagain.wildcatverify.model.SampleData
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.viewmodel.CheckViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.FeedAutoChecker
import edu.northwestern.lookagain.wildcatverify.viewmodel.FeedVerdict
import edu.northwestern.lookagain.wildcatverify.viewmodel.HistoryViewModel
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** A clipboard the test controls. Nothing here reads a real clipboard. */
private class FakeClipboard {
    var token = 1L
    var hasLink = true
    var text: String? = "https://bsky.app/profile/a.bsky.social/post/3k"
    val probe = ClipboardProbe({ token }, { hasLink }, { text })
}

@OptIn(ExperimentalCoroutinesApi::class)
class CopiedLinkOfferTest {
    private val hanging = HttpHang()

    /** Bluesky requests never finish, so a started check stays "analyzing". */
    private class HttpHang : edu.northwestern.lookagain.wildcatverify.data.HttpClient {
        override suspend fun get(url: String): Pair<Int, ByteArray> = CompletableDeferred<Pair<Int, ByteArray>>().await()
    }

    private fun TestScope.model(clipboard: FakeClipboard): CheckViewModel {
        val images = ImageRepository()
        val pipeline = CheckPipeline(BlueskyService(hanging), { error("not classifying") }, images)
        return CheckViewModel(HistoryStore(images), pipeline, backgroundScope, clipboard.probe)
    }

    @Test fun aCopiedLinkIsOfferedOnce() = runTest {
        val clipboard = FakeClipboard()
        val model = model(clipboard)
        model.refreshCopiedLinkOffer()
        assertTrue(model.offersCopiedLink)

        model.dismissCopiedLinkOffer()
        model.refreshCopiedLinkOffer()
        assertFalse("Dismissed until something new is copied", model.offersCopiedLink)

        clipboard.token++
        model.refreshCopiedLinkOffer()
        assertTrue(model.offersCopiedLink)
    }

    @Test fun nothingLinkLikeMeansNoOffer() = runTest {
        val clipboard = FakeClipboard().apply { hasLink = false }
        val model = model(clipboard)
        model.refreshCopiedLinkOffer()
        assertFalse(model.offersCopiedLink)
    }

    @Test fun pastingABlueskyLinkChecksStraightAway() = runTest {
        val model = model(FakeClipboard())
        model.checkPasted("look https://bsky.app/profile/a.bsky.social/post/3k")
        assertEquals(CheckViewModel.Phase.ANALYZING, model.phase)
        assertEquals("https://bsky.app/profile/a.bsky.social/post/3k", model.inputUrl)
        model.cancelAnalysis()
    }

    @Test fun pastingSomethingElseFromTheOfferExplains() = runTest {
        val clipboard = FakeClipboard().apply { text = "https://example.com/cat" }
        val model = model(clipboard)
        model.pasteCopiedLink()
        assertEquals(CheckViewModel.Phase.INPUT, model.phase)
        assertTrue(model.isShowingError)
        assertTrue(model.errorMessage.contains("isn't a Bluesky post"))
    }

    @Test fun pastingSomethingElseInTheFieldJustFillsIt() = runTest {
        val model = model(FakeClipboard())
        model.checkPasted("not a link")
        assertEquals("not a link", model.inputUrl)
        assertFalse(model.isShowingError)
    }
}

@OptIn(ExperimentalCoroutinesApi::class)
class FeedAutoCheckTest {
    private fun post(id: String) = FeedPost(
        id = "at://did:plc:a/app.bsky.feed.post/$id", authorHandle = "a", authorName = "A", avatarUrl = null, text = "",
        postUrl = "https://bsky.app/profile/a/post/$id", thumbUrl = "thumb-$id", fullsizeUrl = "full-$id",
        imageAlt = "", aspectRatio = null, postedAt = null, imageCount = 1,
    )

    @Test fun postsGetAVerdictOneAtATime() = runTest(StandardTestDispatcher()) {
        val asked = mutableListOf<String>()
        val checker = FeedAutoChecker({ url ->
            asked += url
            ClassificationResult(VerdictType.AI, 0.88) to false
        }, this, isAllowed = { true })
        val first = post("1")
        checker.request(first)
        checker.request(post("2"))
        checker.request(first)
        advanceUntilIdle()
        assertEquals(listOf("thumb-1", "thumb-2"), asked)
        assertEquals(FeedVerdict.Done(VerdictType.AI, 88, isDemo = false), checker.verdicts[first.id])
    }

    @Test fun nothingRunsWhenNotAllowed() = runTest(StandardTestDispatcher()) {
        val checker = FeedAutoChecker({ error("should not run") }, this, isAllowed = { false })
        checker.request(post("1"))
        advanceUntilIdle()
        assertTrue("Off, Battery Saver or Data Saver", checker.verdicts.isEmpty())
    }

    @Test fun unreachableImagesFailQuietly() = runTest(StandardTestDispatcher()) {
        val checker = FeedAutoChecker({ throw java.io.IOException("offline") }, this, isAllowed = { true })
        checker.request(post("x"))
        advanceUntilIdle()
        assertEquals(FeedVerdict.Failed, checker.verdicts[post("x").id])
    }

    @Test fun postsScrolledAwayAreSkipped() = runTest(StandardTestDispatcher()) {
        val asked = mutableListOf<String>()
        val checker = FeedAutoChecker({ url -> asked += url; ClassificationResult(VerdictType.REAL, 0.9) to false }, this, isAllowed = { true })
        checker.request(post("1"))
        checker.request(post("2"))
        checker.cancel(post("2"))
        advanceUntilIdle()
        assertEquals(listOf("thumb-1"), asked)
    }

    @Test fun confidenceNeverReadsAsCertain() {
        assertEquals(99, CheckPipeline.displayConfidence(0.999))
        assertEquals(0, CheckPipeline.displayConfidence(-1.0))
    }
}

class HistorySearchTest {
    @Test fun searchIgnoresCaseAndAccents() {
        val store = HistoryStore(ImageRepository())
        store.record(SampleData.monorail.copy(id = "cafe", title = "Café on the lakefront"))
        store.record(SampleData.monorail.copy(id = "other", title = "Storm over the lake"))
        val history = HistoryViewModel(store)

        history.searchQuery = "CAFE"
        assertEquals(listOf("cafe"), history.visibleCases.map { it.id })
        history.searchQuery = "café"
        assertEquals(listOf("cafe"), history.visibleCases.map { it.id })
    }
}
