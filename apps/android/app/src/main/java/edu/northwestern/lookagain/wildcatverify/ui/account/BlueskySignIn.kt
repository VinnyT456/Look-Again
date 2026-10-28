package edu.northwestern.lookagain.wildcatverify.ui.account

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.data.BlueskyAccount
import edu.northwestern.lookagain.wildcatverify.ui.shared.ListRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.PrimaryButton
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.theme.Metrics
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel

private val AppViewModel.isSigningIn get() = account.state == BlueskyAccount.State.SigningIn

/**
 * "Sign In with Bluesky": opens Bluesky's own sign-in page (no password is
 * typed into Look Again) and comes back signed in.
 */
@Composable
fun BlueskySignInButton(app: AppViewModel, title: String = "Sign In with Bluesky", modifier: Modifier = Modifier) {
    PrimaryButton(
        if (app.isSigningIn) "Signing In…" else title,
        onClick = { app.signIn() },
        enabled = !app.isSigningIn,
        modifier = modifier,
    )
}

/** The same, as a Settings row. */
@Composable
fun BlueskySignInRow(app: AppViewModel) {
    ListRow(onClick = if (app.isSigningIn) null else ({ app.signIn() })) {
        if (app.isSigningIn) {
            CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
        } else {
            Icon(Icons.Outlined.AccountCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
        }
        Text(
            if (app.isSigningIn) "Signing In…" else "Sign In with Bluesky",
            style = MaterialTheme.typography.bodyLarge,
            color = if (app.isSigningIn) colors.secondaryText else MaterialTheme.colorScheme.primary,
            modifier = Modifier.weight(1f),
        )
    }
}

/** Top of What's Hot while signed out: one tap to see your own feed instead. */
@Composable
fun FeedSignInCard(app: AppViewModel, onDismiss: () -> Unit) {
    Section {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("See your own feed", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                IconButton(onClick = onDismiss, modifier = Modifier.size(44.dp).padding(start = 8.dp)) {
                    Icon(Icons.Filled.Close, contentDescription = "Not Now", tint = colors.secondaryText, modifier = Modifier.size(18.dp))
                }
            }
            Text(
                "Sign in and the posts you follow are checked here as you scroll. Look Again only reads your timeline.",
                style = MaterialTheme.typography.bodyMedium,
                color = colors.secondaryText,
            )
            BlueskySignInButton(app)
        }
    }
}

/** Settings → "Account on Another Server…": for accounts hosted outside Bluesky. */
@Composable
fun OtherServerDialog(app: AppViewModel, onDismiss: () -> Unit) {
    var handle by remember { mutableStateOf("") }
    val go = {
        onDismiss()
        app.signIn(handle)
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Your Bluesky Handle") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("For accounts hosted outside Bluesky. You'll sign in on your server's own page.")
                TextField(
                    value = handle,
                    onValueChange = { handle = it },
                    placeholder = { Text("name.example.com") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(
                        capitalization = KeyboardCapitalization.None,
                        autoCorrectEnabled = false,
                        keyboardType = KeyboardType.Uri,
                        imeAction = ImeAction.Go,
                    ),
                    keyboardActions = KeyboardActions(onGo = { if (handle.isNotBlank()) go() }),
                    shape = RoundedCornerShape(Metrics.fieldRadius),
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = colors.fill,
                        unfocusedContainerColor = colors.fill,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = { TextButton(onClick = go, enabled = handle.isNotBlank()) { Text("Continue") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

/** Why sign-in failed, or that it expired. Shown once, from anywhere in the app. */
@Composable
fun SignInErrorDialog(app: AppViewModel) {
    val message = app.account.lastError ?: return
    AlertDialog(
        onDismissRequest = { app.account.lastError = null },
        title = { Text("Couldn't Sign In") },
        text = { Text(message) },
        confirmButton = { TextButton(onClick = { app.account.lastError = null }) { Text("OK") } },
    )
}
