import SwiftUI

/// The checked photo, shown whole (never cropped, since a crop could hide the
/// very edit being looked for), with the highlight overlay on top.
struct ResultPhoto: View {
    let viewModel: CheckResultsViewModel

    var body: some View {
        if let image = viewModel.image {
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .overlay {
                    if viewModel.layer == .highlight {
                        Group {
                            if viewModel.showsHeatmap, let heatmap = viewModel.item.heatmap {
                                HeatmapOverlay(heatmap: heatmap, imageSize: image.size)
                            } else {
                                HighlightOverlay(hotspot: viewModel.item.hotspot)
                            }
                        }
                        .transition(.opacity)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: Metrics.photoMaxHeight)
                .background(.black)
                .accessibilityLabel("Checked photo")
                .accessibilityValue(viewModel.layer == .highlight ? "Highlight on" : "")
        } else if viewModel.imageFailed {
            NoPhotoPlaceholder(verdict: viewModel.item.verdict, glyph: .largeTitle, caption: "Photo unavailable")
                .frame(height: Metrics.placeholderHeight)
        } else {
            ProgressView()
                .frame(maxWidth: .infinity, minHeight: Metrics.placeholderHeight)
        }
    }
}
