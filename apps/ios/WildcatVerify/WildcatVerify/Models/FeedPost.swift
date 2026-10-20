import Foundation

/// An image post from Bluesky's public "What's Hot" feed.
struct FeedPost: Identifiable, Hashable, Sendable {
    /// The post's AT URI.
    var id: String
    var authorHandle: String
    var authorName: String
    var avatarURL: URL?
    var text: String
    var postURL: URL
    var thumbURL: URL
    var imageAlt: String
    /// Width ÷ height of the first image, when Bluesky provides it.
    var aspectRatio: Double?
    var postedAt: Date?
    /// How many images the post has; every one is checked.
    var imageCount: Int

    /// The author's DID, from the post's AT URI (at://did:plc:…/app.bsky.feed.post/…).
    /// Stable even when the author changes their handle.
    var authorDID: String {
        let path = id.hasPrefix("at://") ? id.dropFirst(5) : Substring(id)
        return path.split(separator: "/").first.map(String.init) ?? authorHandle
    }
}
