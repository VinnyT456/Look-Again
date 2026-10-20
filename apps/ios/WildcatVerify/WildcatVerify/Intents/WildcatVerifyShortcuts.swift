import AppIntents

/// Phrases Siri knows as soon as the app is installed. Check Image needs an
/// image, so it lives in the user's "Check This Post" shortcut instead.
struct WildcatVerifyShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: CheckCopiedLinkIntent(),
            phrases: [
                "Check the copied link with \(.applicationName)",
                "Check the copied post with \(.applicationName)",
                "Check my clipboard with \(.applicationName)",
            ],
            shortTitle: "Check Copied Link",
            systemImageName: "link"
        )
    }

    static let shortcutTileColor = ShortcutTileColor.purple
}
