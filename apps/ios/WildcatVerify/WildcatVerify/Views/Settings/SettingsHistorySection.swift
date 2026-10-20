import SwiftUI

/// "Keep My Checks": off by default; turning it off deletes what was saved.
struct SettingsHistorySection: View {
    @Environment(AppViewModel.self) private var app

    var body: some View {
        @Bindable var settings = app.settings

        Section {
            Toggle("Keep My Checks", systemImage: "clock.arrow.circlepath", isOn: $settings.keepHistory)
                .onChange(of: settings.keepHistory) { _, isOn in
                    app.setKeepHistory(isOn)
                }
        } header: {
            Text("History")
        } footer: {
            Text(settings.keepHistory
                 ? "Your checks and small copies of photos you checked are saved on this iPhone only and left out of backups. Turning this off deletes them."
                 : "Off: My Checks clears when you close the app. Nothing is saved.")
        }
    }
}
