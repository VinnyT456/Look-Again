import UIKit

/// Asks whether the clipboard holds something that looks like a link,
/// without reading it, so iOS shows no paste prompt. Reading happens only
/// through the system Paste button the user taps.
struct ClipboardProbe: Sendable {
    /// Changes whenever anything is copied.
    var changeCount: @MainActor @Sendable () -> Int
    var hasProbableLink: @MainActor @Sendable () async -> Bool

    static let system = ClipboardProbe(
        changeCount: { UIPasteboard.general.changeCount },
        hasProbableLink: {
            let board = UIPasteboard.general
            guard board.hasStrings || board.hasURLs else { return false }
            let found = try? await board.detectedPatterns(for: [\.probableWebURL])
            return found?.contains(\.probableWebURL) ?? false
        }
    )
}
