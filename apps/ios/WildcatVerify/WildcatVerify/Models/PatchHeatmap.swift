import CoreGraphics

/// The detector's per-patch map: how much each 16×16 patch of the 384×384
/// center crop pushed the decision toward "AI" (positive) or away (negative),
/// in logit units. It covers only part of the decision; the rest comes from
/// whole-image features that have no location.
struct PatchHeatmap: Hashable, Sendable, Codable {
    static let gridSize = 24

    /// Row-major, `gridSize × gridSize`.
    var values: [Float]

    init?(values: [Float]) {
        guard values.count == Self.gridSize * Self.gridSize else { return nil }
        self.values = values
    }

    init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let values = try container.decode([Float].self, forKey: .values)
        guard values.count == Self.gridSize * Self.gridSize else {
            throw DecodingError.dataCorruptedError(forKey: .values, in: container, debugDescription: "Expected a 24×24 grid")
        }
        self.values = values
    }

    /// Whether any patch pushed toward "AI" at all.
    var hasSignal: Bool { (values.max() ?? 0) > 0 }

    /// 0–1 per cell: positive contributions relative to the strongest one.
    /// Cells that pushed toward "real" are 0, so only suspicious areas show.
    var intensities: [Double] {
        guard let peak = values.max(), peak > 0 else { return Array(repeating: 0, count: values.count) }
        return values.map { Double(max($0, 0) / peak) }
    }

    /// The part of the full image the model actually looked at, as fractions
    /// of its width and height. Mirrors `DetectorPreprocessor`: the short edge
    /// is resized to 440 and the centre 384×384 is kept.
    static func coveredRegion(imageSize: CGSize) -> (x: Double, y: Double, width: Double, height: Double) {
        let width = Double(imageSize.width)
        let height = Double(imageSize.height)
        guard width > 0, height > 0 else { return (0, 0, 1, 1) }
        let side = Double(DetectorPreprocessor.cropSize) / Double(DetectorPreprocessor.shortEdge) * min(width, height)
        let fractionX = min(side / width, 1)
        let fractionY = min(side / height, 1)
        return ((1 - fractionX) / 2, (1 - fractionY) / 2, fractionX, fractionY)
    }
}
