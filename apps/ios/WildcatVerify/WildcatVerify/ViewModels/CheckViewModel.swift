import Observation
import PhotosUI
import SwiftUI

/// Drives the Check tab: link and photo input, analysis, and pushed results.
@MainActor
@Observable
final class CheckViewModel {
    enum Phase: Equatable {
        case input
        case analyzing
    }

    var inputURL = ""
    var photoSelection: PhotosPickerItem? {
        didSet { if let photoSelection { analyzePhoto(photoSelection) } }
    }
    /// Results (fresh or recent) pushed on the Check tab's stack.
    var path: [VerificationCase] = []
    var isShowingError = false
    private(set) var phase: Phase = .input
    private(set) var errorMessage = ""
    /// Preview of what is being analyzed, shown in the loading state.
    private(set) var analyzingImage: UIImage?
    /// A link was copied since the app last offered one: show "Check the
    /// link you copied".
    private(set) var offersCopiedLink = false

    var canCheckPost: Bool {
        !inputURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && phase != .analyzing
    }


    private let history: HistoryStore
    private let pipeline: CheckPipeline
    private let clipboard: ClipboardProbe
    private var task: Task<Void, Never>?
    /// Clipboard contents already offered, used or dismissed.
    private var handledChangeCount: Int?

    init(
        history: HistoryStore,
        bluesky: any BlueskyFetching,
        classifier: any ImageClassifying,
        images: ImageRepository = .shared,
        clipboard: ClipboardProbe = .system
    ) {
        self.history = history
        self.clipboard = clipboard
        self.pipeline = CheckPipeline(bluesky: bluesky, classifier: classifier, images: images)
    }

    // MARK: Intents

    func checkPost() {
        guard canCheckPost else { return }
        let link = inputURL
        run {
            try await self.pipeline.checkPost(link: link) { self.analyzingImage = $0 }
        }
    }

    func analyzePhoto(_ item: PhotosPickerItem) {
        run {
            guard let data = try await item.loadTransferable(type: Data.self) else {
                throw CheckError.unreadablePhoto
            }
            return try await self.pipeline.checkImage(data: data) { self.analyzingImage = $0 }
        }
    }

    /// Checks the area the user boxed in a screenshot from Siri or Shortcuts.
    func checkScreenshotArea(_ image: UIImage) {
        run {
            try await self.pipeline.checkImage(image, title: VerificationCase.screenshotTitle) { self.analyzingImage = $0 }
        }
    }

    /// On open: offer the copied link if something new looks like a link.
    func refreshCopiedLinkOffer() async {
        let count = clipboard.changeCount()
        guard count != handledChangeCount, phase == .input, path.isEmpty else {
            offersCopiedLink = false
            return
        }
        offersCopiedLink = await clipboard.hasProbableLink()
    }

    func dismissCopiedLinkOffer() {
        handledChangeCount = clipboard.changeCount()
        offersCopiedLink = false
    }

    /// The user pasted (via the offer or the field's Paste button). A Bluesky
    /// post link is checked straight away; anything else just fills the field.
    func checkPasted(_ text: String, explainIfNotBluesky: Bool = false) {
        handledChangeCount = clipboard.changeCount()
        offersCopiedLink = false
        guard let link = ShareInput.blueskyLink(in: text) else {
            inputURL = text.trimmingCharacters(in: .whitespacesAndNewlines)
            if explainIfNotBluesky {
                errorMessage = "The copied link isn't a Bluesky post. In Bluesky, tap Share on a post, then Copy Link."
                isShowingError = true
            }
            return
        }
        inputURL = link
        checkPost()
    }

    /// Control Center's Check Copied Link: reads the clipboard (iOS asks
    /// first) and checks the Bluesky link on it.
    func checkCopiedLink(from pasteboardText: String? = UIPasteboard.general.string) {
        guard let text = pasteboardText, let link = ShareInput.blueskyLink(in: text) else {
            errorMessage = "There's no Bluesky post link on your clipboard. In Bluesky, tap Share on a post, then Copy Link."
            isShowingError = true
            return
        }
        inputURL = link
        checkPost()
    }

    /// Siri's copied-link check: the same pipeline and a My Checks entry, but
    /// the Check tab is left as it was.
    func checkInBackground(link: String, onImage: (UIImage) -> Void = { _ in }) async throws -> VerificationCase {
        let item = try await pipeline.checkPost(link: link, onImage: onImage)
        history.record(item)
        return item
    }

    /// Returns to an empty form, cancelling any analysis in flight.
    func reset() {
        cancelAnalysis()
        inputURL = ""
        isShowingError = false
        path.removeAll()
    }

    func cancelAnalysis() {
        task?.cancel()
        task = nil
        analyzingImage = nil
        photoSelection = nil
        phase = .input
    }

    func open(_ item: VerificationCase) {
        path.append(item)
    }

    // MARK: Private

    private func run(_ work: @escaping @MainActor () async throws -> VerificationCase) {
        task?.cancel()
        isShowingError = false
        analyzingImage = nil
        phase = .analyzing
        AccessibilityNotification.Announcement("Checking image").post()

        task = Task {
            do {
                let item = try await work()
                try Task.checkCancellation()
                history.record(item)
                inputURL = ""
                photoSelection = nil
                phase = .input
                path.append(item)
                AccessibilityNotification.Announcement(
                    "\(item.verdict.label), \(item.confidencePercentage) percent confidence"
                ).post()
            } catch {
                // A cancelled task was superseded by the user (Cancel, a new
                // check, or Check Another). Whatever they did owns the state now.
                guard !Task.isCancelled, !(error is CancellationError) else { return }
                errorMessage = (error as? LocalizedError)?.errorDescription
                    ?? "Something went wrong checking that image. Please try again."
                photoSelection = nil
                phase = .input
                isShowingError = true
            }
        }
    }
}
