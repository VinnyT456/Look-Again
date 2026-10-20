package edu.northwestern.lookagain.wildcatverify.ui.settings

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Block
import androidx.compose.material.icons.outlined.CloudOff
import androidx.compose.material.icons.outlined.Crop
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.PhoneAndroid
import androidx.compose.material.icons.outlined.PowerSettingsNew
import androidx.compose.material.icons.outlined.Share
import androidx.compose.material.icons.outlined.Visibility
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
import androidx.lifecycle.compose.LifecycleResumeEffect
import edu.northwestern.lookagain.wildcatverify.autolabel.AutoLabelService
import edu.northwestern.lookagain.wildcatverify.ui.shared.BulletRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.IconRowInset
import edu.northwestern.lookagain.wildcatverify.ui.shared.LabelRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.shared.ToggleRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.ValueRow
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel

/** Whether Auto-Label is on, re-read whenever the screen comes back (e.g. from system settings). */
@Composable
private fun rememberAutoLabelEnabled(): Boolean {
    val context = LocalContext.current
    var enabled by remember { mutableStateOf(AutoLabelService.isEnabled(context)) }
    LifecycleResumeEffect(Unit) {
        enabled = AutoLabelService.isEnabled(context)
        onPauseOrDispose { }
    }
    return enabled
}

/** "On", "Paused" or "Off", for the Settings row. */
@Composable
internal fun autoLabelStatus(app: AppViewModel): String = when {
    !AutoLabelService.isSupported -> "Needs Android 11 or later"
    !rememberAutoLabelEnabled() -> "Off"
    app.settings.autoLabelPaused -> "Paused"
    else -> "On"
}

/** Opens this service's page in system Accessibility settings (or the list, before Android 13). */
private fun openAccessibilitySettings(context: Context) {
    val component = ComponentName(context, AutoLabelService::class.java).flattenToString()
    val details = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        // Not in the public SDK constants, but handled by Android 13+ Settings.
        Intent("android.settings.ACCESSIBILITY_DETAILS_SETTINGS").putExtra(Intent.EXTRA_COMPONENT_NAME, component)
    } else {
        null
    }
    val fallback = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
    runCatching { context.startActivity((details ?: fallback).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
        .onFailure { runCatching { context.startActivity(fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } }
}

/**
 * Settings → Auto-Label: what it does, what it reads, and the switch. Turning it
 * on goes through a disclosure first, then system Accessibility settings,
 * where only the user can enable it.
 */
@Composable
fun AutoLabelScreen(app: AppViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    val enabled = rememberAutoLabelEnabled()
    var disclosing by remember { mutableStateOf(false) }

    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Auto-Label", onBack) }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            item {
                Section {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Label photos while you browse Bluesky", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text(
                            "Scroll the Bluesky app (or bsky.app in Chrome) as usual. When you stop, each photo gets a small Real or AI label, checked on this device.",
                            color = colors.secondaryText,
                        )
                    }
                }
            }
            item {
                when {
                    !AutoLabelService.isSupported -> Section(footer = "Auto-Label needs Android 11 or later. You can still share photos to WildcatVerify.") {
                        ValueRow("Status", "Not available")
                    }
                    !enabled -> Section(footer = "Android asks you to turn it on in Settings → Accessibility. You can turn it off there any time.") {
                        ValueRow("Status", "Off")
                        RowDivider()
                        LabelRow("Turn On Auto-Label", Icons.Outlined.PowerSettingsNew, titleColor = MaterialTheme.colorScheme.primary) { disclosing = true }
                    }
                    else -> Section(footer = "Pause hides the labels without turning the service off.") {
                        ToggleRow("Show Labels", Icons.Outlined.Visibility, !app.settings.autoLabelPaused) { app.settings.autoLabelPaused = !it }
                        RowDivider(IconRowInset)
                        LabelRow("Turn Off in Android Settings", Icons.Outlined.PowerSettingsNew, titleColor = MaterialTheme.colorScheme.primary) {
                            openAccessibilitySettings(context)
                        }
                    }
                }
            }
            item {
                Section(header = "How it works") {
                    StepRow(1, "Open Bluesky and scroll your feed.")
                    StepRow(2, "Stop on a post. A label such as ✓ Real 92% or ✦ AI 97% appears on each photo.")
                    StepRow(3, "Tap a label to see the full result, with the heatmap. It's added to My Checks.")
                }
            }
            item {
                Section(header = "What it reads") {
                    BulletRow("Only the Bluesky app, and Chrome while bsky.app is open. Other apps and sites are ignored.", Icons.Outlined.PhoneAndroid)
                    RowDivider(IconRowInset)
                    BulletRow("Only where photos are on screen and the pixels inside them. Not your messages, text, or passwords.", Icons.Outlined.Crop)
                    RowDivider(IconRowInset)
                    BulletRow("Everything is checked on this device. Nothing is uploaded.", Icons.Outlined.CloudOff)
                    RowDivider(IconRowInset)
                    BulletRow("Labels are kept in memory. A photo is only saved to My Checks if you tap its label.", Icons.Outlined.History)
                    RowDivider(IconRowInset)
                    BulletRow("It never taps, types or scrolls for you.", Icons.Outlined.Block)
                }
            }
            item {
                Section(header = "Check a single photo", footer = "Works in any app, with or without Auto-Label.") {
                    BulletRow("Tap Share on a post or photo and choose WildcatVerify.", Icons.Outlined.Share)
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }

    // Google Play's prominent disclosure: say exactly what is accessed before the system screen.
    if (disclosing) {
        AlertDialog(
            onDismissRequest = { disclosing = false },
            title = { Text("Turn on Auto-Label?") },
            text = {
                Text(
                    "WildcatVerify uses Android's Accessibility service to find photos on screen in the Bluesky app and in Chrome on bsky.app, and to read the pixels of those photos so it can label them. " +
                        "Photos are checked on this device and are not uploaded or saved. It doesn't read other apps, and it never taps or types for you.\n\n" +
                        "On the next screen, turn on WildcatVerify Auto-Label.",
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    disclosing = false
                    app.settings.autoLabelPaused = false
                    openAccessibilitySettings(context)
                }) { Text("Continue") }
            },
            dismissButton = { TextButton(onClick = { disclosing = false }) { Text("Not Now") } },
        )
    }
}
