// Visual Intelligence is device-only; the Simulator SDK doesn't include it.
#if canImport(VisualIntelligence)
import AppIntents
import CoreImage
import UIKit
import VisualIntelligence

/// Visual Intelligence (screenshot or camera → search) asks apps for results.
/// WildcatVerify answers with one: check this image. The pixels stay in memory
/// on this iPhone.
@available(iOS 26.0, *)
struct VisualCheckQuery: IntentValueQuery {
    func values(for input: SemanticContentDescriptor) async throws -> [VisualCheckEntity] {
        guard let image = Self.image(from: input) else { return [] }
        let id = await VisualCheckStore.shared.add(image)
        let thumbnail = image.preparingThumbnail(of: CGSize(width: 160, height: 160 / max(image.size.width / max(image.size.height, 1), 0.01)))?
            .jpegData(compressionQuality: 0.7)
        return [VisualCheckEntity(id: id, thumbnail: thumbnail)]
    }

    private static func image(from input: SemanticContentDescriptor) -> UIImage? {
        guard let buffer = input.pixelBuffer else { return nil }
        let cgImage: CGImage? = buffer.withUnsafeBuffer { pixels in
            let ciImage = CIImage(cvPixelBuffer: pixels)
            return CIContext().createCGImage(ciImage, from: ciImage.extent)
        }
        return cgImage.map { UIImage(cgImage: $0) }
    }
}

/// Tapping the result opens the app on the box screen with that image.
@available(iOS 26.0, *)
struct OpenVisualCheckIntent: OpenIntent {
    static let title: LocalizedStringResource = "Check Image from Visual Intelligence"
    static let isDiscoverable = false

    @Parameter(title: "Image")
    var target: VisualCheckEntity

    init() {}

    init(target: VisualCheckEntity) {
        self.target = target
    }

    @MainActor
    func perform() async throws -> some IntentResult {
        guard let image = VisualCheckStore.shared.image(for: target.id) else {
            throw SiriCheckError.unreadableImage
        }
        await AppViewModel.live.receiveScreenshot(image)
        return .result()
    }
}
#endif
