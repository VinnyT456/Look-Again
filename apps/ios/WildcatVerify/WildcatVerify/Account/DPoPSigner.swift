import CryptoKit
import Foundation

/// Signs DPoP proofs (RFC 9449) with a per-session P-256 key, so Bluesky's
/// tokens only work from this iPhone.
struct DPoPSigner: Sendable {
    let key: P256.Signing.PrivateKey

    init(key: P256.Signing.PrivateKey = P256.Signing.PrivateKey()) {
        self.key = key
    }

    init(rawKey: Data) throws {
        key = try P256.Signing.PrivateKey(rawRepresentation: rawKey)
    }

    var rawKey: Data { key.rawRepresentation }

    /// The public key as a JWK, embedded in every proof's header.
    var publicJWK: [String: String] {
        // x963: 0x04 || X (32 bytes) || Y (32 bytes)
        let point = key.publicKey.x963Representation
        return [
            "kty": "EC",
            "crv": "P-256",
            "x": point.subdata(in: 1..<33).base64URLEncoded,
            "y": point.subdata(in: 33..<65).base64URLEncoded,
        ]
    }

    /// A proof for one request. `url` is reduced to scheme, host and path;
    /// `accessToken` adds the `ath` claim for resource requests.
    func proof(method: String, url: URL, nonce: String?, accessToken: String? = nil, now: Date = .now) throws -> String {
        let header = DPoPHeader(alg: "ES256", typ: "dpop+jwt", jwk: publicJWK)
        let payload = DPoPPayload(
            jti: UUID().uuidString,
            htm: method,
            htu: Self.htu(url),
            iat: Int(now.timeIntervalSince1970),
            nonce: nonce,
            ath: accessToken.map { Data(SHA256.hash(data: Data($0.utf8))).base64URLEncoded }
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.withoutEscapingSlashes, .sortedKeys]
        let signingInput = try encoder.encode(header).base64URLEncoded + "." + encoder.encode(payload).base64URLEncoded
        let signature = try key.signature(for: Data(signingInput.utf8))
        // CryptoKit's raw signature is r || s, exactly what JWS ES256 expects.
        return signingInput + "." + signature.rawRepresentation.base64URLEncoded
    }

    /// The target URI without query or fragment.
    static func htu(_ url: URL) -> String {
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        components?.query = nil
        components?.fragment = nil
        return components?.string ?? url.absoluteString
    }
}

private struct DPoPHeader: Encodable {
    let alg: String
    let typ: String
    let jwk: [String: String]
}

private struct DPoPPayload: Encodable {
    let jti: String
    let htm: String
    let htu: String
    let iat: Int
    let nonce: String?
    let ath: String?
}
