import SwiftUI
import WidgetKit

/// Control Center, Lock Screen and Action Button controls.
@main
struct WildcatVerifyControls: WidgetBundle {
    var body: some Widget {
        CheckCopiedLinkControl()
        CheckPostControl()
    }
}
