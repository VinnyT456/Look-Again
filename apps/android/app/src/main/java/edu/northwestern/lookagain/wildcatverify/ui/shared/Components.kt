package edu.northwestern.lookagain.wildcatverify.ui.shared

import android.graphics.Bitmap
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBackIos
import androidx.compose.material.icons.automirrored.outlined.HelpOutline
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LargeTopAppBar
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.TopAppBarScrollBehavior
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.R
import edu.northwestern.lookagain.wildcatverify.data.ImageRepository
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.Palette
import edu.northwestern.lookagain.wildcatverify.ui.theme.background
import edu.northwestern.lookagain.wildcatverify.ui.theme.color
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.ui.theme.icon
import edu.northwestern.lookagain.wildcatverify.ui.theme.textColor
import kotlinx.coroutines.delay

/** The image cache, provided at the root so shared views (also used by the share screen) can load photos. */
val LocalImages = compositionLocalOf { ImageRepository() }

/** Preferences passed down, so shared views don't depend on the settings store. Defaults match a fresh install. */
val LocalHapticsEnabled = compositionLocalOf { true }
val LocalHeatmapEnabled = compositionLocalOf { true }

/** The app mark: the FaceCheck magnifier on its tile (with a dark variant). */
@Composable
fun LogoTile(size: Dp = Metrics.logo) {
    Image(
        painter = painterResource(R.drawable.face_check_magnifier),
        contentDescription = null,
        contentScale = ContentScale.Crop,
        modifier = Modifier
            .size(size)
            .clip(RoundedCornerShape(size * 0.24f)),
    )
}

/**
 * Top-level screen chrome, like the iOS app: the logo leading, round About
 * button trailing, and a large title under them that collapses on scroll.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BrandTopBar(
    title: String,
    onShowAbout: () -> Unit,
    scrollBehavior: TopAppBarScrollBehavior,
    actions: @Composable () -> Unit = {},
) {
    val collapsed = scrollBehavior.state.collapsedFraction > 0.5f
    LargeTopAppBar(
        title = {
            Text(
                title,
                style = if (collapsed) MaterialTheme.typography.titleMedium else MaterialTheme.typography.displaySmall,
                fontWeight = if (collapsed) FontWeight.SemiBold else FontWeight.Bold,
            )
        },
        navigationIcon = { Box(Modifier.padding(start = 16.dp, end = 4.dp)) { LogoTile() } },
        actions = {
            actions()
            GlassCircleButton(Icons.AutoMirrored.Outlined.HelpOutline, "About WildcatVerify", onShowAbout, Modifier.padding(end = 16.dp))
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = colors.groupedBackground,
            scrolledContainerColor = colors.bar,
        ),
        scrollBehavior = scrollBehavior,
    )
}

/** Centered title with a round back button, like a pushed iOS screen. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PushedTopBar(title: String, onBack: (() -> Unit)?, actions: @Composable () -> Unit = {}) {
    CenterAlignedTopAppBar(
        title = { Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) },
        navigationIcon = {
            if (onBack != null) {
                GlassCircleButton(Icons.AutoMirrored.Filled.ArrowBackIos, "Back", onBack, Modifier.padding(start = 16.dp), iconInset = 3.dp)
            }
        },
        actions = { Row(Modifier.padding(end = 16.dp)) { actions() } },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = colors.groupedBackground),
    )
}

/** Full-width Northwestern Purple button; grey while disabled. Dips slightly while pressed. */
@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    trailingIcon: ImageVector? = null,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.98f else 1f, tween(150), label = "press")
    Button(
        onClick = onClick,
        enabled = enabled,
        interactionSource = interaction,
        shape = RoundedCornerShape(Metrics.fieldRadius),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (pressed) Palette.NorthwesternPurpleDark else Palette.NorthwesternPurple,
            contentColor = Color.White,
            disabledContainerColor = colors.fill,
            disabledContentColor = colors.secondaryText,
        ),
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = Metrics.controlHeight)
            .graphicsLayer { scaleX = scale; scaleY = scale },
    ) {
        Text(text, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)
        if (trailingIcon != null) {
            Spacer(Modifier.size(6.dp))
            Icon(trailingIcon, contentDescription = null, modifier = Modifier.size(20.dp))
        }
    }
}

/** Compact verdict marker for list rows. Icon plus word, so it never relies on colour alone. */
@Composable
fun VerdictBadge(verdict: VerdictType) {
    Row(
        Modifier
            .clip(CircleShape)
            .background(verdict.background)
            .padding(horizontal = 8.dp, vertical = 3.dp)
            .clearAndSetSemantics { contentDescription = verdict.label },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Icon(verdict.icon, contentDescription = null, tint = verdict.textColor, modifier = Modifier.size(13.dp))
        Text(verdict.shortLabel, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = verdict.textColor)
    }
}

/** Stand-in for a case without a photo: the verdict's tint and glyph, so rows stay scannable by result. */
@Composable
fun NoPhotoPlaceholder(verdict: VerdictType, modifier: Modifier = Modifier, glyphSize: Dp = 26.dp, caption: String? = null) {
    Box(
        modifier
            .background(verdict.background)
            .then(if (caption != null) Modifier.semantics { contentDescription = caption } else Modifier.clearAndSetSemantics { }),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(verdict.icon, contentDescription = null, tint = verdict.color, modifier = Modifier.size(glyphSize))
            if (caption != null) {
                Text(caption, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = verdict.textColor)
            }
        }
    }
}

/** An image from a URL, decoded off the main thread at the size it's drawn, with a neutral placeholder. */
@Composable
fun RemoteImage(url: String?, pointSize: Dp, modifier: Modifier = Modifier, contentScale: ContentScale = ContentScale.Crop) {
    val images = LocalImages.current
    val pixels = with(LocalDensity.current) { pointSize.roundToPx() }
    var image by remember(url) { mutableStateOf<Bitmap?>(url?.let { images.cachedImage(it, pixels) }) }
    LaunchedEffect(url, pixels) {
        if (url != null && image == null) image = runCatching { images.image(url, pixels) }.getOrNull()
    }
    Box(modifier.background(colors.fill)) {
        image?.let {
            Image(it.asImageBitmap(), contentDescription = null, contentScale = contentScale, modifier = Modifier.fillMaxSize())
        }
    }
}

/** A case's photo, decoded at thumbnail size, or its verdict placeholder. */
@Composable
fun CaseThumbnail(item: VerificationCase, size: Dp = Metrics.thumbnail) {
    val images = LocalImages.current
    val pixels = with(LocalDensity.current) { size.roundToPx() }
    val url = item.imageUrl
    var image by remember(url) { mutableStateOf(url?.let { images.cachedImage(it, pixels) ?: images.cachedImage(it) }) }
    var failed by remember(url) { mutableStateOf(false) }
    LaunchedEffect(url) {
        if (url != null && image == null) {
            image = runCatching { images.image(url, pixels) }.getOrNull()
            failed = image == null
        }
    }
    Box(Modifier.size(size).clip(RoundedCornerShape(Metrics.thumbnailRadius)), contentAlignment = Alignment.Center) {
        val current = image
        when {
            current != null -> Image(current.asImageBitmap(), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
            url == null || failed -> NoPhotoPlaceholder(item.verdict, Modifier.fillMaxSize())
            else -> Box(Modifier.fillMaxSize().background(colors.fill), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
            }
        }
    }
}

/** A checked image in a list: thumbnail, title, source and verdict. */
@Composable
fun CaseRow(item: VerificationCase) {
    Row(
        Modifier.semantics(mergeDescendants = true) {},
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CaseThumbnail(item)
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(item.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
            // Handles are identifiers: keep them on one line.
            Text(item.displayHandle, style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText, maxLines = 1, overflow = TextOverflow.MiddleEllipsis)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                VerdictBadge(item.verdict)
                Text(
                    if (item.isDemo) "${item.timeAgo} · Demo" else item.timeAgo,
                    style = MaterialTheme.typography.bodySmall,
                    color = colors.secondaryText,
                )
            }
        }
    }
}

/** Empty or error state: icon, title, description and an optional action. */
@Composable
fun ContentUnavailable(
    title: String,
    icon: ImageVector,
    description: String? = null,
    modifier: Modifier = Modifier,
    action: Pair<String, () -> Unit>? = null,
) {
    Column(
        modifier.fillMaxSize().padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(icon, contentDescription = null, tint = colors.secondaryText, modifier = Modifier.size(52.dp))
        Spacer(Modifier.height(16.dp))
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
        if (description != null) {
            Spacer(Modifier.height(8.dp))
            Text(description, style = MaterialTheme.typography.bodyLarge, color = colors.secondaryText, textAlign = TextAlign.Center, modifier = Modifier.widthIn(max = 420.dp))
        }
        if (action != null) {
            Spacer(Modifier.height(16.dp))
            Button(onClick = action.second) { Text(action.first) }
        }
    }
}

/**
 * Fades a section up into place the first time it appears, delayed by its
 * position so a screen assembles top to bottom.
 */
@Composable
fun Modifier.staggeredAppear(index: Int): Modifier {
    var shown by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        delay(index * 40L)
        shown = true
    }
    val progress by animateFloatAsState(
        if (shown) 1f else 0f,
        spring(dampingRatio = 0.85f, stiffness = Spring.StiffnessMediumLow),
        label = "appear",
    )
    return graphicsLayer {
        alpha = progress
        translationY = (1 - progress) * 14.dp.toPx()
    }
}

/**
 * A verdict pill laid over a photo, like Auto-Label's badges: "✓ Real 92%",
 * "✦ AI 97%", or "Checking…" while `item` is null.
 */
@Composable
fun VerdictPill(item: VerificationCase?, modifier: Modifier = Modifier) {
    val background = when (item?.verdict) {
        null -> Color.Black.copy(alpha = 0.7f)
        else -> item.verdict.color.copy(alpha = 0.94f)
    }
    val text = when (item?.verdict) {
        null -> "Checking…"
        VerdictType.REAL -> "✓ Real ${item.confidencePercentage}%"
        VerdictType.TAMPERED -> "⚠ Edited ${item.confidencePercentage}%"
        VerdictType.AI -> "✦ AI ${item.confidencePercentage}%"
    }
    Row(
        modifier
            .clip(CircleShape)
            .background(background)
            .padding(horizontal = 10.dp, vertical = 5.dp)
            .clearAndSetSemantics {
                contentDescription = item?.let { "${it.verdict.label}, ${it.confidencePercentage} percent confidence" } ?: "Checking this photo"
            },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        if (item == null) CircularProgressIndicator(Modifier.size(12.dp), color = Color.White, strokeWidth = 1.5.dp)
        Text(text, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = Color.White)
    }
}
