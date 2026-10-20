import Foundation
import Testing
import UIKit
@testable import WildcatVerify

/// Locates files bundled with the test target.
private final class FixtureBundle {}

private struct Reference: Decodable {
    var fakeProb: Double
    var tensorMean: Double
    var channelMeans: [Double]
    var patchMap: [Double]

    enum CodingKeys: String, CodingKey {
        case fakeProb = "fake_prob"
        case tensorMean = "tensor_mean"
        case channelMeans = "channel_means"
        case patchMap = "patch_map"
    }
}

/// Expected values come from Fixtures/reference.json, produced by running the
/// exported model in Python with the model's own Hugging Face image processor.
private enum Fixtures {
    static let bundle = Bundle(for: FixtureBundle.self)

    static func image(_ name: String) throws -> UIImage {
        let url = try #require(bundle.url(forResource: name, withExtension: "png"), "Missing fixture \(name).png")
        return try #require(UIImage(contentsOfFile: url.path()))
    }

    static func reference(_ name: String) throws -> Reference {
        let url = try #require(bundle.url(forResource: "reference", withExtension: "json"))
        let all = try JSONDecoder().decode([String: Reference].self, from: Data(contentsOf: url))
        return try #require(all[name])
    }
}

struct DetectorPreprocessorTests {
    @Test func tensorHasTheModelsShape() throws {
        let tensor = try DetectorPreprocessor.tensor(from: TestImages.solid(width: 800, height: 500))
        #expect(tensor.shape == [1, 3, 384, 384])
        #expect(tensor.dataType == .float32)
    }

    @Test func whitePixelsNormaliseWithClipMeanAndStd() throws {
        let tensor = try DetectorPreprocessor.tensor(from: TestImages.solid(.white, width: 500, height: 500))
        for channel in 0..<3 {
            let expected = (1 - DetectorPreprocessor.mean[channel]) / DetectorPreprocessor.std[channel]
            let value = tensor[[0, NSNumber(value: channel), 100, 100]].floatValue
            #expect(abs(value - expected) < 0.01, "channel \(channel)")
        }
    }

    @Test func tinyImagesAreScaledUpNotRejected() throws {
        let tensor = try DetectorPreprocessor.tensor(from: TestImages.solid(width: 12, height: 9))
        #expect(tensor.shape == [1, 3, 384, 384])
    }

    @Test(arguments: ["gradient", "plasma", "soft_noise"])
    func matchesPythonPreprocessing(fixture: String) throws {
        let reference = try Fixtures.reference(fixture)
        let tensor = try DetectorPreprocessor.tensor(from: Fixtures.image(fixture))
        let plane = 384 * 384
        let pointer = tensor.dataPointer.bindMemory(to: Float.self, capacity: 3 * plane)
        for channel in 0..<3 {
            var sum = 0.0
            for index in 0..<plane { sum += Double(pointer[channel * plane + index]) }
            let mean = sum / Double(plane)
            // Bicubic resampling differs slightly between Core Graphics and PIL.
            #expect(abs(mean - reference.channelMeans[channel]) < 0.03, "\(fixture) channel \(channel): \(mean) vs \(reference.channelMeans[channel])")
        }
    }
}

struct VerdictMappingTests {
    @Test func highProbabilityIsAI() {
        let result = CoreMLImageClassifier.result(fakeProbability: 0.93)
        #expect(result.verdict == .ai)
        #expect(abs(result.confidence - 0.93) < 1e-9)
        #expect(result.hotspot == nil, "The model doesn't localize, so no highlight is invented")
    }

    @Test func lowProbabilityIsReal() {
        let result = CoreMLImageClassifier.result(fakeProbability: 0.2)
        #expect(result.verdict == .real)
        #expect(abs(result.confidence - 0.8) < 1e-9)
    }

    @Test func thresholdBelongsToAI() {
        #expect(CoreMLImageClassifier.result(fakeProbability: 0.5).verdict == .ai)
        #expect(CoreMLImageClassifier.result(fakeProbability: 0.4999).verdict == .real)
    }

    @Test func outOfRangeOutputIsClamped() {
        #expect(CoreMLImageClassifier.result(fakeProbability: 1.7).confidence == 1)
        #expect(CoreMLImageClassifier.result(fakeProbability: -0.3).confidence == 1)
    }

    @Test func modelNeverSaysEdited() {
        for probability in stride(from: 0.0, through: 1.0, by: 0.05) {
            #expect(CoreMLImageClassifier.result(fakeProbability: probability).verdict != .tampered)
        }
    }
}

@MainActor
struct DetectorModelTests {
    @Test func modelShipsInTheAppBundle() throws {
        #expect(CoreMLImageClassifier.modelURL() != nil)
        let classifier = try #require(CoreMLImageClassifier.load())
        #expect(!classifier.isDemo)
    }

    @Test func factoryUsesTheRealModel() {
        #expect(!ClassifierFactory.make().isDemo, "Results are labelled demo only if the model fails to load")
    }

    @Test(arguments: ["gradient", "plasma", "soft_noise"])
    func matchesPythonProbability(fixture: String) async throws {
        let reference = try Fixtures.reference(fixture)
        let classifier = try #require(CoreMLImageClassifier.load())
        let probability = try await classifier.fakeProbability(for: Fixtures.image(fixture))
        #expect(abs(probability - reference.fakeProb) < 0.05, "\(fixture): app \(probability) vs Python \(reference.fakeProb)")
        let verdict = try await classifier.classify(Fixtures.image(fixture)).verdict
        #expect(verdict == (reference.fakeProb >= 0.5 ? .ai : .real))
    }

    @Test(arguments: ["gradient", "plasma", "soft_noise"])
    func heatmapMatchesPython(fixture: String) async throws {
        let reference = try Fixtures.reference(fixture)
        let classifier = try #require(CoreMLImageClassifier.load())
        let output = try await classifier.predict(Fixtures.image(fixture))
        let heatmap = try #require(output.heatmap, "The bundled model must provide patch_map")
        let app = heatmap.values.map(Double.init)
        #expect(app.count == reference.patchMap.count)
        let correlation = Self.pearson(app, reference.patchMap)
        // Preprocessing resamples slightly differently from PIL, so allow a little drift.
        // Same model file, but the Mac reference and the app can run it on
        // different compute units; saturated images (100% AI) drift most.
        #expect(correlation > 0.9, "\(fixture): heatmap correlation \(correlation)")
    }

    @Test func classifierAttachesTheHeatmap() async throws {
        let classifier = try #require(CoreMLImageClassifier.load())
        let result = try await classifier.classify(Fixtures.image("soft_noise"))
        #expect(result.verdict == .ai)
        #expect(result.heatmap?.hasSignal == true)
        #expect(result.hotspot == nil)
    }

    private static func pearson(_ a: [Double], _ b: [Double]) -> Double {
        let n = Double(a.count)
        let meanA = a.reduce(0, +) / n
        let meanB = b.reduce(0, +) / n
        var covariance = 0.0, varianceA = 0.0, varianceB = 0.0
        for (x, y) in zip(a, b) {
            covariance += (x - meanA) * (y - meanB)
            varianceA += (x - meanA) * (x - meanA)
            varianceB += (y - meanB) * (y - meanB)
        }
        return covariance / (varianceA * varianceB).squareRoot()
    }

    @Test func confidenceNeverShowsCertainty() async throws {
        let pipeline = CheckPipeline(
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier(result: ClassificationResult(verdict: .ai, confidence: 0.9996)),
            images: ImageRepository()
        )
        let item = try await pipeline.checkImage(data: TestImages.pngData())
        #expect(item.confidencePercentage == 99)
    }

    @Test func sameImageSameAnswer() async throws {
        let classifier = try #require(CoreMLImageClassifier.load())
        let image = try Fixtures.image("plasma")
        let first = try await classifier.fakeProbability(for: image)
        let second = try await classifier.fakeProbability(for: image)
        #expect(abs(first - second) < 1e-4)
    }

    @Test func realResultsAreNotLabelledDemo() async throws {
        let pipeline = CheckPipeline(
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: try #require(CoreMLImageClassifier.load()),
            images: ImageRepository()
        )
        let item = try await pipeline.checkImage(data: TestImages.pngData(width: 400, height: 300))
        #expect(!item.isDemo)
        #expect(item.hotspot == nil)
        #expect(item.verdict != .tampered)
    }
}

@MainActor
struct HonestResultsTests {
    @Test func aiVerdictWithoutAreaHasNoHighlightToggle() {
        var item = SampleData.monorail
        item.imageURL = URL.inMemoryImage(UUID())
        item.hotspot = nil
        item.isDemo = false
        let model = CheckResultsViewModel(item: item, images: ImageRepository())
        #expect(!model.canToggleHighlight, "Highlight would show nothing for an AI verdict with no area")
        #expect(!model.canShowOnPhoto)
    }

    @Test func realVerdictCanShowNothingFound() {
        var item = SampleData.lakefill
        item.imageURL = URL.inMemoryImage(UUID())
        #expect(CheckResultsViewModel(item: item, images: ImageRepository()).canToggleHighlight)
    }

    @Test func detectorCopyMakesNoVisualClaims() {
        let ai = VerdictCopy.for(.ai).summary
        let real = VerdictCopy.for(.real).summary
        #expect(ai.hasPrefix("The detector"))
        #expect(real.hasPrefix("The detector"))
        #expect(real.contains("isn't proof"), "A Real verdict must not overclaim")
    }
}
