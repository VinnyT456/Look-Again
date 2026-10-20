/// One page of feed posts and the cursor for the next page (nil at the end).
struct FeedPage: Sendable {
    var posts: [FeedPost]
    var cursor: String?
}
