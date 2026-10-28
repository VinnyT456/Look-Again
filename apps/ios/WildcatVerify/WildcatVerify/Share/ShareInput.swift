import Foundation

/// What another app shared with Look Again, reduced to something checkable.
enum ShareInput: Equatable, Sendable {
    /// Raw image bytes (a photo or screenshot).
    case image(Data)
    /// A Bluesky post link.
    case link(String)

    /// Finds the first Bluesky post link in shared text, such as "Look at this
    /// https://bsky.app/profile/a/post/b". Returns nil when there isn't one.
    static func blueskyLink(in text: String) -> String? {
        guard let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) else {
            return nil
        }
        let range = NSRange(text.startIndex..., in: text)
        for match in detector.matches(in: text, range: range) {
            guard let url = match.url else { continue }
            let candidate = url.absoluteString
            if BlueskyService.parse(candidate) != nil { return candidate }
        }
        // Bare "bsky.app/profile/…" without a scheme isn't always detected as a link.
        return text
            .split(whereSeparator: \.isWhitespace)
            .map(String.init)
            .first { BlueskyService.parse($0) != nil }
    }
}
