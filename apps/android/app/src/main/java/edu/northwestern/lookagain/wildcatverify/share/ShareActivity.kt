package edu.northwestern.lookagain.wildcatverify.share

import android.app.Application
import android.content.ContentResolver
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
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
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
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
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Share → WildcatVerify, like the iOS share extension. Accepts one image, a
 * Bluesky post URL, or text containing one (the image wins), runs the same
 * pipeline as the app, and shows the same Results screen. Tapping Done discards
 * everything; nothing is written to disk or added to My Checks.
 */
class ShareActivity : ComponentActivity() {
    /** Survives rotation, so turning the phone doesn't check the item again. */
    private val check: ShareCheck by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val container = container
        // Read through the application's resolver: the read can outlive this activity across a rotation.
        val resolver = applicationContext.contentResolver
        val shared = intent
        check.start { readInput(shared, resolver) }
        setContent {
            WildcatTheme {
                CompositionLocalProvider(
                    LocalImages provides container.images,
                    LocalHeatmapEnabled provides container.settings.heatmapEnabled,
                ) {
                    ShareRoot(check.share, onDone = ::finish)
                }
            }
        }
    }
}

/**
 * Holds one share's check across rotation. When the screen closes for good it
 * drops the shared photo from memory, as the iOS extension does on Done. Only
 * this check's photo: the app shares the process, and My Checks may hold others.
 */
class ShareCheck(application: Application) : AndroidViewModel(application) {
    private val images = application.container.images
    val share = ShareViewModel(application.container.pipeline())
    private var started = false

    /** Runs once per share; later calls (after a rotation) keep the check already running. */
    fun start(read: suspend () -> ShareInput?) {
        if (started) return
        started = true
        viewModelScope.launch {
            val input = read()
            if (input == null) share.fail(CheckException.Unsupported) else share.check(input)
        }
    }

    override fun onCleared() {
        share.uploadUrl?.let(images::removeUpload)
    }
}

/** Picks the best thing to check: an image first, then a Bluesky link in the shared text. */
private suspend fun readInput(intent: Intent, resolver: ContentResolver): ShareInput? {
    if (intent.action != Intent.ACTION_SEND) return null
    IntentCompat.getParcelableExtra(intent, Intent.EXTRA_STREAM, Uri::class.java)?.let { uri ->
        val data = withContext(Dispatchers.IO) {
            runCatching { resolver.openInputStream(uri)?.use { it.readBytes() } }.getOrNull()
        }
        if (data != null) return ShareInput.Image(data)
    }
    val text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString() ?: return null
    return BlueskyService.linkIn(text)?.let { ShareInput.Link(it) }
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
