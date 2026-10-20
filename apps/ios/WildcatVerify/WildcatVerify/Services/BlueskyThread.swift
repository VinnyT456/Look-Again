import Foundation

/// The fields WildcatVerify reads from `app.bsky.feed.getPostThread`.
struct BlueskyThread: Decodable {
    struct Thread: Decodable {
        var post: Post?
    }

    struct Post: Decodable {
        struct Author: Decodable { var handle: String }
        struct Record: Decodable { var text: String? }

        var author: Author
        var record: Record
        var embed: Embed?
    }

    struct Embed: Decodable {
        struct ImageView: Decodable { var fullsize: URL }
        struct Media: Decodable { var images: [ImageView]? }

        var images: [ImageView]?
        /// Present for `app.bsky.embed.recordWithMedia#view`.
        var media: Media?

        var firstImage: URL? { allImages.first }

        var allImages: [URL] {
            (images ?? media?.images ?? []).map(\.fullsize)
        }
    }

    var thread: Thread
}
