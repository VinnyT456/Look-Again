/// A normalized rectangle (0–1 in image space) marking the region that drove a verdict.
struct HotspotArea: Hashable, Sendable, Codable {
    var xRatio: Double
    var yRatio: Double
    var widthRatio: Double
    var heightRatio: Double
    var label: String
}
