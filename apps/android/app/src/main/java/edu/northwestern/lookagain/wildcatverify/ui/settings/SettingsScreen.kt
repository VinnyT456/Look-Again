package edu.northwestern.lookagain.wildcatverify.ui.settings

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AppShortcut
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Crop
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.LocalFireDepartment
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.MailOutline
import androidx.compose.material.icons.outlined.MenuBook
import androidx.compose.material.icons.outlined.PanTool
import androidx.compose.material.icons.outlined.Restore
import androidx.compose.material.icons.automirrored.outlined.Login
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.AutoFixHigh
import androidx.compose.material.icons.outlined.Bolt
import edu.northwestern.lookagain.wildcatverify.ui.welcome.WaysToCheckScreen
import androidx.compose.material.icons.outlined.Tab
import androidx.compose.material.icons.outlined.Vibration
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.BuildConfig
import edu.northwestern.lookagain.wildcatverify.data.TfliteImageClassifier
import edu.northwestern.lookagain.wildcatverify.model.AppLinks
import edu.northwestern.lookagain.wildcatverify.ui.about.CreditsScreen
import edu.northwestern.lookagain.wildcatverify.ui.about.PrivacyPolicyScreen
import edu.northwestern.lookagain.wildcatverify.ui.about.TermsScreen
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.PersonOff
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.foundation.layout.size
import edu.northwestern.lookagain.wildcatverify.ui.shared.ListRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.BrandTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.BulletRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LabelRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LinkRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.NavStack
import edu.northwestern.lookagain.wildcatverify.ui.shared.ListRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.IconRowInset
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.shared.ToggleRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.ValueRow
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppTab
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.SettingsRoute

/** Preferences, what the detector can and can't do, privacy, and data controls. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(app: AppViewModel) {
    val top = app.settingsPath.lastOrNull()
    val pop = { app.settingsPath = app.settingsPath.dropLast(1) }
    val push = { route: SettingsRoute -> app.settingsPath = app.settingsPath + route }
    BackHandler(enabled = top != null, onBack = pop)

    NavStack(app.settingsPath, root = { SettingsRoot(app, push) }, screen = { route ->
        when (route) {
            SettingsRoute.AUTO_LABEL -> AutoLabelScreen(app, onBack = pop)
            SettingsRoute.SCREEN_LABELS -> ScreenLabelScreen(app, onBack = pop)
            SettingsRoute.PRIVACY_POLICY -> PrivacyPolicyScreen(onBack = pop)
            SettingsRoute.CREDITS -> CreditsScreen(onBack = pop)
            SettingsRoute.TERMS -> TermsScreen(onBack = pop)
            SettingsRoute.HIDDEN_ACCOUNTS -> HiddenAccountsScreen(app, onBack = pop)
            SettingsRoute.WAYS_TO_CHECK -> WaysToCheckScreen(app, onDone = null, onBack = pop)
        }
    })
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingsRoot(app: AppViewModel, push: (SettingsRoute) -> Unit) {
    val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior()
    Scaffold(
        modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
        containerColor = colors.groupedBackground,
        topBar = { BrandTopBar("Settings", app::showAbout, scrollBehavior) },
    ) { padding ->
        SettingsList(app, push, Modifier.padding(padding))
    }
}

@Composable
private fun SettingsList(app: AppViewModel, push: (SettingsRoute) -> Unit, modifier: Modifier) {
    val settings = app.settings
    var usingRealModel by remember { mutableStateOf<Boolean?>(null) }
    LaunchedEffect(Unit) { usingRealModel = app.isUsingRealModel() }
    var confirmingErase by remember { mutableStateOf(false) }

    LazyColumn(modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
        item {
            Section(footer = "The quickest ways to check a post, and the tab that labels photos in the Bluesky app itself.") {
                LabelRow("Ways to Check", Icons.Outlined.Bolt, chevron = true) { push(SettingsRoute.WAYS_TO_CHECK) }
                RowDivider(IconRowInset)
                LabelRow(
                    "Label Tab in Bluesky",
                    Icons.Outlined.Tab,
                    subtitle = screenLabelStatus(),
                    chevron = true,
                ) { push(SettingsRoute.SCREEN_LABELS) }
                if (BuildConfig.ACCESSIBILITY_AUTO_LABEL) {
                    RowDivider(IconRowInset)
                    LabelRow(
                        "Auto-Label (Accessibility)",
                        Icons.Outlined.AutoAwesome,
                        subtitle = autoLabelStatus(app),
                        chevron = true,
                    ) { push(SettingsRoute.AUTO_LABEL) }
                }
            }
        }
        item {
            val session = app.account.session
            Section(
                header = "Bluesky Account",
                footer = if (session != null) "Used only to show your Following feed. Sign-in token kept encrypted on this device." else "Optional. Sign in to see your Following feed in the Feed tab.",
            ) {
                if (session != null) {
                    ValueRow("Signed in as", "@${session.handle}")
                    RowDivider()
                    LabelRow("Sign Out", titleColor = MaterialTheme.colorScheme.error) { app.feed.signOut() }
                } else {
                    LabelRow("Sign In", Icons.AutoMirrored.Outlined.Login, titleColor = MaterialTheme.colorScheme.primary) {
                        app.selectedTab = AppTab.FEED
                        app.feed.isShowingSignIn = true
                    }
                }
            }
        }
        item {
            Section(
                header = "History",
                footer = if (settings.keepHistory) {
                    "Your checks and small copies of photos you checked are saved on this device only and left out of backups. Turning this off deletes them."
                } else {
                    "Off: My Checks clears when the app is closed. Nothing is saved."
                },
            ) {
                ToggleRow("Keep My Checks", Icons.Outlined.Restore, settings.keepHistory, app::setKeepHistory)
            }
        }
        item {
            Section(
                header = "Preferences",
                footer = "The heatmap appears under Highlight on Likely AI results and shows which areas influenced the detector most.",
            ) {
                ToggleRow("Haptics", Icons.Outlined.Vibration, settings.hapticsEnabled) { settings.hapticsEnabled = it }
                RowDivider(IconRowInset)
                ToggleRow("Show Heatmap", Icons.Outlined.LocalFireDepartment, settings.heatmapEnabled) { settings.heatmapEnabled = it }
            }
        }
        item {
            Section(
                header = "Feed",
                footer = "Feed posts are checked on this device as they scroll into view. Paused in Battery Saver and on mobile data or Data Saver.",
            ) {
                ToggleRow("Check Posts Automatically", Icons.Outlined.AutoFixHigh, settings.autoCheckFeed) { settings.autoCheckFeed = it }
                RowDivider(IconRowInset)
                ListRow(onClick = { push(SettingsRoute.HIDDEN_ACCOUNTS) }) {
                    Icon(Icons.Outlined.PersonOff, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
                    Text("Hidden Accounts", style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                    Text("${settings.hiddenAccounts.size}", style = MaterialTheme.typography.bodyLarge, color = colors.secondaryText)
                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.secondaryText.copy(alpha = 0.6f))
                }
            }
        }
        item {
            Section(
                header = "Detector",
                footer = "The detector looks for signs of AI generation. It can't tell whether a real photo was edited or shared with a misleading caption, and no detector is always right.",
            ) {
                ValueRow(
                    "Model",
                    when (usingRealModel) {
                        null -> "Loading…"
                        true -> "CommunityForensics ViT"
                        false -> "Demo (model not loaded)"
                    },
                )
                RowDivider()
                ValueRow("Runs on", "This device")
                RowDivider()
                ValueRow("Answers", "Likely Real or Likely AI")
                RowDivider()
                ValueRow("Calls it AI at", "${(TfliteImageClassifier.THRESHOLD * 100).toInt()}% or higher")
            }
        }
        item {
            Section(header = "About") {
                LabelRow("Privacy Policy", Icons.Outlined.PanTool, chevron = true) { push(SettingsRoute.PRIVACY_POLICY) }
                RowDivider(IconRowInset)
                LabelRow("Terms of Use", Icons.Outlined.Description, chevron = true) { push(SettingsRoute.TERMS) }
                RowDivider(IconRowInset)
                LabelRow("Credits", Icons.Outlined.MenuBook, chevron = true) { push(SettingsRoute.CREDITS) }
                RowDivider(IconRowInset)
                LinkRow("Contact Support", AppLinks.SUPPORT, Icons.Outlined.MailOutline)
                RowDivider()
                ValueRow("Version", BuildConfig.VERSION_NAME)
            }
        }
        item {
            Section {
                LabelRow("Erase All Data", Icons.Outlined.Delete, iconTint = MaterialTheme.colorScheme.error, titleColor = MaterialTheme.colorScheme.error) {
                    confirmingErase = true
                }
            }
        }
        item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
    }

    if (confirmingErase) {
        AlertDialog(
            onDismissRequest = { confirmingErase = false },
            title = { Text("Erase all data?") },
            text = { Text("Deletes My Checks, any saved photos, and resets settings.") },
            confirmButton = {
                TextButton(onClick = { confirmingErase = false; app.eraseAllData() }) {
                    Text("Erase All Data", color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { confirmingErase = false }) { Text("Cancel") } },
        )
    }
}

/** One numbered step. */
@Composable
internal fun StepRow(number: Int, text: String) {
    ListRow {
        Box(Modifier.size(26.dp).background(MaterialTheme.colorScheme.primary, CircleShape), contentAlignment = Alignment.Center) {
            Text("$number", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = if (colors.dark) Color.Black else Color.White)
        }
        Text(text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
    }
}
