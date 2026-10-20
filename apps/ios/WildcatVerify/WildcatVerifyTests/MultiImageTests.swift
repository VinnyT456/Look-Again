import Foundation
import Testing
import UIKit
@testable import WildcatVerify

/// Classifier that answers by image width, so each image in a post can get
/// its own verdict.
private struct WidthClassifier: ImageClassifying {
    var results: [Int: ClassificationResult]
    var isDemo: Bool { false }

    func classify(_ image: UIImage) async throws -> ClassificationResult {
        results[Int(image.size.width)] ?? ClassificationResult(verdict: .real, confidence: 0.9, hotspot: nil)
    }
}

@MainActor
struct MultiImageTests {
    private func post(widths: [Int], images: ImageRepository) -> BlueskyPost {
        let urls = widths.map { width in
            let url = URL.inMemoryImage(UUID())
            images.storeUpload(TestImages.solid(width: width, height: 20), for: url)
            return url
        }
        return BlueskyPost(
            authorHandle: "bob.bsky.social",
            text: "Three photos",
            postURL: URL(string: "https://bsky.app/profile/bob.bsky.social/post/1") ?? urls[0],
            imageURL: urls[0],
            moreImageURLs: Array(urls.dropFirst())
        )
    }

    @Test func everyImageIsCheckedAndTheMostSuspiciousLeads() async throws {
        let images = ImageRepository()
        let classifier = WidthClassifier(results: [
            41: ClassificationResult(verdict: .ai, confidence: 0.7, hotspot: nil),
            42: ClassificationResult(verdict: .ai, confidence: 0.95, hotspot: nil),
        ])
        let pipeline = CheckPipeline(
            bluesky: StubBluesky(result: .success(post(widths: [40, 41, 42], images: images))),
            classifier: classifier,
            images: images
        )
        let lead = try await pipeline.checkPost(link: "https://bsky.app/profile/bob.bsky.social/post/1")
        let all = try #require(lead.postImages)
        #expect(all.count == 3)
        #expect(all.map(\.verdict) == [.real, .ai, .ai], "Kept in post order")
        #expect(lead.id == all[2].id, "The most confident AI image leads")
        #expect(lead.confidencePercentage == 95)
        #expect(all.allSatisfy { $0.postImages == nil }, "No nesting")
    }

    @Test func singleImagePostsHaveNoImageList() async throws {
        let images = ImageRepository()
        let pipeline = CheckPipeline(
            bluesky: StubBluesky(result: .success(post(widths: [40], images: images))),
            classifier: StubClassifier(),
            images: images
        )
        let item = try await pipeline.checkPost(link: "https://bsky.app/profile/bob.bsky.social/post/1")
        #expect(item.postImages == nil)
    }

    @Test func suspicionOrdersAIThenEditedThenReal() {
        func item(_ verdict: VerdictType, _ confidence: Int) -> VerificationCase {
            var c = SampleData.lakefill
            c.verdict = verdict
            c.confidencePercentage = confidence
            return c
        }
        let ranked = [item(.real, 99), item(.real, 55), item(.tampered, 60), item(.ai, 51)]
            .sorted { CheckPipeline.suspicion($0) > CheckPipeline.suspicion($1) }
        #expect(ranked.map(\.verdict) == [.ai, .tampered, .real, .real])
        #expect(ranked.last?.confidencePercentage == 99, "A confident Real is the least suspicious")
    }

    @Test func threadParsingReadsEveryImage() throws {
        let json = #"""
        {"thread":{"post":{"author":{"handle":"bob.bsky.social"},"record":{"text":"hi"},
        "embed":{"images":[{"fullsize":"https://cdn.bsky.app/a.jpg"},{"fullsize":"https://cdn.bsky.app/b.jpg"}]}}}}
        """#
        let thread = try JSONDecoder().decode(BlueskyThread.self, from: Data(json.utf8))
        #expect(thread.thread.post?.embed?.allImages.count == 2)

        let quoted = #"""
        {"thread":{"post":{"author":{"handle":"bob.bsky.social"},"record":{},
        "embed":{"media":{"images":[{"fullsize":"https://cdn.bsky.app/c.jpg"}]}}}}}
        """#
        let quote = try JSONDecoder().decode(BlueskyThread.self, from: Data(quoted.utf8))
        #expect(quote.thread.post?.embed?.allImages.map(\.lastPathComponent) == ["c.jpg"])
    }

    @Test func savedChecksFromBeforeMultiImageStillLoad() throws {
        var old = SampleData.lakefill
        old.postImages = nil
        let data = try JSONEncoder().encode([old])
        let text = try #require(String(data: data, encoding: .utf8))
        #expect(!text.contains("postImages"), "Nil isn't written, so old files look the same")
        let decoded = try JSONDecoder().decode([VerificationCase].self, from: data)
        #expect(decoded.first?.postImages == nil)
    }
}
