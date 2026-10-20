import Foundation

enum BlueskyError: LocalizedError, Equatable {
    case invalidLink
    case postNotFound
    case noImage
    case network

    var errorDescription: String? {
        switch self {
        case .invalidLink: "That doesn't look like a Bluesky post link. It should look like bsky.app/profile/…/post/…"
        case .postNotFound: "We couldn't find that post. It may be deleted or private."
        case .noImage: "That post doesn't have a photo to check."
        case .network: "Couldn't reach Bluesky. Check your connection and try again."
        }
    }
}
