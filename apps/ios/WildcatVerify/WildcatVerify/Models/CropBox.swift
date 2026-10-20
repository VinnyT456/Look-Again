import CoreGraphics

/// The area of a screenshot to check, in normalized coordinates (0…1, origin
/// top-left). Every change keeps it inside the image and at least `minSide`
/// wide and tall.
struct CropBox: Equatable {
    static let whole = CropBox(rect: CGRect(x: 0, y: 0, width: 1, height: 1))
    /// Smallest box side, as a fraction of the image.
    static let minSide = 0.1

    private(set) var rect: CGRect

    init(rect: CGRect) {
        self.rect = Self.clamped(rect)
    }

    /// Moves the whole box, stopping at the image edges.
    func moved(by delta: CGSize) -> CropBox {
        var r = rect
        r.origin.x = min(max(r.minX + delta.width, 0), 1 - r.width)
        r.origin.y = min(max(r.minY + delta.height, 0), 1 - r.height)
        return CropBox(rect: r)
    }

    /// Drags one corner; the opposite corner stays put.
    func resized(_ corner: CropCorner, by delta: CGSize) -> CropBox {
        var minX = rect.minX, maxX = rect.maxX, minY = rect.minY, maxY = rect.maxY
        switch corner {
        case .topLeading, .bottomLeading:
            minX = min(max(minX + delta.width, 0), maxX - Self.minSide)
        case .topTrailing, .bottomTrailing:
            maxX = max(min(maxX + delta.width, 1), minX + Self.minSide)
        }
        switch corner {
        case .topLeading, .topTrailing:
            minY = min(max(minY + delta.height, 0), maxY - Self.minSide)
        case .bottomLeading, .bottomTrailing:
            maxY = max(min(maxY + delta.height, 1), minY + Self.minSide)
        }
        return CropBox(rect: CGRect(x: minX, y: minY, width: maxX - minX, height: maxY - minY))
    }

    /// Grows or shrinks around the center (VoiceOver's adjustable action).
    func scaled(by factor: Double) -> CropBox {
        let width = min(max(rect.width * factor, Self.minSide), 1)
        let height = min(max(rect.height * factor, Self.minSide), 1)
        let centered = CGRect(x: rect.midX - width / 2, y: rect.midY - height / 2, width: width, height: height)
        return CropBox(rect: centered).moved(by: .zero)
    }

    /// The box in pixels of an image of `size`, rounded outward to whole pixels.
    func pixelRect(in size: CGSize) -> CGRect {
        CGRect(x: rect.minX * size.width, y: rect.minY * size.height,
               width: rect.width * size.width, height: rect.height * size.height)
            .integral
            .intersection(CGRect(origin: .zero, size: size))
    }

    private static func clamped(_ r: CGRect) -> CGRect {
        guard r.width.isFinite, r.height.isFinite, r.minX.isFinite, r.minY.isFinite else {
            return CGRect(x: 0, y: 0, width: 1, height: 1)
        }
        let width = min(max(r.width, minSide), 1)
        let height = min(max(r.height, minSide), 1)
        let x = min(max(r.minX, 0), 1 - width)
        let y = min(max(r.minY, 0), 1 - height)
        return CGRect(x: x, y: y, width: width, height: height)
    }
}
