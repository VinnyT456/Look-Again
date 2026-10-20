import SwiftUI

/// A case's photo, decoded at thumbnail size, or its verdict placeholder.
struct CaseThumbnail: View {
    let item: VerificationCase
    /// Point size before Dynamic Type scaling.
    var baseSize = Metrics.thumbnail

    @ScaledMetric(relativeTo: .body) private var scale = 1.0
    private var size: Double { baseSize * scale }
    @Environment(\.displayScale) private var displayScale
    @State private var image: UIImage?
    @State private var failed = false

    var body: some View {
        content
            .frame(width: size, height: size)
            .clipShape(.rect(cornerRadius: Metrics.thumbnailRadius))
            .accessibilityHidden(true)
            .task(id: item.imageURL) { await load() }
    }

    @ViewBuilder
    private var content: some View {
        if let image {
            Image(uiImage: image)
                .resizable()
                .scaledToFill()
        } else if item.imageURL == nil || failed {
            NoPhotoPlaceholder(verdict: item.verdict)
        } else {
            ProgressView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(.fill.tertiary)
        }
    }

    private func load() async {
        guard let url = item.imageURL else { return }
        let repository = ImageRepository.shared
        let pixels = (size * displayScale).rounded(.up)
        if let cached = repository.cachedImage(for: url, maxPixelSize: pixels) ?? repository.cachedImage(for: url) {
            image = cached
            return
        }
        do {
            image = try await repository.image(for: url, maxPixelSize: pixels)
        } catch {
            failed = true
        }
    }
}
