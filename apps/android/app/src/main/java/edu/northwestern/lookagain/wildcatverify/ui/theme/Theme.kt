package edu.northwestern.lookagain.wildcatverify.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Camera
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Draw
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Flag
import androidx.compose.material.icons.outlined.Grid4x4
import androidx.compose.material.icons.outlined.PanTool
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.WbSunny
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.WbTwilight
import androidx.compose.material.icons.outlined.CropPortrait
import androidx.compose.material.icons.outlined.Sell
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Forum
import androidx.compose.material.icons.outlined.Subtitles
import androidx.compose.material.icons.outlined.PersonSearch
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.material3.Typography
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import edu.northwestern.lookagain.wildcatverify.model.ClueIcon
import edu.northwestern.lookagain.wildcatverify.model.VerdictType

/**
 * Brand and verdict colors, matching the iOS asset catalog (light and dark).
 * Brand lives in the logo, the purple tint and the verdict colours; everything
 * else is plain grouped-list chrome.
 */
object Palette {
    val NorthwesternPurple = Color(0xFF4E2A84)
    val NorthwesternPurpleDark = Color(0xFF3D2068)
    val CleanBadge = Color(0xFF15803D)
    val HotspotStroke = Color(0xFFEF4444)
    val HotspotLabel = Color(0xFFB91C1C)
}

/** Colors that differ between light and dark. */
data class AppColors(
    val accent: Color,
    /** Navigation bar material over the grouped background. */
    val bar: Color,
    /** Selected-tab pill and segmented-control track. */
    val pill: Color,
    val purpleTint: Color,
    val groupedBackground: Color,
    val card: Color,
    val fill: Color,
    val separator: Color,
    val secondaryText: Color,
    val dark: Boolean,
)

private val LightColors = AppColors(
    accent = Color(0xFF4E2A84),
    bar = Color(0xFFF7F7FA),
    pill = Color(0xFFE5E5EA),
    purpleTint = Color(0xFFEADDFF),
    groupedBackground = Color(0xFFF2F2F7),
    card = Color.White,
    fill = Color(0x1F767680),
    separator = Color(0x4A3C3C43),
    secondaryText = Color(0x993C3C43),
    dark = false,
)

private val DarkColors = AppColors(
    accent = Color(0xFFC4B0EA),
    bar = Color(0xFF121214),
    pill = Color(0xFF3A3A3C),
    purpleTint = Color(0xFF3A2A55),
    groupedBackground = Color.Black,
    card = Color(0xFF1C1C1E),
    fill = Color(0x3D767680),
    separator = Color(0x99545458),
    secondaryText = Color(0x99EBEBF5),
    dark = true,
)

val LocalAppColors = staticCompositionLocalOf { LightColors }

val colors: AppColors
    @Composable @ReadOnlyComposable get() = LocalAppColors.current

/** Shared layout constants, so every screen rounds and sizes the same way. */
object Metrics {
    /** Thumbnails in lists. */
    val thumbnail = 56.dp
    val thumbnailRadius = 10.dp
    /** Verdict glyph tile on the results screen. */
    val verdictTile = 44.dp
    val verdictTileRadius = 12.dp
    /** Tallest the checked photo is drawn on the results screen. */
    val photoMaxHeight = 360.dp
    /** Height of the placeholder when a case has no photo. */
    val placeholderHeight = 160.dp
    val photoRadius = 12.dp
    /** Logo tile in the top bar. */
    val logo = 30.dp
    /** Logo tile in the Check page header. */
    val headerLogo = 44.dp
    /** Major containers, such as the Check card. */
    val cardRadius = 24.dp
    /** Inputs, buttons and the photo drop zone. */
    val fieldRadius = 16.dp
    /** Inset-grouped list sections. */
    val sectionRadius = 26.dp
    /** Minimum height for full-width buttons and inputs. */
    val controlHeight = 52.dp
}

/** Base hue for solid fills, borders and glyphs. */
val VerdictType.color: Color
    get() = when (this) {
        VerdictType.REAL -> Color(0xFF16A34A)
        VerdictType.TAMPERED -> Color(0xFFD97706)
        VerdictType.AI -> Color(0xFFDC2626)
    }

/** Contrast-safe hue for text drawn on [background]. */
val VerdictType.textColor: Color
    @Composable @ReadOnlyComposable get() = if (colors.dark) {
        when (this) {
            VerdictType.REAL -> Color(0xFF4ADE80)
            VerdictType.TAMPERED -> Color(0xFFFBBF24)
            VerdictType.AI -> Color(0xFFF87171)
        }
    } else {
        when (this) {
            VerdictType.REAL -> Color(0xFF166534)
            VerdictType.TAMPERED -> Color(0xFF92400E)
            VerdictType.AI -> Color(0xFFB91C1C)
        }
    }

val VerdictType.background: Color
    @Composable @ReadOnlyComposable get() = if (colors.dark) {
        when (this) {
            VerdictType.REAL -> Color(0x59064E3B)
            VerdictType.TAMPERED -> Color(0x5978350F)
            VerdictType.AI -> Color(0x597F1D1D)
        }
    } else {
        when (this) {
            VerdictType.REAL -> Color(0xFFECFDF5)
            VerdictType.TAMPERED -> Color(0xFFFFFBEB)
            VerdictType.AI -> Color(0xFFFEF2F2)
        }
    }

val VerdictType.icon: ImageVector
    get() = when (this) {
        VerdictType.REAL -> Icons.Filled.VerifiedUser
        VerdictType.TAMPERED -> Icons.Filled.Warning
        VerdictType.AI -> Icons.Filled.Memory
    }

/** Glyph for each finding. */
val VerdictType.findingIcon: ImageVector
    get() = if (this == VerdictType.REAL) Icons.Outlined.CheckCircle else Icons.Outlined.ErrorOutline

val ClueIcon.vector: ImageVector
    get() = when (this) {
        ClueIcon.SUN -> Icons.Outlined.WbSunny
        ClueIcon.TOUCH -> Icons.Outlined.TouchApp
        ClueIcon.PEOPLE -> Icons.Outlined.Groups
        ClueIcon.GRID -> Icons.Outlined.Grid4x4
        ClueIcon.GLASSES -> Icons.Outlined.Visibility
        ClueIcon.HAND -> Icons.Outlined.PanTool
        ClueIcon.SHADOW -> Icons.Outlined.WbTwilight
        ClueIcon.APERTURE -> Icons.Outlined.Camera
        ClueIcon.COPY -> Icons.Outlined.ContentCopy
        ClueIcon.FLAG -> Icons.Outlined.Flag
        ClueIcon.FRAME -> Icons.Outlined.CropPortrait
        ClueIcon.SCRIBBLE -> Icons.Outlined.Draw
        ClueIcon.TAG -> Icons.Outlined.Sell
        ClueIcon.FIRST_POST -> Icons.Outlined.History
        ClueIcon.REPLIES -> Icons.Outlined.Forum
        ClueIcon.CALENDAR -> Icons.Outlined.CalendarMonth
        ClueIcon.CAMERA -> Icons.Outlined.CameraAlt
        ClueIcon.ALT_TEXT -> Icons.Outlined.Subtitles
        ClueIcon.AI -> VerdictType.AI.icon
        ClueIcon.EDITED -> VerdictType.TAMPERED.icon
        ClueIcon.SOURCE -> Icons.Outlined.PersonSearch
    }

/** iOS text styles (Large Title, Title 2, Headline, Body, Subheadline, Footnote, Caption) on the system font. */
private val IosTypography = Typography().let { base ->
    base.copy(
        displaySmall = base.displaySmall.copy(fontSize = 34.sp, lineHeight = 41.sp, fontWeight = FontWeight.Bold),
        headlineSmall = base.headlineSmall.copy(fontSize = 22.sp, lineHeight = 28.sp),
        titleLarge = base.titleLarge.copy(fontSize = 20.sp, lineHeight = 25.sp),
        titleMedium = base.titleMedium.copy(fontSize = 17.sp, lineHeight = 22.sp, letterSpacing = 0.sp),
        bodyLarge = base.bodyLarge.copy(fontSize = 17.sp, lineHeight = 22.sp, letterSpacing = 0.sp),
        bodyMedium = base.bodyMedium.copy(fontSize = 15.sp, lineHeight = 20.sp, letterSpacing = 0.sp),
        bodySmall = base.bodySmall.copy(fontSize = 13.sp, lineHeight = 18.sp, letterSpacing = 0.sp),
        labelLarge = base.labelLarge.copy(fontSize = 15.sp, letterSpacing = 0.sp),
        labelMedium = base.labelMedium.copy(fontSize = 12.sp, letterSpacing = 0.sp),
        labelSmall = base.labelSmall.copy(fontSize = 11.sp, letterSpacing = 0.sp),
    )
}

@Composable
fun WildcatTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val app = if (dark) DarkColors else LightColors
    val scheme = if (dark) {
        darkColorScheme(
            primary = app.accent,
            onPrimary = Color(0xFF21104A),
            primaryContainer = Palette.NorthwesternPurple,
            onPrimaryContainer = Color.White,
            secondaryContainer = app.purpleTint,
            onSecondaryContainer = Color.White,
            background = app.groupedBackground,
            surface = app.groupedBackground,
            surfaceContainer = app.card,
            surfaceContainerLow = app.card,
            surfaceContainerHigh = app.card,
            surfaceContainerHighest = Color(0xFF2C2C2E),
            outlineVariant = app.separator,
        )
    } else {
        lightColorScheme(
            primary = Palette.NorthwesternPurple,
            onPrimary = Color.White,
            primaryContainer = Palette.NorthwesternPurple,
            onPrimaryContainer = Color.White,
            secondaryContainer = app.purpleTint,
            onSecondaryContainer = Palette.NorthwesternPurpleDark,
            background = app.groupedBackground,
            surface = app.groupedBackground,
            surfaceContainer = app.card,
            surfaceContainerLow = app.card,
            surfaceContainerHigh = app.card,
            surfaceContainerHighest = Color(0xFFE5E5EA),
            outlineVariant = app.separator,
        )
    }
    androidx.compose.runtime.CompositionLocalProvider(LocalAppColors provides app) {
        MaterialTheme(colorScheme = scheme, typography = IosTypography, content = content)
    }
}
