import SwiftUI

/// One numbered step in Set Up Siri.
struct SetupStepRow: View {
    let number: Int
    let text: LocalizedStringKey

    @ScaledMetric(relativeTo: .body) private var badge = 26.0

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(number, format: .number)
                .font(.subheadline)
                .bold()
                .monospacedDigit()
                .foregroundStyle(.white)
                .frame(width: badge, height: badge)
                .background(.tint, in: .circle)
                .alignmentGuide(.firstTextBaseline) { $0[VerticalAlignment.center] + 5 }
            Text(text)
        }
        .accessibilityElement(children: .combine)
    }
}
