import SwiftUI

/// Clue areas marked on a practice photo after answering. Real clues use the
/// app's highlight mark; decoys ("this is normal") are dashed and neutral.
struct PracticeHotspotOverlay: View {
    let hotspots: [PracticeHotspot]

    var body: some View {
        ZStack {
            ForEach(hotspots.filter(\.isInsideImage), id: \.self) { spot in
                NormalizedRectLayout(x: spot.x, y: spot.y, width: spot.width, height: spot.height) {
                    if spot.isDecoy {
                        DecoyMark(label: spot.label)
                    } else {
                        HotspotMark(label: spot.label)
                    }
                }
            }
        }
    }
}

/// Dashed outline for a detail that looks suspicious but is normal.
private struct DecoyMark: View {
    let label: String

    var body: some View {
        RoundedRectangle(cornerRadius: 6)
            .strokeBorder(.white.opacity(0.9), style: StrokeStyle(lineWidth: 1.5, dash: [5, 4]))
            .shadow(color: .black.opacity(0.5), radius: 1)
            .overlay(alignment: .bottomLeading) {
                Text(label)
                    .font(.caption)
                    .foregroundStyle(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(.black.opacity(0.6), in: .rect(cornerRadius: 4))
                    .fixedSize()
                    .padding(4)
            }
            .accessibilityElement()
            .accessibilityLabel("Normal detail: \(label)")
    }
}
