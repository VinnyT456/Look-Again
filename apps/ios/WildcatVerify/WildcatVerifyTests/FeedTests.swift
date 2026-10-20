import Foundation
import Testing
@testable import WildcatVerify

struct FeedParsingTests {
    private func decodePost(_ json: String) throws -> BlueskyFeedResponse.Post {
        try JSONDecoder().decode(BlueskyFeedResponse.Post.self, from: Data(json.utf8))
    }

    private let imageEmbed = #"{"images": [{"thumb": "https://cdn.bsky.app/t.jpg", "alt": "A lake", "aspectRatio": {"width": 1200, "height": 800}}, {"thumb": "https://cdn.bsky.app/u.jpg"}]}"#

    private func json(embed: String?, postLabels: String = "[]", authorLabels: String = "[]") -> String {
        let embedPart = embed.map { #", "embed": \#($0)"# } ?? ""
        return #"""
        {"uri": "at://did:plc:abc/app.bsky.feed.post/3xyz",
         "author": {"handle": "alice.bsky.social", "displayName": "Alice", "labels": \#(authorLabels)},
         "record": {"text": "Sunset"}, "labels": \#(postLabels),
         "indexedAt": "2026-10-15T01:07:15.455Z"\#(embedPart)}
        """#
    }

    @Test func imagePostBecomesAFeedPost() throws {
        let post = try #require(BlueskyFeedService.post(from: decodePost(json(embed: imageEmbed))))
        #expect(post.authorHandle == "alice.bsky.social")
        #expect(post.authorName == "Alice")
        #expect(post.postURL.absoluteString == "https://bsky.app/profile/alice.bsky.social/post/3xyz")
        #expect(post.thumbURL.lastPathComponent == "t.jpg")
        #expect(post.imageAlt == "A lake")
        #expect(post.imageCount == 2)
        #expect(abs((post.aspectRatio ?? 0) - 1.5) < 1e-9)
        #expect(post.postedAt != nil, "Fractional-second timestamps parse")
    }

    @Test func textOnlyPostsAreSkipped() throws {
        #expect(BlueskyFeedService.post(from: try decodePost(json(embed: nil))) == nil)
    }

    @Test func labelledPostsAreSkipped() throws {
        let labelled = json(embed: imageEmbed, postLabels: #"[{"val": "porn"}]"#)
        #expect(BlueskyFeedService.post(from: try decodePost(labelled)) == nil)
    }

    @Test func postsByLabelledAuthorsAreSkipped() throws {
        let labelled = json(embed: imageEmbed, authorLabels: #"[{"val": "!hide"}]"#)
        #expect(BlueskyFeedService.post(from: try decodePost(labelled)) == nil)
    }

    @Test func quotePostImagesCount() throws {
        let media = #"{"media": {"images": [{"thumb": "https://cdn.bsky.app/m.jpg"}]}}"#
        let post = try #require(BlueskyFeedService.post(from: decodePost(json(embed: media))))
        #expect(post.thumbURL.lastPathComponent == "m.jpg")
    }

    @Test func missingDisplayNameFallsBackToHandle() throws {
        let noName = json(embed: imageEmbed).replacingOccurrences(of: #""displayName": "Alice", "#, with: "")
        let post = try #require(BlueskyFeedService.post(from: decodePost(noName)))
        #expect(post.authorName == "alice.bsky.social")
    }

    @Test(arguments: ["2026-10-15T01:07:15.455Z", "2026-10-15T01:07:15Z"])
    func parsesBlueskyTimestamps(value: String) {
        #expect(BlueskyFeedService.parseDate(value) != nil)
    }
}

@MainActor
struct FeedViewModelTests {
    @Test func firstLoadShowsPosts() async {
        let feed = StubFeed(pages: [nil: FeedPage(posts: [FeedFixtures.post("a"), FeedFixtures.post("b")], cursor: "c1")])
        let model = FeedViewModel(service: feed)
        #expect(model.status == .idle)
        await model.loadIfNeeded()
        #expect(model.status == .loaded)
        #expect(model.posts.map(\.text) == ["Post a", "Post b"])
        #expect(model.hasMore)
    }

    @Test func loadIfNeededOnlyLoadsOnce() async {
        let feed = StubFeed(pages: [nil: FeedPage(posts: [FeedFixtures.post("a")], cursor: nil)])
        let model = FeedViewModel(service: feed)
        await model.loadIfNeeded()
        await model.loadIfNeeded()
        #expect(feed.requestedCursors.count == 1)
    }

    @Test func failureShowsAnErrorWithNothingLoaded() async {
        let model = FeedViewModel(service: StubFeed(error: .network))
        await model.refresh()
        #expect(model.status == .failed(BlueskyError.network.errorDescription ?? ""))
    }

    @Test func failedRefreshKeepsWhatIsShown() async {
        let feed = StubFeed(pages: [nil: FeedPage(posts: [FeedFixtures.post("a")], cursor: nil)])
        let model = FeedViewModel(service: feed)
        await model.refresh()
        feed.error = .network
        await model.refresh()
        #expect(model.posts.count == 1)
        #expect(model.status == .loaded)
    }

    @Test func scrollingToTheEndLoadsTheNextPageWithoutDuplicates() async {
        let a = FeedFixtures.post("a"), b = FeedFixtures.post("b"), c = FeedFixtures.post("c")
        let feed = StubFeed(pages: [
            nil: FeedPage(posts: [a, b], cursor: "p2"),
            "p2": FeedPage(posts: [b, c], cursor: nil),
        ])
        let model = FeedViewModel(service: feed)
        await model.refresh()
        await model.loadMore(after: a)
        #expect(model.posts.count == 2, "Only the last post triggers paging")
        await model.loadMore(after: b)
        #expect(model.posts.map(\.id) == [a.id, b.id, c.id])
        #expect(!model.hasMore)
    }

    @Test func pagesWithNoImagePostsAreSkipped() async {
        let a = FeedFixtures.post("a"), d = FeedFixtures.post("d")
        let feed = StubFeed(pages: [
            nil: FeedPage(posts: [a], cursor: "p2"),
            "p2": FeedPage(posts: [], cursor: "p3"),
            "p3": FeedPage(posts: [d], cursor: nil),
        ])
        let model = FeedViewModel(service: feed)
        await model.refresh()
        await model.loadMore(after: a)
        #expect(model.posts.map(\.id) == [a.id, d.id])
    }

    @Test func openingAPostPushesIt() {
        let model = FeedViewModel(service: StubFeed())
        model.open(FeedFixtures.post("a"))
        #expect(model.path.count == 1)
    }

    @Test func feedChecksLandInMyChecks() async throws {
        let images = ImageRepository()
        let imageURL = URL.inMemoryImage(UUID())
        images.storeUpload(TestImages.solid(), for: imageURL)
        let post = BlueskyPost(authorHandle: "alice", text: "", postURL: imageURL, imageURL: imageURL)
        var recorded: [VerificationCase] = []
        let model = ShareViewModel(
            pipeline: CheckPipeline(bluesky: StubBluesky(result: .success(post)), classifier: StubClassifier(), images: images),
            onResult: { recorded.append($0) }
        )
        await model.check(.link("https://bsky.app/profile/alice/post/1"))
        #expect(recorded.count == 1)
    }
}

@MainActor
struct FeedModerationTests {
    private func loadedModel(settings: SettingsStore? = nil) async -> FeedViewModel {
        let feed = StubFeed(pages: [nil: FeedPage(posts: [
            FeedFixtures.post("1", handle: "alice.bsky.social"),
            FeedFixtures.post("2", handle: "alice.bsky.social"),
            FeedFixtures.post("3", handle: "bob.bsky.social"),
        ], cursor: nil)])
        let model = FeedViewModel(service: feed, settings: settings)
        await model.refresh()
        return model
    }

    @Test func authorDIDComesFromTheATURI() {
        #expect(FeedFixtures.post("1").authorDID == "did:plc:x")
    }

    @Test func hidingAPostHidesOnlyThatPost() async {
        let model = await loadedModel()
        model.hidePost(model.visiblePosts[0])
        #expect(model.visiblePosts.count == 2)
        #expect(model.posts.count == 3, "Hiding filters the view; nothing is deleted")
    }

    @Test func hidingAnAccountHidesAllItsPostsAndIsSaved() async throws {
        let suite = "WildcatVerifyTests-\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: suite))
        let settings = SettingsStore(defaults: defaults)
        let model = await loadedModel(settings: settings)
        let post = model.visiblePosts[0]
        model.hideAccount(of: post)
        #expect(model.visiblePosts.isEmpty, "All fixture posts share one DID")
        #expect(SettingsStore(defaults: defaults).hiddenAccounts[post.authorDID] == post.authorHandle)
    }

    @Test func showingAnAccountAgainBringsItsPostsBack() async {
        let settings = isolatedSettings()
        let model = await loadedModel(settings: settings)
        let post = model.visiblePosts[0]
        model.hideAccount(of: post)
        settings.hiddenAccounts[post.authorDID] = nil
        #expect(model.visiblePosts.count == 3)
    }

    @Test func eraseAllDataForgetsHiddenAccounts() {
        let settings = isolatedSettings()
        settings.hiddenAccounts = ["did:plc:x": "alice.bsky.social"]
        settings.reset()
        #expect(settings.hiddenAccounts.isEmpty)
    }
}

struct DisclaimerTests {
    @Test func sharedResultsSayTheyAreEstimates() {
        #expect(SampleData.lakefill.shareText.hasSuffix("An automated estimate, not proof."))
    }
}
