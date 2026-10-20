import UIKit

/// Abstraction over the on-device ViT classifier, so the Core ML model can be
/// dropped in without touching view models.
protocol ImageClassifying: Sendable {
    /// True for stand-in classifiers whose output must be labelled as a demo.
    var isDemo: Bool { get }
    func classify(_ image: UIImage) async throws -> ClassificationResult
}

extension ImageClassifying {
    var isDemo: Bool { false }
}
