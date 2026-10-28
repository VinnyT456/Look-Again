import Foundation

/// WildcatVerify's identity as an AT Protocol OAuth client.
///
/// The client ID is the public address of `oauth-client-metadata.json`
/// (served by Vercel from the repository's `docs/` folder). The
/// redirect scheme is that host reversed, as the AT Protocol requires for
/// native apps.
enum BlueskyOAuthConfig {
    /// Turn on once `docs/oauth-client-metadata.json` is live at `clientID`
    /// (hosted on Vercel, Root Directory `docs`). Until then Bluesky rejects
    /// every sign-in with `invalid_client_metadata`, so the sign-in card and
    /// Settings section stay hidden.
    static let isSignInAvailable = false

    static let clientID = "https://look-again-beta.vercel.app/oauth-client-metadata.json"
    static let callbackScheme = "app.vercel.look-again-beta"
    static let redirectURI = "\(callbackScheme):/oauth/callback"
    /// Broad scope, because Bluesky's servers don't list read-only scopes yet.
    /// WildcatVerify only ever calls `app.bsky.feed.getTimeline`.
    static let scope = "atproto transition:generic"
    /// Bluesky's sign-in server for accounts hosted by Bluesky (most people).
    static let entryway = URL(string: "https://bsky.social")!
    /// Asks the user's server to forward timeline reads to Bluesky's AppView.
    static let appViewProxy = "did:web:api.bsky.app#bsky_appview"
    static let timelinePageSize = 30
}
