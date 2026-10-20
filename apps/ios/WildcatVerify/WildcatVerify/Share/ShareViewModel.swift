import Observation
import UIKit

/// Drives the share extension: read what was shared, check it, show the verdict.
@MainActor
@Observable
final class ShareViewModel {
    enum Phase: Equatable {
        case reading
        case analyzing
        case result(VerificationCase)
        case failed(String)
    }

    private(set) var phase: Phase = .reading
    private(set) var analyzingImage: UIImage?

    private let pipeline: CheckPipeline
    /// Called with each finished check, e.g. so the Feed can add it to My Checks.
    private let onResult: (@MainActor (VerificationCase) -> Void)?

    init(pipeline: CheckPipeline = CheckPipeline(), onResult: (@MainActor (VerificationCase) -> Void)? = nil) {
        self.pipeline = pipeline
        self.onResult = onResult
    }

    /// Entry point from the extension: the share sheet's attachments.
    func load(providers: [NSItemProvider]) async {
        guard let input = await ShareItemLoader.input(from: providers) else {
            fail(ShareError.unsupported)
            return
        }
        await check(input)
    }

    /// Checks one input. Separate from `load` so it can be tested without a share sheet.
    func check(_ input: ShareInput) async {
        phase = .analyzing
        analyzingImage = nil
        do {
            let item: VerificationCase = switch input {
            case .image(let data):
                try await pipeline.checkImage(data: data) { self.analyzingImage = $0 }
            case .link(let link):
                try await pipeline.checkPost(link: link) { self.analyzingImage = $0 }
            }
            phase = .result(item)
            onResult?(item)
            AccessibilityNotification.Announcement(
                "\(item.verdict.label), \(item.confidencePercentage) percent confidence"
            ).post()
        } catch is CancellationError {
            // The sheet was dismissed; nothing to show.
        } catch {
            fail(error)
        }
    }

    private func fail(_ error: any Error) {
        let message = (error as? LocalizedError)?.errorDescription
            ?? "Something went wrong checking that item. Please try again."
        phase = .failed(message)
        AccessibilityNotification.Announcement(message).post()
    }
}
