import Foundation
import Testing
import UniformTypeIdentifiers
import UIKit
@testable import WildcatVerify

struct ShareInputTests {
    @Test(arguments: [
        ("https://bsky.app/profile/a.bsky.social/post/3abc", "https://bsky.app/profile/a.bsky.social/post/3abc"),
        ("Wow look https://bsky.app/profile/a.bsky.social/post/3abc !!", "https://bsky.app/profile/a.bsky.social/post/3abc"),
        ("first https://example.com then https://bsky.app/profile/b/post/x", "https://bsky.app/profile/b/post/x"),
        ("bare bsky.app/profile/c/post/y works too", "bsky.app/profile/c/post/y"),
    ])
    func findsBlueskyLinksInText(text: String, expected: String) {
        #expect(ShareInput.blueskyLink(in: text) == expected)
    }

    @Test(arguments: [
        "",
        "no links here",
        "https://example.com/profile/a/post/b",
        "https://bsky.app/profile/someone",
    ])
    func ignoresTextWithoutAPostLink(text: String) {
        #expect(ShareInput.blueskyLink(in: text) == nil)
    }
}

@MainActor
struct ShareViewModelTests {
    private func makeModel(bluesky: any BlueskyFetching = StubBluesky(result: .failure(.network)),
                           images: ImageRepository = ImageRepository()) -> ShareViewModel {
        ShareViewModel(pipeline: CheckPipeline(bluesky: bluesky, classifier: StubClassifier(), images: images))
    }

    @Test func startsReading() {
        #expect(makeModel().phase == .reading)
    }

    @Test func sharedImageGetsAVerdict() async throws {
        let images = ImageRepository()
        let model = makeModel(images: images)
        await model.check(.image(TestImages.pngData(width: 300, height: 200)))

        guard case .result(let item) = model.phase else {
            Issue.record("Expected a result, got \(model.phase)")
            return
        }
        #expect(item.verdict == .tampered)
        #expect(item.authorHandle.isEmpty)
        let url = try #require(item.imageURL)
        #expect(url.isInMemoryImage, "Shared images stay in memory")
        #expect(images.cachedImage(for: url) != nil)
    }

    @Test func sharedLinkGetsAVerdict() async {
        let images = ImageRepository()
        let imageURL = URL.inMemoryImage(UUID())
        images.storeUpload(TestImages.solid(), for: imageURL)
        let post = BlueskyPost(authorHandle: "carol.bsky.social", text: "Is this real?", postURL: imageURL, imageURL: imageURL)
        let model = makeModel(bluesky: StubBluesky(result: .success(post)), images: images)

        await model.check(.link("https://bsky.app/profile/carol.bsky.social/post/1"))
        guard case .result(let item) = model.phase else {
            Issue.record("Expected a result, got \(model.phase)")
            return
        }
        #expect(item.authorHandle == "carol.bsky.social")
        #expect(item.title == "Is this real?")
    }

    @Test func unreadableImageExplainsWhy() async {
        let model = makeModel()
        await model.check(.image(Data("not an image".utf8)))
        #expect(model.phase == .failed(CheckError.unreadablePhoto.errorDescription ?? ""))
    }

    @Test(arguments: [BlueskyError.postNotFound, .noImage, .network])
    func linkFailuresExplainWhy(error: BlueskyError) async {
        let model = makeModel(bluesky: StubBluesky(result: .failure(error)))
        await model.check(.link("https://bsky.app/profile/a/post/b"))
        #expect(model.phase == .failed(error.errorDescription ?? ""))
    }

    @Test func nothingCheckableIsUnsupported() async {
        let model = makeModel()
        await model.load(providers: [])
        #expect(model.phase == .failed(ShareError.unsupported.errorDescription ?? ""))
    }

    @Test func plainTextWithoutALinkIsUnsupported() async {
        let model = makeModel()
        await model.load(providers: [NSItemProvider(object: "just words" as NSString)])
        #expect(model.phase == .failed(ShareError.unsupported.errorDescription ?? ""))
    }

    @Test func sharedImageProviderIsChecked() async {
        let provider = NSItemProvider(item: TestImages.pngData() as NSData, typeIdentifier: UTType.png.identifier)
        let model = makeModel()
        await model.load(providers: [provider])
        guard case .result = model.phase else {
            Issue.record("Expected a result, got \(model.phase)")
            return
        }
    }

    @Test func sharedURLProviderIsChecked() async {
        let images = ImageRepository()
        let imageURL = URL.inMemoryImage(UUID())
        images.storeUpload(TestImages.solid(), for: imageURL)
        let post = BlueskyPost(authorHandle: "dan", text: "", postURL: imageURL, imageURL: imageURL)
        let model = makeModel(bluesky: StubBluesky(result: .success(post)), images: images)

        let link = URL(string: "https://bsky.app/profile/dan/post/9") ?? imageURL
        await model.load(providers: [NSItemProvider(object: link as NSURL)])
        guard case .result(let item) = model.phase else {
            Issue.record("Expected a result, got \(model.phase)")
            return
        }
        #expect(item.authorHandle == "dan")
    }

    @Test func nonBlueskyURLIsUnsupported() async {
        let model = makeModel()
        let url = URL(string: "https://example.com/photo") ?? URL(fileURLWithPath: "/")
        await model.load(providers: [NSItemProvider(object: url as NSURL)])
        #expect(model.phase == .failed(ShareError.unsupported.errorDescription ?? ""))
    }

    @Test func demoClassifierStillLabelsDemo() async {
        let model = ShareViewModel(pipeline: CheckPipeline(
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier(demo: true),
            images: ImageRepository()
        ))
        await model.check(.image(TestImages.pngData()))
        guard case .result(let item) = model.phase else {
            Issue.record("Expected a result")
            return
        }
        #expect(item.isDemo)
    }

}
