import SwiftUI

/// Fades a section up into place the first time it appears, delayed by its
/// position so a screen assembles top to bottom. Reduce Motion: fade only.
struct StaggeredAppear: ViewModifier {
    let index: Int

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isShown = false

    func body(content: Content) -> some View {
        content
            .opacity(isShown ? 1 : 0)
            .offset(y: isShown || reduceMotion ? 0 : 14)
            .onAppear(perform: reveal)
    }

    private func reveal() {
        guard !isShown else { return }
        withAnimation(Motion.enter.delay(Double(index) * Motion.stagger)) {
            isShown = true
        }
    }
}

extension View {
    func staggeredAppear(_ index: Int) -> some View {
        modifier(StaggeredAppear(index: index))
    }
}
