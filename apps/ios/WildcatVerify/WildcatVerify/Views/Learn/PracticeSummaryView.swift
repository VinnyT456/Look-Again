import SwiftUI

/// End of a round, inside the Look Again card: the score, Play Again,
/// what went well, and the misses to look at again.
struct PracticeSummaryView: View {
    let viewModel: PracticeViewModel
    let bestScore: Int?
    let isNewBest: Bool
    let onReviewClues: () -> Void

    @State private var showsAllMisses = false
    @State private var reviewing: PracticeQuestion?

    private static let missPreview = 3

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .center, spacing: 12) {
                MascotReaction(isCorrect: viewModel.score * 2 >= viewModel.round.count)
                VStack(alignment: .leading, spacing: 2) {
                    Text(viewModel.scoreLine)
                        .font(.title2)
                        .bold()
                        .accessibilityAddTraits(.isHeader)
                    if isNewBest {
                        Text("New best")
                            .font(.subheadline)
                            .bold()
                            .foregroundStyle(.tint)
                    } else if bestScore == viewModel.score, viewModel.score > 0 {
                        Text("Your best so far.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    } else if let bestScore {
                        Text("Your best is \(bestScore) of \(viewModel.round.count).")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            RoundDots(viewModel: viewModel)
                .accessibilityHidden(true)
            Text(viewModel.summary)
                .fixedSize(horizontal: false, vertical: true)

            Button("Play Again", systemImage: "arrow.counterclockwise", action: viewModel.restart)
                .buttonStyle(.primary)

            if !viewModel.misses.isEmpty {
                misses
            }

            if !viewModel.misses.isEmpty {
                Button(action: onReviewClues) {
                    Text(reviewTitle)
                        .frame(maxWidth: .infinity, minHeight: 44)
                        .contentShape(.rect)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .sheet(item: $reviewing) { question in
            PracticeReviewSheet(question: question, picked: pick(for: question))
        }
    }

    private var misses: some View {
        let all = viewModel.misses
        let shown = showsAllMisses || all.count <= Self.missPreview + 1 ? all : Array(all.prefix(Self.missPreview))
        return VStack(alignment: .leading, spacing: 4) {
            Text("Take another look")
                .font(.headline)
                .accessibilityAddTraits(.isHeader)
                .padding(.bottom, 4)
            ForEach(shown, id: \.question.id) { miss in
                Button {
                    reviewing = miss.question
                } label: {
                    HStack(alignment: .firstTextBaseline) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(miss.question.caption)
                                .foregroundStyle(.primary)
                                .lineLimit(2)
                            Text("You said \(miss.picked.inSentence). It's \(miss.question.answer.phrase).")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        .multilineTextAlignment(.leading)
                        Spacer(minLength: 8)
                        Image(systemName: "chevron.forward")
                            .font(.footnote.bold())
                            .foregroundStyle(.tertiary)
                            .accessibilityHidden(true)
                    }
                    .padding(.vertical, 8)
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
                .accessibilityHint("Shows the post again with the answer")
            }
            // Only collapse when it hides more than one row.
            if all.count > Self.missPreview + 1 && !showsAllMisses {
                Button {
                    showsAllMisses = true
                } label: {
                    Text("Show all \(all.count)")
                        .frame(minHeight: 44)
                        .contentShape(.rect)
                }
            }
        }
    }

    private func pick(for question: PracticeQuestion) -> PracticeAnswer {
        viewModel.misses.first { $0.question.id == question.id }?.picked ?? question.answer
    }

    private var reviewTitle: String {
        switch viewModel.mostMissed {
        case .ai: "Clues for AI images"
        case .edited: "Clues for edited photos"
        case .real, .misleading: "How to check a source"
        case nil: "Clues for what you missed"
        }
    }
}
