import Foundation

/// Reads Bluesky's public "What's Hot" feed through the unauthenticated
/// AppView and keeps only image posts that are safe to show.
struct BlueskyFeedService: FeedFetching {
    static let whatsHot = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.generator/whats-hot"
    static let pageSize = 30

    var session: URLSession = .shared
    var feedURI: String = whatsHot

    func fetchPage(cursor: String?) async throws -> FeedPage {
        var components = URLComponents(string: "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed")
        var items = [
            URLQueryItem(name: "feed", value: feedURI),
            URLQueryItem(name: "limit", value: String(Self.pageSize)),
        ]
        if let cursor { items.append(URLQueryItem(name: "cursor", value: cursor)) }
        components?.queryItems = items
        guard let url = components?.url else { throw BlueskyError.network }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(from: url)
        } catch let error as URLError where error.code == .cancelled {
            throw CancellationError()
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw BlueskyError.network
        }
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BlueskyError.network
        }
        let decoded: BlueskyFeedResponse
        do {
            decoded = try JSONDecoder().decode(BlueskyFeedResponse.self, from: data)
        } catch {
            throw BlueskyError.network
        }
        return FeedPage(posts: decoded.feed.compactMap { Self.post(from: $0.post) }, cursor: decoded.cursor)
    }

    /// Bluesky timestamps include fractional seconds ("…15.455Z"), which the
    /// default ISO 8601 parser rejects.
    static func parseDate(_ string: String) -> Date? {
        (try? Date(string, strategy: Date.ISO8601FormatStyle(includingFractionalSeconds: true)))
            ?? (try? Date(string, strategy: .iso8601))
    }

    /// Keeps posts with at least one image and no moderation or self labels on
    /// the post or its author. Labels flag adult, graphic or otherwise
    /// sensitive content, so anything labelled is left out entirely.
    static func post(from post: BlueskyFeedResponse.Post) -> FeedPost? {
        guard (post.labels ?? []).isEmpty, (post.author.labels ?? []).isEmpty else { return nil }
        let images = post.embed?.allImages ?? []
        guard let first = images.first else { return nil }
        guard let rkey = post.uri.split(separator: "/").last,
              let postURL = URL(string: "https://bsky.app/profile/\(post.author.handle)/post/\(rkey)")
        else { return nil }

        let ratio = first.aspectRatio.flatMap { $0.height > 0 ? $0.width / $0.height : nil }
        return FeedPost(
            id: post.uri,
            authorHandle: post.author.handle,
            authorName: post.author.displayName?.isEmpty == false ? post.author.displayName ?? post.author.handle : post.author.handle,
            avatarURL: post.author.avatar,
            text: post.record.text ?? "",
            postURL: postURL,
            thumbURL: first.thumb,
            imageAlt: first.alt ?? "",
            aspectRatio: ratio,
            postedAt: post.indexedAt.flatMap(parseDate),
            imageCount: images.count
        )
    }
}
