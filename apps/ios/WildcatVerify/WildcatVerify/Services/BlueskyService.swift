import Foundation

/// Reads public posts through the unauthenticated Bluesky AppView.
struct BlueskyService: BlueskyFetching {
    var session: URLSession = .shared

    /// Parses `https://bsky.app/profile/{handle-or-did}/post/{rkey}` into its parts.
    static func parse(_ link: String) -> (actor: String, rkey: String)? {
        var trimmed = link.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.lowercased().hasPrefix("http") { trimmed = "https://" + trimmed }
        guard let url = URL(string: trimmed),
              let host = url.host()?.lowercased(),
              host == "bsky.app" || host.hasSuffix(".bsky.app")
        else { return nil }

        let parts = url.pathComponents.filter { $0 != "/" }
        guard parts.count >= 4, parts[0] == "profile", parts[2] == "post",
              !parts[1].isEmpty, !parts[3].isEmpty
        else { return nil }
        return (parts[1], parts[3])
    }

    static func threadURL(actor: String, rkey: String) -> URL? {
        var components = URLComponents(string: "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread")
        components?.queryItems = [
            URLQueryItem(name: "uri", value: "at://\(actor)/app.bsky.feed.post/\(rkey)"),
            URLQueryItem(name: "depth", value: "0"),
            URLQueryItem(name: "parentHeight", value: "0"),
        ]
        return components?.url
    }

    func fetchPost(from link: String) async throws -> BlueskyPost {
        guard let (actor, rkey) = Self.parse(link),
              let requestURL = Self.threadURL(actor: actor, rkey: rkey)
        else { throw BlueskyError.invalidLink }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(from: requestURL)
        } catch let error as URLError where error.code == .cancelled {
            throw CancellationError()
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw BlueskyError.network
        }
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw BlueskyError.postNotFound
        }

        let thread: BlueskyThread
        do {
            thread = try JSONDecoder().decode(BlueskyThread.self, from: data)
        } catch {
            throw BlueskyError.postNotFound
        }
        guard let post = thread.thread.post else { throw BlueskyError.postNotFound }
        guard let image = post.embed?.firstImage else { throw BlueskyError.noImage }

        let handle = post.author.handle
        return BlueskyPost(
            authorHandle: handle,
            text: post.record.text ?? "",
            postURL: URL(string: "https://bsky.app/profile/\(handle)/post/\(rkey)") ?? image,
            imageURL: image,
            moreImageURLs: Array(post.embed?.allImages.dropFirst() ?? [])
        )
    }
}
