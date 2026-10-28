package edu.northwestern.lookagain.wildcatverify.ui.results

import android.content.Intent
import edu.northwestern.lookagain.wildcatverify.ui.shared.ListRow
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.runtime.mutableStateOf
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.selection.selectable
import androidx.compose.material.icons.filled.Sell
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.Role
import edu.northwestern.lookagain.wildcatverify.model.ContentCredentials
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.ui.shared.CaseThumbnail
import android.graphics.Bitmap
import android.os.Build
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Science
import androidx.compose.material.icons.outlined.IosShare
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.min
import edu.northwestern.lookagain.wildcatverify.model.HotspotArea
import edu.northwestern.lookagain.wildcatverify.model.PatchHeatmap
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import edu.northwestern.lookagain.wildcatverify.ui.shared.BulletRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.GlassCircleButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.IosSegmentedControl
import edu.northwestern.lookagain.wildcatverify.ui.shared.LabelRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalHeatmapEnabled
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalImages
import edu.northwestern.lookagain.wildcatverify.ui.shared.NoPhotoPlaceholder
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.IconRowInset
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.shared.TextRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.ValueRow
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.Palette
import edu.northwestern.lookagain.wildcatverify.ui.theme.background
import edu.northwestern.lookagain.wildcatverify.ui.theme.color
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.ui.theme.findingIcon
import edu.northwestern.lookagain.wildcatverify.ui.theme.icon
import edu.northwestern.lookagain.wildcatverify.ui.theme.textColor
import edu.northwestern.lookagain.wildcatverify.viewmodel.CheckResultsViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.PhotoLayer
import kotlinx.coroutines.launch

/**
 * The verdict for one image: the whole photo, what the model concluded, why,
 * and what to do about it.
 *
 * @param onCheckAnother null hides "Check Another Image" (the share screen uses Done instead).
 * @param inShareSheet hides sharing and "Open on Bluesky", like the iOS share extension.
 */
@Composable
fun ResultsScreen(
    lead: VerificationCase,
    onBack: (() -> Unit)?,
    onCheckAnother: (() -> Unit)?,
    inShareSheet: Boolean = false,
    topBar: Boolean = true,
) {
    // A multi-image post shows every image; it opens on the most suspicious one, the case itself.
    val postImages = lead.postImages?.takeIf { it.size > 1 }.orEmpty()
    var selection by remember(lead.id) { mutableIntStateOf(postImages.indexOfFirst { it.id == lead.id }.coerceAtLeast(0)) }
    val images = LocalImages.current
    // One view model per image, so each keeps its own Photo/Highlight choice across recomposition and switching.
    val viewModels = remember(lead.id) { postImages.ifEmpty { listOf(lead) }.map { CheckResultsViewModel(it, images) } }
    val viewModel = viewModels[selection.coerceIn(viewModels.indices)]
    val item = viewModel.item
    viewModel.heatmapEnabled = LocalHeatmapEnabled.current
    LaunchedEffect(item.id) { viewModel.loadImage() }

    val context = LocalContext.current
    val listState = rememberLazyListState()
    var showsDetails by remember(lead.id) { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Scaffold(
        containerColor = colors.groupedBackground,
        topBar = {
            if (topBar) {
                PushedTopBar("Result", onBack) {
                    if (!inShareSheet) {
                        GlassCircleButton(Icons.Outlined.IosShare, "Share Result", onClick = {
                            val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, item.shareText)
                            context.startActivity(Intent.createChooser(send, "Share Result"))
                        })
                    }
                }
            }
        },
    ) { padding ->
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().padding(padding),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // The answer first: verdict, confidence, one paragraph.
            item(key = "verdict") {
                Section(
                    background = item.verdict.background,
                    footer = "A verdict is an estimate, not proof. Please don't use it on its own to accuse anyone.",
                ) { VerdictSummary(item) }
            }

            if (item.isDemo) {
                item(key = "demo") {
                    Section {
                        BulletRow("Demo result. This verdict isn't from the Look Again detection model yet, so don't rely on it.", Icons.Outlined.Science)
                    }
                }
            }

            if (viewModel.hasPhoto) {
                item(key = "photo") {
                    Section {
                        ResultPhoto(viewModel)
                        if (viewModel.canToggleHighlight) {
                            IosSegmentedControl(
                                PhotoLayer.entries,
                                viewModel.layer,
                                label = { it.title },
                                onSelect = { viewModel.layer = it },
                                modifier = Modifier.padding(12.dp),
                            )
                        }
                    }
                }
            }

            if (postImages.size > 1) {
                item(key = "strip") {
                    Section(
                        header = "${postImages.size} images in this post",
                        footer = "Each image is checked on its own. The most suspicious one opens first.",
                    ) {
                        PostImageStrip(postImages, selection) { selection = it }
                    }
                }
            }

            item.credentials?.let { credentials ->
                item(key = "credentials") { CredentialsSection(credentials) }
            }

            // Everything else waits behind one tap.
            item(key = "details-toggle") {
                Section {
                    ListRow(onClick = { showsDetails = !showsDetails }, onClickLabel = if (showsDetails) "Hide details" else "Show details") {
                        Text(
                            if (showsDetails) "Hide Details" else "Why This Verdict?",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.weight(1f),
                        )
                        Icon(
                            Icons.Outlined.ExpandMore,
                            contentDescription = null,
                            tint = colors.secondaryText,
                            modifier = Modifier.graphicsLayer { rotationZ = if (showsDetails) 180f else 0f },
                        )
                    }
                }
            }

            if (showsDetails) {
                item(key = "findings") {
                    // Examples describe what was seen; detector results list things to
                    // check, since the model doesn't report specific evidence.
                    Section(header = if (item.isDemo) "What we noticed" else "Things to check yourself") {
                        item.keyFindings.forEachIndexed { index, finding ->
                            if (index > 0) RowDivider(IconRowInset)
                            BulletRow(finding, item.verdict.findingIcon, item.verdict.textColor)
                        }
                        if (viewModel.canShowOnPhoto) {
                            RowDivider(IconRowInset)
                            LabelRow("Show on Photo", Icons.Outlined.Visibility, titleColor = MaterialTheme.colorScheme.primary) {
                                viewModel.showOnPhoto()
                                scope.launch { listState.animateScrollToItem(if (item.isDemo) 2 else 1) }
                            }
                        }
                    }
                }

                item(key = "action") {
                    Section(header = "What to do") { TextRow(item.suggestedAction) }
                }

                item(key = "source") { SourceSection(item, inShareSheet) }
            }

            if (onCheckAnother != null) {
                item(key = "another") {
                    Section {
                        LabelRow("Check Another Image", Icons.Outlined.Refresh, titleColor = MaterialTheme.colorScheme.primary, onClick = onCheckAnother)
                    }
                }
            }
            item { Spacer(Modifier.height(24.dp).navigationBarsPadding()) }
        }
    }
}

/** For posts with several images: every image with its verdict. Tap one to see its result. */
@Composable
private fun PostImageStrip(images: List<VerificationCase>, selection: Int, onSelect: (Int) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        images.forEachIndexed { index, image ->
            Column(
                Modifier
                    .clip(RoundedCornerShape(Metrics.thumbnailRadius))
                    .selectable(index == selection, role = Role.Tab) { onSelect(index) }
                    .semantics { contentDescription = "Image ${index + 1}: ${image.verdict.label}, ${image.confidencePercentage} percent" },
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Box(
                    Modifier.border(
                        3.dp,
                        if (index == selection) MaterialTheme.colorScheme.primary else Color.Transparent,
                        RoundedCornerShape(Metrics.thumbnailRadius),
                    ),
                ) { CaseThumbnail(image, size = 64.dp) }
                // The tile's description already says the verdict; don't read the short label too.
                Row(
                    Modifier.clearAndSetSemantics { },
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(image.verdict.icon, contentDescription = null, tint = image.verdict.textColor, modifier = Modifier.size(13.dp))
                    Text(image.verdict.shortLabel, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = image.verdict.textColor)
                }
            }
        }
    }
}

/** Content Credentials found in the photo's file: who made it and how, as the file itself claims. */
@Composable
private fun CredentialsSection(credentials: ContentCredentials) {
    val (text, color) = when (credentials.source) {
        ContentCredentials.Source.AI_GENERATED -> "Says it was generated by AI" to VerdictType.AI.textColor
        ContentCredentials.Source.AI_EDITED -> "Says it includes AI-generated parts" to VerdictType.TAMPERED.textColor
        ContentCredentials.Source.CAMERA -> "Says it was taken with a camera" to VerdictType.REAL.textColor
        ContentCredentials.Source.UNSPECIFIED -> null to colors.secondaryText
    }
    Section(
        header = "Content Credentials",
        footer = "Read from the photo's file. Look Again doesn't verify the signature yet, so treat this as a strong clue, not proof.",
    ) {
        val rows = buildList<@Composable () -> Unit> {
            if (text != null) add { BulletRow(text, Icons.Filled.Sell, color) }
            credentials.generator?.let { add { ValueRow("Made with", it) } }
            if (credentials.actions.isNotEmpty()) add { ValueRow("History", credentials.actions.joinToString(", ")) }
        }
        if (rows.isEmpty()) ValueRow("Found", "No details")
        rows.forEachIndexed { index, row ->
            if (index > 0) RowDivider()
            row()
        }
    }
}

/** The verdict, how sure the model is, and the one-paragraph explanation. */
@Composable
private fun VerdictSummary(item: VerificationCase) {
    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.semantics(mergeDescendants = true) { heading() },
        ) {
            Box(
                Modifier.size(Metrics.verdictTile).clip(RoundedCornerShape(Metrics.verdictTileRadius)).background(item.verdict.color),
                contentAlignment = Alignment.Center,
            ) { Icon(item.verdict.icon, contentDescription = null, tint = Color.White) }
            Column {
                Text(item.verdict.label, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = item.verdict.textColor)
                Text("${item.confidencePercentage}% confidence", style = MaterialTheme.typography.bodyMedium, color = item.verdict.textColor)
            }
        }
        Text(item.plainSummary, style = MaterialTheme.typography.bodyLarge)
    }
}

/** Where the image came from. */
@Composable
private fun SourceSection(item: VerificationCase, inShareSheet: Boolean) {
    val uriHandler = LocalUriHandler.current
    Section(header = "Source") {
        if (item.authorHandle.isEmpty()) {
            ValueRow("From", if (inShareSheet) "Shared image" else "Your photos")
        } else {
            ValueRow("Posted by", "@${item.authorHandle}")
        }
        RowDivider()
        ValueRow("Checked", item.timeAgo)
        if (item.imageUrl == null) {
            RowDivider()
            ValueRow("Photo", "Not included")
        }
        val postUrl = item.postUrl
        // Like the iOS share extension, the share screen stays a quick look and doesn't send you elsewhere.
        if (postUrl != null && !inShareSheet) {
            RowDivider(IconRowInset)
            LabelRow("Open on Bluesky", Icons.AutoMirrored.Outlined.OpenInNew, titleColor = MaterialTheme.colorScheme.primary) {
                runCatching { uriHandler.openUri(postUrl) }
            }
        }
    }
}

/**
 * The checked photo, shown whole (never cropped, since a crop could hide the
 * very edit being looked for), with the highlight overlay on top.
 */
@Composable
private fun ResultPhoto(viewModel: CheckResultsViewModel) {
    val image = viewModel.image
    when {
        image != null -> BoxWithConstraints(
            Modifier.fillMaxWidth().background(Color.Black),
            contentAlignment = Alignment.Center,
        ) {
            val aspect = image.width.toFloat() / image.height
            val width = min(maxWidth, Metrics.photoMaxHeight * aspect)
            val height = width / aspect
            val highlightOn = viewModel.layer == PhotoLayer.HIGHLIGHT
            Box(
                Modifier
                    .size(width, height)
                    .semantics {
                        contentDescription = "Checked photo"
                        stateDescription = if (highlightOn) "Highlight on" else ""
                    },
            ) {
                Image(image.asImageBitmap(), contentDescription = null, contentScale = ContentScale.FillBounds, modifier = Modifier.fillMaxSize())
                AnimatedVisibility(highlightOn, enter = fadeIn(), exit = fadeOut()) {
                    val heatmap = viewModel.item.heatmap
                    if (viewModel.showsHeatmap && heatmap != null) {
                        HeatmapOverlay(heatmap, image)
                    } else {
                        HighlightOverlay(viewModel.item.hotspot)
                    }
                }
            }
        }
        viewModel.imageFailed -> NoPhotoPlaceholder(
            viewModel.item.verdict,
            Modifier.fillMaxWidth().height(Metrics.placeholderHeight),
            glyphSize = 40.dp,
            caption = "Photo unavailable",
        )
        else -> Box(Modifier.fillMaxWidth().height(Metrics.placeholderHeight), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
    }
}

/** Places content at a rectangle given as fractions (0–1) of the parent, which is exactly the drawn image. */
@Composable
private fun NormalizedRect(x: Double, y: Double, width: Double, height: Double, content: @Composable () -> Unit) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        Box(
            Modifier
                .offset(maxWidth * x.toFloat(), maxHeight * y.toFloat())
                .size(maxWidth * width.toFloat(), maxHeight * height.toFloat()),
        ) { content() }
    }
}

/** Dims the photo and marks the region that drove the verdict, or says nothing was found. */
@Composable
private fun HighlightOverlay(hotspot: HotspotArea?) {
    Box(Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.3f)), contentAlignment = Alignment.Center) {
        if (hotspot != null) {
            NormalizedRect(hotspot.xRatio, hotspot.yRatio, hotspot.widthRatio, hotspot.heightRatio) {
                Box(Modifier.fillMaxSize().semantics { contentDescription = "Highlighted area: ${hotspot.label}" }) {
                    Canvas(Modifier.fillMaxSize()) {
                        val radius = androidx.compose.ui.geometry.CornerRadius(6.dp.toPx())
                        drawRoundRect(Palette.HotspotStroke.copy(alpha = 0.15f), cornerRadius = radius)
                        drawRoundRect(Palette.HotspotStroke, cornerRadius = radius, style = Stroke(2.dp.toPx()))
                    }
                    Text(
                        hotspot.label,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        modifier = Modifier
                            .padding(4.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(Palette.HotspotLabel)
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    )
                }
            }
        } else {
            OverlayCapsule("No signs of AI generation found", Icons.Filled.Verified, Palette.CleanBadge)
        }
    }
}

/**
 * Dims the photo and paints the detector's patch map over the part of the
 * image the model saw, red where patches pushed the verdict toward "AI".
 */
@Composable
private fun HeatmapOverlay(heatmap: PatchHeatmap, image: Bitmap) {
    val region = PatchHeatmap.coveredRegion(image.width, image.height)
    val cells = remember(heatmap) { heatmapBitmap(heatmap).asImageBitmap() }
    Box(
        Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.45f))
            .clearAndSetSemantics { contentDescription = "Heatmap of the areas that influenced the detector most" },
        contentAlignment = Alignment.BottomCenter,
    ) {
        NormalizedRect(region.x, region.y, region.width, region.height) {
            // Bilinear upscaling smooths the 24×24 grid; the blur (Android 12+) softens it further.
            Image(
                cells,
                contentDescription = null,
                contentScale = ContentScale.FillBounds,
                filterQuality = FilterQuality.High,
                modifier = Modifier
                    .fillMaxSize()
                    .then(if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Modifier.blur(6.dp) else Modifier),
            )
        }
        OverlayCapsule("Red areas influenced the detector most", Icons.Filled.LocalFireDepartment, Color.Black.copy(alpha = 0.65f))
    }
}

/** Cells below this share of the strongest one aren't drawn, so noise doesn't tint the whole photo. */
private const val HEATMAP_FLOOR = 0.2

/** Yellow for weaker influence through red for the strongest, so the most important areas stand out on any photo. */
private fun heatmapBitmap(heatmap: PatchHeatmap): Bitmap {
    val grid = PatchHeatmap.GRID_SIZE
    val pixels = IntArray(grid * grid)
    heatmap.intensities.forEachIndexed { index, value ->
        if (value < HEATMAP_FLOOR) return@forEachIndexed
        val t = ((value - HEATMAP_FLOOR) / (1 - HEATMAP_FLOOR)).coerceIn(0.0, 1.0)
        val hue = 0.14f * 360f * (1 - t.toFloat())
        val rgb = android.graphics.Color.HSVToColor(floatArrayOf(hue, 1f, 1f))
        val alpha = ((0.45 + 0.5 * t) * 255).toInt()
        pixels[index] = (alpha shl 24) or (rgb and 0xFFFFFF)
    }
    return Bitmap.createBitmap(pixels, grid, grid, Bitmap.Config.ARGB_8888)
}

@Composable
private fun OverlayCapsule(text: String, icon: androidx.compose.ui.graphics.vector.ImageVector, background: Color) {
    Row(
        Modifier
            .padding(10.dp)
            .clip(CircleShape)
            .background(background)
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Icon(icon, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
        Text(text, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = Color.White)
    }
}

/** Shown while a link or photo is being checked. */
@Composable
fun AnalyzingView(image: Bitmap?, onCancel: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier
            .fillMaxSize()
            .background(colors.groupedBackground)
            // Scrolls so Cancel stays reachable at large text sizes.
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
            .padding(top = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(24.dp),
    ) {
        if (image != null) {
            Image(
                image.asImageBitmap(),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.size(180.dp).clip(RoundedCornerShape(Metrics.photoRadius)),
            )
        }
        CircularProgressIndicator(Modifier.size(44.dp))
        Text("Checking image…", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Text(
            "Looking at lighting, edges and texture.",
            style = MaterialTheme.typography.bodyMedium,
            color = colors.secondaryText,
            textAlign = TextAlign.Center,
        )
        OutlinedButton(onClick = onCancel) { Text("Cancel") }
    }
}
