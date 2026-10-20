import SwiftUI

/// An image from a URL, decoded off the main actor at the size it's drawn,
/// with a neutral placeholder while loading or if it fails.
struct RemoteImage: View {
    let url: URL?
    /// Longest edge it will be drawn at, in points.
    var pointSize: Double
    var contentMode: ContentMode = .fill

    @Environment(\.displayScale) private var displayScale
    @State private var image: UIImage?

    var body: some View {
        ZStack {
            Color(.tertiarySystemFill)
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: contentMode)
            }
        }
        .task(id: url) { await load() }
    }

    private func load() async {
        guard let url else { return }
        let pixels = (pointSize * displayScale).rounded(.up)
        image = try? await ImageRepository.shared.image(for: url, maxPixelSize: pixels)
    }
}
