protocol BlueskyFetching: Sendable {
    func fetchPost(from link: String) async throws -> BlueskyPost
}
