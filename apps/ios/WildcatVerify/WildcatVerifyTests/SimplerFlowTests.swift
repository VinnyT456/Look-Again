import Foundation
import Testing
import UIKit
@testable import WildcatVerify

/// A clipboard the test controls. Nothing here reads the real pasteboard.
@MainActor
final class FakeClipboard {
    var count = 1
    var hasLink = true

    var probe: ClipboardProbe {
        ClipboardProbe(changeCount: { self.count }, hasProbableLink: { self.hasLink })
    }
}

@MainActor
struct CopiedLinkOfferTests {
    private func makeModel(_ clipboard: FakeClipboard) -> CheckViewModel {
        CheckViewModel(
            history: HistoryStore(),
            bluesky: HangingBluesky(),
            classifier: StubClassifier(),
            clipboard: clipboard.probe
        )
    }

    @Test func aCopiedLinkIsOfferedOnce() async {
        let clipboard = FakeClipboard()
        let model = makeModel(clipboard)
        await model.refreshCopiedLinkOffer()
        #expect(model.offersCopiedLink)

        model.dismissCopiedLinkOffer()
        await model.refreshCopiedLinkOffer()
        #expect(!model.offersCopiedLink, "Dismissed until something new is copied")

        clipboard.count += 1
        await model.refreshCopiedLinkOffer()
        #expect(model.offersCopiedLink)
    }

    @Test func nothingLinkLikeMeansNoOffer() async {
        let clipboard = FakeClipboard()
        clipboard.hasLink = false
        let model = makeModel(clipboard)
        await model.refreshCopiedLinkOffer()
        #expect(!model.offersCopiedLink)
    }

    @Test func pastingABlueskyLinkChecksStraightAway() {
        let model = makeModel(FakeClipboard())
        model.checkPasted("look https://bsky.app/profile/a.bsky.social/post/3k")
        #expect(model.phase == .analyzing)
        #expect(model.inputURL == "https://bsky.app/profile/a.bsky.social/post/3k")
        model.cancelAnalysis()
    }

    @Test func pastingSomethingElseFromTheOfferExplains() {
        let model = makeModel(FakeClipboard())
        model.checkPasted("https://example.com/cat", explainIfNotBluesky: true)
        #expect(model.phase == .input)
        #expect(model.isShowingError)
        #expect(model.errorMessage.contains("isn't a Bluesky post"))
    }

    @Test func pastingSomethingElseInTheFieldJustFillsIt() {
        let model = makeModel(FakeClipboard())
        model.checkPasted("not a link")
        #expect(model.inputURL == "not a link")
        #expect(!model.isShowingError)
    }
}

@MainActor
struct FeedAutoCheckTests {
    private func post(_ id: String, images: ImageRepository) -> FeedPost {
        var post = FeedFixtures.post(id)
        post.thumbURL = URL.inMemoryImage(UUID())
        images.storeUpload(TestImages.solid(), for: post.thumbURL)
        return post
    }

    @Test func postsGetABadgeOneAtATime() async throws {
        let images = ImageRepository()
        let checker = FeedAutoChecker(classifier: StubClassifier(), images: images) { nil }
        let first = post("1", images: images)
        let second = post("2", images: images)
        checker.request(first)
        checker.request(second)
        checker.request(first)
        try await waitUntil { checker.verdicts.count == 2 && !checker.verdicts.values.contains(.checking) }
        #expect(checker.verdicts[first.id] == .done(verdict: .tampered, confidence: 88, isDemo: false))
        #expect(checker.verdicts[second.id] != nil)
    }

    @Test func nothingRunsWhenNotAllowed() async throws {
        let images = ImageRepository()
        let checker = FeedAutoChecker(classifier: StubClassifier(), images: images) { .lowPower }
        checker.request(post("1", images: images))
        try await Task.sleep(for: .milliseconds(100))
        #expect(checker.verdicts.isEmpty, "Off, Low Power Mode or a limited network")
    }

    @Test func visiblePostsAreCheckedWhenAPauseEnds() async throws {
        let images = ImageRepository()
        var pause: AutoCheckPause? = .lowPower
        let checker = FeedAutoChecker(classifier: StubClassifier(), images: images) { pause }
        let first = post("1", images: images)
        let second = post("2", images: images)
        checker.request(first)
        checker.request(second)
        try await Task.sleep(for: .milliseconds(100))
        #expect(checker.verdicts.isEmpty, "Paused, so nothing runs")
        #expect(checker.pause == .lowPower)

        pause = nil
        checker.resume()
        try await waitUntil { checker.verdicts.count == 2 && !checker.verdicts.values.contains(.checking) }
        #expect(checker.verdicts[first.id] != nil && checker.verdicts[second.id] != nil, "No scrolling needed")
    }

    @Test func postsThatScrolledAwayAreNotCheckedLater() async throws {
        let images = ImageRepository()
        var pause: AutoCheckPause? = .lowData
        let checker = FeedAutoChecker(classifier: StubClassifier(), images: images) { pause }
        let gone = post("1", images: images)
        checker.request(gone)
        checker.cancel(gone)
        pause = nil
        checker.resume()
        try await Task.sleep(for: .milliseconds(100))
        #expect(checker.verdicts[gone.id] == nil)
    }

    @Test func failedChecksAreRetriedOnResume() async throws {
        let images = ImageRepository()
        let checker = FeedAutoChecker(classifier: StubClassifier(), images: images) { nil }
        var broken = FeedFixtures.post("x")
        broken.thumbURL = URL.inMemoryImage(UUID())
        checker.request(broken)
        try await waitUntil { checker.verdicts[broken.id] == .failed }
        images.storeUpload(TestImages.solid(), for: broken.thumbURL)
        checker.resume()
        try await waitUntil { checker.verdicts[broken.id] != .failed && checker.verdicts[broken.id] != .checking }
        #expect(checker.verdicts[broken.id] != .failed)
    }

    @Test func pauseReasonsExplainThemselves() {
        #expect(AutoCheckPause.off.explanation == nil, "Off by choice needs no banner")
        #expect(AutoCheckPause.lowPower.explanation?.contains("Low Power Mode") == true)
        #expect(AutoCheckPause.lowData.explanation?.contains("Low Data Mode") == true)
    }

    @Test func unreachableImagesFailQuietly() async throws {
        let checker = FeedAutoChecker(classifier: StubClassifier(), images: ImageRepository()) { nil }
        var missing = FeedFixtures.post("x")
        missing.thumbURL = URL.inMemoryImage(UUID())
        checker.request(missing)
        try await waitUntil { checker.verdicts[missing.id] == .failed }
        #expect(checker.verdicts[missing.id] == .failed)
    }

    @Test func autoCheckIsOnByDefaultAndResetsOn() {
        let settings = isolatedSettings()
        #expect(settings.autoCheckFeed)
        settings.autoCheckFeed = false
        settings.reset()
        #expect(settings.autoCheckFeed)
    }

    @Test func confidenceNeverReadsAsCertain() {
        #expect(CheckPipeline.displayConfidence(0.999) == 99)
        #expect(CheckPipeline.displayConfidence(-1) == 0)
    }
}

@MainActor
struct WelcomeAndScreenshotTests {
    private func makeApp(settings: SettingsStore = isolatedSettings()) -> AppViewModel {
        AppViewModel(
            settings: settings,
            persistence: HistoryPersistence(directory: temporaryDirectory()),
            feedService: StubFeed(),
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier()
        )
    }

    @Test func welcomeShowsOnFirstLaunchOnly() {
        let settings = isolatedSettings()
        let first = makeApp(settings: settings)
        #expect(first.isShowingWelcome)
        first.finishWelcome()
        #expect(!makeApp(settings: settings).isShowingWelcome)
    }

    @Test func aSiriHandOffSkipsTheWelcome() async {
        let app = makeApp()
        await app.receiveScreenshot(TestImages.solid())
        #expect(!app.isShowingWelcome)
        #expect(app.settings.welcomeSeen)
    }

    @Test func unclearScreenshotsStillAskForABox() async {
        let app = makeApp()
        await app.receiveScreenshot(TestImages.solid(.white, width: 300, height: 600))
        #expect(app.pendingScreenshot != nil, "No confident photo, so the user boxes it")
        #expect(await PhotoAreaFinder.confidentPhoto(in: TestImages.solid(.white, width: 300, height: 600)) == nil)
    }

    @Test func adjustAreaReopensTheBoxScreen() async {
        let app = makeApp()
        let screenshot = TestImages.solid(width: 300, height: 600)
        await app.receiveScreenshot(screenshot)
        app.pendingScreenshot = nil
        app.adjustLastScreenshot()
        #expect(app.pendingScreenshot?.image === screenshot)
    }
}

@MainActor
struct LeftoverSignInTests {
    private func session() -> BlueskySession {
        BlueskySession(
            did: "did:plc:abc", handle: "alice.bsky.social",
            pds: URL(string: "https://pds.example.com") ?? URL(fileURLWithPath: "/"), issuer: "https://bsky.social",
            tokenEndpoint: URL(string: "https://bsky.social/oauth/token") ?? URL(fileURLWithPath: "/"),
            accessToken: "a", refreshToken: "r", expiresAt: .now.addingTimeInterval(3600), dpopKey: DPoPSigner().rawKey
        )
    }

    private func makeApp(welcomeSeen: Bool, keychain: KeychainStore) throws -> AppViewModel {
        keychain.save(try JSONEncoder().encode(session()))
        let settings = isolatedSettings()
        settings.welcomeSeen = welcomeSeen
        return AppViewModel(
            settings: settings,
            persistence: HistoryPersistence(directory: temporaryDirectory()),
            feedService: StubFeed(),
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier(),
            account: BlueskyAccount(keychain: keychain)
        )
    }

    @Test func aFreshInstallDropsASignInLeftByAnEarlierCopy() throws {
        let keychain = KeychainStore(service: "WildcatVerifyTests-\(UUID().uuidString)", account: "session")
        defer { keychain.delete() }
        let app = try makeApp(welcomeSeen: false, keychain: keychain)
        #expect(app.account.isSignedIn, "Loaded from the Keychain at launch")
        app.discardLeftoverSignIn()
        #expect(!app.account.isSignedIn)
        #expect(keychain.load() == nil)
    }

    @Test func anEstablishedInstallKeepsItsSignIn() throws {
        let keychain = KeychainStore(service: "WildcatVerifyTests-\(UUID().uuidString)", account: "session")
        defer { keychain.delete() }
        let app = try makeApp(welcomeSeen: true, keychain: keychain)
        app.discardLeftoverSignIn()
        #expect(app.account.isSignedIn)
        #expect(keychain.load() != nil)
    }

    @Test func eraseAllDataSignsOut() throws {
        let keychain = KeychainStore(service: "WildcatVerifyTests-\(UUID().uuidString)", account: "session")
        defer { keychain.delete() }
        let app = try makeApp(welcomeSeen: true, keychain: keychain)
        app.eraseAllData()
        #expect(!app.account.isSignedIn)
        #expect(keychain.load() == nil)
    }
}
