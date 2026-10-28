import Foundation

/// What Siri says when a check can't run.
enum SiriCheckError: Error, CustomLocalizedStringResourceConvertible {
    case noCopiedLink
    case unreadableImage
    case failed(String)

    var localizedStringResource: LocalizedStringResource {
        switch self {
        case .noCopiedLink:
            "There's no Bluesky post link on your clipboard. In Bluesky, tap Share on a post, then Copy Link, and try again."
        case .unreadableImage:
            "Look Again couldn't read that image. Try taking the screenshot again."
        case .failed(let message):
            "\(message)"
        }
    }

    /// Keeps the app's own wording for Bluesky and detector errors.
    static func wrapping(_ error: any Error) -> SiriCheckError {
        if let error = error as? SiriCheckError { return error }
        return .failed((error as? LocalizedError)?.errorDescription
            ?? "Something went wrong checking that image. Please try again.")
    }
}
