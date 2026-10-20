/// A draggable corner of the screenshot box.
enum CropCorner: CaseIterable {
    case topLeading, topTrailing, bottomLeading, bottomTrailing

    var accessibilityName: String {
        switch self {
        case .topLeading: "Top left"
        case .topTrailing: "Top right"
        case .bottomLeading: "Bottom left"
        case .bottomTrailing: "Bottom right"
        }
    }
}
