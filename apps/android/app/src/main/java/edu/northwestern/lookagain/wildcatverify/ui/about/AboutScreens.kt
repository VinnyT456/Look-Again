package edu.northwestern.lookagain.wildcatverify.ui.about

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Link
import androidx.compose.material.icons.outlined.ManageSearch
import androidx.compose.material.icons.outlined.NoAccounts
import androidx.compose.material.icons.outlined.PanTool
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import edu.northwestern.lookagain.wildcatverify.BuildConfig
import edu.northwestern.lookagain.wildcatverify.R
import edu.northwestern.lookagain.wildcatverify.model.AppLinks
import edu.northwestern.lookagain.wildcatverify.ui.shared.BulletRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LabelRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LinkRow
import edu.northwestern.lookagain.wildcatverify.ui.shared.LogoTile
import edu.northwestern.lookagain.wildcatverify.ui.shared.PushedTopBar
import edu.northwestern.lookagain.wildcatverify.ui.shared.IconRowInset
import edu.northwestern.lookagain.wildcatverify.ui.shared.RowDivider
import edu.northwestern.lookagain.wildcatverify.ui.shared.Section
import edu.northwestern.lookagain.wildcatverify.ui.shared.TextRow
import edu.northwestern.lookagain.wildcatverify.ui.theme.colors

private enum class AboutRoute { PRIVACY_POLICY, TERMS, CREDITS }

/** About, as a bottom sheet over any tab, with its own Privacy Policy and Credits pages. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AboutSheet(onDismiss: () -> Unit) {
    val state = rememberModalBottomSheetState(skipPartiallyExpanded = false)
    var route by remember { mutableStateOf<AboutRoute?>(null) }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = state, containerColor = colors.groupedBackground) {
        // Back on Privacy Policy, Terms or Credits returns to About instead of closing the sheet.
        BackHandler(enabled = route != null) { route = null }
        when (route) {
            AboutRoute.PRIVACY_POLICY -> PrivacyPolicyScreen(onBack = { route = null })
            AboutRoute.CREDITS -> CreditsScreen(onBack = { route = null })
            AboutRoute.TERMS -> TermsScreen(onBack = { route = null })
            null -> AboutContent(onDismiss, onOpen = { route = it })
        }
    }
}

@Composable
private fun AboutContent(onDismiss: () -> Unit, onOpen: (AboutRoute) -> Unit) {
    LazyColumn(horizontalAlignment = Alignment.CenterHorizontally) {
        item {
            Row(Modifier.padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("About", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                TextButton(onClick = onDismiss) { Text("Done", fontWeight = FontWeight.SemiBold) }
            }
        }
        item {
            Section {
                Row(
                    Modifier.padding(16.dp).semantics(mergeDescendants = true) { },
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    LogoTile(60.dp)
                    Column {
                        Text("WildcatVerify", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                        Text("Version ${BuildConfig.VERSION_NAME}", style = MaterialTheme.typography.bodyMedium, color = colors.secondaryText)
                    }
                }
                RowDivider()
                TextRow("Helps you judge whether a photo on Bluesky is genuine, edited, or AI-generated.")
            }
        }
        item {
            Section(header = "How it works") {
                BulletRow("Pick a post in Feed, paste a link, or choose a photo.", Icons.Outlined.Link)
                RowDivider(IconRowInset)
                BulletRow("Read the verdict and the clues behind it.", Icons.Outlined.ManageSearch)
                RowDivider(IconRowInset)
                BulletRow("Turn on Highlight to see the suspect area.", Icons.Outlined.Visibility)
            }
        }
        item {
            Section(header = "Privacy") {
                TextRow("Photos are analyzed on this device and never uploaded. They're only saved if you turn on Keep My Checks in Settings.")
                RowDivider()
                LabelRow("Privacy Policy", chevron = true) { onOpen(AboutRoute.PRIVACY_POLICY) }
                RowDivider()
                LabelRow("Terms of Use", chevron = true) { onOpen(AboutRoute.TERMS) }
            }
        }
        item {
            Section(footer = "Detector based on Community Forensics by Jeongsoo Park and Andrew Owens (CVPR 2025).") {
                LabelRow("Credits", chevron = true) { onOpen(AboutRoute.CREDITS) }
            }
        }
        item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
    }
}

/** The full privacy policy, bundled so it is readable offline. Keep in sync with PRIVACY.md. */
@Composable
fun PrivacyPolicyScreen(onBack: () -> Unit) {
    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Privacy Policy", onBack) }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            item { Section { TextRow("WildcatVerify is built so your photos and checks stay on your device. Last updated October 19, 2026.") } }
            item {
                Section(header = "Photos you choose") {
                    TextRow("Android's photo picker gives the app only the photo you pick, never the rest of your library. It is analyzed in memory on this device, never uploaded or written to disk, and is discarded when you delete the check, clear My Checks, or the app is closed. Location and other personal metadata aren't read. If the photo carries Content Credentials, only the app or device that made it and its edit history are read and shown with the result.")
                }
            }
            item {
                Section(header = "Items you share") {
                    TextRow("When you use Share → WildcatVerify in another app, only what you shared reaches the app. It is checked in memory the same way and discarded when you tap Done.")
                }
            }
            item {
                Section(header = "Labels") {
                    TextRow("The label tab is off unless you start it. Each time, Android asks you to approve screen sharing; on Android 14 and later you can share only the Bluesky app. Screen frames are kept in memory, replaced as you scroll, and never uploaded or saved. Android shows a sharing indicator and WildcatVerify shows a notification while it runs.")
                    if (BuildConfig.ACCESSIBILITY_AUTO_LABEL) {
                        RowDivider()
                        TextRow("Auto-Label (this version only) is off unless you turn it on in Android's Accessibility settings. It looks only at the Bluesky app and at Chrome while bsky.app is open, reads where photos are on screen, and takes a screenshot to read those photos' pixels, all in memory on this device.")
                    }
                }
            }
            item {
                Section(header = "Your Bluesky account") {
                    TextRow("Signing in is optional and only used to show your Following feed. You sign in on Bluesky's own page, so WildcatVerify never sees your password. It keeps only the sign-in token, bound to a key made on this device and encrypted with a key stored in Android's Keystore, and only ever reads your timeline. Signing out or Erase All Data deletes it.")
                }
            }
            item {
                Section(header = "Bluesky links you paste") {
                    TextRow("To check a post, the app asks Bluesky's public API for that post's text and photo. The request goes straight from your device to Bluesky, which sees your IP address like any website would. WildcatVerify runs no server and keeps no copy of the link.")
                    RowDivider()
                    LinkRow("Bluesky Privacy Policy", AppLinks.BLUESKY_PRIVACY)
                }
            }
            item {
                Section(header = "My Checks") {
                    TextRow("By default, past checks are kept in memory and disappear when the app is closed. If you turn on Settings → Keep My Checks, results and small copies of the photos you checked are saved on this device only: in the app's private storage, left out of backups, never uploaded, and deleted when you turn the setting off or erase your data.")
                }
            }
            item {
                Section(header = "The Feed") {
                    TextRow("The Feed loads image posts directly from Bluesky: the public What's Hot feed, or your Following feed if you sign in. With Check Posts Automatically on, each post's image is analyzed on this device as it appears; those verdicts stay in memory and aren't added to My Checks unless you open the post. Automatic checks pause in Battery Saver and on mobile data or Data Saver.")
                    RowDivider()
                    TextRow("When you open the app, it asks Android only whether the clipboard looks like a link, from its description, without reading it. The link is read only when you tap Paste.")
                }
            }
            item {
                Section(header = "Hidden accounts and settings") {
                    TextRow("Accounts you hide from the Feed, your preferences and your best Look Again score are saved on this device only. Bluesky and hidden accounts aren't told. Erase All Data removes them.")
                }
            }
            item {
                Section(header = "Where processing happens") {
                    TextRow("All image analysis, including the AI-image detector, runs on this device with LiteRT. Nothing is sent to the developer or to any AI service.")
                }
            }
            item {
                Section(header = "Your choices") {
                    TextRow("Delete one check with a swipe, clear My Checks, or use Settings → Erase All Data. Uninstalling the app removes everything. The developer holds no personal data, but you can still contact us with any privacy request.")
                }
            }
            item {
                Section(header = "What the app doesn't do") {
                    BulletRow("No account needed; Bluesky sign-in is optional", Icons.Outlined.NoAccounts)
                    RowDivider(IconRowInset)
                    BulletRow("No analytics, ads or tracking", Icons.Outlined.VisibilityOff)
                    RowDivider(IconRowInset)
                    BulletRow("No data sold, shared or collected", Icons.Outlined.PanTool)
                }
            }
            item {
                Section {
                    LinkRow("View Policy Online", AppLinks.PRIVACY_POLICY)
                    RowDivider()
                    LinkRow("Contact Support", AppLinks.SUPPORT)
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }
}

/** Who made the detector, and the license it ships under. The MIT license asks for its notice to travel with every copy. */
@Composable
fun CreditsScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val license = remember {
        runCatching { context.resources.openRawResource(R.raw.community_forensics_vit_mit).bufferedReader().use { it.readText() } }.getOrNull()
    }
    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Credits", onBack) }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            item {
                Section(header = "Detection model") {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("CommunityForensics ViT", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(
                            "The detector is built on the Community Forensics model by Jeongsoo Park and Andrew Owens, trained on images from 4,803 generators. Hugging Face conversion by Han Yoon, Borderless / Ethix R&D.",
                            color = colors.secondaryText,
                        )
                    }
                    RowDivider()
                    TextRow("WildcatVerify adds a linear probe and the patch heatmap on top, and runs everything on this device.", colors.secondaryText)
                }
            }
            item {
                Section(header = "Paper") {
                    TextRow("Park, J. and Owens, A. “Community Forensics: Using Thousands of Generators to Train Fake Image Detectors.” CVPR 2025, pp. 8245–8257.")
                    RowDivider()
                    LinkRow("Read the Paper", AppLinks.DETECTOR_PAPER)
                    RowDivider()
                    LinkRow("Original Code", AppLinks.DETECTOR_CODE)
                    RowDivider()
                    LinkRow("Model on Hugging Face", AppLinks.DETECTOR_MODEL)
                }
            }
            if (license != null) {
                item {
                    Section(header = "License (MIT)") {
                        SelectionContainer {
                            Text(license, style = MaterialTheme.typography.bodySmall, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(16.dp))
                        }
                    }
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }
}

/** Terms of Use, bundled so they're readable offline. Keep in sync with TERMS.md. */
@Composable
fun TermsScreen(onBack: () -> Unit) {
    val sections = listOf(
        null to "These terms cover your use of WildcatVerify. Last updated October 15, 2026. Google Play's terms also apply when you get it from Google Play.",
        "What WildcatVerify does" to "It estimates whether a photo looks real, edited or AI-generated, using a detection model that runs on your device. It's a tool to help you decide what to trust, not a final answer.",
        "Verdicts are estimates" to "No detector is always right. A verdict can be wrong in either direction, and the confidence number is the model's own score, not a guarantee. Don't rely on a verdict alone for anything important, such as news, legal, academic or safety decisions.",
        "Use it fairly" to "Don't use a verdict to harass, shame or publicly accuse someone of faking a photo. If something matters, look for other evidence: the original poster, other photos of the same moment, and trusted reporting. Don't use the app to break the law or anyone's rights.",
        "Other people's content" to "Posts and photos in the Feed and from links belong to their authors and are shown from Bluesky's service. WildcatVerify doesn't own, endorse or check them in advance. You can hide posts and accounts or report them with ••• on any Feed post. WildcatVerify isn't affiliated with Bluesky.",
        "Your photos" to "Photos you check stay yours. They're processed on this device and aren't uploaded. See the Privacy Policy for exactly what is kept and for how long.",
        "Open source credits" to "The detection model is based on Community Forensics (MIT License). Full notices are under Settings → Credits.",
        "No warranty" to "The app is provided “as is”, without warranties of any kind, to the extent the law allows. The developers aren't liable for decisions made based on a verdict.",
        "Changes" to "If these terms change, the new version will be in the app and online before it applies.",
    )
    Scaffold(containerColor = colors.groupedBackground, topBar = { PushedTopBar("Terms of Use", onBack) }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), horizontalAlignment = Alignment.CenterHorizontally) {
            sections.forEach { (header, text) ->
                item { Section(header = header) { TextRow(text) } }
            }
            item {
                Section {
                    LinkRow("View Terms Online", AppLinks.TERMS)
                    RowDivider()
                    LinkRow("Contact Support", AppLinks.SUPPORT)
                }
            }
            item { Box(Modifier.navigationBarsPadding().padding(bottom = 24.dp)) }
        }
    }
}
