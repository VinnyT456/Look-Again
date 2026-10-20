import SwiftUI

/// Entry to Set Up Siri.
struct SettingsSiriSection: View {
    var body: some View {
        Section {
            NavigationLink(value: SettingsRoute.waysToCheck) {
                Label("Ways to Check", systemImage: "hand.tap")
            }
            .accessibilityIdentifier("waysToCheckRow")
            NavigationLink(value: SettingsRoute.siriSetup) {
                Label("Siri & Shortcuts", systemImage: "mic")
            }
            .accessibilityIdentifier("siriSetupRow")
        } footer: {
            Text("Check posts without leaving Bluesky.")
        }
    }
}
