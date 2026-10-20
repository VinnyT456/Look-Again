import SwiftUI

/// The logo in the leading slot of a top-level screen. It sits on its own tile,
/// so on iOS 26 it opts out of the shared Liquid Glass capsule.
struct LogoToolbarItem: ToolbarContent {
    var body: some ToolbarContent {
        if #available(iOS 26.0, *) {
            ToolbarItem(placement: .topBarLeading) {
                LogoTile()
            }
            .sharedBackgroundVisibility(.hidden)
        } else {
            ToolbarItem(placement: .topBarLeading) {
                LogoTile()
            }
        }
    }
}
