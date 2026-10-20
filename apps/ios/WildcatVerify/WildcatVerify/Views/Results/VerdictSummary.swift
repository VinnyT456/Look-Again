import SwiftUI

/// The verdict, how sure the model is, and the one-paragraph explanation.
struct VerdictSummary: View {
    let item: VerificationCase

    @ScaledMetric(relativeTo: .title2) private var tile = Metrics.verdictTile

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Image(systemName: item.verdict.icon)
                    .font(.title3)
                    .foregroundStyle(.white)
                    .frame(width: tile, height: tile)
                    .background(item.verdict.color, in: .rect(cornerRadius: Metrics.verdictTileRadius))
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 2) {
                    Text(item.verdict.label)
                        .font(.title2)
                        .bold()
                    Text("\(item.confidencePercentage)% confidence")
                        .font(.subheadline)
                        .monospacedDigit()
                }
                .foregroundStyle(item.verdict.textColor)
            }
            .accessibilityElement(children: .combine)
            .accessibilityAddTraits(.isHeader)

            Text(item.plainSummary)
                .font(.body)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    List {
        VerdictSummary(item: SampleData.monorail)
            .listRowBackground(VerdictType.ai.background)
    }
}
