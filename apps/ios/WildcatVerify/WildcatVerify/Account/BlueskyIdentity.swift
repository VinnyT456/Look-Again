import Foundation

/// Turns a handle into a DID and a DID into its document (where the account
/// lives and which handle it claims).
struct BlueskyIdentity: Sendable {
    let session: URLSession

    func resolveHandle(_ handle: String) async throws -> String {
        var components = URLComponents(string: "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle")
        components?.queryItems = [URLQueryItem(name: "handle", value: handle)]
        guard let url = components?.url else { throw BlueskyAuthError.accountNotFound }
        struct Reply: Decodable { let did: String }
        let (data, status) = try await get(url)
        guard status == 200, let reply = try? JSONDecoder().decode(Reply.self, from: data) else {
            throw BlueskyAuthError.accountNotFound
        }
        return reply.did
    }

    func document(for did: String) async throws -> DIDDocument {
        guard let url = Self.documentURL(for: did) else { throw BlueskyAuthError.accountNotFound }
        let (data, status) = try await get(url)
        guard status == 200, let document = try? JSONDecoder().decode(DIDDocument.self, from: data), document.id == did else {
            throw BlueskyAuthError.accountNotFound
        }
        return document
    }

    /// did:plc lives in the PLC directory; did:web on its own host.
    static func documentURL(for did: String) -> URL? {
        if did.hasPrefix("did:plc:") {
            return URL(string: "https://plc.directory/\(did)")
        }
        if did.hasPrefix("did:web:") {
            let host = did.dropFirst("did:web:".count).replacingOccurrences(of: "%3A", with: ":")
            return URL(string: "https://\(host)/.well-known/did.json")
        }
        return nil
    }

    /// "@Alice.bsky.social " → "alice.bsky.social".
    static func normalize(_ handle: String) -> String {
        var trimmed = handle.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if trimmed.hasPrefix("@") { trimmed.removeFirst() }
        return trimmed
    }

    private func get(_ url: URL) async throws -> (Data, Int) {
        do {
            let (data, response) = try await session.data(from: url)
            return (data, (response as? HTTPURLResponse)?.statusCode ?? 0)
        } catch {
            throw BlueskyAuthError.badResponse
        }
    }
}
