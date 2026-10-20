import SwiftUI

/// Feed controls: automatic checks and hidden accounts.
struct SettingsFeedSection: View {
    @Bindable var settings: SettingsStore

    var body: some View {
        Section {
            Toggle("Check Posts Automatically", systemImage: "wand.and.rays", isOn: $settings.autoCheckFeed)
            NavigationLink(value: SettingsRoute.hiddenAccounts) {
                LabeledContent {
                    Text(settings.hiddenAccounts.count, format: .number)
                } label: {
                    Label("Hidden Accounts", systemImage: "person.crop.circle.badge.xmark")
                }
            }
            .accessibilityIdentifier("hiddenAccountsRow")
        } header: {
            Text("Feed")
        } footer: {
            Text("Feed posts are checked on this iPhone as they scroll into view. Paused in Low Power Mode and on cellular or Low Data Mode.")
        }
    }
}
