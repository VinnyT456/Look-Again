import SwiftUI

/// Hairline divider with "OR UPLOAD MEDIA" set into it.
struct OrUploadDivider: View {
    var body: some View {
        HStack(spacing: 12) {
            line
            Text("OR UPLOAD MEDIA")
                .font(.caption)
                .bold()
                .tracking(1)
                .foregroundStyle(.secondary)
                .fixedSize()
            line
        }
        .accessibilityHidden(true)
    }

    private var line: some View {
        Rectangle()
            .fill(Color(.separator))
            .frame(height: 0.5)
    }
}
