package edu.northwestern.lookagain.wildcatverify.ui.welcome

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.ui.shared.LogoTile
import edu.northwestern.lookagain.wildcatverify.ui.shared.PrimaryButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel

/**
 * The fastest ways to check a post, shortest first. Shown once on first launch
 * (with `onDone`) and kept under Settings → Ways to Check (with `onBack`).
 */
@Composable
fun WaysToCheckScreen(app: AppViewModel, onDone: (() -> Unit)?, onBack: (() -> Unit)?) {
    Scaffold(
        containerColor = colors.groupedBackground,
        topBar = { if (onBack != null) PushedTopBar("Ways to Check", onBack) },
        bottomBar = {
            if (onDone != null) {
                Box(Modifier.navigationBarsPadding().padding(horizontal = 24.dp, vertical = 12.dp)) {
                    PrimaryButton("Start Checking", onClick = onDone)
                }
            }
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .then(if (onBack == null) Modifier.statusBarsPadding() else Modifier)
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(Modifier.widthIn(max = 560.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(24.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    LogoTile(54.dp)
                    Text("Check a post in one or two taps", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                }
                WayRow(1, "Hold the photo, tap Share", "In Bluesky, Chrome, Photos or Messages, press and hold any image, tap Share, then WildcatVerify.")
                WayRow(2, "Copy the link, open WildcatVerify", "In Bluesky, tap Share on a post, then Copy Link. Open WildcatVerify and tap Paste.")
                WayRow(3, "Scroll the Feed tab", "Posts in the Feed are checked as they appear, so the verdict is waiting under each one.")
                WayRow(4, "Turn on the label tab", "Labels photos right in the Bluesky app as you scroll. Start it in Settings → Label Tab in Bluesky.")
                Text("Photos are checked on this device and never uploaded.", style = MaterialTheme.typography.bodySmall, color = colors.secondaryText)
            }
        }
    }
}

@Composable
private fun WayRow(number: Int, title: String, detail: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.semantics(mergeDescendants = true) { }) {
        Box(
            Modifier.size(30.dp).background(MaterialTheme.colorScheme.primary, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text("$number", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, color = if (colors.dark) Color.Black else Color.White)
        }
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(detail, style = MaterialTheme.typography.bodyLarge, color = colors.secondaryText)
        }
    }
}
