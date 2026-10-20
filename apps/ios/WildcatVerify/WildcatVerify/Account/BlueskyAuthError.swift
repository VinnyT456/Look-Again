import Foundation

enum BlueskyAuthError: LocalizedError, Equatable {
    case cancelled
    case accountNotFound
    case serverRejected(String)
    case badResponse
    case stateMismatch
    case wrongIssuer
    case signedOut
    case sessionExpired

    var errorDescription: String? {
        switch self {
        case .cancelled: "Sign-in was cancelled."
        case .accountNotFound: "Couldn't find that Bluesky account. Check the handle and try again."
        case .serverRejected(let reason): "Bluesky didn't accept the sign-in (\(reason)). Please try again."
        case .badResponse: "Couldn't reach Bluesky to sign in. Check your connection and try again."
        case .stateMismatch, .wrongIssuer: "The sign-in reply didn't match this request, so it was ignored for safety. Please try again."
        case .signedOut: "Sign in with Bluesky to see your Following feed."
        case .sessionExpired: "Your Bluesky sign-in expired. Sign in again to see your Following feed."
        }
    }
}
