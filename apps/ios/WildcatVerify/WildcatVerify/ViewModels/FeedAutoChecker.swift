import Foundation
import Observation

/// Checks Feed posts on its own as they scroll into view, one at a time, so a
/// verdict badge is there before anyone taps. Runs on device; results stay in
/// memory and aren't added to My Checks unless the post is opened.
@MainActor
@Observable
final class FeedAutoChecker {
    private(set) var verdicts: [String: FeedVerdict] = [:]

    private let classifier: any ImageClassifying
    private let images: ImageRepository
    /// Whether checks may run right now (setting on, not Low Power Mode, not
    /// on a limited network).
    private let isAllowed: @MainActor () -> Bool
    private var queue: [FeedPost] = []
    private var worker: Task<Void, Never>?

    init(
        classifier: any ImageClassifying,
        images: ImageRepository = .shared,
        isAllowed: @escaping @MainActor () -> Bool
    ) {
        self.classifier = classifier
        self.images = images
        self.isAllowed = isAllowed
    }

    /// A post scrolled into view.
    func request(_ post: FeedPost) {
        guard isAllowed(), verdicts[post.id] == nil, !queue.contains(where: { $0.id == post.id }) else { return }
        queue.append(post)
        startIfIdle()
    }

    /// A post scrolled away before its turn.
    func cancel(_ post: FeedPost) {
        queue.removeAll { $0.id == post.id }
    }

    private func startIfIdle() {
        guard worker == nil else { return }
        worker = Task {
            while let post = nextPost() {
                verdicts[post.id] = .checking
                verdicts[post.id] = await check(post)
            }
            worker = nil
        }
    }

    private func nextPost() -> FeedPost? {
        guard isAllowed(), !queue.isEmpty else {
            queue.removeAll()
            return nil
        }
        return queue.removeFirst()
    }

    private func check(_ post: FeedPost) async -> FeedVerdict {
        do {
            let image = try await images.image(for: post.thumbURL)
            let result = try await classifier.classify(image)
            return .done(
                verdict: result.verdict,
                confidence: CheckPipeline.displayConfidence(result.confidence),
                isDemo: classifier.isDemo
            )
        } catch {
            return .failed
        }
    }
}
