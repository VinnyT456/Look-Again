import SwiftUI

/// The clue groups on the Learn home, leading into the Clue Guide.
struct ClueIndex: View {
    let groups: [ClueGroup]

    @ScaledMetric(relativeTo: .body) private var iconWidth = 28.0

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Clue Guide")
                .font(.title3)
                .bold()
                .accessibilityAddTraits(.isHeader)
                .padding(.horizontal, 4)

            VStack(spacing: 0) {
                ForEach(groups) { group in
                    NavigationLink(value: LearnRoute.clueGuide(group.id)) {
                        row(group)
                    }
                    .buttonStyle(.plain)
                    .accessibilityIdentifier("clueGroup-\(group.shortTitle)")
                    if group.id != groups.last?.id {
                        Divider().padding(.leading, iconWidth + 28)
                    }
                }
            }
            .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: Metrics.cardRadius))
        }
    }

    private func row(_ group: ClueGroup) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Image(systemName: group.icon)
                .foregroundStyle(.tint)
                .frame(width: iconWidth)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 3) {
                Text(group.title)
                    .font(.headline)
                Text(group.summary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.leading)
            }
            Spacer(minLength: 8)
            Text(group.clues.count, format: .number)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .accessibilityLabel("\(group.clues.count) clues")
            Image(systemName: "chevron.forward")
                .font(.footnote.bold())
                .foregroundStyle(.tertiary)
                .accessibilityHidden(true)
        }
        .padding(16)
        .contentShape(.rect)
    }
}
