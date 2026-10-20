import Foundation

/// A Bluesky post reduced to what the checker needs.
struct BlueskyPost: Sendable {
    var authorHandle: String
    var text: String
    var postURL: URL
    var imageURL: URL
    /// The post's other images, in order (Bluesky allows up to four).
    var moreImageURLs: [URL] = []

    var imageURLs: [URL] { [imageURL] + moreImageURLs }
}
