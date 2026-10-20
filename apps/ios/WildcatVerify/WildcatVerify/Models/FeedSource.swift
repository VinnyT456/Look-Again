/// Which Bluesky feed the Feed tab shows.
enum FeedSource: String, CaseIterable, Hashable, Sendable {
    /// The signed-in user's own timeline.
    case following
    /// Bluesky's public trending feed; no sign-in needed.
    case whatsHot

    var title: String {
        switch self {
        case .following: "Following"
        case .whatsHot: "What's Hot"
        }
    }
}
