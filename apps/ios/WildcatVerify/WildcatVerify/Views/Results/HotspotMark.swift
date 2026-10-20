import SwiftUI

/// Outline and label for a highlighted region.
struct HotspotMark: View {
    let label: String

    var body: some View {
        RoundedRectangle(cornerRadius: 6)
            .fill(.hotspotStroke.opacity(0.15))
            .stroke(.hotspotStroke, lineWidth: 2)
            .overlay(alignment: .topLeading) {
                Text(label)
                    .font(.caption)
                    .bold()
                    .foregroundStyle(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(.hotspotLabel, in: .rect(cornerRadius: 4))
                    .fixedSize()
                    .padding(4)
            }
            .accessibilityElement()
            .accessibilityLabel("Highlighted area: \(label)")
    }
}
