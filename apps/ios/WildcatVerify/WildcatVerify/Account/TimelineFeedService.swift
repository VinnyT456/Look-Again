import Foundation

/// The signed-in user's Following timeline, as image posts for the Feed tab.
/// Same filtering as What's Hot: image posts only, nothing labelled.
struct TimelineFeedService: FeedFetching {
    let account: BlueskyAccount

    func fetchPage(cursor: String?) async throws -> FeedPage {
        let data = try await account.timelineData(cursor: cursor)
        guard let decoded = try? JSONDecoder().decode(BlueskyFeedResponse.self, from: data) else {
            throw BlueskyError.network
        }
        return FeedPage(posts: decoded.feed.compactMap { BlueskyFeedService.post(from: $0.post) }, cursor: decoded.cursor)
    }
}
