package edu.northwestern.lookagain.wildcatverify.ui.shared

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors

/*
 * Inset-grouped list building blocks, the Android counterpart of the iOS app's
 * `List` + `.insetGrouped` screens: a header, rounded rows on a card, a footer.
 */

/** Gutter around sections; matches iOS's 16 pt inset. */
val SectionGutter = 16.dp

/** A section as one lazy item. */
fun LazyListScope.section(
    key: Any? = null,
    header: String? = null,
    footer: String? = null,
    background: Color? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    item(key = key) {
        Section(header = header, footer = footer, background = background, content = content)
    }
}

@Composable
fun Section(
    header: String? = null,
    footer: String? = null,
    background: Color? = null,
    headerContent: (@Composable () -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .widthIn(max = 720.dp)
            .padding(horizontal = SectionGutter)
            .padding(top = if (header != null || headerContent != null) 24.dp else 18.dp),
    ) {
        if (headerContent != null) {
            Box(Modifier.padding(start = 20.dp, bottom = 8.dp)) { headerContent() }
        } else if (header != null) {
            SectionHeader(header)
        }
        Column(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(Metrics.sectionRadius))
                .background(background ?: colors.card),
            content = content,
        )
        if (footer != null) {
            Text(
                footer,
                style = MaterialTheme.typography.bodySmall,
                color = colors.secondaryText,
                modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp),
            )
        }
    }
}

/** iOS 26 section header: title case, semibold, secondary colour. */
@Composable
fun SectionHeader(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        color = colors.secondaryText,
        modifier = Modifier
            .padding(start = 20.dp, bottom = 8.dp)
            .semantics { heading() },
    )
}

/** A thin line between rows, inset like iOS separators (under the text on rows with an icon: [IconRowInset]). */
@Composable
fun RowDivider(start: androidx.compose.ui.unit.Dp = 16.dp) {
    HorizontalDivider(
        Modifier.padding(start = start, end = 16.dp),
        thickness = 0.5.dp,
        color = colors.separator,
    )
}

/** A row's padding and minimum touch height. */
@Composable
fun ListRow(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    onClickLabel: String? = null,
    padding: PaddingValues = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
    content: @Composable RowScope.() -> Unit,
) {
    Row(
        modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp)
            .then(if (onClick != null) Modifier.clickable(onClickLabel = onClickLabel, role = Role.Button, onClick = onClick) else Modifier)
            .padding(padding),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        content = content,
    )
}

/** Icon + title (+ subtitle), with an optional trailing chevron for pushed screens. */
@Composable
fun LabelRow(
    title: String,
    icon: ImageVector? = null,
    subtitle: String? = null,
    iconTint: Color = MaterialTheme.colorScheme.primary,
    titleColor: Color = MaterialTheme.colorScheme.onSurface,
    chevron: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    ListRow(onClick = onClick) {
        if (icon != null) Icon(icon, contentDescription = null, tint = iconTint, modifier = Modifier.size(22.dp))
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge, color = titleColor)
            if (subtitle != null) {
                Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
            }
        }
        if (chevron) {
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.secondaryText.copy(alpha = 0.6f))
        }
    }
}

/** "Label ……… value", like SwiftUI's LabeledContent. */
@Composable
fun ValueRow(label: String, value: String) {
    ListRow {
        Text(label, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Text(
            value,
            style = MaterialTheme.typography.bodyLarge,
            color = colors.secondaryText,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** Opens a web page in the browser. */
@Composable
fun LinkRow(title: String, url: String, icon: ImageVector? = null) {
    val uriHandler = LocalUriHandler.current
    ListRow(onClick = { runCatching { uriHandler.openUri(url) } }) {
        if (icon != null) Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
        Text(title, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f))
        Icon(Icons.AutoMirrored.Outlined.OpenInNew, contentDescription = "Opens in browser", tint = colors.secondaryText, modifier = Modifier.size(18.dp))
    }
}

@Composable
fun ToggleRow(title: String, icon: ImageVector, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    ListRow(onClick = { onCheckedChange(!checked) }) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
        Text(title, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        IosSwitch(checked)
    }
}

/** Plain paragraph in a section. */
@Composable
fun TextRow(text: String, color: Color = MaterialTheme.colorScheme.onSurface) {
    ListRow { Text(text, style = MaterialTheme.typography.bodyLarge, color = color) }
}

/** A list-style label: small icon, then wrapping text. */
@Composable
fun BulletRow(text: String, icon: ImageVector, tint: Color = MaterialTheme.colorScheme.primary) {
    ListRow {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(20.dp).align(Alignment.Top))
        Text(text, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
    }
}

/** Places rows with dividers between them. */
@Composable
fun ColumnScope.Rows(vararg rows: @Composable () -> Unit) {
    rows.forEachIndexed { index, row ->
        if (index > 0) RowDivider()
        row()
    }
}

@Composable
fun BoldText(text: String, modifier: Modifier = Modifier) {
    Text(text, modifier = modifier, fontWeight = FontWeight.SemiBold)
}

@Composable
fun VerticalSpace(height: Int) = Spacer(Modifier.size(height.dp))

@Composable
fun HorizontalSpace(width: Int) = Spacer(Modifier.width(width.dp))
