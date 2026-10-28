import SwiftUI

/// Top-level screen chrome: a large title that collapses on scroll, the logo
/// leading and the About button trailing.
struct BrandToolbar: ViewModifier {
    let title: String
    let onShowAbout: () -> Void

    func body(content: Content) -> some View {
        content
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                LogoToolbarItem()
                ToolbarItem(placement: .topBarTrailing) {
                    Button("About Look Again", systemImage: "questionmark.circle", action: onShowAbout)
                }
            }
    }
}

extension View {
    func brandToolbar(_ title: String, onShowAbout: @escaping () -> Void) -> some View {
        modifier(BrandToolbar(title: title, onShowAbout: onShowAbout))
    }
}
