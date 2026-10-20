import UIKit

/// Cuts the boxed area out of a screenshot at full resolution.
enum ImageCropper {
    static func crop(_ image: UIImage, to box: CropBox) -> UIImage? {
        guard let cgImage = upright(image).cgImage else { return nil }
        let rect = box.pixelRect(in: CGSize(width: cgImage.width, height: cgImage.height))
        guard !rect.isEmpty, let cropped = cgImage.cropping(to: rect) else { return nil }
        return UIImage(cgImage: cropped, scale: 1, orientation: .up)
    }

    /// Box coordinates are in display orientation, so bake any rotation in first.
    private static func upright(_ image: UIImage) -> UIImage {
        guard image.imageOrientation != .up else { return image }
        let format = UIGraphicsImageRendererFormat()
        format.scale = image.scale
        return UIGraphicsImageRenderer(size: image.size, format: format).image { _ in
            image.draw(at: .zero)
        }
    }
}
