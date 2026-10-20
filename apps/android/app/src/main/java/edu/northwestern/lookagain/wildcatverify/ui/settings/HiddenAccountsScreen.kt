package edu.northwestern.lookagain.wildcatverify.ui.settings

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.HowToReg
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.ui.shared.ContentUnavailable
import edu.northwestern.lookagain.wildcatverify.ui.shared.ListRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel

/** Settings → Hidden Accounts: Bluesky accounts hidden from the Feed. */
@Composable
fun HiddenAccountsScreen(app: AppViewModel, onBack: () -> Unit) {
    val settings = app.settings
    val accounts = settings.hiddenAccounts.entries.sortedBy { it.value }
    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Hidden Accounts", onBack) }) { padding ->
        if (accounts.isEmpty()) {
            ContentUnavailable("No Hidden Accounts", Icons.Outlined.HowToReg, "Use ••• on a Feed post to hide an account.", Modifier.padding(padding))
            return@Scaffold
        }
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            item {
                Section(footer = "Hidden on this device only. Bluesky and the account aren't told.") {
                    accounts.forEachIndexed { index, (did, handle) ->
                        if (index > 0) RowDivider()
                        ListRow {
                            Text("@$handle", style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.MiddleEllipsis, modifier = Modifier.weight(1f))
                            OutlinedButton(
                                onClick = { settings.hiddenAccounts = settings.hiddenAccounts - did },
                                modifier = Modifier.semantics { contentDescription = "Show posts from @$handle" },
                            ) { Text("Show") }
                        }
                    }
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }
}
