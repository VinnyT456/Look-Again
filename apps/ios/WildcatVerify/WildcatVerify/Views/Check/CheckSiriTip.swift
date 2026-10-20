import SwiftUI

/// Dismissible tip on the Check page pointing to Set Up Siri.
struct CheckSiriTip: View {
    let onOpen: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Button(action: onOpen) {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "mic.fill")
                        .font(.title3)
                        .foregroundStyle(.tint)
                        .accessibilityHidden(true)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Check posts without leaving Bluesky")
                            .font(.subheadline)
                            .bold()
                        Text("Set up “Check This Post” with Siri or the Action Button.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .multilineTextAlignment(.leading)
                    Spacer(minLength: 0)
                }
                .contentShape(.rect)
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("siriTip")
            .accessibilityHint("Opens Siri & Shortcuts in Settings")

            Button("Dismiss Tip", systemImage: "xmark", action: onDismiss)
                .labelStyle(.iconOnly)
                .font(.footnote)
                .bold()
                .foregroundStyle(.secondary)
                .frame(width: 44, height: 44)
                .contentShape(.rect)
                .accessibilityIdentifier("dismissSiriTip")
        }
        .padding(16)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: Metrics.fieldRadius))
        .overlay {
            RoundedRectangle(cornerRadius: Metrics.fieldRadius)
                .strokeBorder(Color(.separator).opacity(0.5), lineWidth: 0.5)
        }
    }
}
