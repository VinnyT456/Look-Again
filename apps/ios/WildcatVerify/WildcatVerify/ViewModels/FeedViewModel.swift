import Foundation
import Observation

/// The Feed tab: pages through image posts from What's Hot or, when signed
/// in, the user's Following timeline. Each source keeps its own place.
@MainActor
@Observable
final class FeedViewModel {
    enum Status: Equatable {
        case idle
        case loading
        case loaded
        case failed(String)
    }

    var path: [FeedPost] = []
    private(set) var posts: [FeedPost] = []
    private(set) var status: Status = .idle
    private(set) var isLoadingMore = false
    private(set) var hasMore = true

    /// What the list is showing now.
    private(set) var source: FeedSource
    private var services: [FeedSource: any FeedFetching]
    private let isFollowingAvailable: @MainActor () -> Bool
    /// Each source's posts and place, kept while the other is shown.
    private var saved: [FeedSource: Snapshot] = [:]

    private struct Snapshot {
        var posts: [FeedPost]
        var cursor: String?
        var hasMore: Bool
        var status: Status
    }

    private var service: any FeedFetching {
        services[source] ?? services[.whatsHot] ?? BlueskyFeedService()
    }
    /// Where hidden accounts are kept; nil keeps them in memory (tests, previews).
    private let settings: SettingsStore?
    private var memoryHiddenAccounts: [String: String] = [:]
    /// Posts hidden one at a time; forgotten when the app closes.
    private var hiddenPostIDs: Set<String> = []
    private var cursor: String?

    /// Checks posts on its own as they appear; nil turns that off (tests).
    let autoCheck: FeedAutoChecker?

    init(
        service: any FeedFetching = BlueskyFeedService(),
        following: (any FeedFetching)? = nil,
        isFollowingAvailable: @escaping @MainActor () -> Bool = { false },
        settings: SettingsStore? = nil,
        autoCheck: FeedAutoChecker? = nil
    ) {
        var services: [FeedSource: any FeedFetching] = [.whatsHot: service]
        services[.following] = following
        self.services = services
        self.isFollowingAvailable = isFollowingAvailable
        self.settings = settings
        self.autoCheck = autoCheck
        source = following != nil && isFollowingAvailable() ? .following : .whatsHot
    }

    /// Sources the switch offers: Following only while signed in.
    var availableSources: [FeedSource] {
        services[.following] != nil && isFollowingAvailable() ? [.following, .whatsHot] : [.whatsHot]
    }

    /// For the Following / What's Hot switch.
    var selectedSource: FeedSource {
        get { source }
        set { select(newValue) }
    }

    /// Shows another source, picking up where it was left.
    func select(_ newSource: FeedSource) {
        guard newSource != source, availableSources.contains(newSource) else { return }
        saved[source] = Snapshot(posts: posts, cursor: cursor, hasMore: hasMore, status: status)
        source = newSource
        path.removeAll()
        if let snapshot = saved[newSource] {
            posts = snapshot.posts
            cursor = snapshot.cursor
            hasMore = snapshot.hasMore
            status = snapshot.status
        } else {
            posts = []
            cursor = nil
            hasMore = true
            status = .idle
        }
    }

    /// After sign-in: open on the user's own feed.
    func showFollowing() {
        saved[.following] = nil
        select(.following)
    }

    /// After sign-out: forget the timeline and go back to What's Hot.
    func forgetFollowing() {
        saved[.following] = nil
        if source == .following {
            source = .whatsHot
            path.removeAll()
            if let snapshot = saved[.whatsHot] {
                posts = snapshot.posts
                cursor = snapshot.cursor
                hasMore = snapshot.hasMore
                status = snapshot.status
            } else {
                posts = []
                cursor = nil
                hasMore = true
                status = .idle
            }
        }
    }

    func verdict(for post: FeedPost) -> FeedVerdict? {
        autoCheck?.verdicts[post.id]
    }

    private var hiddenAccounts: [String: String] {
        get { settings?.hiddenAccounts ?? memoryHiddenAccounts }
        set {
            if let settings { settings.hiddenAccounts = newValue } else { memoryHiddenAccounts = newValue }
        }
    }

    /// What the list shows: every loaded post except hidden ones.
    var visiblePosts: [FeedPost] {
        posts.filter { !hiddenPostIDs.contains($0.id) && hiddenAccounts[$0.authorDID] == nil }
    }

    /// Feed → … → Hide This Post.
    func hidePost(_ post: FeedPost) {
        hiddenPostIDs.insert(post.id)
    }

    /// Feed → … → Hide Posts from @handle. Undo in Settings → Hidden Accounts.
    func hideAccount(of post: FeedPost) {
        hiddenAccounts[post.authorDID] = post.authorHandle
    }

    /// First load, or pull to refresh. Keeps the old posts on screen if it fails.
    func refresh() async {
        if posts.isEmpty { status = .loading }
        let requested = source
        do {
            let page = try await service.fetchPage(cursor: nil)
            // The user switched sources while this loaded.
            guard requested == source else { return }
            posts = Self.unique(page.posts)
            cursor = page.cursor
            hasMore = page.cursor != nil
            status = .loaded
        } catch is CancellationError {
            if posts.isEmpty { status = .idle }
        } catch {
            if posts.isEmpty {
                status = .failed((error as? LocalizedError)?.errorDescription ?? "Couldn't load the feed.")
            }
        }
    }

    func loadIfNeeded() async {
        guard status == .idle else { return }
        await refresh()
    }

    /// Called as the last post scrolls into view.
    func loadMore(after post: FeedPost) async {
        guard post.id == visiblePosts.last?.id, hasMore, !isLoadingMore, let cursor else { return }
        isLoadingMore = true
        defer { isLoadingMore = false }
        var next: String? = cursor
        // A page can contain no image posts; skip ahead a few pages so the
        // list doesn't stall with nothing new to trigger the next load.
        for _ in 0..<3 {
            guard let pageCursor = next else { break }
            let requested = source
            do {
                let page = try await service.fetchPage(cursor: pageCursor)
                guard requested == source else { return }
                let before = posts.count
                posts = Self.unique(posts + page.posts)
                next = page.cursor
                if posts.count > before { break }
            } catch {
                // Keep what's shown; scrolling back down will try again.
                return
            }
        }
        self.cursor = next
        hasMore = next != nil
    }

    func open(_ post: FeedPost) {
        path.append(post)
    }

    /// Feeds can repeat a post across pages; keep the first copy.
    private static func unique(_ posts: [FeedPost]) -> [FeedPost] {
        var seen = Set<String>()
        return posts.filter { seen.insert($0.id).inserted }
    }
}
