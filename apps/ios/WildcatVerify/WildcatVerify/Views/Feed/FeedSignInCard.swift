import SwiftUI

/// Top of What's Hot while signed out: one tap to see your own feed instead.
struct FeedSignInCard: View {
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("See your own feed")
                    .font(.headline)
                Spacer()
                Button("Not Now", systemImage: "xmark", action: onDismiss)
                    .labelStyle(.iconOnly)
                    .font(.footnote.bold())
                    .foregroundStyle(.secondary)
                    .frame(width: 44, height: 44)
                    .contentShape(.rect)
                    .padding(-12)
            }
            Text("Sign in and the posts you follow are checked here as you scroll. Look Again only reads your timeline.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            BlueskySignInButton()
                .buttonStyle(.borderedProminent)
                .tint(.northwesternPurple)
        }
        .padding(.vertical, 6)
    }
}
