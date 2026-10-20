import SwiftUI

/// "Check the link you copied": one tap from copying a post in Bluesky to
/// its result. Uses the system Paste button, so iOS doesn't ask permission.
struct CopiedLinkOffer: View {
    let onPaste: (String) -> Void
    let onDismiss: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Check the link you copied")
                    .font(.headline)
                Text("Tap Paste and the post is checked right away.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            PasteButton(payloadType: String.self) { strings in
                if let first = strings.first { onPaste(first) }
            }
            .buttonBorderShape(.capsule)
            .tint(.northwesternPurple)
            .accessibilityIdentifier("pasteCopiedLink")

            Button("Not Now", systemImage: "xmark", action: onDismiss)
                .labelStyle(.iconOnly)
                .font(.footnote.bold())
                .foregroundStyle(.secondary)
                .frame(width: 44, height: 44)
                .contentShape(.rect)
        }
        .padding(.leading, 16)
        .padding(.vertical, 12)
        .padding(.trailing, 4)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: Metrics.fieldRadius))
        .overlay {
            RoundedRectangle(cornerRadius: Metrics.fieldRadius)
                .strokeBorder(Color.accentColor, lineWidth: 1.5)
        }
    }
}
