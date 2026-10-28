import Foundation
import Observation

/// Why automatic Feed checks aren't running right now.
enum AutoCheckPause: Equatable, Sendable {
    /// The user turned the setting off.
    case off
    case lowPower
    case lowData

    /// Shown above the Feed, so a pause never looks like a broken feature.
    var explanation: String? {
        switch self {
        case .off: nil
        case .lowPower: "Automatic checks are paused in Low Power Mode. Tap any post to check it."
        case .lowData: "Automatic checks are paused in Low Data Mode. Tap any post to check it."
        }
    }
}

/// Checks Feed posts on its own as they scroll into view, one at a time, so a
/// verdict badge is there before anyone taps. Runs on device; results stay in
/// memory and aren't added to My Checks unless the post is opened.
@MainActor
@Observable
final class FeedAutoChecker {
    private(set) var verdicts: [String: FeedVerdict] = [:]

    private let classifier: any ImageClassifying
    private let images: ImageRepository
    /// Nil when checks may run right now.
    private let currentPause: @MainActor () -> AutoCheckPause?
    /// Posts on screen, in the order they appeared. When a pause ends these
    /// are checked, so joining Wi-Fi or leaving Low Power Mode fills in the
    /// badges without scrolling.
    private var visible: [FeedPost] = []
    private var queue: [FeedPost] = []
    private var worker: Task<Void, Never>?

    init(
        classifier: any ImageClassifying,
        images: ImageRepository = .shared,
        pause: @escaping @MainActor () -> AutoCheckPause?
    ) {
        self.classifier = classifier
        self.images = images
        self.currentPause = pause
    }

    var pause: AutoCheckPause? { currentPause() }

    /// A post scrolled into view.
    func request(_ post: FeedPost) {
        if !visible.contains(where: { $0.id == post.id }) { visible.append(post) }
        enqueue(post)
    }

    /// A post scrolled away before its turn.
    func cancel(_ post: FeedPost) {
        visible.removeAll { $0.id == post.id }
        queue.removeAll { $0.id == post.id }
    }

    /// Conditions changed (network, Low Power Mode, the setting): check what's
    /// on screen if checks are allowed now, including ones that failed before.
    func resume() {
        for post in visible { enqueue(post) }
    }

    private func enqueue(_ post: FeedPost) {
        guard currentPause() == nil,
              verdicts[post.id] == nil || verdicts[post.id] == .failed,
              !queue.contains(where: { $0.id == post.id })
        else { return }
        queue.append(post)
        startIfIdle()
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
        // A pause leaves the posts in `visible`; `resume()` brings them back.
        guard currentPause() == nil, !queue.isEmpty else {
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
