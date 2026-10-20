import SwiftUI

/// The four answers, as plain words until you pick so none looks like the
/// right one. Afterwards the correct answer is marked in purple and a wrong
/// pick gets a grey cross.
struct PracticeAnswerButtons: View {
    /// Nil while answering; the user's pick once revealed.
    let picked: PracticeAnswer?
    let answer: PracticeAnswer
    let onSelect: (PracticeAnswer) -> Void

    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        let columns = dynamicTypeSize.isAccessibilitySize ? 1 : 2
        let rows = stride(from: 0, to: PracticeAnswer.allCases.count, by: columns).map {
            Array(PracticeAnswer.allCases[$0..<min($0 + columns, PracticeAnswer.allCases.count)])
        }
        Grid(horizontalSpacing: 8, verticalSpacing: 8) {
            ForEach(rows, id: \.self) { row in
                GridRow {
                    ForEach(row, id: \.self, content: button)
                }
            }
        }
    }

    private func button(_ choice: PracticeAnswer) -> some View {
        let state = state(of: choice)
        return Button {
            onSelect(choice)
        } label: {
            HStack(spacing: 6) {
                if let symbol = state.symbol {
                    Image(systemName: symbol)
                        .foregroundStyle(state == .correct ? AnyShapeStyle(.tint) : AnyShapeStyle(.secondary))
                }
                Text(choice.label)
            }
            .font(.headline)
            .foregroundStyle(state == .faded ? AnyShapeStyle(.secondary) : AnyShapeStyle(.primary))
            .multilineTextAlignment(.center)
            .padding(.horizontal, 12)
            .frame(maxWidth: .infinity, minHeight: Metrics.controlHeight)
            .background(state == .correct ? AnyShapeStyle(.tint.opacity(0.12)) : AnyShapeStyle(Color(.tertiarySystemFill)),
                        in: .rect(cornerRadius: Metrics.fieldRadius))
            .overlay {
                RoundedRectangle(cornerRadius: Metrics.fieldRadius)
                    .strokeBorder(state == .correct ? AnyShapeStyle(.tint) : AnyShapeStyle(.clear), lineWidth: 2)
            }
            .contentShape(.rect(cornerRadius: Metrics.fieldRadius))
        }
        .buttonStyle(.pressableCard)
        // Locked after answering without reading every button as "dimmed".
        .allowsHitTesting(picked == nil)
        .accessibilityLabel(choice.label)
        .accessibilityValue(accessibilityValue(for: choice))
        .accessibilityHint(picked == nil ? choice.definition : "")
        .accessibilityIdentifier("answer-\(choice.rawValue)")
        // Once revealed these are a record of the answer, not controls.
        .accessibilityRemoveTraits(picked == nil ? [] : .isButton)
        .accessibilityAddTraits(picked == nil ? [] : .isStaticText)
    }

    private enum AnswerState {
        case idle, correct, wrongPick, faded

        var symbol: String? {
            switch self {
            case .correct: "checkmark"
            case .wrongPick: "xmark"
            default: nil
            }
        }
    }

    private func state(of choice: PracticeAnswer) -> AnswerState {
        guard let picked else { return .idle }
        if choice == answer { return .correct }
        return choice == picked ? .wrongPick : .faded
    }

    private func accessibilityValue(for choice: PracticeAnswer) -> String {
        guard let picked else { return "" }
        switch (choice == picked, choice == answer) {
        case (true, true): return "Your answer, correct"
        case (true, false): return "Your answer"
        case (false, true): return "Correct answer"
        default: return ""
        }
    }
}
