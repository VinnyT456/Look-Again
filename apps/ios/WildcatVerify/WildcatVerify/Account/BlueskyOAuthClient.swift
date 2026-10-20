import Foundation

/// The AT Protocol OAuth flow for a native app: discovery, a pushed
/// authorization request (PAR) with PKCE and DPoP, the code exchange, and
/// refresh. Nothing goes through a WildcatVerify server; there isn't one.
struct BlueskyOAuthClient: Sendable {
    /// Everything needed between opening Bluesky's sign-in page and its reply.
    struct PendingSignIn: Sendable {
        let authorizeURL: URL
        let state: String
        let pkce: PKCE
        let signer: DPoPSigner
        let metadata: AuthServerMetadata
        /// Set when the user typed a handle; the result must be that account.
        let expectedDID: String?
    }

    let session: URLSession
    let http: DPoPHTTPClient
    let identity: BlueskyIdentity

    init(session: URLSession = .shared, nonces: DPoPNonceStore = DPoPNonceStore()) {
        self.session = session
        http = DPoPHTTPClient(session: session, nonces: nonces)
        identity = BlueskyIdentity(session: session)
    }

    // MARK: Sign in

    /// With no handle, signs in through Bluesky's own server, which covers
    /// accounts hosted by Bluesky. With a handle, finds that account's server.
    func beginSignIn(handle: String?) async throws -> PendingSignIn {
        var expectedDID: String?
        var authServer = BlueskyOAuthConfig.entryway
        let loginHint = handle.map(BlueskyIdentity.normalize).flatMap { $0.isEmpty ? nil : $0 }

        if let loginHint {
            let did = try await identity.resolveHandle(loginHint)
            let document = try await identity.document(for: did)
            guard document.handle?.lowercased() == loginHint, let pds = document.pdsEndpoint else {
                throw BlueskyAuthError.accountNotFound
            }
            expectedDID = did
            authServer = try await authorizationServer(for: pds)
        }

        let metadata = try await serverMetadata(authServer)
        let pkce = PKCE()
        let state = Data.random(count: 16).base64URLEncoded
        let signer = DPoPSigner()

        var form = [
            "client_id": BlueskyOAuthConfig.clientID,
            "response_type": "code",
            "redirect_uri": BlueskyOAuthConfig.redirectURI,
            "scope": BlueskyOAuthConfig.scope,
            "state": state,
            "code_challenge": pkce.challenge,
            "code_challenge_method": "S256",
        ]
        if let loginHint { form["login_hint"] = loginHint }

        let (data, response) = try await http.send(Self.formRequest(metadata.pushedAuthorizationRequestEndpoint, form), signer: signer)
        struct PARReply: Decodable {
            let requestURI: String
            enum CodingKeys: String, CodingKey { case requestURI = "request_uri" }
        }
        guard (200..<300).contains(response.statusCode), let reply = try? JSONDecoder().decode(PARReply.self, from: data) else {
            throw Self.rejection(data)
        }

        var components = URLComponents(url: metadata.authorizationEndpoint, resolvingAgainstBaseURL: false)
        components?.queryItems = [
            URLQueryItem(name: "client_id", value: BlueskyOAuthConfig.clientID),
            URLQueryItem(name: "request_uri", value: reply.requestURI),
        ]
        guard let authorizeURL = components?.url else { throw BlueskyAuthError.badResponse }
        return PendingSignIn(authorizeURL: authorizeURL, state: state, pkce: pkce, signer: signer, metadata: metadata, expectedDID: expectedDID)
    }

    /// Checks Bluesky's reply to the sign-in page and exchanges its code for tokens.
    func finishSignIn(_ pending: PendingSignIn, callback: URL) async throws -> BlueskySession {
        let query = URLComponents(url: callback, resolvingAgainstBaseURL: false)?.queryItems ?? []
        func value(_ name: String) -> String? { query.first { $0.name == name }?.value }

        if let error = value("error") {
            throw error == "access_denied" ? BlueskyAuthError.cancelled : BlueskyAuthError.serverRejected(error)
        }
        guard value("state") == pending.state else { throw BlueskyAuthError.stateMismatch }
        guard value("iss") == pending.metadata.issuer else { throw BlueskyAuthError.wrongIssuer }
        guard let code = value("code") else { throw BlueskyAuthError.badResponse }

        let token = try await tokenRequest(pending.metadata.tokenEndpoint, signer: pending.signer, form: [
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": BlueskyOAuthConfig.redirectURI,
            "code_verifier": pending.pkce.verifier,
            "client_id": BlueskyOAuthConfig.clientID,
        ])
        guard token.scope?.split(separator: " ").contains("atproto") == true else {
            throw BlueskyAuthError.serverRejected("missing atproto scope")
        }
        if let expected = pending.expectedDID, token.sub != expected { throw BlueskyAuthError.wrongIssuer }

        // The account's server must use this same sign-in server.
        let document = try await identity.document(for: token.sub)
        guard let pds = document.pdsEndpoint else { throw BlueskyAuthError.accountNotFound }
        let server = try await authorizationServer(for: pds)
        guard DPoPNonceStore.origin(server) == DPoPNonceStore.origin(URL(string: pending.metadata.issuer) ?? server) else {
            throw BlueskyAuthError.wrongIssuer
        }

        return BlueskySession(
            did: token.sub,
            handle: document.handle ?? token.sub,
            pds: pds,
            issuer: pending.metadata.issuer,
            tokenEndpoint: pending.metadata.tokenEndpoint,
            accessToken: token.accessToken,
            refreshToken: token.refreshToken,
            expiresAt: .now.addingTimeInterval(TimeInterval(token.expiresIn ?? 300)),
            dpopKey: pending.signer.rawKey
        )
    }

    // MARK: Refresh

    func refresh(_ current: BlueskySession) async throws -> BlueskySession {
        guard let refreshToken = current.refreshToken else { throw BlueskyAuthError.sessionExpired }
        let signer = try DPoPSigner(rawKey: current.dpopKey)
        let token: TokenResponse
        do {
            token = try await tokenRequest(current.tokenEndpoint, signer: signer, form: [
                "grant_type": "refresh_token",
                "refresh_token": refreshToken,
                "client_id": BlueskyOAuthConfig.clientID,
            ])
        } catch BlueskyAuthError.serverRejected {
            throw BlueskyAuthError.sessionExpired
        }
        guard token.sub == current.did else { throw BlueskyAuthError.wrongIssuer }
        var next = current
        next.accessToken = token.accessToken
        next.refreshToken = token.refreshToken ?? refreshToken
        next.expiresAt = .now.addingTimeInterval(TimeInterval(token.expiresIn ?? 300))
        return next
    }

    // MARK: Timeline

    /// One page of the user's Following timeline, read through their own
    /// server, which forwards it to Bluesky's AppView. 401 means the access
    /// token needs refreshing.
    func timeline(_ current: BlueskySession, cursor: String?) async throws -> (Data, Int) {
        var components = URLComponents(url: current.pds.appending(path: "xrpc/app.bsky.feed.getTimeline"), resolvingAgainstBaseURL: false)
        var items = [URLQueryItem(name: "limit", value: String(BlueskyOAuthConfig.timelinePageSize))]
        if let cursor { items.append(URLQueryItem(name: "cursor", value: cursor)) }
        components?.queryItems = items
        guard let url = components?.url else { throw BlueskyAuthError.badResponse }
        var request = URLRequest(url: url)
        request.setValue(BlueskyOAuthConfig.appViewProxy, forHTTPHeaderField: "atproto-proxy")
        let (data, response) = try await http.send(request, signer: DPoPSigner(rawKey: current.dpopKey), accessToken: current.accessToken)
        return (data, response.statusCode)
    }

    // MARK: Helpers

    private func authorizationServer(for pds: URL) async throws -> URL {
        let url = pds.appending(path: ".well-known/oauth-protected-resource")
        guard let (data, response) = try? await session.data(from: url),
              (response as? HTTPURLResponse)?.statusCode == 200,
              let resource = try? JSONDecoder().decode(ProtectedResourceMetadata.self, from: data),
              let server = resource.authorizationServers.first
        else { throw BlueskyAuthError.badResponse }
        return server
    }

    private func serverMetadata(_ server: URL) async throws -> AuthServerMetadata {
        let url = server.appending(path: ".well-known/oauth-authorization-server")
        guard let (data, response) = try? await session.data(from: url),
              (response as? HTTPURLResponse)?.statusCode == 200,
              let metadata = try? JSONDecoder().decode(AuthServerMetadata.self, from: data)
        else { throw BlueskyAuthError.badResponse }
        // The document must describe the server it came from.
        guard DPoPNonceStore.origin(URL(string: metadata.issuer) ?? url) == DPoPNonceStore.origin(server) else {
            throw BlueskyAuthError.wrongIssuer
        }
        guard metadata.dpopSigningAlgValuesSupported?.contains("ES256") != false else {
            throw BlueskyAuthError.serverRejected("ES256 unsupported")
        }
        return metadata
    }

    private func tokenRequest(_ endpoint: URL, signer: DPoPSigner, form: [String: String]) async throws -> TokenResponse {
        let (data, response) = try await http.send(Self.formRequest(endpoint, form), signer: signer)
        guard response.statusCode == 200, let token = try? JSONDecoder().decode(TokenResponse.self, from: data) else {
            throw Self.rejection(data)
        }
        return token
    }

    static func formRequest(_ url: URL, _ form: [String: String]) -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        request.httpBody = Data(form
            .sorted { $0.key < $1.key }
            .map { "\($0.key)=\($0.value.addingPercentEncoding(withAllowedCharacters: allowed) ?? "")" }
            .joined(separator: "&")
            .utf8)
        return request
    }

    private static func rejection(_ data: Data) -> BlueskyAuthError {
        if let body = try? JSONDecoder().decode(OAuthErrorBody.self, from: data) {
            return .serverRejected(body.error)
        }
        return .badResponse
    }
}
