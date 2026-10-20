import SwiftUI

/// Shown while a link or photo is being checked.
struct AnalyzingView: View {
    let image: UIImage?
    let onCancel: () -> Void

    @ScaledMetric(relativeTo: .body) private var previewSize = 180.0

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                preview
                ProgressView {
                    Text("Checking image…")
                        .font(.headline)
                }
                .controlSize(.large)

                Text("Looking at lighting, edges and texture.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                Button("Cancel", role: .cancel, action: onCancel)
                    .buttonStyle(.bordered)
                    .controlSize(.large)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .padding(.top, 32)
        }
        .background(Color(.systemGroupedBackground))
    }

    @ViewBuilder
    private var preview: some View {
        if let image {
            Image(uiImage: image)
                .resizable()
                .scaledToFit()
                .frame(maxWidth: previewSize, maxHeight: previewSize)
                .clipShape(.rect(cornerRadius: Metrics.photoRadius))
                .accessibilityHidden(true)
        }
    }
}

#Preview {
    AnalyzingView(image: nil, onCancel: {})
}
