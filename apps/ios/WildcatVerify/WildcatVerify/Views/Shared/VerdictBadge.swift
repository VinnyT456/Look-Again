import SwiftUI

/// Compact verdict marker for list rows. Icon plus word, so it never relies on
/// colour alone.
struct VerdictBadge: View {
    let verdict: VerdictType

    var body: some View {
        Label(verdict.shortLabel, systemImage: verdict.icon)
            .labelStyle(.compact)
            .font(.caption)
            .bold()
            .foregroundStyle(verdict.textColor)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(verdict.background, in: .capsule)
            .accessibilityLabel(verdict.label)
    }
}

#Preview {
    VStack {
        ForEach(VerdictType.allCases, id: \.self) { VerdictBadge(verdict: $0) }
    }
}
