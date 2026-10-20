package edu.northwestern.lookagain.wildcatverify.ui.shared

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors

/*
 * Controls drawn the way the iOS app shows them, so both apps look alike.
 */

/** iOS's green on/off switch (51 × 31). The row around it handles the tap. */
@Composable
fun IosSwitch(checked: Boolean, modifier: Modifier = Modifier) {
    val track by animateColorAsState(if (checked) Color(0xFF34C759) else colors.pill, tween(200), label = "track")
    val offset by animateDpAsState(if (checked) 22.dp else 2.dp, spring(dampingRatio = 0.7f, stiffness = 600f), label = "thumb")
    Box(
        modifier
            .size(51.dp, 31.dp)
            .clip(CircleShape)
            .background(track)
            .semantics { stateDescription = if (checked) "On" else "Off" },
    ) {
        Box(
            Modifier
                .offset(x = offset, y = 2.dp)
                .size(27.dp)
                .shadow(2.dp, CircleShape)
                .background(Color.White, CircleShape),
        )
    }
}

/** iOS segmented control: a grey track with a white, raised pill on the selected item. */
@Composable
fun <T> IosSegmentedControl(
    options: List<T>,
    selected: T,
    label: (T) -> String,
    onSelect: (T) -> Unit,
    modifier: Modifier = Modifier,
) {
    val index = options.indexOf(selected).coerceAtLeast(0)
    BoxWithConstraints(
        modifier
            .fillMaxWidth()
            .height(34.dp)
            .clip(RoundedCornerShape(9.dp))
            .background(colors.pill)
            .padding(2.dp),
    ) {
        val segment = maxWidth / options.size
        val pillOffset by animateDpAsState(segment * index, spring(dampingRatio = 0.8f, stiffness = 500f), label = "pill")
        Box(
            Modifier
                .offset(x = pillOffset)
                .width(segment)
                .fillMaxHeight()
                .shadow(1.dp, RoundedCornerShape(7.dp))
                .background(if (colors.dark) Color(0xFF636366) else Color.White, RoundedCornerShape(7.dp)),
        )
        Row(Modifier.fillMaxWidth().fillMaxHeight()) {
            options.forEach { option ->
                val isSelected = option == selected
                Box(
                    Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .clickable(remember { MutableInteractionSource() }, indication = null) { onSelect(option) }
                        .semantics {
                            role = Role.Tab
                            this.selected = isSelected
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        label(option),
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
                    )
                }
            }
        }
    }
}

/** iOS 26's round "glass" toolbar button: white circle, soft shadow, dark glyph. */
@Composable
fun GlassCircleButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    size: Dp = 44.dp,
    tint: Color = MaterialTheme.colorScheme.onSurface,
    /** Nudges glyphs that aren't optically centered, like the back chevron. */
    iconInset: Dp = 0.dp,
) {
    Box(
        modifier
            .size(size)
            .shadow(6.dp, CircleShape, ambientColor = Color.Black.copy(alpha = 0.12f), spotColor = Color.Black.copy(alpha = 0.12f))
            .clip(CircleShape)
            .background(if (colors.dark) Color(0xFF2C2C2E) else Color.White)
            .border(0.5.dp, colors.separator.copy(alpha = colors.separator.alpha * 0.4f), CircleShape)
            .clickable(role = Role.Button, onClickLabel = contentDescription, onClick = onClick)
            .semantics { this.contentDescription = contentDescription },
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.padding(start = iconInset).size(size * 0.5f))
    }
}

/**
 * A tab's stack of pushed screens: pushes slide in from the right over the
 * screen below, pops slide back out, like a UINavigationController.
 */
@Composable
fun <T> NavStack(path: List<T>, root: @Composable () -> Unit, screen: @Composable (T) -> Unit) {
    AnimatedContent(
        targetState = path,
        contentKey = { it.size to it.lastOrNull() },
        transitionSpec = {
            val push = targetState.size >= initialState.size
            val duration = 320
            if (push) {
                slideInHorizontally(tween(duration)) { it } togetherWith
                    slideOutHorizontally(tween(duration)) { -it / 3 } + fadeOut(tween(duration), targetAlpha = 0.6f)
            } else {
                slideInHorizontally(tween(duration)) { -it / 3 } + fadeIn(tween(duration), initialAlpha = 0.6f) togetherWith
                    slideOutHorizontally(tween(duration)) { it }
            }.apply { targetContentZIndex = if (push) 1f else -1f }
        },
        label = "stack",
    ) { stack ->
        val top = stack.lastOrNull()
        if (top == null) root() else screen(top)
    }
}

/** Separators start under the text, not the icon, on rows with a leading icon. */
val IconRowInset = 52.dp
