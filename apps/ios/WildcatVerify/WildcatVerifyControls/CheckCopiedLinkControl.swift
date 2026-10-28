import AppIntents
import SwiftUI
import WidgetKit

/// Copy a post's link in Bluesky, tap this, see the verdict.
struct CheckCopiedLinkControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        StaticControlConfiguration(kind: "edu.northwestern.lookagain.WildcatVerify.checkCopiedLink") {
            ControlWidgetButton(action: OpenURLIntent(AppDeepLink.checkCopiedLink.url)) {
                Label("Check Copied Link", systemImage: "link")
            }
        }
        .displayName("Check Copied Link")
        .description("Checks the Bluesky post link you copied. iOS asks before Look Again reads the clipboard.")
    }
}
