import Foundation

/// `/.well-known/oauth-authorization-server` (RFC 8414), the fields used.
struct AuthServerMetadata: Decodable, Sendable {
    let issuer: String
    let authorizationEndpoint: URL
    let tokenEndpoint: URL
    let pushedAuthorizationRequestEndpoint: URL
    let requirePushedAuthorizationRequests: Bool?
    let dpopSigningAlgValuesSupported: [String]?

    enum CodingKeys: String, CodingKey {
        case issuer
        case authorizationEndpoint = "authorization_endpoint"
        case tokenEndpoint = "token_endpoint"
        case pushedAuthorizationRequestEndpoint = "pushed_authorization_request_endpoint"
        case requirePushedAuthorizationRequests = "require_pushed_authorization_requests"
        case dpopSigningAlgValuesSupported = "dpop_signing_alg_values_supported"
    }
}

/// `/.well-known/oauth-protected-resource` (RFC 9728) on the user's server.
struct ProtectedResourceMetadata: Decodable, Sendable {
    let authorizationServers: [URL]

    enum CodingKeys: String, CodingKey {
        case authorizationServers = "authorization_servers"
    }
}

/// The token endpoint's reply.
struct TokenResponse: Decodable, Sendable {
    let accessToken: String
    let refreshToken: String?
    let expiresIn: Int?
    let scope: String?
    let sub: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
        case scope, sub
    }
}

/// An OAuth error body: `{"error": "...", "error_description": "..."}`.
struct OAuthErrorBody: Decodable {
    let error: String
    let errorDescription: String?

    enum CodingKeys: String, CodingKey {
        case error
        case errorDescription = "error_description"
    }
}

/// A DID document: where the account's data lives and which handle it claims.
struct DIDDocument: Decodable, Sendable {
    struct Service: Decodable, Sendable {
        let id: String
        let type: String
        let serviceEndpoint: String
    }

    let id: String
    let alsoKnownAs: [String]?
    let service: [Service]?

    /// The account's Personal Data Server.
    var pdsEndpoint: URL? {
        service?.first { $0.id.hasSuffix("#atproto_pds") && $0.type == "AtprotoPersonalDataServer" }
            .flatMap { URL(string: $0.serviceEndpoint) }
    }

    /// The handle the DID claims, from `at://handle`.
    var handle: String? {
        alsoKnownAs?.first { $0.hasPrefix("at://") }.map { String($0.dropFirst(5)) }
    }
}
