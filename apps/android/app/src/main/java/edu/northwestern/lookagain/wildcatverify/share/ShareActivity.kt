package edu.northwestern.lookagain.wildcatverify.share

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.SearchOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.IntentCompat
import edu.northwestern.lookagain.wildcatverify.container
import edu.northwestern.lookagain.wildcatverify.data.BlueskyService
import edu.northwestern.lookagain.wildcatverify.model.CheckException
import edu.northwestern.lookagain.wildcatverify.ui.results.AnalyzingView
import edu.northwestern.lookagain.wildcatverify.ui.results.ResultsScreen
import edu.northwestern.lookagain.wildcatverify.ui.shared.ContentUnavailable
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalHeatmapEnabled
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalImages
import edu.northwestern.lookagain.wildcatverify.ui.shared.LogoTile
import edu.northwestern.lookagain.wildcatverify.ui.theme.WildcatTheme
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.ShareInput
import edu.northwestern.lookagain.wildcatverify.viewmodel.ShareViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Share → WildcatVerify, like the iOS share extension. Accepts one image, a
 * Bluesky post URL, or text containing one (the image wins), runs the same
 * pipeline as the app, and shows the same Results screen. Tapping Done discards
 * everything; nothing is written to disk or added to My Checks.
 */
class ShareActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val container = container
        val viewModel = ShareViewModel(container.pipeline())
        val shared = intent
        setContent {
            WildcatTheme {
                CompositionLocalProvider(
                    LocalImages provides container.images,
                    LocalHeatmapEnabled provides container.settings.heatmapEnabled,
                ) {
                    ShareRoot(viewModel, onDone = ::finish)
                }
            }
            LaunchedEffect(Unit) {
                val input = readInput(shared)
                if (input == null) viewModel.fail(CheckException.Unsupported) else viewModel.check(input)
            }
        }
    }

    /** Picks the best thing to check: an image first, then a Bluesky link in the shared text. */
    private suspend fun readInput(intent: Intent): ShareInput? {
        if (intent.action != Intent.ACTION_SEND) return null
        IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)?.let { uri ->
            val data = withContext(Dispatchers.IO) {
                runCatching { contentResolver.openInputStream(uri)?.use { it.readBytes() } }.getOrNull()
            }
            if (data != null) return ShareInput.Image(data)
        }
        val text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString() ?: return null
        return BlueskyService.linkIn(text)?.let { ShareInput.Link(it) }
    }
}

/** The share screen's content: progress, the verdict, or why it couldn't check. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ShareRoot(viewModel: ShareViewModel, onDone: () -> Unit) {
    val view = LocalView.current
    LaunchedEffect(viewModel.phase) {
        when (val phase = viewModel.phase) {
            is ShareViewModel.Phase.Result -> view.announceForAccessibility("${phase.item.verdict.label}, ${phase.item.confidencePercentage} percent confidence")
            is ShareViewModel.Phase.Failed -> view.announceForAccessibility(phase.message)
            else -> Unit
        }
    }
    Scaffold(
        containerColor = colors.groupedBackground,
        topBar = {
            TopAppBar(
                title = { Text("WildcatVerify", fontWeight = FontWeight.SemiBold) },
                navigationIcon = { Box(Modifier.padding(start = 12.dp, end = 8.dp)) { LogoTile() } },
                actions = { TextButton(onClick = onDone) { Text("Done", fontWeight = FontWeight.SemiBold) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = colors.groupedBackground),
            )
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (val phase = viewModel.phase) {
                ShareViewModel.Phase.Reading -> Column(
                    Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    CircularProgressIndicator()
                    Text("Reading shared item…", color = colors.secondaryText, modifier = Modifier.padding(top = 12.dp))
                }
                ShareViewModel.Phase.Analyzing -> AnalyzingView(viewModel.analyzingImage, onCancel = onDone)
                is ShareViewModel.Phase.Result -> ResultsScreen(phase.item, onBack = null, onCheckAnother = null, inShareSheet = true, topBar = false)
                is ShareViewModel.Phase.Failed -> ContentUnavailable("Can't Check This", Icons.Outlined.SearchOff, phase.message)
            }
        }
    }
}
