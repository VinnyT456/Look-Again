protocol FeedFetching: Sendable {
    func fetchPage(cursor: String?) async throws -> FeedPage
}
