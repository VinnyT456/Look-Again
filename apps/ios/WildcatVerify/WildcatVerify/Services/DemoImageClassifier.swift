import CryptoKit
import UIKit

/// Placeholder until the ViT checkpoint from `ml/` is exported to Core ML.
/// Deterministic per image (hash of its pixels) so re-checking the same photo
/// gives the same answer. Every result it produces is labelled as a demo.
struct DemoImageClassifier: ImageClassifying {
    var isDemo: Bool { true }

    func classify(_ image: UIImage) async throws -> ClassificationResult {
        try await Task.sleep(for: .milliseconds(1200))

        let bytes = image.jpegData(compressionQuality: 0.3) ?? Data()
        let digest = Array(SHA256.hash(data: bytes))
        let verdict = VerdictType.allCases[Int(digest[0]) % VerdictType.allCases.count]
        let confidence = 0.80 + Double(digest[1] % 19) / 100

        let hotspot: HotspotArea? = switch verdict {
        case .real: nil
        case .tampered: HotspotArea(xRatio: 0.28, yRatio: 0.30, widthRatio: 0.44, heightRatio: 0.32, label: "Possible edit")
        case .ai: HotspotArea(xRatio: 0.20, yRatio: 0.22, widthRatio: 0.60, heightRatio: 0.50, label: "Synthetic texture")
        }
        return ClassificationResult(verdict: verdict, confidence: confidence, hotspot: hotspot)
    }
}
