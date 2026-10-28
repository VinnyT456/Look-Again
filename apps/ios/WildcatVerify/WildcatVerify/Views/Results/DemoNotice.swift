import SwiftUI

/// Shown on every result that did not come from the trained model, so a
/// placeholder verdict is never mistaken for a real analysis.
struct DemoNotice: View {
    var body: some View {
        Label {
            Text("Demo result. This verdict isn't from the Look Again detection model yet, so don't rely on it.")
                .font(.subheadline)
        } icon: {
            Image(systemName: "flask")
                .foregroundStyle(.tint)
        }
    }
}
