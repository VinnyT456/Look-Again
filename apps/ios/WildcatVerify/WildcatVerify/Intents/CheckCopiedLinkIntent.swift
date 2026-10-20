import AppIntents
import SwiftUI

/// "Check the copied link with WildcatVerify": reads a Bluesky link from the
/// clipboard (iOS asks first), checks the post's photo without opening the
/// app, and answers with a card.
struct CheckCopiedLinkIntent: AppIntent {
    static let title: LocalizedStringResource = "Check Copied Link"
    static var description: IntentDescription {
        IntentDescription(
            "Checks the photo in the Bluesky post link you copied, and tells you whether it looks real or AI. The clipboard is read only when you run this.",
            categoryName: "Checking"
        )
    }

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog & ShowsSnippetView {
        guard let text = UIPasteboard.general.string, let link = ShareInput.blueskyLink(in: text) else {
            throw SiriCheckError.noCopiedLink
        }
        var thumbnail: UIImage?
        let item: VerificationCase
        do {
            item = try await AppViewModel.live.check.checkInBackground(link: link) { image in
                thumbnail = image.preparingThumbnail(of: CheckSnippetView.thumbnailPixels(for: image.size))
            }
        } catch {
            throw SiriCheckError.wrapping(error)
        }
        return .result(
            dialog: "\(item.verdict.label), \(item.confidencePercentage) percent confidence.",
            view: CheckSnippetView(item: item, thumbnail: thumbnail)
        )
    }
}
