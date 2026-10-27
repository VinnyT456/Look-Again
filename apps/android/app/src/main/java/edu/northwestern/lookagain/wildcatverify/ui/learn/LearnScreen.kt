package edu.northwestern.lookagain.wildcatverify.ui.learn

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animate
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.focusable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.Reply
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.Image
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.isSpecified
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.collapse
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.expand
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import edu.northwestern.lookagain.wildcatverify.model.ClueGroup
import edu.northwestern.lookagain.wildcatverify.model.PracticeAnswer
import edu.northwestern.lookagain.wildcatverify.model.PracticeHotspot
import edu.northwestern.lookagain.wildcatverify.model.PracticeQuestion
import edu.northwestern.lookagain.wildcatverify.ui.shared.BrandTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.IconRowInset
import edu.northwestern.lookagain.wildcatverify.ui.shared.IosSegmentedControl
import edu.northwestern.lookagain.wildcatverify.ui.shared.ListRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LocalHapticsEnabled
import edu.northwestern.lookagain.wildcatverify.ui.shared.LogoTile
import edu.northwestern.lookagain.wildcatverify.ui.shared.NavStack
import edu.northwestern.lookagain.wildcatverify.ui.shared.PrimaryButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.Palette
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.ui.theme.vector
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.LearnRoute
import edu.northwestern.lookagain.wildcatverify.viewmodel.LearnViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.PracticeViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Learn to spot fakes: a Look Again round played in place, and the clue guide. */
@Composable
fun LearnScreen(app: AppViewModel) {
    val viewModel = app.learn
    val pop = { viewModel.path = viewModel.path.dropLast(1) }
    BackHandler(enabled = viewModel.path.isNotEmpty(), onBack = pop)

    NavStack(viewModel.path, root = { LearnRoot(app) }, screen = { route ->
        when (route) {
            is LearnRoute.ClueGuide -> ClueGuideScreen(viewModel.clueGroups, route.groupId, onBack = pop)
        }
    })
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LearnRoot(app: AppViewModel) {
    val viewModel = app.learn
    val practice = viewModel.practice
    // Kept on the view model: this screen leaves composition while the Clue Guide is pushed.
    val scroll = viewModel.scroll
    val haptics = LocalHapticFeedback.current
    val hapticsEnabled = LocalHapticsEnabled.current
    val answers = remember { BringIntoViewRequester() }

    // A new post, or a new round, starts at the top of the card.
    val position = practice.roundNumber to practice.index
    LaunchedEffect(position) {
        val previous = viewModel.shownPosition
        viewModel.shownPosition = position
        if (previous != null && previous != position) scroll.animateScrollTo(0)
    }
    // Once per answer, not again when coming back to the tab.
    LaunchedEffect(practice.answerCount) {
        if (practice.answerCount <= viewModel.handledAnswerCount) return@LaunchedEffect
        viewModel.handledAnswerCount = practice.answerCount
        if (hapticsEnabled) {
            haptics.performHapticFeedback(if (practice.lastAnswerWasCorrect) HapticFeedbackType.Confirm else HapticFeedbackType.Reject)
        }
        // Bring the answers and the result into view once they've laid out.
        delay(100)
        answers.bringIntoView()
    }

    val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior()
    Scaffold(
        modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
        containerColor = colors.groupedBackground,
        topBar = { BrandTopBar("Learn", app::showAbout, scrollBehavior) },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(scroll)
                .padding(16.dp)
                .navigationBarsPadding(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Column(Modifier.widthIn(max = 640.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(32.dp)) {
                PracticeRoundCard(viewModel, answers)
                ClueIndex(viewModel.clueGroups, onOpen = viewModel::openGuide)
            }
        }
    }
}

/** Look Again on the Learn home. The whole round happens here: read the post, answer, see why, next. */
@Composable
private fun PracticeRoundCard(viewModel: LearnViewModel, answers: BringIntoViewRequester) {
    val practice = viewModel.practice
    val picked = (practice.phase as? PracticeViewModel.Phase.Revealed)?.picked
    val showingDefinitions = viewModel.showsDefinitions
    val toggleDefinitions = { viewModel.showsDefinitions = !showingDefinitions }

    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(Metrics.cardRadius))
            .background(colors.card)
            .padding(20.dp)
            .animateContentSize(),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        val title = @Composable { modifier: Modifier ->
            Text(
                "Look Again",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                modifier = modifier.semantics { heading() },
            )
        }
        val progress = @Composable {
            if (practice.isInProgress) {
                Text(practice.progressText, style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText, modifier = Modifier.clearAndSetSemantics { })
            }
        }
        // At the largest text sizes the progress goes under the title.
        if (isLargeText()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                title(Modifier)
                progress()
            }
        } else {
            Row(verticalAlignment = Alignment.CenterVertically) {
                title(Modifier.weight(1f))
                progress()
            }
        }

        val question = practice.current
        if (practice.phase == PracticeViewModel.Phase.Finished) {
            PracticeSummary(viewModel)
        } else if (question != null) {
            if (practice.isInProgress) {
                RoundDots(practice)
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(
                        "Is each post real, edited, made by AI, or a real photo with a false story? ${PracticeViewModel.ROUND_LENGTH} posts, about two minutes.",
                        color = colors.secondaryText,
                    )
                    Row(
                        Modifier
                            .clickable(role = Role.Button, onClickLabel = if (showingDefinitions) "Hide" else "Show", onClick = toggleDefinitions)
                            .padding(vertical = 6.dp)
                            .semantics {
                                stateDescription = if (showingDefinitions) "Expanded" else "Collapsed"
                                if (showingDefinitions) collapse { toggleDefinitions(); true } else expand { toggleDefinitions(); true }
                            },
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text("What the answers mean", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary, modifier = Modifier.weight(1f))
                        Icon(if (showingDefinitions) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    }
                    AnimatedVisibility(showingDefinitions) {
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            PracticeAnswer.entries.forEach { answer ->
                                Column(Modifier.semantics(mergeDescendants = true) { }) {
                                    Text(answer.label, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                                    Text(answer.definition, style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
                                }
                            }
                        }
                    }
                }
            }

            AnimatedContent(question, contentKey = { it.id }, transitionSpec = { fadeIn(tween(250)) togetherWith fadeOut(tween(150)) }, label = "post") { shown ->
                PracticePostCard(shown, showsHotspots = picked != null)
            }

            // Brought into view after each answer, so the result and Next Post show without scrolling.
            Column(Modifier.bringIntoViewRequester(answers), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                PracticeAnswerButtons(picked, question.answer, onSelect = practice::select)

                if (picked != null) {
                    PracticeFeedback(question, picked, practice.answerCount)
                    PrimaryButton(
                        if (practice.isLastQuestion) "See Results" else "Next Post",
                        onClick = practice::next,
                        trailingIcon = Icons.AutoMirrored.Filled.ArrowForward,
                    )
                }
            }
        }
    }
}

/** A practice case drawn like a post in the Feed: avatar, name, handle and time, the caption, then the photo (or its description). */
@Composable
private fun PracticePostCard(question: PracticeQuestion, showsHotspots: Boolean) {
    var zoomed by remember { mutableStateOf(false) }
    val image = question.imageRes
    val large = isLargeText()
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.clearAndSetSemantics {
                contentDescription = "Post by ${question.author}, ${spokenTime(question.posted)}. ${sentence(question.caption)}"
            },
        ) {
            // Grows with the text, up to a point.
            Monogram(question.author, (36.dp * LocalDensity.current.fontScale).coerceAtMost(52.dp))
            Column {
                Text(question.author, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, maxLines = if (large) 2 else 1, overflow = TextOverflow.Ellipsis)
                // Handle and time, as the Feed shows them. The handle never wraps (a broken handle reads as a different account).
                if (large) {
                    Text("@${question.handle}", style = MaterialTheme.typography.bodySmall, color = colors.secondaryText, maxLines = 1, overflow = TextOverflow.MiddleEllipsis)
                    Text(question.posted, style = MaterialTheme.typography.bodySmall, color = colors.secondaryText)
                } else {
                    Text(
                        "@${question.handle} · ${question.posted}",
                        style = MaterialTheme.typography.bodySmall,
                        color = colors.secondaryText,
                        maxLines = 1,
                        overflow = TextOverflow.MiddleEllipsis,
                    )
                }
            }
        }
        Text(question.caption, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.clearAndSetSemantics { })

        if (image != null) {
            val shape = RoundedCornerShape(Metrics.photoRadius)
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                // Tall enough to see detail, short enough to leave the answers in view.
                Box(Modifier.fillMaxWidth().heightIn(max = 440.dp), contentAlignment = Alignment.Center) {
                    FittedPhoto(
                        image,
                        Modifier
                            .clip(shape)
                            .border(0.5.dp, colors.separator, shape)
                            .clickable(onClickLabel = "Open the photo full screen to zoom in") { zoomed = true }
                            .semantics { contentDescription = "Photo: ${question.spokenImageDescription}" },
                    ) {
                        // The photo's label covers it; the marks aren't read separately (as on iOS).
                        if (showsHotspots) HotspotOverlay(question.hotspots, describe = false)
                    }
                }
                question.credit?.let { Text(it, style = MaterialTheme.typography.labelSmall, color = colors.secondaryText) }
            }
        } else {
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(Metrics.photoRadius))
                    .background(colors.fill)
                    .padding(12.dp)
                    .clearAndSetSemantics { contentDescription = "Photo: ${question.imageDescription}" },
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Icon(Icons.Outlined.Image, contentDescription = null, tint = colors.secondaryText, modifier = Modifier.size(20.dp))
                Text(question.imageDescription, style = MaterialTheme.typography.bodyMedium)
            }
        }

        question.context?.let { context ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.AutoMirrored.Outlined.Reply, contentDescription = null, tint = colors.secondaryText, modifier = Modifier.size(16.dp))
                Text(context, style = MaterialTheme.typography.bodySmall, color = colors.secondaryText)
            }
        }
    }

    if (zoomed && image != null) {
        PracticePhotoViewer(image, question.spokenImageDescription, question.credit, if (showsHotspots) question.hotspots else emptyList()) { zoomed = false }
    }
}

/**
 * A bundled photo drawn at its own aspect ratio, so the box is exactly the
 * image and 0–1 hotspot coordinates land on the right pixels.
 */
@Composable
private fun FittedPhoto(image: Int, modifier: Modifier, overlay: @Composable () -> Unit) {
    val painter = painterResource(image)
    val ratio = painter.intrinsicSize.takeIf { it.isSpecified && it.width > 0f && it.height > 0f }?.let { it.width / it.height }
    Box(if (ratio != null) Modifier.aspectRatio(ratio).then(modifier) else modifier.fillMaxWidth()) {
        Image(
            painter,
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = if (ratio != null) Modifier.fillMaxSize() else Modifier.fillMaxWidth(),
        )
        overlay()
    }
}

/**
 * Clue areas marked on a practice photo after answering. Real clues use the
 * highlight mark; decoys are dashed and neutral. `describe` gives each mark
 * its own TalkBack label (the full-screen viewer); otherwise the photo's
 * label covers them.
 */
@Composable
private fun HotspotOverlay(hotspots: List<PracticeHotspot>, describe: Boolean) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        hotspots.filter { it.isInsideImage }.forEach { spot ->
            val color = if (spot.isDecoy) Color.White.copy(alpha = 0.9f) else Palette.HotspotStroke
            Box(
                Modifier
                    .offset(maxWidth * spot.x.toFloat(), maxHeight * spot.y.toFloat())
                    .size(maxWidth * spot.width.toFloat(), maxHeight * spot.height.toFloat())
                    .drawBehind {
                        val radius = CornerRadius(6.dp.toPx())
                        if (!spot.isDecoy) drawRoundRect(color.copy(alpha = 0.15f), cornerRadius = radius)
                        drawRoundRect(
                            color,
                            cornerRadius = radius,
                            style = Stroke(
                                (if (spot.isDecoy) 1.5f else 2f) * density,
                                pathEffect = if (spot.isDecoy) PathEffect.dashPathEffect(floatArrayOf(5 * density, 4 * density)) else null,
                            ),
                        )
                    }
                    .then(
                        if (describe) Modifier.semantics { contentDescription = if (spot.isDecoy) "Normal detail: ${spot.label}" else "Highlighted area: ${spot.label}" }
                        else Modifier,
                    ),
            ) {
                Text(
                    spot.label,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = if (spot.isDecoy) FontWeight.Normal else FontWeight.Bold,
                    color = Color.White,
                    modifier = Modifier
                        .align(if (spot.isDecoy) Alignment.BottomStart else Alignment.TopStart)
                        .padding(4.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (spot.isDecoy) Color.Black.copy(alpha = 0.6f) else Palette.HotspotLabel)
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                        .clearAndSetSemantics { },
                )
            }
        }
    }
}

/** Full-screen practice photo: pinch or double-tap to zoom, drag to move. Clue marks appear once answered. */
@Composable
private fun PracticePhotoViewer(image: Int, description: String, credit: String?, hotspots: List<PracticeHotspot>, onDone: () -> Unit) {
    var scale by remember { mutableFloatStateOf(1f) }
    var offsetX by remember { mutableFloatStateOf(0f) }
    var offsetY by remember { mutableFloatStateOf(0f) }
    val transform = rememberTransformableState { zoom, pan, _ ->
        scale = (scale * zoom).coerceIn(1f, 5f)
        if (scale > 1f) {
            offsetX += pan.x
            offsetY += pan.y
        } else {
            offsetX = 0f
            offsetY = 0f
        }
    }
    val scope = rememberCoroutineScope()
    // Double-tap and the TalkBack zoom actions ease to the new scale; back at 1 the photo recentres.
    fun setScale(value: Float) {
        if (value == 1f) {
            offsetX = 0f
            offsetY = 0f
        }
        scope.launch { animate(scale, value, animationSpec = tween(250)) { current, _ -> scale = current } }
    }
    Dialog(onDismissRequest = onDone, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Box(Modifier.fillMaxSize().background(Color.Black)) {
            FittedPhoto(
                image,
                Modifier
                    .align(Alignment.Center)
                    .graphicsLayer { scaleX = scale; scaleY = scale; translationX = offsetX; translationY = offsetY }
                    .transformable(transform)
                    .pointerInput(Unit) {
                        detectTapGestures(onDoubleTap = { setScale(if (scale > 1f) 1f else 2.5f) })
                    }
                    .semantics {
                        contentDescription = "Photo: $description"
                        customActions = listOf(
                            CustomAccessibilityAction("Zoom in") { setScale(minOf(scale * 2, 5f)); true },
                            CustomAccessibilityAction("Zoom out") { setScale(maxOf(scale / 2, 1f)); true },
                        )
                    },
            ) {
                if (hotspots.isNotEmpty()) HotspotOverlay(hotspots, describe = true)
            }
            TextButton(onClick = onDone, modifier = Modifier.align(Alignment.TopEnd).padding(16.dp)) {
                Text("Done", color = Color.White, fontWeight = FontWeight.SemiBold)
            }
            credit?.let {
                Text(it, style = MaterialTheme.typography.labelSmall, color = Color.White.copy(alpha = 0.8f), modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp).navigationBarsPadding())
            }
        }
    }
}

/**
 * The four answers, as plain words until you pick so none looks like the
 * right one. Afterwards the correct answer is marked in purple and a wrong
 * pick gets a grey cross.
 */
@Composable
private fun PracticeAnswerButtons(picked: PracticeAnswer?, answer: PracticeAnswer, onSelect: (PracticeAnswer) -> Unit) {
    val tint = MaterialTheme.colorScheme.primary
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        PracticeAnswer.entries.chunked(if (isLargeText()) 1 else 2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { choice ->
                    val correct = picked != null && choice == answer
                    val wrongPick = picked != null && choice == picked && choice != answer
                    val faded = picked != null && !correct && !wrongPick
                    Row(
                        Modifier
                            .weight(1f)
                            .heightIn(min = Metrics.controlHeight)
                            .clip(RoundedCornerShape(Metrics.fieldRadius))
                            .background(if (correct) tint.copy(alpha = 0.12f) else colors.fill)
                            .border(2.dp, if (correct) tint else Color.Transparent, RoundedCornerShape(Metrics.fieldRadius))
                            // Once revealed these are a record of the answer, not controls, so
                            // they aren't read as disabled buttons.
                            .then(if (picked == null) Modifier.clickable(role = Role.Button) { onSelect(choice) } else Modifier)
                            .padding(horizontal = 12.dp)
                            .semantics {
                                // The definition is the hint while choosing.
                                contentDescription = if (picked == null) "${choice.label}. ${choice.definition}" else choice.label
                                stateDescription = when {
                                    picked == null -> ""
                                    choice == picked && choice == answer -> "Your answer, correct"
                                    choice == picked -> "Your answer"
                                    choice == answer -> "Correct answer"
                                    else -> ""
                                }
                            },
                        horizontalArrangement = Arrangement.spacedBy(6.dp, Alignment.CenterHorizontally),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        if (correct) Icon(Icons.Filled.Check, contentDescription = null, tint = tint, modifier = Modifier.size(18.dp))
                        if (wrongPick) Icon(Icons.Filled.Close, contentDescription = null, tint = colors.secondaryText, modifier = Modifier.size(18.dp))
                        Text(
                            choice.label,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                            color = if (faded) colors.secondaryText else MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.clearAndSetSemantics { },
                        )
                    }
                }
            }
        }
    }
}

/** After answering: right or not, what to look for, then why. */
@Composable
private fun PracticeFeedback(question: PracticeQuestion, picked: PracticeAnswer, answerCount: Int, live: Boolean = true) {
    val correct = picked == question.answer
    val headline = remember { FocusRequester() }
    LaunchedEffect(answerCount) {
        // Land TalkBack on the result instead of a locked answer button. Not in
        // the review sheet, where it starts at the post.
        if (!live) return@LaunchedEffect
        delay(300)
        runCatching { headline.requestFocus() }
    }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            MascotReaction(correct, trigger = answerCount, animates = live)
            Text(
                if (correct) "Yes, it's ${question.answer.phrase}." else "Not quite. It's ${question.answer.phrase}.",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .focusRequester(headline)
                    .focusable()
                    .semantics { heading() },
            )
        }
        Column(
            verticalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.clearAndSetSemantics { contentDescription = "What to look for: ${question.clues.joinToString(". ")}" },
        ) {
            question.clues.forEach { Text(it, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Bold) }
        }
        Text(question.explanation, style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
    }
}

/** The magnifier mascot reacting to an answer: a hop when you're right, a head-shake when you're not. */
@Composable
private fun MascotReaction(isCorrect: Boolean, trigger: Int = 0, animates: Boolean = true) {
    val angle = remember { Animatable(0f) }
    val lift = remember { Animatable(0f) }
    LaunchedEffect(trigger) {
        if (!animates) return@LaunchedEffect
        delay(150)
        if (isCorrect) {
            lift.animateTo(-8f, tween(180))
            lift.animateTo(0f, spring(dampingRatio = Spring.DampingRatioMediumBouncy))
        } else {
            angle.animateTo(-9f, tween(80))
            angle.animateTo(9f, tween(120))
            angle.animateTo(-5f, tween(100))
            angle.animateTo(0f, spring())
        }
    }
    Box(Modifier.graphicsLayer { rotationZ = angle.value; translationY = lift.value * density }) {
        LogoTile(42.dp)
    }
}

/** Initials in a circle, coloured per name, standing in for an avatar. */
@Composable
private fun Monogram(name: String, size: Dp) {
    val palette = listOf(Color(0xFF007AFF), Color(0xFF5856D6), Color(0xFFAF52DE), Color(0xFFA2845E), Color(0xFFFF3B30), Color(0xFF8E8E93))
    val initials = name.split(" ").mapNotNull { word -> word.firstOrNull { it.isLetter() } }.take(2).joinToString("")
    val color = palette[name.sumOf { it.code } % palette.size]
    Box(Modifier.size(size).background(color, CircleShape).clearAndSetSemantics { }, contentAlignment = Alignment.Center) {
        Text(initials, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = (size.value * 0.4f).sp)
    }
}

/**
 * One mark per question: filled for right, hollow for wrong, a wider bar for
 * the current one. `hidden` keeps TalkBack off it where the score is already read.
 */
@Composable
private fun RoundDots(practice: PracticeViewModel, hidden: Boolean = false) {
    val total = practice.round.size
    val finished = practice.phase == PracticeViewModel.Phase.Finished
    val tint = MaterialTheme.colorScheme.primary
    // Grows with the text, like the rest of the card.
    val size = 10.dp * LocalDensity.current.fontScale.coerceAtMost(2f)
    Row(
        Modifier.clearAndSetSemantics {
            if (hidden) return@clearAndSetSemantics
            contentDescription = if (finished) "${practice.score} of $total right"
            else "Question ${minOf(practice.index + 1, total)} of $total, ${practice.score} right so far"
        },
        horizontalArrangement = Arrangement.spacedBy(size * 0.6f),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        practice.round.indices.forEach { index ->
            val current = index == practice.index && index >= practice.picks.size && !finished
            val shape = if (current) RoundedCornerShape(size / 2) else CircleShape
            val base = Modifier.size(width = if (current) size * 2 else size, height = size)
            when {
                index < practice.picks.size && practice.picks[index] == practice.round[index].answer -> Box(base.background(tint, shape))
                index < practice.picks.size -> Box(base.border(1.5.dp, colors.secondaryText, shape))
                current -> Box(base.background(tint, shape))
                else -> Box(base.background(colors.fill, shape))
            }
        }
    }
}

/** End of a round, inside the Look Again card: the score, Play Again, what went well, and the misses to look at again. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PracticeSummary(viewModel: LearnViewModel) {
    val practice = viewModel.practice
    // On the view model, so both survive a visit to the Clue Guide.
    val showAll = viewModel.showsAllMisses
    val reviewing = viewModel.reviewing
    val misses = practice.misses
    val preview = 3

    Column(verticalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.fillMaxWidth()) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            MascotReaction(practice.score * 2 >= practice.round.size)
            Column {
                Text(practice.scoreLine, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, modifier = Modifier.semantics { heading() })
                val best = viewModel.bestScore
                when {
                    viewModel.lastRoundWasNewBest -> Text("New best", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    best == practice.score && practice.score > 0 -> Text("Your best so far.", style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
                    best != null -> Text("Your best is $best of ${practice.round.size}.", style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
                }
            }
        }
        // The score line above already says how many were right.
        RoundDots(practice, hidden = true)
        Text(practice.summary, style = MaterialTheme.typography.bodyLarge)
        PrimaryButton("Play Again", onClick = viewModel::startPractice, trailingIcon = Icons.Outlined.Refresh)

        if (misses.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Take another look", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.semantics { heading() }.padding(bottom = 4.dp))
                // Only collapse when it hides more than one row.
                val shown = if (showAll || misses.size <= preview + 1) misses else misses.take(preview)
                shown.forEach { miss ->
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .clickable(role = Role.Button, onClickLabel = "Show the post again with the answer") { viewModel.reviewing = miss }
                            .padding(vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(miss.first.caption, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
                            Text(
                                "You said ${miss.second.inSentence}. It's ${miss.first.answer.phrase}.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = colors.secondaryText,
                            )
                        }
                        Spacer(Modifier.width(8.dp))
                        Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.secondaryText.copy(alpha = 0.6f))
                    }
                }
                if (misses.size > preview + 1 && !showAll) {
                    TextButton(onClick = { viewModel.showsAllMisses = true }) { Text("Show all ${misses.size}") }
                }
            }
            TextButton(onClick = viewModel::openGuideForMisses, modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp)) {
                Text(
                    when (practice.mostMissed) {
                        PracticeAnswer.AI -> "Clues for AI images"
                        PracticeAnswer.EDITED -> "Clues for edited photos"
                        PracticeAnswer.REAL, PracticeAnswer.MISLEADING -> "How to check a source"
                        null -> "Clues for what you missed"
                    },
                )
            }
        }
    }

    reviewing?.let { (question, picked) ->
        ModalBottomSheet(
            onDismissRequest = { viewModel.reviewing = null },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = colors.card,
        ) {
            Column(
                Modifier
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp)
                    .padding(bottom = 24.dp)
                    .navigationBarsPadding(),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Take Another Look", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f).semantics { heading() })
                    TextButton(onClick = { viewModel.reviewing = null }) { Text("Done", fontWeight = FontWeight.SemiBold) }
                }
                PracticePostCard(question, showsHotspots = true)
                PracticeAnswerButtons(picked, question.answer, onSelect = { })
                PracticeFeedback(question, picked, answerCount = 0, live = false)
            }
        }
    }
}

/** The clue groups on the Learn home, leading into the Clue Guide. */
@Composable
private fun ClueIndex(groups: List<ClueGroup>, onOpen: (ClueGroup) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Clue Guide", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 4.dp).semantics { heading() })
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(Metrics.cardRadius)).background(colors.card)) {
            groups.forEachIndexed { index, group ->
                if (index > 0) RowDivider(IconRowInset + 4.dp)
                ListRow(onClick = { onOpen(group) }, padding = PaddingValues(16.dp)) {
                    Icon(group.icon.vector, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(24.dp))
                    Column(Modifier.weight(1f)) {
                        Text(group.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(group.summary, style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
                    }
                    Text("${group.clues.size}", style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText, modifier = Modifier.semantics { contentDescription = "${group.clues.size} clues" })
                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.secondaryText.copy(alpha = 0.6f))
                }
            }
        }
    }
}

/** What to look for, one group at a time: signs of AI, signs of editing, and checking the source. */
@Composable
private fun ClueGuideScreen(groups: List<ClueGroup>, initial: String, onBack: () -> Unit) {
    var selection by remember { mutableStateOf(groups.firstOrNull { it.id == initial } ?: groups.first()) }
    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Clue Guide", onBack) }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            item {
                IosSegmentedControl(
                    groups,
                    selection,
                    label = { it.shortTitle },
                    onSelect = { selection = it },
                    modifier = Modifier.widthIn(max = 720.dp).padding(horizontal = 16.dp, vertical = 8.dp),
                )
            }
            item {
                Section(header = selection.title) {
                    selection.clues.forEachIndexed { index, clue ->
                        if (index > 0) RowDivider(IconRowInset + 6.dp)
                        ListRow(modifier = Modifier.semantics(mergeDescendants = true) { }) {
                            Icon(clue.icon.vector, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(26.dp).align(Alignment.Top))
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(clue.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                                Text(clue.detail, style = MaterialTheme.typography.bodyLarge, color = colors.secondaryText)
                            }
                        }
                    }
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }
}

/** "40m" → "40 minutes ago" so TalkBack doesn't read meters. */
internal fun spokenTime(short: String): String {
    val value = short.dropLast(1).toIntOrNull() ?: return "posted $short"
    val word = when (short.last()) {
        'm' -> if (value == 1) "minute" else "minutes"
        'h' -> if (value == 1) "hour" else "hours"
        'd' -> if (value == 1) "day" else "days"
        else -> return "posted $short"
    }
    return "$value $word ago"
}

/** Ends a caption with exactly one sentence mark. */
internal fun sentence(caption: String): String {
    val trimmed = caption.trim()
    return if (trimmed.isEmpty() || trimmed.last() in ".!?") trimmed else "$trimmed."
}

/** The largest text sizes, where the card stacks what usually sits side by side (iOS's accessibility sizes). */
@Composable
private fun isLargeText(): Boolean = LocalDensity.current.fontScale >= 1.5f
