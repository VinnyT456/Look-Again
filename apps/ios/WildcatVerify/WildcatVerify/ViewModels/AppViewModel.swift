import Observation
import UIKit

/// Root coordinator: owns tab selection, settings and the per-tab view models.
@MainActor
@Observable
final class AppViewModel {
    /// The app's single instance, shared with App Intents (Siri and Shortcuts).
    static let live = AppViewModel()

    var selectedTab: AppTab = .check {
        didSet { if selectedTab == .history { history.markSeen() } }
    }
    var isShowingAbout = false
    /// A screenshot from Siri or Shortcuts waiting to be boxed.
    var pendingScreenshot: PendingScreenshot?
    /// The last Siri screenshot, kept in memory so its result can offer
    /// "Adjust Area" when the photo was boxed automatically.
    private(set) var lastScreenshot: UIImage?
    var settingsPath: [SettingsRoute] = []
    /// Check Image ran without a screenshot (usually the Action Button set to
    /// the action instead of the shortcut): Set Up Siri explains the fix.
    var showsMissingScreenshotHelp = false
    /// First launch: the "fastest ways to check" sheet.
    var isShowingWelcome: Bool

    let settings: SettingsStore
    /// Optional Bluesky sign-in, for the Following feed.
    let account: BlueskyAccount
    let history: HistoryStore
    let check: CheckViewModel
    let feed: FeedViewModel
    let learn: LearnViewModel
    let historyList: HistoryViewModel

    private let persistence: HistoryPersistence
    private let network: NetworkConditions

    init(
        settings: SettingsStore = SettingsStore(),
        persistence: HistoryPersistence = .standard,
        feedService: any FeedFetching = BlueskyFeedService(),
        bluesky: any BlueskyFetching = BlueskyService(),
        classifier: any ImageClassifying = ClassifierFactory.make(),
        account: BlueskyAccount = BlueskyAccount()
    ) {
        self.account = account
        self.settings = settings
        self.isShowingWelcome = !settings.welcomeSeen
        self.persistence = persistence
        let history = HistoryStore(persistence: settings.keepHistory ? persistence : nil)
        self.history = history
        self.check = CheckViewModel(history: history, bluesky: bluesky, classifier: classifier)
        let network = NetworkConditions()
        self.network = network
        let autoCheck = FeedAutoChecker(classifier: classifier) {
            settings.autoCheckFeed && !ProcessInfo.processInfo.isLowPowerModeEnabled && !network.isLimited
        }
        self.feed = FeedViewModel(
            service: feedService,
            following: TimelineFeedService(account: account),
            isFollowingAvailable: { account.isSignedIn },
            settings: settings,
            autoCheck: autoCheck
        )
        self.learn = LearnViewModel(settings: settings)
        self.historyList = HistoryViewModel(store: history)
    }

    /// "Check Another Image" from any results screen: unwinds every tab and
    /// lands on a fresh Check form.
    func startNewCheck() {
        feed.path.removeAll()
        learn.path.removeAll()
        historyList.path.removeAll()
        check.reset()
        selectedTab = .check
    }

    /// Siri or Shortcuts handed over a screenshot: show the box screen on the
    /// Check tab.
    func receiveScreenshot(_ image: UIImage) async {
        // A Siri hand-off on first launch skips the welcome; it's in Settings.
        finishWelcome()
        startNewCheck()
        lastScreenshot = image
        // When Vision is sure where the photo is, check it straight away;
        // otherwise ask the user to box it.
        if let box = await PhotoAreaFinder.confidentPhoto(in: image), let area = ImageCropper.crop(image, to: box) {
            check.checkScreenshotArea(area)
        } else {
            pendingScreenshot = PendingScreenshot(image: image)
        }
    }

    /// "Adjust Area" on a result that was boxed automatically.
    func adjustLastScreenshot() {
        guard let lastScreenshot else { return }
        check.reset()
        pendingScreenshot = PendingScreenshot(image: lastScreenshot)
    }

    /// The user boxed the photo: check that area like any other photo.
    func checkBoxedArea(_ image: UIImage) {
        pendingScreenshot = nil
        selectedTab = .check
        check.checkScreenshotArea(image)
    }

    /// Opens a check from My Checks (the Siri card's Open button). Returns
    /// false when it's no longer there, e.g. after the app was relaunched with
    /// Keep My Checks off.
    @discardableResult
    func openCase(id: VerificationCase.ID) -> Bool {
        guard let item = history.cases.first(where: { $0.id == id }) else {
            selectedTab = .history
            return false
        }
        historyList.path = [item]
        selectedTab = .history
        return true
    }

    /// Answers a wildcatverify:// link from a control. Returns false for
    /// anything it doesn't recognize.
    @discardableResult
    func handle(_ url: URL) -> Bool {
        guard let link = AppDeepLink(url: url) else { return false }
        pendingScreenshot = nil
        startNewCheck()
        if link == .checkCopiedLink { check.checkCopiedLink() }
        return true
    }

    func showMissingScreenshotHelp() {
        finishWelcome()
        showsMissingScreenshotHelp = true
        showSiriSetup()
    }

    /// The Check page tip and Settings both lead here.
    func showSiriSetup() {
        settingsPath = [.siriSetup]
        selectedTab = .settings
    }

    func finishWelcome() {
        isShowingWelcome = false
        settings.welcomeSeen = true
    }

    func showAbout() {
        isShowingAbout = true
    }

    /// Settings → Keep My Checks.
    func setKeepHistory(_ isOn: Bool) {
        settings.keepHistory = isOn
        history.setPersistence(isOn ? persistence : nil)
    }

    /// Settings → Erase All Data: checks, saved photos and preferences.
    /// Sign in with Bluesky, then open the Feed on the user's own timeline.
    func signIn(handle: String? = nil, authenticate: (URL) async throws -> URL) async {
        await account.signIn(handle: handle, authenticate: authenticate)
        if account.isSignedIn {
            feed.showFollowing()
        }
    }

    func signOut() {
        account.signOut()
        feed.forgetFollowing()
    }

    func eraseAllData() {
        signOut()
        history.clear()
        history.setPersistence(nil)
        persistence.erase()
        settings.reset()
        historyList.path.removeAll()
    }
}
