package edu.northwestern.lookagain.wildcatverify.ui.feed

import android.text.format.DateUtils
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.outlined.MailOutline
import androidx.compose.material.icons.outlined.PersonOff
import androidx.compose.material.icons.outlined.Report
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.IconButton
import edu.northwestern.lookagain.wildcatverify.model.AppLinks
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Login
import androidx.compose.material.icons.outlined.ImageNotSupported
import androidx.compose.material.icons.outlined.SearchOff
import androidx.compose.material.icons.outlined.VerifiedUser
import androidx.compose.material.icons.outlined.WifiOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.ui.account.FeedSignInCard
import edu.northwestern.lookagain.wildcatverify.model.FeedPost
import edu.northwestern.lookagain.wildcatverify.ui.results.AnalyzingView
import edu.northwestern.lookagain.wildcatverify.ui.results.ResultsScreen
import edu.northwestern.lookagain.wildcatverify.ui.shared.BrandTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.ContentUnavailable
import edu.northwestern.lookagain.wildcatverify.ui.shared.IosSegmentedControl
import edu.northwestern.lookagain.wildcatverify.ui.shared.LabelRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.NavStack
import edu.northwestern.lookagain.wildcatverify.ui.shared.PrimaryButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.RemoteImage
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.shared.SectionGutter
import edu.northwestern.lookagain.wildcatverify.ui.shared.SectionHeader
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.FeedVerdict
import edu.northwestern.lookagain.wildcatverify.ui.shared.VerdictBadge
import androidx.compose.ui.semantics.clearAndSetSemantics
import edu.northwestern.lookagain.wildcatverify.viewmodel.FeedSource
import edu.northwestern.lookagain.wildcatverify.viewmodel.FeedViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.ShareInput
import edu.northwestern.lookagain.wildcatverify.viewmodel.ShareViewModel
import kotlinx.coroutines.launch

/** Image posts from Bluesky, each labelled Real or AI as it scrolls into view. Tap one for the full result. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FeedScreen(app: AppViewModel) {
    val viewModel = app.feed
    val top = viewModel.path.lastOrNull()
    BackHandler(enabled = top != null) { viewModel.path = viewModel.path.dropLast(1) }
    LaunchedEffect(viewModel.source) { viewModel.loadIfNeeded() }

    NavStack(viewModel.path, screen = { post ->
        FeedCheckScreen(app, post, onBack = { viewModel.path = viewModel.path.dropLast(1) })
    }, root = {
        val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior()
        Scaffold(
            modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
            containerColor = colors.groupedBackground,
            topBar = { BrandTopBar("Feed", app::showAbout, scrollBehavior) },
        ) { padding ->
            Column(Modifier.padding(padding).fillMaxSize()) {
                if (viewModel.isSignedIn) {
                    IosSegmentedControl(
                        FeedSource.entries,
                        viewModel.source,
                        label = { it.title },
                        onSelect = viewModel::select,
                        modifier = Modifier.widthIn(max = 720.dp).padding(horizontal = SectionGutter, vertical = 4.dp),
                        contentDescription = "Feed",
                    )
                }
                Box(Modifier.fillMaxSize()) {
                    when (val status = viewModel.status) {
                        is FeedViewModel.Status.Failed -> ContentUnavailable(
                            "Couldn't Load the Feed",
                            Icons.Outlined.WifiOff,
                            status.message,
                            action = "Try Again" to viewModel::refreshAsync,
                        )
                        else -> if (viewModel.posts.isEmpty() && status != FeedViewModel.Status.Loaded) {
                            Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
                                CircularProgressIndicator()
                                Text("Loading posts…", color = colors.secondaryText, modifier = Modifier.padding(top = 12.dp))
                            }
                        } else {
                            FeedList(app, viewModel)
                        }
                    }
                }
            }
        }
    })
}

/** The scrolling list of feed posts, with pull to refresh, endless paging and labels. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FeedList(app: AppViewModel, viewModel: FeedViewModel) {
    // Kept by the view model so each source's place survives switching sources, opening a post and changing tabs.
    val listState = viewModel.listState(viewModel.source)
    // Posts are checked as they scroll into view, top to bottom; ones that scroll away before their turn are skipped.
    LaunchedEffect(listState, viewModel.visiblePosts, app.settings.autoCheckFeed, app.autoCheckPausedReason) {
        var onScreen = emptyList<FeedPost>()
        snapshotFlow { listState.layoutInfo.visibleItemsInfo.mapNotNull { it.key as? String } }
            .collect { keys ->
                val byId = viewModel.visiblePosts.associateBy { it.id }
                val visible = keys.mapNotNull(byId::get)
                (onScreen - visible.toSet()).forEach { viewModel.autoCheck?.cancel(it) }
                visible.forEach { viewModel.autoCheck?.request(it) }
                onScreen = visible
            }
    }

    PullToRefreshBox(isRefreshing = viewModel.isRefreshing, onRefresh = viewModel::refreshAsync) {
        LazyColumn(Modifier.fillMaxSize(), state = listState, horizontalAlignment = Alignment.CenterHorizontally) {
            if (viewModel.source == FeedSource.WHATS_HOT && !viewModel.isSignedIn && !app.settings.feedSignInDismissed) {
                item(key = "sign-in") {
                    FeedSignInCard(app, onDismiss = { app.settings.feedSignInDismissed = true })
                }
            }
            if (viewModel.visiblePosts.isNotEmpty()) {
                item(key = "header") {
                    Box(Modifier.widthIn(max = 720.dp).fillMaxWidth().padding(horizontal = SectionGutter).padding(top = 12.dp)) {
                        SectionHeader(if (viewModel.source == FeedSource.FOLLOWING) "Posts you follow" else "Trending on Bluesky")
                    }
                }
            }
            app.autoCheckPausedReason?.let { reason ->
                item(key = "paused") {
                    Text(
                        "Automatic checks are paused because $reason. Tap a post to check it.",
                        style = MaterialTheme.typography.bodySmall,
                        color = colors.secondaryText,
                        modifier = Modifier.widthIn(max = 720.dp).padding(start = 32.dp, end = 32.dp, top = 12.dp),
                    )
                }
            }
            if (viewModel.visiblePosts.isEmpty()) {
                item(key = "empty") {
                    ContentUnavailable("No Image Posts Right Now", Icons.Outlined.ImageNotSupported, "Pull down to refresh.", Modifier.padding(top = 48.dp))
                }
            }
            items(viewModel.visiblePosts, key = { it.id }) { post ->
                LaunchedEffect(post.id) { viewModel.loadMore(post) }
                Box(Modifier.animateItem()) {
                    FeedPostRow(
                        post,
                        verdict = viewModel.verdict(post),
                        onClick = { viewModel.open(post) },
                    )
                    FeedPostMenu(post, viewModel, Modifier.align(Alignment.TopEnd).padding(end = SectionGutter + 4.dp, top = 10.dp))
                }
            }
            if (viewModel.isLoadingMore) {
                item(key = "more") { CircularProgressIndicator(Modifier.padding(16.dp).size(28.dp)) }
            }
            item(key = "footer") {
                Text(
                    when (viewModel.source) {
                        FeedSource.FOLLOWING -> "Image posts from people you follow."
                        FeedSource.WHATS_HOT -> "Image posts from Bluesky's public What's Hot feed."
                    } + " Posts carrying content labels are hidden. Posts are checked on this device as they appear; tap one for every image and the details. Use ••• on a post to hide it, hide that account, or report it.",
                    style = MaterialTheme.typography.bodySmall,
                    color = colors.secondaryText,
                    modifier = Modifier.widthIn(max = 720.dp).padding(horizontal = 32.dp, vertical = 12.dp),
                )
            }
        }
    }
}

/**
 * The ••• on each feed post: hide it, hide its author, or report it. Feeds of
 * other people's posts need all three.
 */
@Composable
private fun FeedPostMenu(post: FeedPost, viewModel: FeedViewModel, modifier: Modifier = Modifier) {
    var open by remember { mutableStateOf(false) }
    val uriHandler = LocalUriHandler.current
    Box(modifier) {
        IconButton(onClick = { open = true }) {
            Icon(Icons.Filled.MoreHoriz, contentDescription = "Post options", tint = colors.secondaryText)
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            DropdownMenuItem(
                text = { Text("Hide This Post") },
                leadingIcon = { Icon(Icons.Outlined.VisibilityOff, contentDescription = null) },
                onClick = { open = false; viewModel.hidePost(post) },
            )
            DropdownMenuItem(
                text = { Text("Hide Posts from @${post.authorHandle}", maxLines = 1, overflow = TextOverflow.MiddleEllipsis) },
                leadingIcon = { Icon(Icons.Outlined.PersonOff, contentDescription = null) },
                onClick = { open = false; viewModel.hideAccount(post) },
            )
            HorizontalDivider()
            DropdownMenuItem(
                text = { Text("Report on Bluesky") },
                leadingIcon = { Icon(Icons.Outlined.Report, contentDescription = null) },
                onClick = { open = false; runCatching { uriHandler.openUri(post.postUrl) } },
            )
            DropdownMenuItem(
                text = { Text("Report to Look Again") },
                leadingIcon = { Icon(Icons.Outlined.MailOutline, contentDescription = null) },
                onClick = { open = false; runCatching { uriHandler.openUri(AppLinks.SUPPORT) } },
            )
        }
    }
}

/**
 * Under each Feed post: the automatic verdict once it's in, "Checking…"
 * while it runs, or the plain tap-to-check prompt.
 */
@Composable
private fun FeedVerdictLine(verdict: FeedVerdict?) {
    when (verdict) {
        is FeedVerdict.Done -> Row(
            Modifier.clearAndSetSemantics {
                contentDescription = "${verdict.verdict.label}, ${verdict.confidence} percent${if (verdict.isDemo) ", demo result" else ""}. Tap for details."
            },
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            VerdictBadge(verdict.verdict)
            Text(
                "${verdict.confidence}%${if (verdict.isDemo) " · demo" else ""}",
                style = MaterialTheme.typography.bodyMedium,
                color = colors.secondaryText,
                modifier = Modifier.weight(1f),
            )
            Text("Details", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        }
        FeedVerdict.Checking -> Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
            Text("Checking…", style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
        }
        FeedVerdict.Failed, null -> Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.VerifiedUser, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
            Text("Check this post", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        }
    }
}

/** One feed post: who posted it, when, its text, the image with its label, and a check cue. */
@Composable
private fun FeedPostRow(post: FeedPost, verdict: FeedVerdict?, onClick: () -> Unit) {
    // Previews are at most square so tall images don't fill the screen; the check itself always uses the full image.
    val ratio = (post.aspectRatio ?: (4.0 / 3.0)).coerceIn(1.0, 2.0).toFloat()
    val relative = remember(post.postedAt) {
        post.postedAt?.let {
            val now = System.currentTimeMillis()
            // Under a minute reads "now", like iOS, rather than "0 minutes ago".
            if (now - it < DateUtils.MINUTE_IN_MILLIS) "now"
            else DateUtils.getRelativeTimeSpanString(it, now, DateUtils.MINUTE_IN_MILLIS).toString()
        }
    }
    Column(
        Modifier
            .widthIn(max = 720.dp)
            .fillMaxWidth()
            .padding(horizontal = SectionGutter, vertical = 6.dp)
            .clip(RoundedCornerShape(Metrics.sectionRadius))
            .background(colors.card)
            .clickable(
                onClickLabel = if (post.imageCount > 1) "Check all ${post.imageCount} images in this post" else "Check the image in this post",
                onClick = onClick,
            )
            .padding(14.dp)
            .semantics(mergeDescendants = true) { },
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(end = 40.dp)) {
            RemoteImage(post.avatarUrl, 36.dp, Modifier.size(36.dp).clip(CircleShape))
            Column {
                Text(post.authorName, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    listOfNotNull("@${post.authorHandle}", relative).joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                    color = colors.secondaryText,
                    maxLines = 1,
                    overflow = TextOverflow.MiddleEllipsis,
                )
            }
        }
        if (post.text.isNotEmpty()) {
            Text(post.text, style = MaterialTheme.typography.bodyLarge, maxLines = 4, overflow = TextOverflow.Ellipsis)
        }
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(ratio)
                .clip(RoundedCornerShape(Metrics.photoRadius))
                .semantics { contentDescription = post.imageAlt.ifEmpty { "Post image" } },
        ) {
            RemoteImage(post.thumbUrl, 400.dp, Modifier.fillMaxSize())
            if (post.imageCount > 1) {
                Text(
                    "1 of ${post.imageCount}",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(8.dp)
                        .clip(CircleShape)
                        .background(Color.Black.copy(alpha = 0.6f))
                        .padding(horizontal = 8.dp, vertical = 3.dp),
                )
            }
        }
        FeedVerdictLine(verdict)
    }
}

/** Checks one feed post when opened (every image), then shows its result. The result is added to My Checks. */
@Composable
private fun FeedCheckScreen(app: AppViewModel, post: FeedPost, onBack: () -> Unit) {
    val viewModel = remember(post.id) { app.feedCheck() }
    LaunchedEffect(post.id) { viewModel.check(ShareInput.Link(post.postUrl)) }
    when (val phase = viewModel.phase) {
        is ShareViewModel.Phase.Result -> ResultsScreen(phase.item, onBack = onBack, onCheckAnother = null)
        is ShareViewModel.Phase.Failed -> Scaffold(
            containerColor = colors.groupedBackground,
            // No title here, as on iOS: "Checking" is only shown while the check runs.
            topBar = { PushedTopBar("", onBack) },
        ) { padding ->
            val scope = rememberCoroutineScope()
            ContentUnavailable(
                "Couldn't Check This Post",
                Icons.Outlined.SearchOff,
                phase.message,
                Modifier.padding(padding),
                action = "Try Again" to { scope.launch { viewModel.check(ShareInput.Link(post.postUrl)) }; Unit },
            )
        }
        else -> Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Checking", onBack) }) { padding ->
            AnalyzingView(viewModel.analyzingImage, onCancel = onBack, modifier = Modifier.padding(padding))
        }
    }
}

