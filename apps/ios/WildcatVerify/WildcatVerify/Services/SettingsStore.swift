import Foundation
import Observation

/// User preferences, saved in UserDefaults. Declared in PrivacyInfo.xcprivacy
/// as NSPrivacyAccessedAPICategoryUserDefaults with reason CA92.1 (the app's
/// own settings, read only by the app).
@MainActor
@Observable
final class SettingsStore {
    private enum Key {
        static let keepHistory = "settings.keepHistory"
        static let haptics = "settings.haptics"
        static let heatmap = "settings.heatmap"
        static let siriTipDismissed = "settings.siriTipDismissed"
        static let bestPracticeScore = "learn.bestScore"
        static let hiddenAccounts = "feed.hiddenAccounts"
        static let welcomeSeen = "settings.welcomeSeen"
        static let autoCheckFeed = "feed.autoCheck"
        static let feedSignInDismissed = "feed.signInDismissed"
    }

    /// Save My Checks on this iPhone between launches. Off by default.
    var keepHistory: Bool {
        didSet { defaults.set(keepHistory, forKey: Key.keepHistory) }
    }

    /// Light haptic taps on tab switches, valid links and practice answers.
    var hapticsEnabled: Bool {
        didSet { defaults.set(hapticsEnabled, forKey: Key.haptics) }
    }

    /// Show the detector's heatmap under Highlight on Likely AI results.
    var heatmapEnabled: Bool {
        didSet { defaults.set(heatmapEnabled, forKey: Key.heatmap) }
    }

    /// The "Check posts without leaving Bluesky" tip on the Check page was closed.
    var siriTipDismissed: Bool {
        didSet { defaults.set(siriTipDismissed, forKey: Key.siriTipDismissed) }
    }

    /// Best Look Again score so far; 0 until a round is finished.
    var bestPracticeScore: Int {
        didSet { defaults.set(bestPracticeScore, forKey: Key.bestPracticeScore) }
    }

    /// Bluesky accounts the user hid from the Feed, by DID, with the handle
    /// shown in Settings. Kept on this iPhone only.
    var hiddenAccounts: [String: String] {
        didSet { defaults.set(hiddenAccounts, forKey: Key.hiddenAccounts) }
    }

    /// The first-run "fastest ways to check" screen was shown.
    var welcomeSeen: Bool {
        didSet { defaults.set(welcomeSeen, forKey: Key.welcomeSeen) }
    }

    /// Check Feed posts automatically as they scroll into view. On by default;
    /// paused in Low Power Mode and on cellular or limited networks.
    var autoCheckFeed: Bool {
        didSet { defaults.set(autoCheckFeed, forKey: Key.autoCheckFeed) }
    }

    /// The Feed's "See your own feed" sign-in card was closed.
    var feedSignInDismissed: Bool {
        didSet { defaults.set(feedSignInDismissed, forKey: Key.feedSignInDismissed) }
    }

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        keepHistory = defaults.object(forKey: Key.keepHistory) as? Bool ?? false
        hapticsEnabled = defaults.object(forKey: Key.haptics) as? Bool ?? true
        heatmapEnabled = defaults.object(forKey: Key.heatmap) as? Bool ?? true
        siriTipDismissed = defaults.bool(forKey: Key.siriTipDismissed)
        bestPracticeScore = defaults.integer(forKey: Key.bestPracticeScore)
        hiddenAccounts = defaults.dictionary(forKey: Key.hiddenAccounts) as? [String: String] ?? [:]
        welcomeSeen = defaults.bool(forKey: Key.welcomeSeen)
        autoCheckFeed = defaults.object(forKey: Key.autoCheckFeed) as? Bool ?? true
        feedSignInDismissed = defaults.bool(forKey: Key.feedSignInDismissed)
    }

    /// Back to defaults; used by "Erase All Data".
    func reset() {
        keepHistory = false
        hapticsEnabled = true
        heatmapEnabled = true
        siriTipDismissed = false
        bestPracticeScore = 0
        hiddenAccounts = [:]
        welcomeSeen = false
        autoCheckFeed = true
        feedSignInDismissed = false
    }
}
