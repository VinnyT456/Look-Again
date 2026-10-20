import Foundation
import Observation

/// The optional Bluesky sign-in. Only used to read the user's Following
/// timeline; tokens stay in this iPhone's Keychain.
@MainActor
@Observable
final class BlueskyAccount {
    enum State: Equatable {
        case signedOut
        case signingIn
        case signedIn(handle: String)
    }

    private(set) var state: State = .signedOut
    /// Why the last sign-in failed, shown once.
    var lastError: String?

    private let client: BlueskyOAuthClient
    private let keychain: KeychainStore
    private var session: BlueskySession? {
        didSet { persist() }
    }
    private var refreshTask: Task<BlueskySession, Error>?

    init(client: BlueskyOAuthClient = BlueskyOAuthClient(), keychain: KeychainStore = .blueskySession) {
        self.client = client
        self.keychain = keychain
        if let data = keychain.load(), let saved = try? JSONDecoder().decode(BlueskySession.self, from: data) {
            session = saved
            state = .signedIn(handle: saved.handle)
        }
    }

    var isSignedIn: Bool {
        if case .signedIn = state { return true }
        return false
    }

    var handle: String? {
        if case .signedIn(let handle) = state { return handle }
        return nil
    }

    /// Opens Bluesky's sign-in page via `authenticate` (a web authentication
    /// session) and stores the result. `handle` is only for accounts hosted
    /// outside Bluesky.
    func signIn(handle: String? = nil, authenticate: (URL) async throws -> URL) async {
        guard state != .signingIn else { return }
        let previous = state
        state = .signingIn
        lastError = nil
        do {
            let pending = try await client.beginSignIn(handle: handle)
            let callback = try await authenticate(pending.authorizeURL)
            let newSession = try await client.finishSignIn(pending, callback: callback)
            session = newSession
            state = .signedIn(handle: newSession.handle)
        } catch {
            state = previous == .signingIn ? .signedOut : previous
            if !Self.isCancellation(error) {
                lastError = (error as? LocalizedError)?.errorDescription ?? "Couldn't sign in. Please try again."
            }
        }
    }

    func signOut() {
        refreshTask?.cancel()
        refreshTask = nil
        session = nil
        state = .signedOut
    }

    /// Raw JSON for one timeline page, refreshing the access token when it's
    /// about to expire or the server says it has.
    func timelineData(cursor: String?) async throws -> Data {
        guard var current = session else { throw BlueskyAuthError.signedOut }
        if current.needsRefresh() { current = try await refreshed() }
        var (data, status) = try await client.timeline(current, cursor: cursor)
        if status == 401 {
            current = try await refreshed()
            (data, status) = try await client.timeline(current, cursor: cursor)
        }
        guard status == 200 else {
            if status == 401 { expire() ; throw BlueskyAuthError.sessionExpired }
            throw BlueskyError.network
        }
        return data
    }

    /// One refresh at a time: refresh tokens are single-use.
    private func refreshed() async throws -> BlueskySession {
        if let refreshTask { return try await refreshTask.value }
        guard let current = session else { throw BlueskyAuthError.signedOut }
        let task = Task { [client] in try await client.refresh(current) }
        refreshTask = task
        defer { refreshTask = nil }
        do {
            let next = try await task.value
            session = next
            return next
        } catch {
            if (error as? BlueskyAuthError) == .sessionExpired { expire() }
            throw error
        }
    }

    private func expire() {
        signOut()
        lastError = BlueskyAuthError.sessionExpired.errorDescription
    }

    private func persist() {
        if let session, let data = try? JSONEncoder().encode(session) {
            keychain.save(data)
        } else {
            keychain.delete()
        }
    }

    private static func isCancellation(_ error: Error) -> Bool {
        if error is CancellationError { return true }
        if (error as? BlueskyAuthError) == .cancelled { return true }
        let ns = error as NSError
        // ASWebAuthenticationSessionError.canceledLogin
        return ns.domain == "com.apple.AuthenticationServices.WebAuthenticationSession" && ns.code == 1
    }
}
