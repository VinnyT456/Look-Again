import SwiftUI

struct CheckLinkTitle: View {
    var body: some View {
        Label {
            Text("Bluesky Post Link")
                .font(.headline)
        } icon: {
            Image(systemName: "link")
                .foregroundStyle(.tint)
        }
        .accessibilityAddTraits(.isHeader)
    }
}
