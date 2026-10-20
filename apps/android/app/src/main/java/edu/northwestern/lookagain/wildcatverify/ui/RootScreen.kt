package edu.northwestern.lookagain.wildcatverify.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.filled.AccessTimeFilled
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import edu.northwestern.lookagain.wildcatverify.ui.about.AboutSheet
import edu.northwestern.lookagain.wildcatverify.ui.welcome.WaysToCheckScreen
import androidx.activity.compose.BackHandler
import edu.northwestern.lookagain.wildcatverify.ui.check.CheckScreen
import edu.northwestern.lookagain.wildcatverify.ui.feed.FeedScreen
import edu.northwestern.lookagain.wildcatverify.ui.history.HistoryScreen
import edu.northwestern.lookagain.wildcatverify.ui.learn.LearnScreen
import edu.northwestern.lookagain.wildcatverify.ui.settings.SettingsScreen
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalHapticsEnabled
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalHeatmapEnabled
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalImages
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppTab
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel

/** Filled glyphs in every state, as in the iOS tab bar; selection shows as tint and a pill. */
private val AppTab.icon: ImageVector
    get() = when (this) {
        AppTab.FEED -> Icons.Filled.LocalFireDepartment
        AppTab.LEARN -> Icons.Filled.School
        AppTab.CHECK -> Icons.Filled.VerifiedUser
        AppTab.HISTORY -> Icons.Filled.AccessTimeFilled
        AppTab.SETTINGS -> Icons.Filled.Settings
    }

/** Five tabs with Check in the middle; each tab keeps its own stack of pushed screens. */
@Composable
fun RootScreen(app: AppViewModel) {
    val haptics = LocalHapticFeedback.current
    val view = LocalView.current

    // Screen readers hear each verdict as it arrives.
    LaunchedEffect(app.check.lastResult) {
        app.check.lastResult?.let { view.announceForAccessibility("${it.verdict.label}, ${it.confidencePercentage} percent confidence") }
    }

    CompositionLocalProvider(
        LocalImages provides app.images,
        LocalHapticsEnabled provides app.settings.hapticsEnabled,
        LocalHeatmapEnabled provides app.settings.heatmapEnabled,
    ) {
        // First launch: the quickest ways to check, once. Kept under Settings → Ways to Check.
        if (app.isShowingWelcome) {
            BackHandler(onBack = app::finishWelcome)
            WaysToCheckScreen(app, onDone = app::finishWelcome, onBack = null)
            return@CompositionLocalProvider
        }

        Scaffold(
            containerColor = colors.groupedBackground,
            bottomBar = {
                FloatingTabBar(app.selectedTab, app.history.unseenCount) { tab ->
                    if (tab == app.selectedTab) return@FloatingTabBar
                    if (app.settings.hapticsEnabled) haptics.performHapticFeedback(HapticFeedbackType.SegmentTick)
                    app.selectedTab = tab
                }
            },
        ) { padding ->
            Box(Modifier.fillMaxSize().padding(padding).consumeWindowInsets(padding)) {
                // Tab switches slide in from the side you moved toward, so switching keeps a sense of place.
                AnimatedContent(
                    app.selectedTab,
                    transitionSpec = {
                        val direction = if (targetState.ordinal > initialState.ordinal) 1 else -1
                        (slideInHorizontally(tween(320)) { direction * it / 14 } + fadeIn(tween(320))) togetherWith fadeOut(tween(120))
                    },
                    label = "tabs",
                ) { tab ->
                    when (tab) {
                        AppTab.FEED -> FeedScreen(app)
                        AppTab.LEARN -> LearnScreen(app)
                        AppTab.CHECK -> CheckScreen(app)
                        AppTab.HISTORY -> HistoryScreen(app)
                        AppTab.SETTINGS -> SettingsScreen(app)
                    }
                }
            }
        }

        if (app.isShowingAbout) {
            AboutSheet(onDismiss = { app.isShowingAbout = false })
        }
    }
}

/** The iOS 26 tab bar: a floating capsule, with a grey pill behind the selected tab. */
@Composable
private fun FloatingTabBar(selected: AppTab, unseen: Int, onSelect: (AppTab) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(horizontal = 20.dp)
            .padding(bottom = 8.dp)
            .height(64.dp)
            .shadow(16.dp, CircleShape, ambientColor = Color.Black.copy(alpha = 0.18f), spotColor = Color.Black.copy(alpha = 0.18f))
            .clip(CircleShape)
            .background(if (colors.dark) Color(0xFF1C1C1E) else Color.White.copy(alpha = 0.97f))
            .border(0.5.dp, colors.separator.copy(alpha = colors.separator.alpha * 0.4f), CircleShape)
            .padding(4.dp)
            .selectableGroup(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        AppTab.entries.forEach { tab ->
            val isSelected = tab == selected
            val tint = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
            Column(
                Modifier
                    .weight(if (tab == AppTab.HISTORY) 1.25f else 1f)
                    .fillMaxHeight()
                    .clip(CircleShape)
                    .background(if (isSelected) colors.pill else Color.Transparent)
                    .selectable(isSelected, role = Role.Tab, onClick = { onSelect(tab) }),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                BadgedBox(badge = {
                    if (tab == AppTab.HISTORY && unseen > 0) {
                        Badge(Modifier.semantics { contentDescription = "$unseen new" }) { Text("$unseen") }
                    }
                }) {
                    Icon(tab.icon, contentDescription = null, tint = tint, modifier = Modifier.size(26.dp))
                }
                Text(tab.title, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Medium, color = tint, maxLines = 1)
            }
        }
    }
}
