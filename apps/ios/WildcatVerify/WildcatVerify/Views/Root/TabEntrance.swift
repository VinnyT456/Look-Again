import SwiftUI

/// Plays when a tab becomes selected: its content slides in from the side you
/// moved toward and fades up, so switching tabs keeps a sense of place.
/// Reduce Motion: a plain fade.
///
/// The slide is applied with `visualEffect`, which only changes how the view is
/// drawn. Using `.offset` here moved the layout of each tab's UIKit-backed
/// navigation view, which could leave the whole tab stuck off to one side.
struct TabEntrance: ViewModifier {
    let tab: AppTab
    let selection: AppTab

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var shift = 0.0
    @State private var fade = 1.0

    func body(content: Content) -> some View {
        content
            .visualEffect { [shift, fade] view, _ in
                view
                    .offset(x: shift)
                    .opacity(fade)
            }
            .onChange(of: selection) { old, new in
                guard new == tab, old != tab else { return }
                enter(from: old, to: new)
            }
    }

    private func enter(from old: AppTab, to new: AppTab) {
        let direction: Double = Self.index(of: new) > Self.index(of: old) ? 1 : -1
        var jump = Transaction()
        jump.disablesAnimations = true
        withTransaction(jump) {
            shift = reduceMotion ? 0 : direction * Motion.tabOffset
            fade = 0
        }
        // Next run loop, so the start position renders before animating home.
        Task { @MainActor in
            withAnimation(.snappy(duration: 0.32)) {
                shift = 0
                fade = 1
            }
        }
    }

    private static func index(of tab: AppTab) -> Int {
        AppTab.allCases.firstIndex(of: tab) ?? 0
    }
}

extension View {
    func tabEntrance(_ tab: AppTab, selection: AppTab) -> some View {
        modifier(TabEntrance(tab: tab, selection: selection))
    }
}
