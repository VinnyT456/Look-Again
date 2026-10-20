import SwiftUI

/// One mark per question: filled for right, hollow for wrong, and a wider
/// bar for the current one, so none of it depends on color alone.
struct RoundDots: View {
    let viewModel: PracticeViewModel

    @ScaledMetric(relativeTo: .body) private var size = 10.0

    var body: some View {
        HStack(spacing: size * 0.6) {
            ForEach(viewModel.round.indices, id: \.self) { index in
                dot(at: index)
                    .frame(width: isCurrent(index) ? size * 2 : size, height: size)
            }
        }
        .accessibilityElement()
        .accessibilityLabel(accessibilityText)
    }

    @ViewBuilder
    private func dot(at index: Int) -> some View {
        if index < viewModel.picks.count {
            if viewModel.picks[index] == viewModel.round[index].answer {
                Circle().fill(.tint)
            } else {
                Circle()
                    .strokeBorder(.secondary, lineWidth: 1.5)
            }
        } else if isCurrent(index) {
            Capsule().fill(.tint)
        } else {
            Circle().fill(Color(.tertiarySystemFill))
        }
    }

    private func isCurrent(_ index: Int) -> Bool {
        index == viewModel.index && index >= viewModel.picks.count && viewModel.phase != .finished
    }

    private var accessibilityText: String {
        let total = viewModel.round.count
        if viewModel.phase == .finished {
            return "\(viewModel.score) of \(total) right"
        }
        return "Question \(min(viewModel.index + 1, total)) of \(total), \(viewModel.score) right so far"
    }
}
