import SwiftUI

/// Brand bar for the Check page: logo, wordmark and the About button.
struct CheckHeader: View {
    let onShowAbout: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            LogoTile(scale: Metrics.headerLogo / Metrics.logo)
                // The mark stays legible without crowding out the wordmark.
                .dynamicTypeSize(...DynamicTypeSize.xxxLarge)
            Text("Look Again")
                .font(.title3)
                .bold()
                .accessibilityAddTraits(.isHeader)
            Spacer()
            Button("About Look Again", systemImage: "questionmark.circle", action: onShowAbout)
                .labelStyle(.iconOnly)
                .font(.title3)
                .foregroundStyle(.secondary)
                .frame(width: 44, height: 44)
                .background(Color(.secondarySystemGroupedBackground), in: .circle)
                .overlay {
                    Circle().strokeBorder(Color(.separator), lineWidth: 0.5)
                }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 8)
        .background(.bar)
        .overlay(alignment: .bottom) {
            Divider()
        }
    }
}

#Preview {
    CheckHeader(onShowAbout: {})
}
