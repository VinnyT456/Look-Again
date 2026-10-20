import Foundation
import Testing
import UIKit
@testable import WildcatVerify

@MainActor
struct CheckViewModelTests {
    private let link = "https://bsky.app/profile/a/post/b"

    /// A post whose image is an in-memory upload, so no network is needed.
    private func makeModel(
        bluesky: any BlueskyFetching,
        classifier: any ImageClassifying = StubClassifier(),
        history: HistoryStore = HistoryStore()
    ) -> CheckViewModel {
        CheckViewModel(history: history, bluesky: bluesky, classifier: classifier, images: ImageRepository())
    }

    private func reachablePost(images: ImageRepository) -> BlueskyPost {
        let imageURL = URL.inMemoryImage(UUID())
        images.storeUpload(TestImages.solid(), for: imageURL)
        return BlueskyPost(
            authorHandle: "bob.bsky.social",
            text: "",
            postURL: URL(string: "https://bsky.app/profile/bob.bsky.social/post/1") ?? imageURL,
            imageURL: imageURL
        )
    }

    // MARK: Input

    @Test func checkPostNeedsALink() {
        let model = makeModel(bluesky: StubBluesky(result: .failure(.network)))
        #expect(!model.canCheckPost)
        model.inputURL = "   \n"
        #expect(!model.canCheckPost, "Whitespace is not a link")
        model.inputURL = link
        #expect(model.canCheckPost)
    }

    @Test func emptyLinkDoesNothing() {
        let model = makeModel(bluesky: StubBluesky(result: .failure(.network)))
        model.checkPost()
        #expect(model.phase == .input)
        #expect(!model.isShowingError)
    }

    @Test func cannotStartASecondCheckWhileAnalyzing() {
        let model = makeModel(bluesky: HangingBluesky())
        model.inputURL = link
        model.checkPost()
        #expect(model.phase == .analyzing)
        #expect(!model.canCheckPost, "Check Post is disabled during analysis")
        model.cancelAnalysis()
    }

    // MARK: Success

    @Test func successfulCheckPushesResultAndRecordsIt() async throws {
        let images = ImageRepository()
        let history = HistoryStore()
        let model = CheckViewModel(
            history: history,
            bluesky: StubBluesky(result: .success(reachablePost(images: images))),
            classifier: StubClassifier(),
            images: images
        )
        model.inputURL = link
        model.checkPost()
        try await waitUntil { !model.path.isEmpty }

        let item = try #require(model.path.last)
        #expect(item.title == "Bluesky post", "Empty post text falls back to a generic title")
        #expect(item.hotspot?.label == "Edit")
        #expect(item.detectedIssue == "Edit")
        #expect(item.keyFindings.count == 3)
        #expect(history.cases.map(\.id) == [item.id])
        #expect(history.unseenCount == 1)
        #expect(model.phase == .input)
    }

    @Test func demoClassifierResultsAreFlaggedDemo() async throws {
        let images = ImageRepository()
        let model = CheckViewModel(
            history: HistoryStore(),
            bluesky: StubBluesky(result: .success(reachablePost(images: images))),
            classifier: StubClassifier(demo: true),
            images: images
        )
        model.inputURL = link
        model.checkPost()
        try await waitUntil { !model.path.isEmpty }
        #expect(model.path.last?.isDemo == true)
    }

    // MARK: Errors

    @Test(arguments: [BlueskyError.invalidLink, .postNotFound, .noImage, .network])
    func fetchFailureShowsItsMessage(error: BlueskyError) async throws {
        let model = makeModel(bluesky: StubBluesky(result: .failure(error)))
        model.inputURL = link
        model.checkPost()
        try await waitUntil { model.isShowingError }

        #expect(model.phase == .input)
        #expect(model.errorMessage == error.errorDescription)
        #expect(model.path.isEmpty)
        #expect(model.inputURL == link, "The link stays so the user can fix it")
    }

    @Test func imageThatCannotLoadShowsAnError() async throws {
        // Post points at an in-memory image that was never stored.
        let post = BlueskyPost(
            authorHandle: "a",
            text: "",
            postURL: URL.inMemoryImage(UUID()),
            imageURL: URL.inMemoryImage(UUID())
        )
        let model = makeModel(bluesky: StubBluesky(result: .success(post)))
        model.inputURL = link
        model.checkPost()
        try await waitUntil { model.isShowingError }
        #expect(!model.errorMessage.isEmpty)
        #expect(model.path.isEmpty)
    }

    // MARK: Cancel and reset

    @Test func cancelReturnsToInputWithoutError() async throws {
        let model = makeModel(bluesky: HangingBluesky())
        model.inputURL = link
        model.checkPost()
        model.cancelAnalysis()
        try await Task.sleep(for: .milliseconds(150))

        #expect(model.phase == .input)
        #expect(!model.isShowingError, "Cancelling must never surface an error")
        #expect(model.path.isEmpty)
    }

    @Test func resetClearsEverything() async throws {
        let model = makeModel(bluesky: StubBluesky(result: .failure(.network)))
        model.inputURL = link
        model.checkPost()
        try await waitUntil { model.isShowingError }
        model.path = [SampleData.monorail]

        model.reset()
        #expect(model.inputURL.isEmpty)
        #expect(model.path.isEmpty)
        #expect(!model.isShowingError)
        #expect(model.phase == .input)
    }

    // MARK: Titles

    @Test func titleUsesFirstLine() {
        #expect(CheckPipeline.title(from: "Hello\nworld") == "Hello")
        #expect(CheckPipeline.title(from: "") == "Bluesky post")
        #expect(CheckPipeline.title(from: "\n\nSecond") == "Second")
    }

    @Test func longTitlesAreTruncated() {
        let title = CheckPipeline.title(from: String(repeating: "a", count: 200))
        #expect(title.count == 60)
        #expect(title.hasSuffix("…"))
    }
}
