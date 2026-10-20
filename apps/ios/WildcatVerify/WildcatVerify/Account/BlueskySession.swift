import Foundation

/// A signed-in Bluesky account, stored in the Keychain on this iPhone only.
struct BlueskySession: Codable, Sendable, Equatable {
    var did: String
    var handle: String
    /// The account's own server, where timeline requests go.
    var pds: URL
    var issuer: String
    var tokenEndpoint: URL
    var accessToken: String
    var refreshToken: String?
    var expiresAt: Date
    /// The DPoP private key the tokens are bound to.
    var dpopKey: Data

    /// Refresh a minute early so a request never races the expiry.
    func needsRefresh(now: Date = .now) -> Bool {
        expiresAt.addingTimeInterval(-60) <= now
    }
}
