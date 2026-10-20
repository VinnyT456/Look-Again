import CoreGraphics
import CoreML
import UIKit

/// Turns an image into the tensor the detector expects. Mirrors the model's
/// Hugging Face `CLIPImageProcessor`: resize so the short edge is 440 (bicubic),
/// center-crop 384×384, scale to 0–1, then normalize with CLIP mean/std.
/// Source: ml/checkpoints/coreml/community_forensics_vit_rich_probe.json and the
/// model's preprocessor_config.json.
enum DetectorPreprocessor {
    static let shortEdge = 440
    static let cropSize = 384
    static let mean: [Float] = [0.48145466, 0.4578275, 0.40821073]
    static let std: [Float] = [0.26862954, 0.26130258, 0.27577711]

    enum Failure: Error {
        case noPixels
        case contextUnavailable
    }

    /// Returns a 1×3×384×384 Float32 array in channel-first (RGB) order.
    static func tensor(from image: UIImage) throws -> MLMultiArray {
        let pixels = try croppedRGBA(from: image)
        let side = cropSize
        let array = try MLMultiArray(shape: [1, 3, NSNumber(value: side), NSNumber(value: side)], dataType: .float32)
        let plane = side * side
        let pointer = array.dataPointer.bindMemory(to: Float.self, capacity: 3 * plane)

        for index in 0..<plane {
            let base = index * 4
            for channel in 0..<3 {
                let value = Float(pixels[base + channel]) / 255
                pointer[channel * plane + index] = (value - mean[channel]) / std[channel]
            }
        }
        return array
    }

    /// Resizes (short edge → 440) and center-crops to 384×384, returning
    /// RGBA8 bytes with alpha flattened onto black.
    static func croppedRGBA(from image: UIImage) throws -> [UInt8] {
        guard let cgImage = image.cgImage ?? renderedCGImage(image) else { throw Failure.noPixels }

        let width = Double(cgImage.width)
        let height = Double(cgImage.height)
        let scale = Double(shortEdge) / min(width, height)
        let scaledWidth = (width * scale).rounded()
        let scaledHeight = (height * scale).rounded()
        // Draw the scaled image offset so its centre lands in the crop.
        let originX = (Double(cropSize) - scaledWidth) / 2
        let originY = (Double(cropSize) - scaledHeight) / 2

        var pixels = [UInt8](repeating: 0, count: cropSize * cropSize * 4)
        let drawn: Bool = pixels.withUnsafeMutableBytes { buffer in
            guard let context = CGContext(
                data: buffer.baseAddress,
                width: cropSize,
                height: cropSize,
                bitsPerComponent: 8,
                bytesPerRow: cropSize * 4,
                space: CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
            ) else { return false }
            context.interpolationQuality = .high
            context.draw(cgImage, in: CGRect(x: originX, y: originY, width: scaledWidth, height: scaledHeight))
            return true
        }
        guard drawn else { throw Failure.contextUnavailable }
        return pixels
    }

    /// For images backed by CIImage or symbols rather than a CGImage.
    private static func renderedCGImage(_ image: UIImage) -> CGImage? {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: image.size, format: format).image { _ in
            image.draw(at: .zero)
        }.cgImage
    }
}
