import SwiftUI

/// Full-width Northwestern Purple button; grey while disabled.
struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var isEnabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .labelStyle(TrailingIconLabelStyle())
            .font(.headline)
            .foregroundStyle(isEnabled ? .white : .secondary)
            .multilineTextAlignment(.center)
            .padding(.horizontal)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity, minHeight: Metrics.controlHeight)
            .background(background(isPressed: configuration.isPressed), in: .rect(cornerRadius: Metrics.fieldRadius))
            .scaleEffect(configuration.isPressed && !reduceMotion ? 0.98 : 1)
            .animation(.snappy(duration: 0.15), value: configuration.isPressed)
    }

    private func background(isPressed: Bool) -> Color {
        guard isEnabled else { return Color(.tertiarySystemFill) }
        return isPressed ? .northwesternPurpleDark : .northwesternPurple
    }
}

extension ButtonStyle where Self == PrimaryButtonStyle {
    static var primary: PrimaryButtonStyle { PrimaryButtonStyle() }
}
