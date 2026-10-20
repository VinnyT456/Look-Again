package edu.northwestern.lookagain.wildcatverify.ui.history

import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.FilterList
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.SearchOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SwipeToDismissBox
import androidx.compose.material3.SwipeToDismissBoxValue
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberSwipeToDismissBoxState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.semantics.CustomAccessibilityAction
import androidx.compose.ui.semantics.customActions
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.model.VerdictFilter
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import edu.northwestern.lookagain.wildcatverify.ui.results.ResultsScreen
import edu.northwestern.lookagain.wildcatverify.ui.shared.BrandTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.CaseRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.ContentUnavailable
import edu.northwestern.lookagain.wildcatverify.ui.shared.NavStack
import edu.northwestern.lookagain.wildcatverify.ui.shared.SectionGutter
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppTab
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.HistoryViewModel

/** Every check the user ran: searchable, filterable by verdict, swipe to delete. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(app: AppViewModel) {
    val viewModel = app.historyList
    val top = viewModel.path.lastOrNull()
    val pop = { viewModel.path = viewModel.path.dropLast(1) }
    BackHandler(enabled = top != null, onBack = pop)

    NavStack(viewModel.path, screen = { item ->
        ResultsScreen(item, onBack = pop, onCheckAnother = app::startNewCheck)
    }, root = {
        val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior()
        Scaffold(
            modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
            containerColor = colors.groupedBackground,
            topBar = {
                BrandTopBar("My Checks", app::showAbout, scrollBehavior) {
                    TextButton(onClick = { viewModel.isConfirmingClear = true }, enabled = !viewModel.isEmpty) {
                        Text("Clear", color = if (viewModel.isEmpty) colors.secondaryText else MaterialTheme.colorScheme.error)
                    }
                }
            },
        ) { padding ->
            LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
                if (!viewModel.isEmpty) {
                    item(key = "search") { SearchBar(viewModel) }
                }
                val visible = viewModel.visibleCases
                items(visible, key = { it.id }) { case ->
                    SwipeToDeleteRow(case, onOpen = { viewModel.open(case) }, onDelete = { viewModel.delete(case) })
                }
                if (visible.isEmpty()) {
                    item(key = "empty") { EmptyState(viewModel) { app.selectedTab = AppTab.CHECK } }
                }
                item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
            }
        }

        if (viewModel.isConfirmingClear) {
            AlertDialog(
                onDismissRequest = { viewModel.isConfirmingClear = false },
                title = { Text("Clear all checks?") },
                text = { Text("This removes every check and uploaded photo from this device.") },
                confirmButton = {
                    TextButton(onClick = { viewModel.isConfirmingClear = false; viewModel.clearAll() }) {
                        Text("Clear All", color = MaterialTheme.colorScheme.error)
                    }
                },
                dismissButton = { TextButton(onClick = { viewModel.isConfirmingClear = false }) { Text("Cancel") } },
            )
        }
    })
}

/** "Search by author or topic", plus the verdict scopes. */
@Composable
private fun SearchBar(viewModel: HistoryViewModel) {
    androidx.compose.foundation.layout.Column(
        Modifier.widthIn(max = 720.dp).fillMaxWidth().padding(horizontal = SectionGutter).padding(top = 4.dp, bottom = 4.dp),
    ) {
        TextField(
            value = viewModel.searchQuery,
            onValueChange = { viewModel.searchQuery = it },
            placeholder = { Text("Search by author or topic") },
            leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null) },
            trailingIcon = {
                if (viewModel.searchQuery.isNotEmpty()) {
                    IconButton(onClick = { viewModel.searchQuery = "" }) { Icon(Icons.Filled.Cancel, contentDescription = "Clear search") }
                }
            },
            singleLine = true,
            shape = RoundedCornerShape(12.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = colors.fill,
                unfocusedContainerColor = colors.fill,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
            ),
            modifier = Modifier.fillMaxWidth(),
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
            items(VerdictFilter.entries) { filter ->
                FilterChip(
                    selected = viewModel.scope == filter,
                    onClick = { viewModel.scope = filter },
                    label = { Text(filter.title) },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SwipeToDeleteRow(item: VerificationCase, onOpen: () -> Unit, onDelete: () -> Unit) {
    val state = rememberSwipeToDismissBoxState()
    SwipeToDismissBox(
        state = state,
        enableDismissFromStartToEnd = false,
        onDismiss = { value -> if (value == SwipeToDismissBoxValue.EndToStart) onDelete() },
        modifier = Modifier
            .widthIn(max = 720.dp)
            .fillMaxWidth()
            .padding(horizontal = SectionGutter, vertical = 4.dp)
            .clip(RoundedCornerShape(Metrics.sectionRadius)),
        backgroundContent = {
            Box(
                Modifier.fillMaxSize().background(MaterialTheme.colorScheme.error).padding(horizontal = 20.dp),
                contentAlignment = Alignment.CenterEnd,
            ) { Icon(Icons.Outlined.Delete, contentDescription = "Delete", tint = Color.White) }
        },
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .background(colors.card)
                .clickable(onClick = onOpen)
                .padding(horizontal = 16.dp, vertical = 10.dp)
                .semantics { customActions = listOf(CustomAccessibilityAction("Delete") { onDelete(); true }) },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.weight(1f)) { CaseRow(item) }
            Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.secondaryText)
        }
    }
}

/** Empty states for My Checks: nothing checked yet, or nothing matching. */
@Composable
private fun EmptyState(viewModel: HistoryViewModel, onCheck: () -> Unit) {
    Box(Modifier.fillMaxWidth().padding(top = 48.dp)) {
        when {
            viewModel.isEmpty -> ContentUnavailable(
                "No Checks Yet",
                Icons.Outlined.History,
                "Paste a Bluesky link or choose a photo. Your results show up here and stay on this device.",
                action = "Check an Image" to onCheck,
            )
            viewModel.searchQuery.isEmpty() -> ContentUnavailable(
                "No ${viewModel.scope.title} Checks",
                Icons.Outlined.FilterList,
                "Try a different filter.",
            )
            else -> ContentUnavailable(
                "No Results for “${viewModel.searchQuery}”",
                Icons.Outlined.SearchOff,
                "Check the spelling or try a new search.",
            )
        }
    }
}
