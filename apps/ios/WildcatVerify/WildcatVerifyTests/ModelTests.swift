import Foundation
import Testing
import UIKit
@testable import WildcatVerify

struct ModelTests {
    @Test func uploadsShowLibraryInsteadOfAHandle() {
        var item = SampleData.lakefill
        #expect(item.displayHandle == "@dailynorthwestern.bsky.social")
        item.authorHandle = ""
        #expect(item.displayHandle == "From your photo library")
    }

    @Test func shareTextMarksDemosAndIncludesSource() {
        let text = SampleData.monorail.shareText
        #expect(text.contains("(demo result)"))
        #expect(text.contains("Likely AI, 98% confidence"))
        #expect(text.contains("@chicago_future.bsky.social"))

        var real = SampleData.monorail
        real.isDemo = false
        real.authorHandle = ""
        real.postURL = nil
        #expect(!real.shareText.contains("demo"))
        #expect(!real.shareText.contains("Posted by"))
    }

    @Test func inMemoryURLsAreRecognised() {
        let url = URL.inMemoryImage(UUID())
        #expect(url.isInMemoryImage)
        #expect(!(URL(string: "https://example.com/a.jpg")?.isInMemoryImage ?? true))
        #expect(URL.inMemoryImage(UUID()) != url, "Each upload gets its own address")
    }

    @Test func everyVerdictHasDistinctCopyAndStyling() {
        let all = VerdictType.allCases
        #expect(Set(all.map(\.label)).count == all.count)
        #expect(Set(all.map(\.shortLabel)).count == all.count)
        #expect(Set(all.map(\.icon)).count == all.count, "Icons differ, so verdicts never rely on colour alone")
        #expect(all.allSatisfy { !$0.explanation.isEmpty })
        #expect(!VerdictType.real.hasAnomaly)
        #expect(VerdictType.ai.hasAnomaly && VerdictType.tampered.hasAnomaly)
    }

    @Test func filtersMatchOnlyTheirVerdict() {
        let cases = SampleData.examples
        #expect(cases.filter(VerdictFilter.all.matches).count == 3)
        for filter in [VerdictFilter.real, .tampered, .ai] {
            #expect(cases.filter(filter.matches).count == 1, "\(filter.title)")
        }
        #expect(VerdictFilter.allCases.map(\.title) == ["All", "Real", "Edited", "AI"])
    }

    @Test func examplesCoverEveryVerdictAndAreDemos() {
        let allDemo = SampleData.examples.allSatisfy { $0.isDemo }
        #expect(allDemo)
        #expect(Set(SampleData.examples.map(\.verdict)) == Set(VerdictType.allCases))
        #expect(Set(SampleData.examples.map(\.id)).count == 3)
        let withoutPhotos = SampleData.examples.allSatisfy { $0.imageURL == nil }
        #expect(withoutPhotos)
    }

    @Test func hotspotsStayInsideTheImage() {
        for item in SampleData.examples {
            guard let spot = item.hotspot else { continue }
            #expect(spot.xRatio >= 0 && spot.yRatio >= 0)
            #expect(spot.xRatio + spot.widthRatio <= 1)
            #expect(spot.yRatio + spot.heightRatio <= 1)
        }
    }

    @Test func errorMessagesAreAllWritten() {
        let errors: [BlueskyError] = [.invalidLink, .postNotFound, .noImage, .network]
        #expect(errors.allSatisfy { ($0.errorDescription ?? "").count > 10 })
        #expect(CheckError.unreadablePhoto.errorDescription?.isEmpty == false)
    }

    @Test func policyLinksAreValid() {
        #expect(AppLinks.privacyPolicy?.scheme == "https")
        #expect(AppLinks.blueskyPrivacy?.scheme == "https")
        #expect(AppLinks.support?.scheme == "https")
    }
}

struct ImageProcessingTests {
    @Test func downsampleCapsTheLongEdgeAndKeepsAspect() async throws {
        let image = try #require(await ImageRepository.downsample(TestImages.pngData(width: 800, height: 400), maxPixelSize: 200))
        #expect(image.size.width == 200)
        #expect(image.size.height == 100)
    }

    @Test func downsampleNeverUpscales() async throws {
        let image = try #require(await ImageRepository.downsample(TestImages.pngData(width: 40, height: 20), maxPixelSize: 2048))
        #expect(image.size.width == 40)
    }

    @Test func garbageIsNotAnImage() async {
        #expect(await ImageRepository.downsample(Data("nope".utf8), maxPixelSize: 100) == nil)
        #expect(await ImageRepository.downsample(Data(), maxPixelSize: 100) == nil)
    }

    @Test func demoClassifierIsStablePerImage() async throws {
        let classifier = DemoImageClassifier()
        #expect(classifier.isDemo)
        let image = TestImages.solid(.systemTeal)
        let first = try await classifier.classify(image)
        let second = try await classifier.classify(image)
        #expect(first.verdict == second.verdict)
        #expect(first.confidence == second.confidence)
        #expect((0.8...0.99).contains(first.confidence))
        #expect((first.hotspot == nil) == (first.verdict == .real), "Only edited and AI verdicts point at an area")
    }

    @Test func verdictCopyCoversEveryVerdict() {
        for verdict in VerdictType.allCases {
            let copy = VerdictCopy.for(verdict)
            #expect(!copy.summary.isEmpty && !copy.action.isEmpty)
            #expect(copy.findings.count == 3)
        }
    }
}

@MainActor
struct ImageRepositoryTests {
    @Test func uploadsAreServedFromMemory() async throws {
        let repository = ImageRepository()
        let url = URL.inMemoryImage(UUID())
        repository.storeUpload(TestImages.solid(), for: url)
        #expect(repository.cachedImage(for: url) != nil)
        _ = try await repository.image(for: url)
    }

    @Test func missingUploadThrowsInsteadOfFetching() async {
        await #expect(throws: URLError.self) {
            try await ImageRepository().image(for: URL.inMemoryImage(UUID()))
        }
    }

    @Test func removingUploadsForgetsThem() {
        let repository = ImageRepository()
        let one = URL.inMemoryImage(UUID())
        let two = URL.inMemoryImage(UUID())
        repository.storeUpload(TestImages.solid(), for: one)
        repository.storeUpload(TestImages.solid(), for: two)

        repository.removeUpload(for: one)
        #expect(repository.cachedImage(for: one) == nil)
        #expect(repository.cachedImage(for: two) != nil)
        repository.removeAllUploads()
        #expect(repository.cachedImage(for: two) == nil)
    }
}
