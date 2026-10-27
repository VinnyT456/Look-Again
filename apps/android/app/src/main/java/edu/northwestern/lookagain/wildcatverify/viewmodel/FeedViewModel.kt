package edu.northwestern.lookagain.wildcatverify.viewmodel

import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import edu.northwestern.lookagain.wildcatverify.data.BlueskyAccount
import edu.northwestern.lookagain.wildcatverify.data.BlueskyFeedService
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import edu.northwestern.lookagain.wildcatverify.data.SettingsStore
import edu.northwestern.lookagain.wildcatverify.model.FeedPage
import edu.northwestern.lookagain.wildcatverify.model.FeedPost
import edu.northwestern.lookagain.wildcatverify.model.ClassificationResult
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.model.userMessage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Which feed the Feed tab shows. */
enum class FeedSource(val title: String) {
    FOLLOWING("Following"),
    WHATS_HOT("What's Hot"),
}

/**
 * The Feed tab: pages through image posts from the signed-in user's Following
 * timeline or Bluesky's public What's Hot feed, and labels them as they scroll by.
 */
class FeedViewModel(
    private val publicFeed: BlueskyFeedService,
    private val account: BlueskyAccount,
    pipeline: CheckPipeline,
    private val scope: CoroutineScope,
    /** Where hidden accounts are kept; null keeps them in memory (tests). */
    private val settings: SettingsStore? = null,
) {
    sealed interface Status {
        data object Idle : Status
        data object Loading : Status
        data object Loaded : Status
        data class Failed(val message: String) : Status
    }

    var path by mutableStateOf<List<FeedPost>>(emptyList())
    var posts by mutableStateOf<List<FeedPost>>(emptyList())
        private set
    var status by mutableStateOf<Status>(Status.Idle)
        private set
    var isRefreshing by mutableStateOf(false)
        private set
    var isLoadingMore by mutableStateOf(false)
        private set
    var hasMore by mutableStateOf(true)
        private set

    private var chosenSource by mutableStateOf<FeedSource?>(null)
    private var memoryHiddenAccounts by mutableStateOf<Map<String, String>>(emptyMap())
    /** Posts hidden one at a time; forgotten when the app closes. */
    private var hiddenPostIds by mutableStateOf<Set<String>>(emptySet())

    private var hiddenAccounts: Map<String, String>
        get() = settings?.hiddenAccounts ?: memoryHiddenAccounts
        set(value) {
            if (settings != null) settings.hiddenAccounts = value else memoryHiddenAccounts = value
        }

    /** What the list shows: every loaded post except hidden ones. */
    val visiblePosts: List<FeedPost>
        get() = posts.filter { it.id !in hiddenPostIds && it.authorDid !in hiddenAccounts }

    /** Feed → ••• → Hide This Post. */
    fun hidePost(post: FeedPost) {
        hiddenPostIds = hiddenPostIds + post.id
    }

    /** Feed → ••• → Hide Posts from @handle. Undo in Settings → Hidden Accounts. */
    fun hideAccount(post: FeedPost) {
        hiddenAccounts = hiddenAccounts + (post.authorDid to post.authorHandle)
    }

    /** Following once signed in (unless the user picked What's Hot); What's Hot otherwise. */
    val source: FeedSource
        get() = when {
            !account.isSignedIn -> FeedSource.WHATS_HOT
            else -> chosenSource ?: FeedSource.FOLLOWING
        }

    val isSignedIn: Boolean get() = account.isSignedIn

    /** Checks posts on its own as they appear; null turns that off (tests). */
    var autoCheck: FeedAutoChecker? = null

    fun verdict(post: FeedPost): FeedVerdict? = autoCheck?.verdicts?.get(post.id)

    private var cursor: String? = null
    private var loadedSource: FeedSource? = null
    private var loadJob: Job? = null
    private var moreJob: Job? = null

    /** The source [posts], [cursor] and [status] belong to; [source] can move ahead of it when sign-in changes. */
    private var shownSource = FeedSource.WHATS_HOT
    /** Each source's posts and place, kept while the other is shown. */
    private val saved = mutableMapOf<FeedSource, Snapshot>()

    private data class Snapshot(
        val posts: List<FeedPost>,
        val cursor: String?,
        val hasMore: Boolean,
        val status: Status,
        val loadedSource: FeedSource?,
    )

    /** Each source's scroll position, kept across source switches, pushed posts and tab switches. */
    private val listStates = mutableStateMapOf<FeedSource, LazyListState>().apply {
        FeedSource.entries.forEach { put(it, LazyListState()) }
    }

    fun listState(source: FeedSource): LazyListState = listStates.getValue(source)

    private suspend fun fetch(from: FeedSource, cursor: String?): FeedPage = when (from) {
        FeedSource.FOLLOWING -> account.timeline(cursor)
        FeedSource.WHATS_HOT -> publicFeed.fetchPage(cursor)
    }

    /** Shows another source, picking up where it was left. */
    fun select(new: FeedSource) {
        if (new == source || (new == FeedSource.FOLLOWING && !account.isSignedIn)) return
        chosenSource = new
        path = emptyList()
        show(new)
        loadIfNeeded()
    }

    /** Saves what's on screen under its source and restores [new]'s posts and place. */
    private fun show(new: FeedSource) {
        if (new == shownSource) return
        loadJob?.cancel()
        moreJob?.cancel()
        // A load cut short here starts again when this source is shown next.
        saved[shownSource] = Snapshot(posts, cursor, hasMore, if (status == Status.Loading) Status.Idle else status, loadedSource)
        shownSource = new
        val snapshot = saved[new]
        posts = snapshot?.posts ?: emptyList()
        cursor = snapshot?.cursor
        hasMore = snapshot?.hasMore ?: true
        status = snapshot?.status ?: Status.Idle
        loadedSource = snapshot?.loadedSource
    }

    /** Catches up when sign-in changed which source applies. */
    private fun syncSource() {
        if (shownSource != source) show(source)
    }

    /** First load, or pull to refresh. Keeps the old posts on screen if it fails. */
    suspend fun refresh() {
        val requested = shownSource
        if (posts.isEmpty() || loadedSource != requested) status = Status.Loading
        isRefreshing = true
        try {
            val page = fetch(requested, null)
            // The user switched sources while this loaded.
            if (requested != shownSource) return
            posts = page.posts.distinctBy { it.id }
            cursor = page.cursor
            hasMore = page.cursor != null
            loadedSource = requested
            status = Status.Loaded
        } catch (e: CancellationException) {
            if (requested == shownSource && posts.isEmpty()) status = Status.Idle
            throw e
        } catch (e: Throwable) {
            if (requested == FeedSource.FOLLOWING && !account.isSignedIn) {
                // The sign-in expired while loading; show What's Hot instead.
                forgetFollowing()
                scope.launch(Dispatchers.Main) { loadIfNeeded() }
                return
            }
            if (requested != shownSource) return
            if (posts.isEmpty() || loadedSource != requested) {
                posts = emptyList()
                status = Status.Failed(e.userMessage("Couldn't load the feed."))
            }
        } finally {
            isRefreshing = false
        }
    }

    fun refreshAsync() {
        // Before launching: switching sources cancels the load in flight.
        syncSource()
        loadJob?.cancel()
        loadJob = scope.launch { refresh() }
    }

    /** Loads on first show, and again if sign-in changed which feed applies. */
    fun loadIfNeeded() {
        syncSource()
        if (status == Status.Idle || (status == Status.Loaded && loadedSource != source)) refreshAsync()
    }

    /** Called as the last post scrolls into view. */
    fun loadMore(after: FeedPost) {
        if (after.id != visiblePosts.lastOrNull()?.id || !hasMore || isLoadingMore) return
        val start = cursor ?: return
        val requested = shownSource
        isLoadingMore = true
        moreJob = scope.launch {
            var next: String? = start
            try {
                // A page can contain no image posts; skip ahead a few pages so the
                // list doesn't stall with nothing new to trigger the next load.
                repeat(3) {
                    val pageCursor = next ?: return@repeat
                    val page = fetch(requested, pageCursor)
                    if (requested != shownSource) return@launch
                    val before = posts.size
                    posts = (posts + page.posts).distinctBy { it.id }
                    next = page.cursor
                    if (posts.size > before) {
                        cursor = next
                        hasMore = next != null
                        return@launch
                    }
                }
                cursor = next
                hasMore = next != null
            } catch (e: CancellationException) {
                throw e
            } catch (e: Throwable) {
                // Keep what's shown; scrolling back down will try again.
            } finally {
                isLoadingMore = false
            }
        }
    }

    fun open(post: FeedPost) {
        path = path + post
    }

    /** After sign-in: open on the user's own feed, loaded fresh. */
    fun showFollowing() {
        chosenSource = null
        path = emptyList()
        if (shownSource == FeedSource.FOLLOWING) {
            // Already showing an older Following list; start it over.
            show(FeedSource.WHATS_HOT)
        }
        saved.remove(FeedSource.FOLLOWING)
        listStates[FeedSource.FOLLOWING] = LazyListState()
        show(FeedSource.FOLLOWING)
        loadIfNeeded()
    }

    /** After sign-out: forget the timeline and go back to What's Hot where it was left. */
    fun forgetFollowing() {
        chosenSource = null
        if (shownSource == FeedSource.FOLLOWING) {
            path = emptyList()
            show(FeedSource.WHATS_HOT)
        }
        saved.remove(FeedSource.FOLLOWING)
        listStates[FeedSource.FOLLOWING] = LazyListState()
    }
}

/** A quick, automatic check of a Feed post's first image, shown under the post. */
sealed interface FeedVerdict {
    data object Checking : FeedVerdict
    data class Done(val verdict: VerdictType, val confidence: Int, val isDemo: Boolean) : FeedVerdict
    data object Failed : FeedVerdict
}

/**
 * Checks Feed posts on its own as they scroll into view, one at a time, so a
 * verdict is there before anyone taps. Uses each post's thumbnail; opening the
 * post runs the full check (every image, highlight, My Checks). Results stay
 * in memory.
 */
class FeedAutoChecker(
    private val classify: suspend (String) -> Pair<ClassificationResult, Boolean>,
    private val scope: CoroutineScope,
    /** Whether checks may run right now (setting on, not Battery Saver, not a metered network). */
    private val isAllowed: () -> Boolean,
) {
    /** Post id → verdict. Read by the feed rows. */
    val verdicts = mutableStateMapOf<String, FeedVerdict>()

    private val queue = ArrayDeque<FeedPost>()
    private var worker: Job? = null

    /** A post scrolled into view. */
    fun request(post: FeedPost) {
        if (!isAllowed() || post.id in verdicts || queue.any { it.id == post.id }) return
        queue.addLast(post)
        startIfIdle()
    }

    /** A post scrolled away before its turn. */
    fun cancel(post: FeedPost) {
        queue.removeAll { it.id == post.id }
    }

    private fun startIfIdle() {
        if (worker?.isActive == true) return
        worker = scope.launch {
            while (true) {
                if (!isAllowed()) {
                    queue.clear()
                    break
                }
                val post = queue.removeFirstOrNull() ?: break
                verdicts[post.id] = FeedVerdict.Checking
                verdicts[post.id] = try {
                    val (result, isDemo) = classify(post.thumbUrl)
                    FeedVerdict.Done(result.verdict, CheckPipeline.displayConfidence(result.confidence), isDemo)
                } catch (e: CancellationException) {
                    verdicts.remove(post.id)
                    throw e
                } catch (e: Throwable) {
                    FeedVerdict.Failed
                }
                // A breather between checks keeps scrolling smooth and the phone cool.
                delay(PAUSE_MS)
            }
        }
    }

    private companion object {
        const val PAUSE_MS = 150L
    }
}
