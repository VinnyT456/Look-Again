import AppIntents
import SwiftUI
import WidgetKit

/// Opens the Check tab, ready for a link or photo.
struct CheckPostControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        StaticControlConfiguration(kind: "edu.northwestern.lookagain.WildcatVerify.checkPost") {
            ControlWidgetButton(action: OpenURLIntent(AppDeepLink.check.url)) {
                Label("Check a Post", systemImage: "checkmark.shield")
            }
        }
        .displayName("Check a Post")
        .description("Opens Look Again on Check.")
    }
}
