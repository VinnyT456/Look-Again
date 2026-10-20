/// A region of a practice photo to point at after answering, in 0–1 image
/// coordinates. Decoys mark details that look suspicious but are normal.
struct PracticeHotspot: Hashable, Sendable {
    var x: Double
    var y: Double
    var width: Double
    var height: Double
    /// Short label drawn on the photo, usually one of the case's clues.
    var label: String
    /// True for "this is normal" details (lens flare, grain), drawn neutrally.
    var isDecoy = false

    var isInsideImage: Bool {
        x >= 0 && y >= 0 && width > 0 && height > 0 && x + width <= 1 && y + height <= 1
    }
}
