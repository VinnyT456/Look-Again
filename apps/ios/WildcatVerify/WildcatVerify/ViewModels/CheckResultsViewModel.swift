import Observation
import UIKit

/// State for one results screen: the case, its loaded image, and the overlay mode.
@MainActor
@Observable
final class CheckResultsViewModel {
    let item: VerificationCase
    var layer: PhotoLayer = .photo
    /// Settings → Show Heatmap.
    var heatmapEnabled = true
    private(set) var image: UIImage?
    private(set) var imageFailed = false

    private let images: ImageRepository

    init(item: VerificationCase, images: ImageRepository = .shared) {
        self.item = item
        self.images = images
    }

    /// Whether this case has a photo at all. Without one there is nothing to highlight.
    var hasPhoto: Bool { item.imageURL != nil }

    /// Show the detector's heatmap only when it backs an AI verdict; on a
    /// Real verdict the same map would just be noise.
    var showsHeatmap: Bool {
        heatmapEnabled && hasPhoto && item.verdict == .ai && (item.heatmap?.hasSignal ?? false)
    }

    var canShowOnPhoto: Bool {
        hasPhoto && item.verdict.hasAnomaly && (item.hotspot != nil || showsHeatmap)
    }

    /// The Photo/Highlight toggle only appears when the highlight says
    /// something true: a marked area, a heatmap, or "nothing found" on a Real verdict.
    var canToggleHighlight: Bool {
        hasPhoto && (item.hotspot != nil || item.verdict == .real || showsHeatmap)
    }

    func loadImage() async {
        guard image == nil, let url = item.imageURL else { return }
        if let cached = images.cachedImage(for: url) {
            image = cached
            return
        }
        do {
            image = try await images.image(for: url)
        } catch {
            imageFailed = true
        }
    }

    func showOnPhoto() {
        layer = .highlight
    }
}
