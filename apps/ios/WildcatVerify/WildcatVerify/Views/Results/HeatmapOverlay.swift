import SwiftUI

/// Dims the photo and paints the detector's patch map over the part of the
/// image the model saw, red where patches pushed the verdict toward "AI".
struct HeatmapOverlay: View {
    let heatmap: PatchHeatmap
    let imageSize: CGSize

    var body: some View {
        let region = PatchHeatmap.coveredRegion(imageSize: imageSize)

        ZStack(alignment: .bottom) {
            Color.black.opacity(0.45)

            NormalizedRectLayout(x: region.x, y: region.y, width: region.width, height: region.height) {
                HeatmapCanvas(heatmap: heatmap)
            }

            Label("Red areas influenced the detector most", systemImage: "flame.fill")
                .labelStyle(.compact)
                .font(.footnote)
                .bold()
                .foregroundStyle(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(.black.opacity(0.65), in: .capsule)
                .padding(10)
        }
        .clipped()
        .allowsHitTesting(false)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Heatmap of the areas that influenced the detector most")
    }
}
