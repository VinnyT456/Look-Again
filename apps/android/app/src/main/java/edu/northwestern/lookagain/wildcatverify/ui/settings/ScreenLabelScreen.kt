package edu.northwestern.lookagain.wildcatverify.ui.settings

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.BatteryStd
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.Crop
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.DynamicFeed
import androidx.compose.material.icons.outlined.PhoneAndroid
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.autolabel.AutoLabelService
import edu.northwestern.lookagain.wildcatverify.autolabel.ScreenLabelService
import edu.northwestern.lookagain.wildcatverify.ui.shared.BulletRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.IconRowInset
import edu.northwestern.lookagain.wildcatverify.ui.shared.LabelRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.shared.ValueRow
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppTab
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel

/** "On", "Paused" or "Off", for the Settings row. */
@Composable
internal fun screenLabelStatus(): String = when {
    !ScreenLabelService.isRunning -> "Off"
    ScreenLabelService.isPaused -> "Paused"
    else -> "On"
}

private fun openBluesky(context: Context) {
    context.packageManager.getLaunchIntentForPackage(AutoLabelService.BLUESKY)?.let {
        context.startActivity(it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}

/**
 * Settings → Label Tab: a small tab over the Bluesky app, backed by a screen
 * capture the user approves each time. Starting it asks, in order, for
 * "Display over other apps" (once), notifications (once, Android 13+), and
 * Android's screen-sharing consent (every session).
 */
@Composable
fun ScreenLabelScreen(app: AppViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    var explainingOverlay by remember { mutableStateOf(false) }
    val blueskyInstalled = remember { context.packageManager.getLaunchIntentForPackage(AutoLabelService.BLUESKY) != null }

    val capture = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        val data = result.data
        if (result.resultCode == Activity.RESULT_OK && data != null) {
            ScreenLabelService.start(context, result.resultCode, data)
            openBluesky(context)
        }
    }
    val askCapture = {
        val manager = context.getSystemService(android.media.projection.MediaProjectionManager::class.java)
        capture.launch(manager.createScreenCaptureIntent())
    }
    val notifications = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { askCapture() }
    val start = {
        when {
            !Settings.canDrawOverlays(context) -> explainingOverlay = true
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU -> notifications.launch(Manifest.permission.POST_NOTIFICATIONS)
            else -> askCapture()
        }
    }

    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Label Tab", onBack) }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            item {
                Section {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Labels right in the Bluesky app", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text(
                            "A small WildcatVerify tab sits at the edge of the screen. Scroll Bluesky as usual; when you stop, photos get a Real or AI label, checked on this device.",
                            color = colors.secondaryText,
                        )
                    }
                }
            }
            item {
                if (ScreenLabelService.isRunning) {
                    Section(footer = "You can also pause or stop it from the notification, or tap the tab to pause.") {
                        ValueRow("Status", if (ScreenLabelService.isPaused) "Paused" else "On")
                        if (blueskyInstalled) {
                            RowDivider()
                            LabelRow("Open Bluesky", Icons.AutoMirrored.Outlined.OpenInNew, titleColor = MaterialTheme.colorScheme.primary) { openBluesky(context) }
                        }
                        RowDivider(if (blueskyInstalled) IconRowInset else 16.dp)
                        LabelRow("Stop Label Tab", Icons.Outlined.Stop, iconTint = MaterialTheme.colorScheme.error, titleColor = MaterialTheme.colorScheme.error) {
                            ScreenLabelService.stop(context)
                        }
                    }
                } else {
                    Section(
                        footer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                            "When Android asks what to share, choose “A single app” and pick Bluesky. Then only Bluesky is seen."
                        } else {
                            "Android asks to share your screen each time you start the tab. Stop it when you leave Bluesky."
                        },
                    ) {
                        ValueRow("Status", "Off")
                        RowDivider()
                        LabelRow("Start Label Tab", Icons.Outlined.PlayArrow, titleColor = MaterialTheme.colorScheme.primary, onClick = start)
                    }
                }
            }
            item {
                Section(header = "How it works") {
                    StepRow(1, "Tap Start, allow Display over other apps the first time, then choose Bluesky to share.")
                    StepRow(2, "Scroll your feed. When you stop, each photo gets a label such as ✓ Real 92% or ✦ AI 97%.")
                    StepRow(3, "Tap a label for the full result. Tap the tab to pause; stop it from the notification.")
                }
            }
            item {
                Section(header = "What it sees") {
                    BulletRow("On Android 14 and later, only the app you choose to share. Android shows a sharing indicator while it runs.", Icons.Outlined.PhoneAndroid)
                    RowDivider(IconRowInset)
                    BulletRow("Screen frames stay in memory and are replaced as you scroll. Only photo areas are checked.", Icons.Outlined.Crop)
                    RowDivider(IconRowInset)
                    BulletRow("Everything is checked on this device. Nothing is uploaded or recorded.", Icons.Outlined.CloudOff)
                    RowDivider(IconRowInset)
                    BulletRow("A photo is saved to My Checks only if you tap its label.", Icons.Outlined.History)
                    RowDivider(IconRowInset)
                    BulletRow("Reading the screen uses more battery than browsing; pause or stop it when you're done.", Icons.Outlined.BatteryStd)
                }
            }
            item {
                Section(footer = "Photos are found from what's on screen, so a collage or a photo on a plain background can be missed or boxed loosely. The Feed tab's labels are exact.") {
                    LabelRow("Use Feed Labels Instead", Icons.Outlined.DynamicFeed, titleColor = MaterialTheme.colorScheme.primary) {
                        app.selectedTab = AppTab.FEED
                    }
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }

    if (explainingOverlay) {
        AlertDialog(
            onDismissRequest = { explainingOverlay = false },
            title = { Text("Allow the tab over other apps") },
            text = {
                Text("To show its tab and labels on top of Bluesky, WildcatVerify needs “Display over other apps”. On the next screen, turn it on for WildcatVerify, then come back and tap Start again.")
            },
            confirmButton = {
                TextButton(onClick = {
                    explainingOverlay = false
                    context.startActivity(
                        Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                    )
                }) { Text("Continue") }
            },
            dismissButton = { TextButton(onClick = { explainingOverlay = false }) { Text("Not Now") } },
        )
    }
}
