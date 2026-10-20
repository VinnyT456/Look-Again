import CoreML
import UIKit

/// The on-device detector: CommunityForensics ViT with a linear probe, exported
/// from `ml/` to Core ML. It outputs the probability the image is fake
/// (AI-generated), so it answers Real or AI but not Edited, plus a 24×24
/// `patch_map` of which areas pushed it toward "AI".
final class CoreMLImageClassifier: ImageClassifying, @unchecked Sendable {
    /// Above this, the image is called AI-generated.
    static let threshold = 0.5
    static let modelName = "WildcatDetector"

    // MLModel is safe to use from multiple threads for predictions; it is
    // created once and never mutated, hence @unchecked Sendable.
    private let model: MLModel

    init(model: MLModel) {
        self.model = model
    }

    /// Loads the compiled model from the app bundle. The share extension finds
    /// it in its containing app, so the 42 MB model ships only once.
    static func load() -> CoreMLImageClassifier? {
        guard let url = modelURL() else { return nil }
        let configuration = MLModelConfiguration()
        configuration.computeUnits = .all
        guard let model = try? MLModel(contentsOf: url, configuration: configuration) else { return nil }
        return CoreMLImageClassifier(model: model)
    }

    static func modelURL(in bundle: Bundle = .main) -> URL? {
        if let url = bundle.url(forResource: modelName, withExtension: "mlmodelc") {
            return url
        }
        // Inside an app extension: …/App.app/PlugIns/Share.appex → …/App.app
        let appBundleURL = bundle.bundleURL.deletingLastPathComponent().deletingLastPathComponent()
        return Bundle(url: appBundleURL)?.url(forResource: modelName, withExtension: "mlmodelc")
    }

    func classify(_ image: UIImage) async throws -> ClassificationResult {
        let output = try await predict(image)
        return Self.result(fakeProbability: output.fakeProbability, heatmap: output.heatmap)
    }

    /// Raw model output, 0–1.
    func fakeProbability(for image: UIImage) async throws -> Double {
        try await predict(image).fakeProbability
    }

    /// Both outputs. `heatmap` is nil for an older export without `patch_map`.
    func predict(_ image: UIImage) async throws -> (fakeProbability: Double, heatmap: PatchHeatmap?) {
        let input = try DetectorPreprocessor.tensor(from: image)
        let features = try MLDictionaryFeatureProvider(dictionary: ["pixel_values": MLFeatureValue(multiArray: input)])
        let output = try await model.prediction(from: features)
        guard let value = output.featureValue(for: "fake_prob")?.multiArrayValue else {
            throw CocoaError(.coderValueNotFound)
        }
        var heatmap: PatchHeatmap?
        if let map = output.featureValue(for: "patch_map")?.multiArrayValue {
            heatmap = PatchHeatmap(values: (0..<map.count).map { map[$0].floatValue })
        }
        return (Double(truncating: value[0]), heatmap)
    }

    /// Maps the probability onto the app's verdicts. No hotspot box: the model
    /// gives a soft per-patch map instead, and the app never invents a box.
    static func result(fakeProbability: Double, heatmap: PatchHeatmap? = nil) -> ClassificationResult {
        let probability = min(max(fakeProbability, 0), 1)
        let isFake = probability >= threshold
        return ClassificationResult(
            verdict: isFake ? .ai : .real,
            confidence: isFake ? probability : 1 - probability,
            hotspot: nil,
            heatmap: heatmap
        )
    }
}
