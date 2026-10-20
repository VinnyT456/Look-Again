import Observation
import SwiftUI

/// One Look Again round: a balanced draw of cases, the user's picks, and a score.
@MainActor
@Observable
final class PracticeViewModel {
    enum Phase: Equatable {
        /// Waiting for the user to pick an answer.
        case answering
        /// The user picked; showing whether it was right and why.
        case revealed(picked: PracticeAnswer)
        /// Every question in the round is done.
        case finished
    }

    static let roundLength = 8

    private(set) var round: [PracticeQuestion] = []
    private(set) var index = 0
    private(set) var score = 0
    private(set) var phase: Phase = .answering
    /// Bumped on each answer, so views can play feedback once per pick.
    private(set) var answerCount = 0
    private(set) var lastAnswerWasCorrect = false
    /// What the user picked for each answered question, in round order.
    private(set) var picks: [PracticeAnswer] = []
    /// Called once with the score when a round finishes.
    var onFinish: ((Int) -> Void)?

    private let bank: [PracticeQuestion]
    private let shuffle: Bool
    /// Cases from the previous round, skipped when the bank has enough others.
    private var lastRoundIDs: Set<String> = []

    /// - Parameter shuffle: false draws in bank order, for tests.
    init(questions: [PracticeQuestion], shuffle: Bool = true) {
        self.bank = questions
        self.shuffle = shuffle
        restart()
    }

    var current: PracticeQuestion? {
        round.indices.contains(index) ? round[index] : nil
    }

    var progressText: String {
        "\(min(index + 1, round.count)) of \(round.count)"
    }

    var isLastQuestion: Bool { index >= round.count - 1 }

    /// A round has started but isn't finished.
    var isInProgress: Bool {
        phase != .finished && (!picks.isEmpty || index > 0)
    }

    /// Questions answered wrong, with what the user picked.
    var misses: [(question: PracticeQuestion, picked: PracticeAnswer)] {
        zip(round, picks).filter { $0.answer != $1 }.map { ($0, $1) }
    }

    /// The answer the user missed most this round, to point them at the right
    /// clues. Nil when nothing was missed or misses are tied across answers.
    var mostMissed: PracticeAnswer? {
        let counts = Dictionary(grouping: misses.map(\.question.answer), by: { $0 }).mapValues(\.count)
        guard let top = counts.values.max(), counts.values.filter({ $0 == top }).count == 1 else { return nil }
        return counts.first { $0.value == top }?.key
    }

    /// The answer type the user got all of, if any, to lead the summary with
    /// something they did well.
    var strongest: PracticeAnswer? {
        let answered = zip(round, picks)
        return PracticeAnswer.allCases.first { answer in
            let cases = answered.filter { $0.0.answer == answer }
            return !cases.isEmpty && cases.allSatisfy { $0.0.answer == $0.1 }
        }
    }

    /// End-of-round headline.
    var scoreLine: String { "\(score) of \(round.count) right" }

    /// What to take from the round.
    var summary: String {
        if misses.isEmpty { return "Every one right." }
        var parts: [String] = []
        if let strongest { parts.append("You caught every \(strongest.singularNoun).") }
        if let mostMissed {
            parts.append("Most misses were \(mostMissed.pluralNoun).")
        } else {
            parts.append("Your misses were spread across answer types.")
        }
        return parts.joined(separator: " ")
    }

    func select(_ answer: PracticeAnswer) {
        guard phase == .answering, let current else { return }
        lastAnswerWasCorrect = answer == current.answer
        if lastAnswerWasCorrect { score += 1 }
        picks.append(answer)
        answerCount += 1
        phase = .revealed(picked: answer)
    }

    func next() {
        guard case .revealed = phase else { return }
        if isLastQuestion {
            phase = .finished
            onFinish?(score)
        } else {
            index += 1
            phase = .answering
        }
    }

    func restart() {
        round = Self.draw(from: bank, avoiding: lastRoundIDs, shuffle: shuffle)
        lastRoundIDs = Set(round.map(\.id))
        index = 0
        score = 0
        picks = []
        phase = round.isEmpty ? .finished : .answering
    }

    /// An even mix of answers (two of each for a round of eight), preferring
    /// cases not in `avoiding`, topped up from the rest when a type runs short.
    static func draw(from bank: [PracticeQuestion], avoiding: Set<String>, shuffle: Bool) -> [PracticeQuestion] {
        let perAnswer = roundLength / PracticeAnswer.allCases.count
        var picked: [PracticeQuestion] = []
        for answer in PracticeAnswer.allCases {
            let pool = bank.filter { $0.answer == answer }
            let fresh = pool.filter { !avoiding.contains($0.id) }
            let stale = pool.filter { avoiding.contains($0.id) }
            let ordered = (shuffle ? fresh.shuffled() : fresh) + (shuffle ? stale.shuffled() : stale)
            picked += ordered.prefix(perAnswer)
        }
        if picked.count < roundLength {
            let pickedIDs = Set(picked.map(\.id))
            let rest = bank.filter { !pickedIDs.contains($0.id) }
            picked += (shuffle ? rest.shuffled() : rest).prefix(roundLength - picked.count)
        }
        return shuffle ? picked.shuffled() : picked
    }
}
