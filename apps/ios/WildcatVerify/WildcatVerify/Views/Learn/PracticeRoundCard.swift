import SwiftUI

/// Look Again on the Learn home. The whole round happens here: read the
/// post, answer, see why, next.
struct PracticeRoundCard: View {
    let viewModel: LearnViewModel

    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    static let nextButtonID = "practiceNext"
    static let answersID = "practiceAnswers"

    private var practice: PracticeViewModel { viewModel.practice }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            header
            content
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: Metrics.cardRadius))
        .animation(reduceMotion ? nil : .smooth(duration: 0.25), value: practice.phase)
    }

    private var header: some View {
        let layout = dynamicTypeSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: 4))
            : AnyLayout(HStackLayout(alignment: .firstTextBaseline))
        return layout {
            Text("Look Again")
                .font(.title2)
                .bold()
                .accessibilityAddTraits(.isHeader)
            if !dynamicTypeSize.isAccessibilitySize { Spacer() }
            if practice.isInProgress {
                Text(practice.progressText)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .accessibilityHidden(true)
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        if practice.phase == .finished {
            PracticeSummaryView(
                viewModel: practice,
                bestScore: viewModel.bestScore,
                isNewBest: viewModel.lastRoundWasNewBest,
                onReviewClues: viewModel.openGuideForMisses
            )
        } else if let question = practice.current {
            if practice.isInProgress {
                RoundDots(viewModel: practice)
            } else {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Is each post real, edited, made by AI, or a real photo with a false story? \(PracticeViewModel.roundLength) posts, about two minutes.")
                        .foregroundStyle(.secondary)
                    DisclosureGroup("What the answers mean") {
                        VStack(alignment: .leading, spacing: 6) {
                            ForEach(PracticeAnswer.allCases, id: \.self) { answer in
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(answer.label).bold()
                                    Text(answer.definition).foregroundStyle(.secondary)
                                }
                                .font(.subheadline)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .accessibilityElement(children: .combine)
                            }
                        }
                        .padding(.top, 6)
                    }
                    .font(.subheadline)
                }
            }

            PracticePostCard(question: question, showsHotspots: picked != nil)
                .id(question.id)
                .transition(.opacity)

            PracticeAnswerButtons(picked: picked, answer: question.answer, onSelect: practice.select)
                .id(Self.answersID)

            if let picked {
                PracticeFeedback(question: question, picked: picked, answerCount: practice.answerCount)
                    .transition(.opacity)
                Button(practice.isLastQuestion ? "See Results" : "Next Post",
                       systemImage: "arrow.right",
                       action: next)
                    .buttonStyle(.primary)
                    .id(Self.nextButtonID)
            }
        }
    }

    private var picked: PracticeAnswer? {
        if case .revealed(let picked) = practice.phase { return picked }
        return nil
    }

    private func next() {
        withAnimation(reduceMotion ? nil : .smooth(duration: 0.25)) {
            practice.next()
        }
    }
}
