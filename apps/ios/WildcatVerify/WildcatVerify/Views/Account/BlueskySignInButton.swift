import AuthenticationServices
import SwiftUI

/// "Sign In with Bluesky": opens Bluesky's own sign-in page (no password is
/// typed into WildcatVerify) and comes back signed in.
struct BlueskySignInButton: View {
    /// For accounts hosted outside Bluesky; nil uses Bluesky's server.
    var handle: String?
    var title = "Sign In with Bluesky"

    @Environment(AppViewModel.self) private var app
    @Environment(\.webAuthenticationSession) private var webAuthenticationSession

    var body: some View {
        Button(action: signIn) {
            HStack(spacing: 8) {
                if app.account.state == .signingIn {
                    ProgressView()
                } else {
                    Image(systemName: "person.crop.circle.badge.checkmark")
                }
                Text(title)
            }
        }
        .disabled(app.account.state == .signingIn)
        .accessibilityIdentifier("blueskySignIn")
    }

    private func signIn() {
        Task {
            await app.signIn(handle: handle, authenticate: webAuthenticationSession.blueskySignIn)
        }
    }
}
