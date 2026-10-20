import Foundation
import Testing
@testable import WildcatVerify

struct AppDeepLinkTests {
    @Test func linksRoundTrip() {
        for link in AppDeepLink.allCases {
            #expect(AppDeepLink(url: link.url) == link)
        }
    }

    @Test func onlyKnownActionsAreAccepted() throws {
        #expect(AppDeepLink(url: try #require(URL(string: "wildcatverify://delete-everything"))) == nil)
        #expect(AppDeepLink(url: try #require(URL(string: "https://check"))) == nil)
        #expect(AppDeepLink(url: try #require(URL(string: "WildcatVerify://CHECK"))) == .check, "Scheme and host ignore case")
    }
}

@MainActor
struct DeepLinkRoutingTests {
    private func makeApp() -> AppViewModel {
        AppViewModel(
            settings: isolatedSettings(),
            persistence: HistoryPersistence(directory: temporaryDirectory()),
            feedService: StubFeed(),
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier()
        )
    }

    @Test func checkLinkOpensAFreshCheckTab() {
        let app = makeApp()
        app.selectedTab = .feed
        app.check.inputURL = "half typed"
        #expect(app.handle(AppDeepLink.check.url))
        #expect(app.selectedTab == .check)
        #expect(app.check.inputURL.isEmpty)
    }

    @Test func unknownLinksAreIgnored() throws {
        let app = makeApp()
        app.selectedTab = .feed
        #expect(!app.handle(try #require(URL(string: "wildcatverify://nope"))))
        #expect(app.selectedTab == .feed)
    }

    @Test func copiedLinkWithoutABlueskyLinkExplainsWhy() {
        let app = makeApp()
        app.check.checkCopiedLink(from: "just some words")
        #expect(app.check.isShowingError)
        #expect(app.check.errorMessage.contains("Copy Link"))
        #expect(app.check.phase == .input)
    }

    @Test func copiedLinkStartsTheCheck() {
        let app = makeApp()
        app.check.checkCopiedLink(from: "look https://bsky.app/profile/a.bsky.social/post/3k")
        #expect(app.check.phase == .analyzing)
        #expect(app.check.inputURL == "https://bsky.app/profile/a.bsky.social/post/3k")
    }
}
