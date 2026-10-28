import AppIntents
import SwiftUI

/// Settings → Siri & Shortcuts: how to set up "Check This Post" and the
/// copied-link phrase.
struct SiriSetupView: View {
    @Environment(AppViewModel.self) private var app

    var body: some View {
        List {
            if app.showsMissingScreenshotHelp {
                Section {
                    Label {
                        Text("Your Action Button ran Look Again's **Check Image** on its own, so there was no screenshot to check.")
                    } icon: {
                        Image(systemName: "exclamationmark.circle.fill")
                            .foregroundStyle(.tint)
                    }
                    SetupStepRow(number: 1, text: "Open **Settings → Action Button** and swipe to **Shortcut**.")
                    SetupStepRow(number: 2, text: "Tap the shortcut name, then **Choose a Shortcut**.")
                    SetupStepRow(number: 3, text: "Pick **Check This Post** under **My Shortcuts**. It takes the screenshot first, then checks it.")
                    Button("Got It") { app.showsMissingScreenshotHelp = false }
                        .accessibilityIdentifier("missingScreenshotGotIt")
                } header: {
                    Text("Almost there")
                }
            }

            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Check posts without leaving Bluesky")
                        .font(.title3)
                        .bold()
                    Text("Say “Check This Post” while a post is on screen. The shortcut takes a screenshot, you box the photo, and it's checked like any other.")
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)

                if let url = AppLinks.checkThisPostShortcut {
                    Link(destination: url) {
                        Label("Add “Check This Post” Shortcut", systemImage: "plus.circle.fill")
                            .bold()
                    }
                    .accessibilityIdentifier("addShortcut")
                }
            }

            Section {
                if let url = AppLinks.newShortcut {
                    Link(destination: url) {
                        Label("Start a New Shortcut", systemImage: "plus.square.on.square")
                            .bold()
                    }
                    .accessibilityIdentifier("newShortcut")
                }
                SetupStepRow(number: 1, text: "Tap **Start a New Shortcut** above. (Or in Shortcuts, open the **Library** tab and tap **+** at the top right.)")
                SetupStepRow(number: 2, text: "Add the **Take Screenshot** action.")
                SetupStepRow(number: 3, text: "Search for **Look Again** and add **Check Image**. Its Image field should say **Screenshot**; if it says Ask Each Time, tap it and pick Screenshot.")
                SetupStepRow(number: 4, text: "Tap the name at the top, rename it **Check This Post**, and tap **Done**.")
            } header: {
                Text(AppLinks.checkThisPostShortcut == nil ? "Set it up" : "Or build it yourself")
            }

            Section("Run it from a post") {
                Label("Say “Hey Siri, Check This Post.”", systemImage: "mic")
                Label("Action Button: Settings → Action Button → Shortcut → Choose a Shortcut → Check This Post (under My Shortcuts, not the Look Again actions).", systemImage: "button.vertical.right.press")
                Label("Back Tap: Settings → Accessibility → Touch → Back Tap → Check This Post.", systemImage: "hand.tap")
            }

            Section {
                Label("Copy a post's link in Bluesky (Share → Copy Link), then say “Check the copied link with Look Again.” Siri answers with the verdict and an Open button.", systemImage: "link")
            } header: {
                Text("Copied links")
                ShortcutsLink()
                    .shortcutsLinkStyle(.automaticOutline)
                    .frame(maxWidth: .infinity)
                    .listRowBackground(Color.clear)
            } footer: {
                Text("Check Image only shows up in Shortcuts after you've opened Look Again once. iOS asks before Look Again reads your clipboard, and it's only read when you ask.")
            }

            Section {
                Label("Control Center or Lock Screen: edit controls, search for Look Again, and add Check Copied Link or Check a Post.", systemImage: "switch.2")
                Label("Visual Intelligence (Apple Intelligence iPhones): take a screenshot, tap Image Search, and choose Check with Look Again.", systemImage: "eye")
            } header: {
                Text("More ways in")
            }

            Section("Privacy") {
                Label("Screenshots are passed straight to Look Again. No access to your photo library is needed, and nothing is uploaded.", systemImage: "lock.shield")
                Label("Checks appear in My Checks. They're only saved if Keep My Checks is on.", systemImage: "clock.arrow.circlepath")
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Siri & Shortcuts")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        SiriSetupView()
    }
    .environment(AppViewModel())
}
