import Foundation
import Testing
import UIKit
@testable import WildcatVerify

/// Everything that goes over the network, against a stubbed URLSession.
/// Serialized because the stub's reply is shared static state.
@Suite(.serialized)
@MainActor
struct NetworkTests {
    private let link = "https://bsky.app/profile/alice.bsky.social/post/3abc"

    init() {
        StubURLProtocol.reset()
    }

    private func threadJSON(embed: String?, text: String = "Look at this") -> Data {
        let embedJSON = embed.map { ", \"embed\": \($0)" } ?? ""
        let json = """
        {"thread": {"post": {"author": {"handle": "alice.bsky.social"}, "record": {"text": "\(text)"}\(embedJSON)}}}
        """
        return Data(json.utf8)
    }

    private let imagesEmbed = #"{"images": [{"fullsize": "https://cdn.bsky.app/img/full.jpg"}]}"#
    private let recordWithMediaEmbed = #"{"media": {"images": [{"fullsize": "https://cdn.bsky.app/img/media.jpg"}]}}"#

    // MARK: Bluesky

    @Test func fetchesPostWithImage() async throws {
        let body = threadJSON(embed: imagesEmbed)
        StubURLProtocol.reply = { _ in .response(status: 200, body: body) }
        let post = try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)

        #expect(post.authorHandle == "alice.bsky.social")
        #expect(post.text == "Look at this")
        #expect(post.imageURL.absoluteString == "https://cdn.bsky.app/img/full.jpg")
        #expect(post.postURL.absoluteString == "https://bsky.app/profile/alice.bsky.social/post/3abc")
        let requested = try #require(StubURLProtocol.requestedURLs.first)
        #expect(requested.host() == "public.api.bsky.app")
    }

    @Test func readsImageFromQuotePostMedia() async throws {
        let body = threadJSON(embed: recordWithMediaEmbed)
        StubURLProtocol.reply = { _ in .response(status: 200, body: body) }
        let post = try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        #expect(post.imageURL.lastPathComponent == "media.jpg")
    }

    @Test func textOnlyPostIsNoImage() async {
        let body = threadJSON(embed: nil)
        StubURLProtocol.reply = { _ in .response(status: 200, body: body) }
        await #expect(throws: BlueskyError.noImage) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test(arguments: [400, 404, 500])
    func errorStatusIsPostNotFound(status: Int) async {
        StubURLProtocol.reply = { _ in .response(status: status, body: Data()) }
        await #expect(throws: BlueskyError.postNotFound) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func malformedJSONIsPostNotFound() async {
        StubURLProtocol.reply = { _ in .response(status: 200, body: Data("<html>".utf8)) }
        await #expect(throws: BlueskyError.postNotFound) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func deletedPostIsPostNotFound() async {
        StubURLProtocol.reply = { _ in .response(status: 200, body: Data(#"{"thread": {}}"#.utf8)) }
        await #expect(throws: BlueskyError.postNotFound) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test(arguments: [URLError.Code.notConnectedToInternet, .timedOut, .cannotFindHost])
    func connectionProblemsAreNetworkErrors(code: URLError.Code) async {
        StubURLProtocol.reply = { _ in .failure(code) }
        await #expect(throws: BlueskyError.network) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func cancelledRequestIsCancellationNotAnError() async {
        StubURLProtocol.reply = { _ in .failure(.cancelled) }
        await #expect(throws: CancellationError.self) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func invalidLinkMakesNoRequest() async {
        await #expect(throws: BlueskyError.invalidLink) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: "https://twitter.com/x/status/1")
        }
        #expect(StubURLProtocol.requestedURLs.isEmpty)
    }

    // MARK: Image download

    @Test func downloadsAndCachesImage() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/a.png"))
        let png = TestImages.pngData(width: 400, height: 200)
        StubURLProtocol.reply = { _ in .response(status: 200, body: png) }
        let repository = ImageRepository(session: StubURLProtocol.session())

        let image = try await repository.image(for: url, maxPixelSize: 100)
        #expect(max(image.size.width, image.size.height) <= 100)
        _ = try await repository.image(for: url, maxPixelSize: 100)
        #expect(StubURLProtocol.requestedURLs.count == 1, "Second load should come from the cache")
    }

    @Test func differentSizesReuseDownloadedData() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/b.png"))
        let png = TestImages.pngData(width: 400, height: 200)
        StubURLProtocol.reply = { _ in .response(status: 200, body: png) }
        let repository = ImageRepository(session: StubURLProtocol.session())

        _ = try await repository.image(for: url, maxPixelSize: 64)
        _ = try await repository.image(for: url, maxPixelSize: 300)
        #expect(StubURLProtocol.requestedURLs.count == 1)
    }

    @Test func imageServerErrorThrows() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/missing.png"))
        StubURLProtocol.reply = { _ in .response(status: 404, body: Data()) }
        await #expect(throws: URLError.self) {
            try await ImageRepository(session: StubURLProtocol.session()).image(for: url)
        }
    }

    @Test func nonImageDataThrows() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/not-an-image"))
        StubURLProtocol.reply = { _ in .response(status: 200, body: Data("hello".utf8)) }
        await #expect(throws: URLError.self) {
            try await ImageRepository(session: StubURLProtocol.session()).image(for: url)
        }
    }

    // MARK: Full link check

    @Test func checkingALinkEndToEnd() async throws {
        // Build bodies up front: the stub runs on URLSession's thread, so it must
        // not call back into this main-actor test.
        let thread = threadJSON(embed: imagesEmbed, text: #"Breaking: lake monorail\nmore text"#)
        let image = TestImages.pngData()
        StubURLProtocol.reply = { request in
            request.url?.host() == "public.api.bsky.app"
                ? .response(status: 200, body: thread)
                : .response(status: 200, body: image)
        }
        let session = StubURLProtocol.session()
        let history = HistoryStore()
        let model = CheckViewModel(
            history: history,
            bluesky: BlueskyService(session: session),
            classifier: StubClassifier(),
            images: ImageRepository(session: session)
        )
        model.inputURL = "  \(link)  "
        model.checkPost()
        try await waitUntil { !model.path.isEmpty || model.isShowingError }

        #expect(!model.isShowingError, "Unexpected error: \(model.errorMessage)")
        let item = try #require(model.path.first)
        #expect(item.title == "Breaking: lake monorail")
        #expect(item.authorHandle == "alice.bsky.social")
        #expect(item.verdict == .tampered)
        #expect(item.confidencePercentage == 88)
        #expect(!item.isDemo)
        #expect(history.cases.first?.id == item.id)
        #expect(model.inputURL.isEmpty, "Field clears after a successful check")
    }
}
