import Foundation

/// Sends requests with a DPoP proof, remembering each server's nonce and
/// retrying once when the server asks for a fresh one.
struct DPoPHTTPClient: Sendable {
    let session: URLSession
    let nonces: DPoPNonceStore

    func send(_ request: URLRequest, signer: DPoPSigner, accessToken: String? = nil) async throws -> (Data, HTTPURLResponse) {
        var attempt = 0
        while true {
            var signed = request
            guard let url = request.url else { throw BlueskyAuthError.badResponse }
            let proof = try signer.proof(
                method: request.httpMethod ?? "GET",
                url: url,
                nonce: await nonces.nonce(for: url),
                accessToken: accessToken
            )
            signed.setValue(proof, forHTTPHeaderField: "DPoP")
            if let accessToken {
                signed.setValue("DPoP \(accessToken)", forHTTPHeaderField: "Authorization")
            }

            let (data, response) = try await load(signed)
            if let nonce = response.value(forHTTPHeaderField: "DPoP-Nonce") {
                await nonces.remember(nonce, for: url)
            }
            if attempt == 0, Self.asksForNonce(data: data, response: response) {
                attempt += 1
                continue
            }
            return (data, response)
        }
    }

    private func load(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw BlueskyAuthError.badResponse }
            return (data, http)
        } catch let error as URLError where error.code == .cancelled {
            throw CancellationError()
        } catch let error as BlueskyAuthError {
            throw error
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw BlueskyAuthError.badResponse
        }
    }

    /// Token endpoints say so in the body (400); resource servers in the
    /// `WWW-Authenticate` header (401).
    static func asksForNonce(data: Data, response: HTTPURLResponse) -> Bool {
        if response.statusCode == 400, (try? JSONDecoder().decode(OAuthErrorBody.self, from: data))?.error == "use_dpop_nonce" {
            return true
        }
        if response.statusCode == 401, response.value(forHTTPHeaderField: "WWW-Authenticate")?.contains("use_dpop_nonce") == true {
            return true
        }
        return false
    }
}
