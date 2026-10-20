import AuthenticationServices
import SwiftUI

extension WebAuthenticationSession {
    /// Shows Bluesky's sign-in page and returns its redirect back to the app.
    /// Shares Safari's sign-in, so people already logged in to bsky.app just
    /// tap Authorize.
    func blueskySignIn(_ url: URL) async throws -> URL {
        try await authenticate(
            using: url,
            callback: .customScheme(BlueskyOAuthConfig.callbackScheme),
            preferredBrowserSession: .shared,
            additionalHeaderFields: [:]
        )
    }
}
