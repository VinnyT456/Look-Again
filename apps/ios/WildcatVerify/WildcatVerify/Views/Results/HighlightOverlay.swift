import SwiftUI

/// Dims the photo and marks the region that drove the verdict, or says
/// nothing was found.
struct HighlightOverlay: View {
    let hotspot: HotspotArea?

    var body: some View {
        ZStack {
            Color.black.opacity(0.3)
            if let hotspot {
                NormalizedRectLayout(
                    x: hotspot.xRatio,
                    y: hotspot.yRatio,
                    width: hotspot.widthRatio,
                    height: hotspot.heightRatio
                ) {
                    HotspotMark(label: hotspot.label)
                }
            } else {
                Label("No signs of AI generation found", systemImage: "checkmark.seal.fill")
                    .font(.footnote)
                    .bold()
                    .foregroundStyle(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(.cleanBadge, in: .capsule)
                    .padding()
            }
        }
        .allowsHitTesting(false)
    }
}
