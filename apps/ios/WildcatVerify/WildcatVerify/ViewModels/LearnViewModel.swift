import Observation

/// The Learn tab: the Look Again round (played in place) and the clue guide.
@MainActor
@Observable
final class LearnViewModel {
    var path: [LearnRoute] = []
    let clueGroups: [ClueGroup]
    let practice: PracticeViewModel

    /// Where the best score is kept; nil keeps it in memory only (tests, previews).
    private let settings: SettingsStore?
    private var sessionBest = 0
    /// The round that just ended beat the previous best.
    private(set) var lastRoundWasNewBest = false

    init(
        settings: SettingsStore? = nil,
        clueGroups: [ClueGroup] = ClueGroup.guide,
        questions: [PracticeQuestion] = PracticeBank.questions
    ) {
        self.settings = settings
        self.clueGroups = clueGroups
        self.practice = PracticeViewModel(questions: questions)
        practice.onFinish = { [weak self] score in self?.recordScore(score) }
    }

    var clueCount: Int { clueGroups.reduce(0) { $0 + $1.clues.count } }

    /// Best finished-round score, or nil before the first round ends.
    var bestScore: Int? {
        let best = settings?.bestPracticeScore ?? sessionBest
        return best > 0 ? best : nil
    }

    /// Starts a fresh round in place.
    func startPractice() {
        practice.restart()
    }

    func openGuide(_ group: ClueGroup) {
        path.append(.clueGuide(group.id))
    }

    /// After a round: the guide on what was missed most (or the first group).
    func openGuideForMisses() {
        // On a tie, the first miss decides; never the type the player aced.
        let missed = practice.mostMissed ?? practice.misses.first?.question.answer
        let group = missed.flatMap { ClueGroup.group(for: $0.guideFocus, in: clueGroups) } ?? clueGroups.first
        if let group { openGuide(group) }
    }

    private func recordScore(_ score: Int) {
        // The first finished round sets a best; it isn't "new" yet.
        lastRoundWasNewBest = bestScore.map { score > $0 } ?? false
        if let settings {
            settings.bestPracticeScore = max(settings.bestPracticeScore, score)
        } else {
            sessionBest = max(sessionBest, score)
        }
    }
}
