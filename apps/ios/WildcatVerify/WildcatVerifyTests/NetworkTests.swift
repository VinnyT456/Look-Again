import CryptoKit
import Foundation
import Testing
import UIKit
@testable import WildcatVerify

/// Everything that goes over the network, against a stubbed URLSession.
/// Serialized because the stub's reply is shared static state.
@Suite(.serialized)
@MainActor
struct NetworkTests {
    private let link = "https://bsky.app/profile/alice.bsky.social/post/3abc"

    init() {
        StubURLProtocol.reset()
    }

    private func threadJSON(embed: String?, text: String = "Look at this") -> Data {
        let embedJSON = embed.map { ", \"embed\": \($0)" } ?? ""
        let json = """
        {"thread": {"post": {"author": {"handle": "alice.bsky.social"}, "record": {"text": "\(text)"}\(embedJSON)}}}
        """
        return Data(json.utf8)
    }

    private let imagesEmbed = #"{"images": [{"fullsize": "https://cdn.bsky.app/img/full.jpg"}]}"#
    private let recordWithMediaEmbed = #"{"media": {"images": [{"fullsize": "https://cdn.bsky.app/img/media.jpg"}]}}"#

    // MARK: Bluesky

    @Test func fetchesPostWithImage() async throws {
        let body = threadJSON(embed: imagesEmbed)
        StubURLProtocol.reply = { _ in .response(status: 200, body: body) }
        let post = try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)

        #expect(post.authorHandle == "alice.bsky.social")
        #expect(post.text == "Look at this")
        #expect(post.imageURL.absoluteString == "https://cdn.bsky.app/img/full.jpg")
        #expect(post.postURL.absoluteString == "https://bsky.app/profile/alice.bsky.social/post/3abc")
        let requested = try #require(StubURLProtocol.requestedURLs.first)
        #expect(requested.host() == "public.api.bsky.app")
    }

    @Test func readsImageFromQuotePostMedia() async throws {
        let body = threadJSON(embed: recordWithMediaEmbed)
        StubURLProtocol.reply = { _ in .response(status: 200, body: body) }
        let post = try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        #expect(post.imageURL.lastPathComponent == "media.jpg")
    }

    @Test func textOnlyPostIsNoImage() async {
        let body = threadJSON(embed: nil)
        StubURLProtocol.reply = { _ in .response(status: 200, body: body) }
        await #expect(throws: BlueskyError.noImage) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test(arguments: [400, 404, 500])
    func errorStatusIsPostNotFound(status: Int) async {
        StubURLProtocol.reply = { _ in .response(status: status, body: Data()) }
        await #expect(throws: BlueskyError.postNotFound) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func malformedJSONIsPostNotFound() async {
        StubURLProtocol.reply = { _ in .response(status: 200, body: Data("<html>".utf8)) }
        await #expect(throws: BlueskyError.postNotFound) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func deletedPostIsPostNotFound() async {
        StubURLProtocol.reply = { _ in .response(status: 200, body: Data(#"{"thread": {}}"#.utf8)) }
        await #expect(throws: BlueskyError.postNotFound) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test(arguments: [URLError.Code.notConnectedToInternet, .timedOut, .cannotFindHost])
    func connectionProblemsAreNetworkErrors(code: URLError.Code) async {
        StubURLProtocol.reply = { _ in .failure(code) }
        await #expect(throws: BlueskyError.network) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func cancelledRequestIsCancellationNotAnError() async {
        StubURLProtocol.reply = { _ in .failure(.cancelled) }
        await #expect(throws: CancellationError.self) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: link)
        }
    }

    @Test func invalidLinkMakesNoRequest() async {
        await #expect(throws: BlueskyError.invalidLink) {
            try await BlueskyService(session: StubURLProtocol.session()).fetchPost(from: "https://twitter.com/x/status/1")
        }
        #expect(StubURLProtocol.requestedURLs.isEmpty)
    }

    // MARK: Image download

    @Test func downloadsAndCachesImage() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/a.png"))
        let png = TestImages.pngData(width: 400, height: 200)
        StubURLProtocol.reply = { _ in .response(status: 200, body: png) }
        let repository = ImageRepository(session: StubURLProtocol.session())

        let image = try await repository.image(for: url, maxPixelSize: 100)
        #expect(max(image.size.width, image.size.height) <= 100)
        _ = try await repository.image(for: url, maxPixelSize: 100)
        #expect(StubURLProtocol.requestedURLs.count == 1, "Second load should come from the cache")
    }

    @Test func differentSizesReuseDownloadedData() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/b.png"))
        let png = TestImages.pngData(width: 400, height: 200)
        StubURLProtocol.reply = { _ in .response(status: 200, body: png) }
        let repository = ImageRepository(session: StubURLProtocol.session())

        _ = try await repository.image(for: url, maxPixelSize: 64)
        _ = try await repository.image(for: url, maxPixelSize: 300)
        #expect(StubURLProtocol.requestedURLs.count == 1)
    }

    @Test func imageServerErrorThrows() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/missing.png"))
        StubURLProtocol.reply = { _ in .response(status: 404, body: Data()) }
        await #expect(throws: URLError.self) {
            try await ImageRepository(session: StubURLProtocol.session()).image(for: url)
        }
    }

    @Test func nonImageDataThrows() async throws {
        let url = try #require(URL(string: "https://cdn.example.com/not-an-image"))
        StubURLProtocol.reply = { _ in .response(status: 200, body: Data("hello".utf8)) }
        await #expect(throws: URLError.self) {
            try await ImageRepository(session: StubURLProtocol.session()).image(for: url)
        }
    }

    // MARK: Full link check

    @Test func checkingALinkEndToEnd() async throws {
        // Build bodies up front: the stub runs on URLSession's thread, so it must
        // not call back into this main-actor test.
        let thread = threadJSON(embed: imagesEmbed, text: #"Breaking: lake monorail\nmore text"#)
        let image = TestImages.pngData()
        StubURLProtocol.reply = { request in
            request.url?.host() == "public.api.bsky.app"
                ? .response(status: 200, body: thread)
                : .response(status: 200, body: image)
        }
        let session = StubURLProtocol.session()
        let history = HistoryStore()
        let model = CheckViewModel(
            history: history,
            bluesky: BlueskyService(session: session),
            classifier: StubClassifier(),
            images: ImageRepository(session: session)
        )
        model.inputURL = "  \(link)  "
        model.checkPost()
        try await waitUntil { !model.path.isEmpty || model.isShowingError }

        #expect(!model.isShowingError, "Unexpected error: \(model.errorMessage)")
        let item = try #require(model.path.first)
        #expect(item.title == "Breaking: lake monorail")
        #expect(item.authorHandle == "alice.bsky.social")
        #expect(item.verdict == .tampered)
        #expect(item.confidencePercentage == 88)
        #expect(!item.isDemo)
        #expect(history.cases.first?.id == item.id)
        #expect(model.inputURL.isEmpty, "Field clears after a successful check")
    }
}


// MARK: - Sign in with Bluesky

private func base64URLDecode(_ string: String) -> Data? {
    var base64 = string.replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
    base64 += String(repeating: "=", count: (4 - base64.count % 4) % 4)
    return Data(base64Encoded: base64)
}

private struct ParsedJWT {
    var header: [String: Any]
    var payload: [String: Any]
    var signingInput: String
    var signature: Data
}

private func parseJWT(_ jwt: String) -> ParsedJWT? {
    let parts = jwt.split(separator: ".").map(String.init)
    guard parts.count == 3,
          let headerData = base64URLDecode(parts[0]), let payloadData = base64URLDecode(parts[1]),
          let signature = base64URLDecode(parts[2]),
          let header = try? JSONSerialization.jsonObject(with: headerData) as? [String: Any],
          let payload = try? JSONSerialization.jsonObject(with: payloadData) as? [String: Any]
    else { return nil }
    return ParsedJWT(header: header, payload: payload, signingInput: parts[0] + "." + parts[1], signature: signature)
}

/// The nonce a request's DPoP proof carries, if any.
private func dpopNonce(in request: URLRequest) -> String? {
    request.value(forHTTPHeaderField: "DPoP").flatMap(parseJWT)?.payload["nonce"] as? String
}

private let testMetadataJSON = Data(#"""
{"issuer":"https://bsky.social","authorization_endpoint":"https://bsky.social/oauth/authorize",
"token_endpoint":"https://bsky.social/oauth/token","pushed_authorization_request_endpoint":"https://bsky.social/oauth/par",
"require_pushed_authorization_requests":true,"dpop_signing_alg_values_supported":["ES256"]}
"""#.utf8)

private func tokenBody(access: String = "access-2", refresh: String = "refresh-2", sub: String = "did:plc:abc") -> Data {
    Data(#"{"access_token":"\#(access)","refresh_token":"\#(refresh)","expires_in":1800,"scope":"atproto transition:generic","sub":"\#(sub)"}"#.utf8)
}

private let timelineBody = Data(#"""
{"cursor":"next-page","feed":[
 {"post":{"uri":"at://did:plc:x/app.bsky.feed.post/1","author":{"handle":"a.bsky.social","displayName":"A"},"record":{"text":"keep"},
  "embed":{"images":[{"thumb":"https://cdn.bsky.app/t.jpg"}]},"indexedAt":"2026-10-15T01:07:15Z"}},
 {"post":{"uri":"at://did:plc:x/app.bsky.feed.post/2","author":{"handle":"b.bsky.social"},"record":{"text":"labelled"},"labels":[{"val":"porn"}],
  "embed":{"images":[{"thumb":"https://cdn.bsky.app/u.jpg"}]}}},
 {"post":{"uri":"at://did:plc:x/app.bsky.feed.post/3","author":{"handle":"c.bsky.social"},"record":{"text":"no image"}}}
]}
"""#.utf8)

private func testSession(expiresIn: TimeInterval = 3600, refreshToken: String? = "refresh-1") -> BlueskySession {
    BlueskySession(
        did: "did:plc:abc",
        handle: "alice.bsky.social",
        pds: URL(string: "https://pds.example.com") ?? URL(fileURLWithPath: "/"),
        issuer: "https://bsky.social",
        tokenEndpoint: URL(string: "https://bsky.social/oauth/token") ?? URL(fileURLWithPath: "/"),
        accessToken: "access-1",
        refreshToken: refreshToken,
        expiresAt: .now.addingTimeInterval(expiresIn),
        dpopKey: DPoPSigner().rawKey
    )
}

extension NetworkTests {
    private func makeAccount(session: BlueskySession?, keychain: KeychainStore) throws -> BlueskyAccount {
        if let session { keychain.save(try JSONEncoder().encode(session)) }
        return BlueskyAccount(client: BlueskyOAuthClient(session: StubURLProtocol.session()), keychain: keychain)
    }

    private func isolatedKeychain() -> KeychainStore {
        KeychainStore(service: "WildcatVerifyTests-\(UUID().uuidString)", account: "session")
    }

    // MARK: PKCE

    @Test func pkceMatchesTheRFC7636Example() {
        let pkce = PKCE(verifier: "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
        #expect(pkce.challenge == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
    }

    @Test func pkceVerifiersAreFreshAndURLSafe() {
        let a = PKCE(), b = PKCE()
        #expect(a.verifier != b.verifier)
        #expect(a.verifier.count >= 43, "RFC 7636 minimum length")
        for value in [a.verifier, a.challenge] {
            #expect(!value.contains { "+/=".contains($0) })
        }
    }

    // MARK: DPoP

    @Test func dpopProofIsAValidSignedJWT() throws {
        let signer = DPoPSigner()
        let now = Date(timeIntervalSince1970: 1_800_000_000)
        let url = try #require(URL(string: "https://bsky.social/oauth/par?x=1#frag"))
        let jwt = try #require(parseJWT(try signer.proof(method: "POST", url: url, nonce: "n1", accessToken: "tok", now: now)))

        #expect(jwt.header["alg"] as? String == "ES256")
        #expect(jwt.header["typ"] as? String == "dpop+jwt")
        let jwk = try #require(jwt.header["jwk"] as? [String: String])
        #expect(jwk["kty"] == "EC" && jwk["crv"] == "P-256")

        #expect(jwt.payload["htm"] as? String == "POST")
        #expect(jwt.payload["htu"] as? String == "https://bsky.social/oauth/par", "Query and fragment are dropped")
        #expect(jwt.payload["iat"] as? Int == 1_800_000_000)
        #expect(jwt.payload["nonce"] as? String == "n1")
        #expect((jwt.payload["jti"] as? String)?.isEmpty == false)
        let expectedHash = Data(SHA256.hash(data: Data("tok".utf8))).base64URLEncoded
        #expect(jwt.payload["ath"] as? String == expectedHash)

        // The embedded public key verifies the signature (raw r||s, as JWS ES256 requires).
        let xText = try #require(jwk["x"]), yText = try #require(jwk["y"])
        let x = try #require(base64URLDecode(xText))
        let y = try #require(base64URLDecode(yText))
        let publicKey = try P256.Signing.PublicKey(x963Representation: Data([0x04]) + x + y)
        #expect(jwt.signature.count == 64)
        let signature = try P256.Signing.ECDSASignature(rawRepresentation: jwt.signature)
        #expect(publicKey.isValidSignature(signature, for: Data(jwt.signingInput.utf8)))
    }

    @Test func dpopProofsOmitWhatTheyDontNeedAndNeverRepeat() throws {
        let signer = DPoPSigner()
        let url = try #require(URL(string: "https://bsky.social/oauth/token"))
        let first = try #require(parseJWT(try signer.proof(method: "POST", url: url, nonce: nil)))
        let second = try #require(parseJWT(try signer.proof(method: "POST", url: url, nonce: nil)))
        #expect(first.payload["nonce"] == nil && first.payload["ath"] == nil)
        #expect(first.payload["jti"] as? String != second.payload["jti"] as? String)
    }

    @Test func savedDPoPKeysRestoreTheSameIdentity() throws {
        let original = DPoPSigner()
        let restored = try DPoPSigner(rawKey: original.rawKey)
        #expect(restored.publicJWK == original.publicJWK)
    }

    @Test func tokenRequestsRetryOnceWithTheServersNonce() async throws {
        let token = tokenBody()
        StubURLProtocol.reply = { request in
            if dpopNonce(in: request) == "server-nonce" { return .response(status: 200, body: token) }
            return .response(status: 400, body: Data(#"{"error":"use_dpop_nonce"}"#.utf8), headers: ["DPoP-Nonce": "server-nonce"])
        }
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        let next = try await client.refresh(testSession())
        #expect(next.accessToken == "access-2")
        #expect(StubURLProtocol.requestedURLs.count == 2, "One retry, not a loop")
    }

    @Test func serversThatKeepDemandingNoncesAreGivenUpOn() async throws {
        StubURLProtocol.reply = { _ in
            .response(status: 400, body: Data(#"{"error":"use_dpop_nonce"}"#.utf8), headers: ["DPoP-Nonce": "again"])
        }
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        await #expect(throws: BlueskyAuthError.sessionExpired) { try await client.refresh(testSession()) }
        #expect(StubURLProtocol.requestedURLs.count == 2)
    }

    @Test func resourceRequestsRetryOnA401NonceChallenge() async throws {
        StubURLProtocol.reply = { request in
            if dpopNonce(in: request) == "pds-nonce" { return .response(status: 200, body: timelineBody) }
            return .response(status: 401, body: Data(), headers: ["WWW-Authenticate": #"DPoP error="use_dpop_nonce""#, "DPoP-Nonce": "pds-nonce"])
        }
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        let (_, status) = try await client.timeline(testSession(), cursor: nil)
        #expect(status == 200)
        #expect(StubURLProtocol.requestedURLs.count == 2)
    }

    // MARK: Requests

    @Test func formBodiesPercentEncodeReservedCharacters() throws {
        let url = try #require(URL(string: "https://bsky.social/oauth/par"))
        let request = BlueskyOAuthClient.formRequest(url, [
            "x": "a+b&c=d",
            "scope": "atproto transition:generic",
            "redirect_uri": "io.github.vinnyt456:/oauth/callback",
        ])
        let body = String(decoding: try #require(request.httpBody), as: UTF8.self)
        #expect(body == "redirect_uri=io.github.vinnyt456%3A%2Foauth%2Fcallback&scope=atproto%20transition%3Ageneric&x=a%2Bb%26c%3Dd")
        #expect(request.value(forHTTPHeaderField: "Content-Type") == "application/x-www-form-urlencoded")
    }

    @Test func timelineRequestsGoToTheUsersServerThroughTheAppView() async throws {
        let seen = LockedBox<URLRequest?>(nil)
        StubURLProtocol.reply = { request in
            seen.value = request
            return .response(status: 200, body: timelineBody)
        }
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        _ = try await client.timeline(testSession(), cursor: "abc")
        let request = try #require(seen.value)
        #expect(request.url?.host() == "pds.example.com")
        #expect(request.url?.path() == "/xrpc/app.bsky.feed.getTimeline")
        #expect(request.url?.query()?.contains("cursor=abc") == true)
        #expect(request.value(forHTTPHeaderField: "atproto-proxy") == "did:web:api.bsky.app#bsky_appview")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "DPoP access-1")
        #expect(request.value(forHTTPHeaderField: "DPoP") != nil)
    }

    // MARK: The reply to Bluesky's sign-in page

    @Test func callbackRepliesAreCheckedBeforeAnyCodeIsUsed() async throws {
        let metadata = try JSONDecoder().decode(AuthServerMetadata.self, from: testMetadataJSON)
        let pending = BlueskyOAuthClient.PendingSignIn(
            authorizeURL: try #require(URL(string: "https://bsky.social/oauth/authorize")),
            state: "s1", pkce: PKCE(), signer: DPoPSigner(), metadata: metadata, expectedDID: nil
        )
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        func callback(_ query: String) throws -> URL {
            try #require(URL(string: "io.github.vinnyt456:/oauth/callback?\(query)"))
        }

        await #expect(throws: BlueskyAuthError.stateMismatch) {
            try await client.finishSignIn(pending, callback: callback("state=other&iss=https%3A%2F%2Fbsky.social&code=c"))
        }
        await #expect(throws: BlueskyAuthError.wrongIssuer) {
            try await client.finishSignIn(pending, callback: callback("state=s1&iss=https%3A%2F%2Fevil.example&code=c"))
        }
        await #expect(throws: BlueskyAuthError.wrongIssuer, "A reply with no issuer is refused too") {
            try await client.finishSignIn(pending, callback: callback("state=s1&code=c"))
        }
        await #expect(throws: BlueskyAuthError.cancelled) {
            try await client.finishSignIn(pending, callback: callback("error=access_denied&state=s1"))
        }
        await #expect(throws: BlueskyAuthError.serverRejected("server_error")) {
            try await client.finishSignIn(pending, callback: callback("error=server_error&state=s1"))
        }
        await #expect(throws: BlueskyAuthError.badResponse) {
            try await client.finishSignIn(pending, callback: callback("state=s1&iss=https%3A%2F%2Fbsky.social"))
        }
        #expect(StubURLProtocol.requestedURLs.isEmpty, "Nothing was sent to the token endpoint")
    }

    // MARK: Refresh

    @Test func refreshReplacesTheTokensAndKeepsTheAccount() async throws {
        let token = tokenBody()
        StubURLProtocol.reply = { _ in .response(status: 200, body: token) }
        let original = testSession(expiresIn: -10)
        let next = try await BlueskyOAuthClient(session: StubURLProtocol.session()).refresh(original)
        #expect(next.accessToken == "access-2" && next.refreshToken == "refresh-2")
        #expect(next.did == original.did && next.pds == original.pds && next.dpopKey == original.dpopKey)
        #expect(!next.needsRefresh())
        #expect(original.needsRefresh(), "An expired session is refreshed")
        #expect(testSession(expiresIn: 30).needsRefresh(), "A minute of margin")
    }

    @Test func aRefreshRejectedByBlueskyMeansSignInAgain() async throws {
        StubURLProtocol.reply = { _ in .response(status: 400, body: Data(#"{"error":"invalid_grant"}"#.utf8)) }
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        await #expect(throws: BlueskyAuthError.sessionExpired) { try await client.refresh(testSession()) }
        await #expect(throws: BlueskyAuthError.sessionExpired) { try await client.refresh(testSession(refreshToken: nil)) }
    }

    @Test func aRefreshForADifferentAccountIsRefused() async throws {
        let stranger = tokenBody(sub: "did:plc:someone-else")
        StubURLProtocol.reply = { _ in .response(status: 200, body: stranger) }
        let client = BlueskyOAuthClient(session: StubURLProtocol.session())
        await #expect(throws: BlueskyAuthError.wrongIssuer) { try await client.refresh(testSession()) }
    }

    // MARK: The signed-in account

    @Test func anExpiredTokenIsRefreshedBeforeReadingTheTimeline() async throws {
        let token = tokenBody()
        StubURLProtocol.reply = { request in
            if request.url?.host() == "bsky.social" { return .response(status: 200, body: token) }
            let ok = request.value(forHTTPHeaderField: "Authorization") == "DPoP access-2"
            return .response(status: ok ? 200 : 401, body: ok ? timelineBody : Data())
        }
        let keychain = isolatedKeychain()
        defer { keychain.delete() }
        let account = try makeAccount(session: testSession(expiresIn: -10), keychain: keychain)
        let page = try await TimelineFeedService(account: account).fetchPage(cursor: nil)
        #expect(page.posts.map(\.authorHandle) == ["a.bsky.social"], "Labelled and text-only posts are filtered like What's Hot")
        #expect(page.cursor == "next-page")
        let saved = try JSONDecoder().decode(BlueskySession.self, from: try #require(keychain.load()))
        #expect(saved.accessToken == "access-2", "The new tokens are stored")
    }

    @Test func aRejectedTokenIsRefreshedOnceAndTheReadRetried() async throws {
        let token = tokenBody()
        StubURLProtocol.reply = { request in
            if request.url?.host() == "bsky.social" { return .response(status: 200, body: token) }
            let ok = request.value(forHTTPHeaderField: "Authorization") == "DPoP access-2"
            return .response(status: ok ? 200 : 401, body: ok ? timelineBody : Data())
        }
        let keychain = isolatedKeychain()
        defer { keychain.delete() }
        let account = try makeAccount(session: testSession(), keychain: keychain)
        let data = try await account.timelineData(cursor: nil)
        #expect(data == timelineBody)
        #expect(account.isSignedIn)
    }

    @Test func aTimelineThatStaysUnauthorizedSignsTheUserOut() async throws {
        let token = tokenBody()
        StubURLProtocol.reply = { request in
            request.url?.host() == "bsky.social" ? .response(status: 200, body: token) : .response(status: 401, body: Data())
        }
        let keychain = isolatedKeychain()
        defer { keychain.delete() }
        let account = try makeAccount(session: testSession(), keychain: keychain)
        await #expect(throws: BlueskyAuthError.sessionExpired) { try await account.timelineData(cursor: nil) }
        #expect(!account.isSignedIn)
        #expect(account.lastError?.contains("expired") == true)
        #expect(keychain.load() == nil, "Nothing stale is left in the Keychain")
    }

    @Test func serverErrorsOnTheTimelineDontSignAnyoneOut() async throws {
        StubURLProtocol.reply = { _ in .response(status: 500, body: Data()) }
        let keychain = isolatedKeychain()
        defer { keychain.delete() }
        let account = try makeAccount(session: testSession(), keychain: keychain)
        await #expect(throws: BlueskyError.network) { try await account.timelineData(cursor: nil) }
        #expect(account.isSignedIn)
    }

    @Test func signedOutAccountsCantReadATimeline() async throws {
        let keychain = isolatedKeychain()
        let account = try makeAccount(session: nil, keychain: keychain)
        await #expect(throws: BlueskyAuthError.signedOut) { try await account.timelineData(cursor: nil) }
        #expect(StubURLProtocol.requestedURLs.isEmpty)
    }

    @Test func sessionsSurviveARelaunchAndSignOutClearsThem() throws {
        let keychain = isolatedKeychain()
        defer { keychain.delete() }
        _ = try makeAccount(session: testSession(), keychain: keychain)
        let relaunched = BlueskyAccount(client: BlueskyOAuthClient(session: StubURLProtocol.session()), keychain: keychain)
        #expect(relaunched.state == .signedIn(handle: "alice.bsky.social"))

        relaunched.signOut()
        #expect(relaunched.state == .signedOut)
        #expect(keychain.load() == nil)
        let afterSignOut = BlueskyAccount(client: BlueskyOAuthClient(session: StubURLProtocol.session()), keychain: keychain)
        #expect(!afterSignOut.isSignedIn)
    }

    // MARK: Signing in

    private func serveSignInPages(parStatus: Int, parBody: String) {
        let metadata = testMetadataJSON
        let par = Data(parBody.utf8)
        StubURLProtocol.reply = { request in
            request.url?.path() == "/oauth/par"
                ? .response(status: parStatus, body: par)
                : .response(status: 200, body: metadata)
        }
    }

    @Test func aSignInBlueskyRejectsExplainsItselfAndStaysSignedOut() async throws {
        serveSignInPages(parStatus: 400, parBody: #"{"error":"invalid_client_metadata"}"#)
        let keychain = isolatedKeychain()
        let account = try makeAccount(session: nil, keychain: keychain)
        var openedPage = false
        await account.signIn { _ in openedPage = true; throw CancellationError() }
        #expect(!openedPage, "The sign-in page never opens when the request was refused")
        #expect(account.state == .signedOut)
        #expect(account.lastError?.contains("invalid_client_metadata") == true)
    }

    @Test func cancellingTheSignInPageIsNotAnError() async throws {
        serveSignInPages(parStatus: 200, parBody: #"{"request_uri":"urn:ietf:params:oauth:request_uri:abc","expires_in":60}"#)
        let account = try makeAccount(session: nil, keychain: isolatedKeychain())
        var opened: URL?
        await account.signIn { url in opened = url; throw CancellationError() }
        #expect(opened?.host() == "bsky.social")
        let items = URLComponents(url: try #require(opened), resolvingAgainstBaseURL: false)?.queryItems ?? []
        #expect(items.first { $0.name == "request_uri" }?.value == "urn:ietf:params:oauth:request_uri:abc")
        #expect(items.first { $0.name == "client_id" }?.value == BlueskyOAuthConfig.clientID)
        #expect(items.count == 2, "Only client_id and request_uri, as the spec requires")
        #expect(account.state == .signedOut && account.lastError == nil)

        // The system sheet's own "Cancel" is also silent.
        await account.signIn { _ in throw NSError(domain: "com.apple.AuthenticationServices.WebAuthenticationSession", code: 1) }
        #expect(account.lastError == nil)
    }

    @Test func aSignInThatFailsMidwayShowsAMessage() async throws {
        serveSignInPages(parStatus: 200, parBody: #"{"request_uri":"urn:x"}"#)
        let account = try makeAccount(session: nil, keychain: isolatedKeychain())
        await account.signIn { _ in throw URLError(.notConnectedToInternet) }
        #expect(account.lastError != nil)
        #expect(account.state == .signedOut)
    }

    // MARK: Identity

    @Test func handlesAreTidiedBeforeLookup() {
        #expect(BlueskyIdentity.normalize("  @Alice.Bsky.Social \n") == "alice.bsky.social")
        #expect(BlueskyIdentity.normalize("bob.example.com") == "bob.example.com")
    }

    @Test func didsMapToTheirDocumentLocations() {
        #expect(BlueskyIdentity.documentURL(for: "did:plc:abc")?.absoluteString == "https://plc.directory/did:plc:abc")
        #expect(BlueskyIdentity.documentURL(for: "did:web:example.com")?.absoluteString == "https://example.com/.well-known/did.json")
        #expect(BlueskyIdentity.documentURL(for: "did:web:localhost%3A3000")?.absoluteString == "https://localhost:3000/.well-known/did.json")
        #expect(BlueskyIdentity.documentURL(for: "did:key:zabc") == nil)
    }

    @Test func didDocumentsNameTheServerAndTheHandle() throws {
        let json = #"""
        {"id":"did:plc:abc","alsoKnownAs":["at://alice.bsky.social"],
         "service":[{"id":"#atproto_pds","type":"AtprotoPersonalDataServer","serviceEndpoint":"https://pds.example.com"}]}
        """#
        let document = try JSONDecoder().decode(DIDDocument.self, from: Data(json.utf8))
        #expect(document.pdsEndpoint?.absoluteString == "https://pds.example.com")
        #expect(document.handle == "alice.bsky.social")
        let bare = try JSONDecoder().decode(DIDDocument.self, from: Data(#"{"id":"did:plc:abc"}"#.utf8))
        #expect(bare.pdsEndpoint == nil && bare.handle == nil)
    }

    @Test func theRedirectSchemeIsTheClientHostReversed() throws {
        let host = try #require(URL(string: BlueskyOAuthConfig.clientID)?.host())
        #expect(host.split(separator: ".").reversed().joined(separator: ".") == BlueskyOAuthConfig.callbackScheme)
        #expect(BlueskyOAuthConfig.redirectURI.hasPrefix(BlueskyOAuthConfig.callbackScheme + ":/"))
        #expect(!BlueskyOAuthConfig.redirectURI.contains("://"), "One slash, as the AT Protocol requires")
        #expect(BlueskyOAuthConfig.scope.split(separator: " ").contains("atproto"))
    }
}

/// A value a `@Sendable` stub closure can write and a test can read.
private final class LockedBox<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: Value

    init(_ value: Value) { stored = value }

    var value: Value {
        get { lock.withLock { stored } }
        set { lock.withLock { stored = newValue } }
    }
}
