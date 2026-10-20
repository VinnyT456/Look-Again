import CryptoKit
import Foundation

/// Proof Key for Code Exchange (RFC 7636, S256 only): a fresh secret per
/// sign-in, so an intercepted authorization code is useless on its own.
struct PKCE: Sendable {
    let verifier: String
    let challenge: String

    init(verifier: String = Data.random(count: 32).base64URLEncoded) {
        self.verifier = verifier
        challenge = Data(SHA256.hash(data: Data(verifier.utf8))).base64URLEncoded
    }
}
