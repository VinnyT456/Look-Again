import Foundation

/// The fields WildcatVerify reads from `app.bsky.feed.getFeed`.
struct BlueskyFeedResponse: Decodable {
    struct Item: Decodable {
        var post: Post
    }

    struct Post: Decodable {
        struct Author: Decodable {
            var handle: String
            var displayName: String?
            var avatar: URL?
            var labels: [Label]?
        }

        struct Record: Decodable {
            var text: String?
        }

        var uri: String
        var author: Author
        var record: Record
        var embed: Embed?
        var labels: [Label]?
        var indexedAt: String?
    }

    struct Embed: Decodable {
        struct Image: Decodable {
            struct Ratio: Decodable {
                var width: Double
                var height: Double
            }

            var thumb: URL
            var alt: String?
            var aspectRatio: Ratio?
        }

        struct Media: Decodable {
            var images: [Image]?
        }

        var images: [Image]?
        /// Present for posts that quote another post and attach images.
        var media: Media?

        var allImages: [Image] { images ?? media?.images ?? [] }
    }

    struct Label: Decodable {
        var val: String
    }

    var feed: [Item]
    var cursor: String?
}
