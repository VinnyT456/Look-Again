import Foundation

/// wildcatverify:// links the app answers, used by the Control Center and
/// Lock Screen controls. Only these fixed actions are accepted; nothing in a
/// link is trusted as data.
enum AppDeepLink: String, CaseIterable, Sendable {
    /// Open the Check tab, ready for a link or photo.
    case check
    /// Open the Check tab and check the Bluesky link on the clipboard.
    case checkCopiedLink = "check-copied-link"

    static let scheme = "wildcatverify"

    var url: URL {
        URL(string: "\(Self.scheme)://\(rawValue)") ?? URL(fileURLWithPath: "/")
    }

    init?(url: URL) {
        guard url.scheme?.lowercased() == Self.scheme, let host = url.host()?.lowercased() else { return nil }
        self.init(rawValue: host)
    }
}
