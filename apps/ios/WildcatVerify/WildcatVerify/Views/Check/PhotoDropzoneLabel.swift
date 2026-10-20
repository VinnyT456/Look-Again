import SwiftUI

/// The drop zone's contents. A separate view so it is main-actor isolated
/// inside the picker's label closure.
struct PhotoDropzoneLabel: View {
    @ScaledMetric(relativeTo: .title2) private var iconTile = 64.0

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: "square.and.arrow.up")
                .font(.title2)
                .foregroundStyle(.tint)
                .frame(width: iconTile, height: iconTile)
                .background(.northwesternPurpleTint.opacity(0.6), in: .rect(cornerRadius: Metrics.fieldRadius))
                .padding(.bottom, 6)

            Text("Choose Photo or Screenshot")
                .font(.headline)
            Text("From your camera roll or files")
                .font(.footnote)
                .foregroundStyle(.secondary)

            ViewThatFits {
                HStack(spacing: 8) { SourceTags() }
                VStack(spacing: 8) { SourceTags() }
            }
            .padding(.top, 6)
        }
        .multilineTextAlignment(.center)
        .frame(maxWidth: .infinity, minHeight: 280)
        .padding()
        .background(Color(.systemBackground).opacity(0.4), in: .rect(cornerRadius: Metrics.fieldRadius))
        .overlay {
            RoundedRectangle(cornerRadius: Metrics.fieldRadius)
                .strokeBorder(Color(.separator), style: StrokeStyle(lineWidth: 1.5, dash: [6, 5]))
        }
        .contentShape(.rect(cornerRadius: Metrics.fieldRadius))
    }
}
