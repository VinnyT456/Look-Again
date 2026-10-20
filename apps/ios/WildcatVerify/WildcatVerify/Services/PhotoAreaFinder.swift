import UIKit
import Vision

/// Suggests where the photo is in a screenshot of a Bluesky post, so the user
/// only has to nudge the box. Runs on this iPhone with Vision.
enum PhotoAreaFinder {
    /// Rectangles covering nearly the whole screenshot are the screen itself.
    private static let maxArea = 0.9
    private static let minArea = 0.04

    /// Tries photo-shaped rectangles first, then what draws the eye, then a
    /// centered box.
    static func suggest(in image: UIImage) async -> CropBox {
        await Task.detached(priority: .userInitiated) {
            guard let cgImage = image.cgImage else { return fallback }
            return rectangle(in: cgImage) ?? salientArea(in: cgImage) ?? fallback
        }.value
    }

    /// Vision's own score a rectangle needs before the box screen is skipped.
    static let confidentScore: Float = 0.9

    /// The photo's box when Vision is sure of it, so a Siri screenshot can be
    /// checked without asking the user to box it. Nil means "ask".
    static func confidentPhoto(in image: UIImage) async -> CropBox? {
        await Task.detached(priority: .userInitiated) {
            guard let cgImage = image.cgImage else { return nil }
            return confidentRectangle(in: cgImage)
        }.value
    }

    static func confidentRectangle(in cgImage: CGImage) -> CropBox? {
        guard let best = rectangleObservations(in: cgImage).first, best.confidence >= confidentScore else { return nil }
        return CropBox(rect: topLeft(best.boundingBox))
    }

    static let fallback = CropBox(rect: CGRect(x: 0.05, y: 0.2, width: 0.9, height: 0.5))

    /// The largest photo-like rectangle (Bluesky draws photos as rounded
    /// rectangles in the post).
    static func rectangle(in cgImage: CGImage) -> CropBox? {
        rectangleObservations(in: cgImage).first.map { CropBox(rect: topLeft($0.boundingBox)) }
    }

    /// Photo-sized rectangles, largest first.
    private static func rectangleObservations(in cgImage: CGImage) -> [VNRectangleObservation] {
        let request = VNDetectRectanglesRequest()
        request.maximumObservations = 8
        request.minimumSize = 0.2
        request.minimumAspectRatio = 0.2
        request.maximumAspectRatio = 1
        request.minimumConfidence = 0.5
        request.quadratureTolerance = 20
        guard (try? VNImageRequestHandler(cgImage: cgImage).perform([request])) != nil else { return [] }
        return (request.results ?? [])
            .filter { (minArea...maxArea).contains($0.boundingBox.width * $0.boundingBox.height) }
            .sorted { $0.boundingBox.width * $0.boundingBox.height > $1.boundingBox.width * $1.boundingBox.height }
    }

    /// Everything Vision thinks draws attention, merged into one box.
    static func salientArea(in cgImage: CGImage) -> CropBox? {
        let request = VNGenerateAttentionBasedSaliencyImageRequest()
        guard (try? VNImageRequestHandler(cgImage: cgImage).perform([request])) != nil,
              let objects = request.results?.first?.salientObjects, !objects.isEmpty else { return nil }
        let union = objects.map(\.boundingBox).reduce(CGRect.null) { $0.union($1) }
        let box = topLeft(union)
        guard box.width * box.height >= minArea else { return nil }
        return CropBox(rect: box)
    }

    /// Vision's origin is bottom-left; the box's is top-left.
    private static func topLeft(_ r: CGRect) -> CGRect {
        CGRect(x: r.minX, y: 1 - r.maxY, width: r.width, height: r.height)
    }
}
