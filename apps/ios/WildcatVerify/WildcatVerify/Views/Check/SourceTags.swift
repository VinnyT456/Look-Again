import SwiftUI

/// "Camera Roll" and "Screenshots": the kinds of image the picker accepts.
struct SourceTags: View {
    var body: some View {
        ForEach(["Camera Roll", "Screenshots"], id: \.self) { tag in
            Text(tag)
                .font(.caption)
                .bold()
                .foregroundStyle(.secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .background(Color(.tertiarySystemFill), in: .capsule)
        }
    }
}
