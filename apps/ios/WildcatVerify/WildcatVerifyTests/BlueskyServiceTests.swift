import Foundation
import Testing
@testable import WildcatVerify

struct BlueskyServiceTests {
    @Test(arguments: [
        "https://bsky.app/profile/bsky.app/post/3mxu3hsnebc2v",
        "bsky.app/profile/bsky.app/post/3mxu3hsnebc2v",
        "  https://bsky.app/profile/bsky.app/post/3mxu3hsnebc2v\n",
    ])
    func parsesPostLinks(_ link: String) throws {
        let parsed = try #require(BlueskyService.parse(link))
        #expect(parsed.actor == "bsky.app")
        #expect(parsed.rkey == "3mxu3hsnebc2v")
    }

    @Test func parsesDIDLinks() throws {
        let parsed = try #require(BlueskyService.parse("https://bsky.app/profile/did:plc:abc123/post/xyz"))
        #expect(parsed.actor == "did:plc:abc123")
    }

    @Test(arguments: [
        "",
        "https://example.com/profile/a/post/b",
        "https://bsky.app/profile/someone",
        "https://bsky.app/profile/someone/feed/xyz",
        "not a link",
    ])
    func rejectsOtherLinks(_ link: String) {
        #expect(BlueskyService.parse(link) == nil)
    }

    @Test func buildsThreadRequest() throws {
        let url = try #require(BlueskyService.threadURL(actor: "bsky.app", rkey: "abc"))
        let components = try #require(URLComponents(url: url, resolvingAgainstBaseURL: false))
        #expect(components.host == "public.api.bsky.app")
        #expect(components.queryItems?.first { $0.name == "uri" }?.value == "at://bsky.app/app.bsky.feed.post/abc")
    }

    @Test func invalidLinkThrows() async {
        await #expect(throws: BlueskyError.invalidLink) {
            try await BlueskyService().fetchPost(from: "https://example.com")
        }
    }
}
