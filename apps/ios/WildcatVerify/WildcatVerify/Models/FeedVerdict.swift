/// A quick, automatic check of a Feed post's first image, shown as a badge.
/// Opening the post runs the full check (every image, highlight, My Checks).
enum FeedVerdict: Equatable, Sendable {
    case checking
    case done(verdict: VerdictType, confidence: Int, isDemo: Bool)
    case failed
}
