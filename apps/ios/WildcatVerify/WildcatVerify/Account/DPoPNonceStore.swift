import Foundation

/// The latest DPoP nonce each server handed out, keyed by origin. Servers
/// rotate them every few minutes; a stale one just costs one retry.
actor DPoPNonceStore {
    private var nonces: [String: String] = [:]

    func nonce(for url: URL) -> String? {
        nonces[Self.origin(url)]
    }

    func remember(_ nonce: String, for url: URL) {
        nonces[Self.origin(url)] = nonce
    }

    static func origin(_ url: URL) -> String {
        "\(url.scheme ?? "https")://\(url.host() ?? "")\(url.port.map { ":\($0)" } ?? "")"
    }
}
