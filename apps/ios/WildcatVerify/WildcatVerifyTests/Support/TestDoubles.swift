import Foundation
import UIKit
@testable import WildcatVerify

/// Bluesky fetcher that returns a fixed post or throws a fixed error.
struct StubBluesky: BlueskyFetching {
    var result: Result<BlueskyPost, BlueskyError>

    func fetchPost(from link: String) async throws -> BlueskyPost {
        try result.get()
    }
}

/// Bluesky fetcher that never finishes until cancelled, for cancel tests.
struct HangingBluesky: BlueskyFetching {
    func fetchPost(from link: String) async throws -> BlueskyPost {
        try await Task.sleep(for: .seconds(60))
        throw BlueskyError.network
    }
}

/// Classifier that returns a fixed result.
struct StubClassifier: ImageClassifying {
    var result = ClassificationResult(verdict: .tampered, confidence: 0.876, hotspot: HotspotArea(xRatio: 0.1, yRatio: 0.2, widthRatio: 0.3, heightRatio: 0.4, label: "Edit"))
    var demo = false

    var isDemo: Bool { demo }

    func classify(_ image: UIImage) async throws -> ClassificationResult { result }
}

enum TestImages {
    /// A solid-colour image of the given pixel size.
    static func solid(_ color: UIColor = .systemPurple, width: Int = 40, height: Int = 20) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: CGSize(width: width, height: height), format: format).image { context in
            color.setFill()
            context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        }
    }

    static func pngData(width: Int = 40, height: Int = 20) -> Data {
        solid(width: width, height: height).pngData() ?? Data()
    }
}

/// Polls until `condition` is true or about a second passes.
@MainActor
func waitUntil(_ condition: () -> Bool) async throws {
    for _ in 0..<100 where !condition() {
        try await Task.sleep(for: .milliseconds(10))
    }
}

/// Feed fetcher that serves canned pages keyed by cursor (nil = first page).
final class StubFeed: FeedFetching, @unchecked Sendable {
    var pages: [String?: FeedPage]
    var error: BlueskyError?
    private(set) var requestedCursors: [String?] = []

    init(pages: [String?: FeedPage] = [:], error: BlueskyError? = nil) {
        self.pages = pages
        self.error = error
    }

    func fetchPage(cursor: String?) async throws -> FeedPage {
        requestedCursors.append(cursor)
        if let error { throw error }
        return pages[cursor] ?? FeedPage(posts: [], cursor: nil)
    }
}

enum FeedFixtures {
    static func post(_ id: String, handle: String = "alice.bsky.social") -> FeedPost {
        FeedPost(
            id: "at://did:plc:x/app.bsky.feed.post/\(id)",
            authorHandle: handle,
            authorName: "Alice",
            avatarURL: nil,
            text: "Post \(id)",
            postURL: URL(string: "https://bsky.app/profile/\(handle)/post/\(id)") ?? URL(fileURLWithPath: "/"),
            thumbURL: URL(string: "https://cdn.bsky.app/img/\(id).jpg") ?? URL(fileURLWithPath: "/"),
            imageAlt: "",
            aspectRatio: 1.5,
            postedAt: nil,
            imageCount: 1
        )
    }
}

/// A fresh, empty temporary folder for persistence tests.
func temporaryDirectory() -> URL {
    let url = URL.temporaryDirectory.appending(path: "WildcatVerifyTests-\(UUID().uuidString)", directoryHint: .isDirectory)
    try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
    return url
}

/// Settings backed by a throwaway UserDefaults suite.
@MainActor
func isolatedSettings() -> SettingsStore {
    let name = "WildcatVerifyTests-\(UUID().uuidString)"
    return SettingsStore(defaults: UserDefaults(suiteName: name) ?? .standard)
}
