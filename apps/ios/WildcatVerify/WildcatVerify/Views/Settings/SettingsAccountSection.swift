import AuthenticationServices
import SwiftUI

/// Settings → Bluesky Account: sign in for the Following feed, or sign out.
struct SettingsAccountSection: View {
    @Environment(AppViewModel.self) private var app
    @Environment(\.webAuthenticationSession) private var webAuthenticationSession
    @State private var isAskingForHandle = false
    @State private var handle = ""
    @State private var isConfirmingSignOut = false

    var body: some View {
        @Bindable var account = app.account

        Section {
            if let signedIn = app.account.handle {
                LabeledContent("Signed In", value: "@\(signedIn)")
                Button("Sign Out", role: .destructive) { isConfirmingSignOut = true }
                    .accessibilityIdentifier("blueskySignOut")
            } else {
                BlueskySignInButton()
                Button("Account on Another Server…") { isAskingForHandle = true }
                    .font(.subheadline)
            }
        } header: {
            Text("Bluesky Account")
        } footer: {
            Text("Optional. Signed in, the Feed shows the posts you follow, checked as you scroll. WildcatVerify only reads your timeline; it never posts, likes or follows. Your sign-in is kept in this iPhone's Keychain.")
        }
        .alert("Your Bluesky Handle", isPresented: $isAskingForHandle) {
            TextField("name.example.com", text: $handle)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .keyboardType(.URL)
            Button("Cancel", role: .cancel) {}
            Button("Continue", action: signInElsewhere)
        } message: {
            Text("For accounts hosted outside Bluesky. You'll sign in on your server's own page.")
        }
        .confirmationDialog("Sign out of Bluesky?", isPresented: $isConfirmingSignOut, titleVisibility: .visible) {
            Button("Sign Out", role: .destructive, action: app.signOut)
        } message: {
            Text("The Following feed goes away until you sign in again.")
        }
        .alert("Couldn't Sign In", isPresented: Binding(
            get: { account.lastError != nil },
            set: { if !$0 { account.lastError = nil } }
        )) {
        } message: {
            Text(account.lastError ?? "")
        }
    }

    private func signInElsewhere() {
        let typed = handle
        Task { await app.signIn(handle: typed, authenticate: webAuthenticationSession.blueskySignIn) }
    }
}
