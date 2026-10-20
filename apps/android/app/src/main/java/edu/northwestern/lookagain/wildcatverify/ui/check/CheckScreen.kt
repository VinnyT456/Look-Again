package edu.northwestern.lookagain.wildcatverify.ui.check

import android.content.ClipboardManager
import android.content.Context
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.platform.LocalWindowInfo
import edu.northwestern.lookagain.wildcatverify.ui.theme.Palette
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.outlined.HelpOutline
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.ContentPaste
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.IosShare
import androidx.compose.material.icons.outlined.Link
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import edu.northwestern.lookagain.wildcatverify.ui.results.AnalyzingView
import edu.northwestern.lookagain.wildcatverify.ui.results.ResultsScreen
import edu.northwestern.lookagain.wildcatverify.ui.shared.GlassCircleButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.LogoTile
import edu.northwestern.lookagain.wildcatverify.ui.shared.NavStack
import edu.northwestern.lookagain.wildcatverify.ui.shared.PrimaryButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.staggeredAppear
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.CheckViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** The Check tab: the brand header and check card (or analysis in progress) at the root, results pushed on top. */
@Composable
fun CheckScreen(app: AppViewModel) {
    val viewModel = app.check
    val top = viewModel.path.lastOrNull()
    BackHandler(enabled = top != null) { viewModel.pop() }

    NavStack(viewModel.path, screen = { item ->
        ResultsScreen(item, onBack = viewModel::pop, onCheckAnother = app::startNewCheck)
    }, root = {
            Column(Modifier.fillMaxSize().background(colors.groupedBackground)) {
                CheckHeader(app::showAbout)
                AnimatedContent(viewModel.phase, transitionSpec = { fadeIn() togetherWith fadeOut() }, label = "phase") { phase ->
                    if (phase == CheckViewModel.Phase.ANALYZING) {
                        AnalyzingView(viewModel.analyzingImage, onCancel = viewModel::cancelAnalysis)
                    } else {
                        CheckPage(app)
                    }
                }
            }
    })

    if (viewModel.isShowingError) {
        AlertDialog(
            onDismissRequest = { viewModel.isShowingError = false },
            title = { Text("Couldn't Check Image") },
            text = { Text(viewModel.errorMessage) },
            confirmButton = { TextButton(onClick = { viewModel.isShowingError = false }) { Text("OK") } },
        )
    }
}

/** Brand bar for the Check page: logo, wordmark and the About button. */
@Composable
private fun CheckHeader(onShowAbout: () -> Unit) {
    Column(Modifier.background(colors.bar).statusBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            LogoTile(Metrics.headerLogo)
            Text(
                "WildcatVerify",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f).semantics { heading() },
            )
            GlassCircleButton(Icons.AutoMirrored.Outlined.HelpOutline, "About WildcatVerify", onShowAbout, tint = colors.secondaryText)
        }
        HorizontalDivider(thickness = 0.5.dp, color = colors.separator)
    }
}

/** Scrollable body of the Check tab: the check card and the share tip. Past checks live in My Checks. */
@Composable
private fun CheckPage(app: AppViewModel) {
    val viewModel = app.check
    // Android only shows the clipboard to the focused window, so look each time the app gets focus.
    val window = LocalWindowInfo.current
    LaunchedEffect(window) {
        snapshotFlow { window.isWindowFocused }.collect { focused -> if (focused) viewModel.refreshCopiedLinkOffer() }
    }
    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        AnimatedVisibility(viewModel.offersCopiedLink, enter = expandVertically() + fadeIn(), exit = shrinkVertically() + fadeOut()) {
            CopiedLinkOffer(
                onPaste = viewModel::pasteCopiedLink,
                onDismiss = viewModel::dismissCopiedLinkOffer,
                modifier = Modifier.widthIn(max = 640.dp),
            )
        }
        CheckCard(app, Modifier.widthIn(max = 640.dp).staggeredAppear(0))
        AnimatedVisibility(!app.settings.shareTipDismissed, exit = fadeOut()) {
            ShareTip(
                onOpen = app::showLabelSetup,
                onDismiss = { app.settings.shareTipDismissed = true },
                modifier = Modifier.widthIn(max = 640.dp).staggeredAppear(1),
            )
        }
    }
}

/** "Check the link you copied": one tap from copying a post in Bluesky to its result. */
@Composable
private fun CopiedLinkOffer(onPaste: () -> Unit, onDismiss: () -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Metrics.fieldRadius))
            .background(colors.card)
            .border(1.5.dp, MaterialTheme.colorScheme.primary, RoundedCornerShape(Metrics.fieldRadius))
            .padding(start = 16.dp, top = 12.dp, bottom = 12.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text("Check the link you copied", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text("Tap Paste and the post is checked right away.", style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
        }
        Row(
            Modifier
                .clip(CircleShape)
                .background(Palette.NorthwesternPurple)
                .clickable(onClickLabel = "Paste the copied link and check it", onClick = onPaste)
                .padding(horizontal = 14.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Icon(Icons.Filled.ContentPaste, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
            Text("Paste", color = Color.White, fontWeight = FontWeight.SemiBold)
        }
        IconButton(onClick = onDismiss) {
            Icon(Icons.Outlined.Close, contentDescription = "Not Now", tint = colors.secondaryText, modifier = Modifier.size(18.dp))
        }
    }
}

/** The Check page's main card: link input, divider, photo drop zone and the privacy line. */
@Composable
private fun CheckCard(app: AppViewModel, modifier: Modifier = Modifier) {
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Metrics.cardRadius))
            .background(colors.card)
            .border(0.5.dp, colors.separator.copy(alpha = colors.separator.alpha * 0.35f), RoundedCornerShape(Metrics.cardRadius))
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp),
    ) {
        LinkInput(app.check)
        OrUploadDivider()
        PhotoDropzone(app.check)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            Icon(Icons.Filled.VerifiedUser, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
            Text(
                if (app.settings.keepHistory) "Checks saved on this device • Change in Settings" else "Private • Photos are not stored",
                style = MaterialTheme.typography.bodySmall,
                color = colors.secondaryText,
            )
        }
    }
}

/** "Bluesky Post Link": the field, paste/clear, and the Check Post button. */
@Composable
private fun LinkInput(viewModel: CheckViewModel) {
    val context = LocalContext.current
    val focus = LocalFocusManager.current
    var focused by remember { mutableStateOf(false) }
    val submit = {
        focus.clearFocus()
        viewModel.checkPost()
    }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Link, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp).rotate(-45f))
            Spacer(Modifier.size(8.dp))
            Text(
                "Bluesky Post Link",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.weight(1f).semantics { heading() },
            )
            Text("bsky.app", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = colors.secondaryText)
        }

        TextField(
            value = viewModel.inputUrl,
            onValueChange = { viewModel.inputUrl = it },
            placeholder = { Text("Paste link to Bluesky post…") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Go, autoCorrectEnabled = false),
            keyboardActions = KeyboardActions(onGo = { submit() }),
            trailingIcon = {
                if (viewModel.inputUrl.isEmpty()) {
                    // iOS's PasteButton: a tinted circle.
                    Box(
                        Modifier
                            .padding(end = 4.dp)
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.35f))
                            .clickable(onClickLabel = "Paste") { pasteText(context)?.let { viewModel.checkPasted(it) } },
                        contentAlignment = Alignment.Center,
                    ) { Icon(Icons.Filled.ContentPaste, contentDescription = "Paste", tint = Color.White, modifier = Modifier.size(20.dp)) }
                } else {
                    IconButton(onClick = { viewModel.inputUrl = "" }) {
                        Icon(Icons.Filled.Cancel, contentDescription = "Clear Link", tint = colors.secondaryText)
                    }
                }
            },
            shape = RoundedCornerShape(Metrics.fieldRadius),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = colors.fill,
                unfocusedContainerColor = colors.fill,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = Metrics.controlHeight)
                .onFocusChanged { focused = it.isFocused }
                .border(1.5.dp, if (focused) MaterialTheme.colorScheme.primary else Color.Transparent, RoundedCornerShape(Metrics.fieldRadius))
                .semantics { contentDescription = "Bluesky post link" },
        )

        PrimaryButton("Check Post", onClick = submit, enabled = viewModel.canCheckPost, trailingIcon = Icons.AutoMirrored.Filled.ArrowForward)
    }
}

private fun pasteText(context: Context): String? {
    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
    return clipboard.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(context)?.toString()?.trim()
}

/** Hairline divider with "OR UPLOAD MEDIA" set into it. */
@Composable
private fun OrUploadDivider() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        HorizontalDivider(Modifier.weight(1f), thickness = 0.5.dp, color = colors.separator)
        Text("OR UPLOAD MEDIA", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, letterSpacing = 1.sp, color = colors.secondaryText)
        HorizontalDivider(Modifier.weight(1f), thickness = 0.5.dp, color = colors.separator)
    }
}

/** Dashed drop zone that opens the system photo picker (no storage permission needed). Dips on press. */
@Composable
private fun PhotoDropzone(viewModel: CheckViewModel) {
    val context = LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri: Uri? ->
        if (uri != null) {
            viewModel.analyzePhoto {
                withContext(Dispatchers.IO) { context.contentResolver.openInputStream(uri)?.use { it.readBytes() } }
            }
        }
    }
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.97f else 1f, label = "dip")
    val dash = colors.separator
    val tint = colors.purpleTint

    Column(
        Modifier
            .fillMaxWidth()
            .heightIn(min = 280.dp)
            .graphicsLayer { scaleX = scale; scaleY = scale; alpha = if (pressed) 0.9f else 1f }
            .clip(RoundedCornerShape(Metrics.fieldRadius))
            .drawBehind {
                drawRoundRect(
                    dash,
                    cornerRadius = CornerRadius(Metrics.fieldRadius.toPx()),
                    style = Stroke(1.5.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(6.dp.toPx(), 5.dp.toPx()))),
                )
            }
            .clickable(interaction, indication = null, role = Role.Button, onClickLabel = "Choose photo or screenshot to check") {
                picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
            }
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Box(
            Modifier.size(64.dp).clip(RoundedCornerShape(Metrics.fieldRadius)).background(tint.copy(alpha = 0.6f)),
            contentAlignment = Alignment.Center,
        ) { Icon(Icons.Outlined.IosShare, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(28.dp)) }
        Spacer(Modifier.height(16.dp))
        Text("Choose Photo or Screenshot", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
        Spacer(Modifier.height(4.dp))
        Text("From your gallery or files", style = MaterialTheme.typography.bodySmall, color = colors.secondaryText)
        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("Gallery", "Screenshots").forEach { tag ->
                Text(
                    tag,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = colors.secondaryText,
                    modifier = Modifier.clip(CircleShape).background(colors.fill).padding(horizontal = 12.dp, vertical = 5.dp),
                )
            }
        }
    }
}

/** Dismissible tip on the Check page pointing to Auto-Label. */
@Composable
private fun ShareTip(onOpen: () -> Unit, onDismiss: () -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Metrics.fieldRadius))
            .background(colors.card)
            .border(BorderStroke(0.5.dp, colors.separator.copy(alpha = colors.separator.alpha * 0.35f)), RoundedCornerShape(Metrics.fieldRadius)),
        verticalAlignment = Alignment.Top,
    ) {
        Row(
            Modifier
                .weight(1f)
                .clickable(onClickLabel = "Open label settings", onClick = onOpen)
                .padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("Label photos right in Bluesky", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                Text("Turn on the label tab to see Real or AI on photos in the Bluesky app.", style = MaterialTheme.typography.bodySmall, color = colors.secondaryText)
            }
        }
        IconButton(onClick = onDismiss, modifier = Modifier.padding(4.dp)) {
            Icon(Icons.Outlined.Close, contentDescription = "Dismiss Tip", tint = colors.secondaryText, modifier = Modifier.size(18.dp))
        }
    }
}
