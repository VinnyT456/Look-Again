import SwiftUI

/// After answering: right or not, what to look for, then why.
struct PracticeFeedback: View {
    let question: PracticeQuestion
    let picked: PracticeAnswer
    /// Changes per answer so the mascot reacts each time.
    let answerCount: Int
    /// False in the review sheet: VoiceOver starts at the post, and the
    /// mascot doesn't react to an old miss.
    var isLive = true

    @AccessibilityFocusState private var headlineFocused: Bool

    private var isCorrect: Bool { picked == question.answer }

    private var headline: String {
        isCorrect ? "Yes, it's \(question.answer.phrase)." : "Not quite. It's \(question.answer.phrase)."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 12) {
                MascotReaction(isCorrect: isCorrect, trigger: answerCount, animates: isLive)
                Text(headline)
                    .font(.title3)
                    .bold()
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityAddTraits(.isHeader)
                    .accessibilityFocused($headlineFocused)
            }

            VStack(alignment: .leading, spacing: 6) {
                ForEach(question.clues, id: \.self) { clue in
                    Text(clue)
                        .font(.callout)
                        .bold()
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel("What to look for: \(question.clues.joined(separator: ". "))")

            Text(question.explanation)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .task(id: answerCount) {
            // Land VoiceOver on the result instead of a locked answer button.
            guard isLive else { return }
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            headlineFocused = true
        }
    }
}
