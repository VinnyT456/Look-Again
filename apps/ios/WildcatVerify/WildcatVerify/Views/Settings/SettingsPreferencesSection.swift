import SwiftUI

/// Haptics and the heatmap.
struct SettingsPreferencesSection: View {
    @Bindable var settings: SettingsStore

    var body: some View {
        Section {
            Toggle("Haptics", systemImage: "iphone.radiowaves.left.and.right", isOn: $settings.hapticsEnabled)
            Toggle("Show Heatmap", systemImage: "flame", isOn: $settings.heatmapEnabled)
        } header: {
            Text("Preferences")
        } footer: {
            Text("The heatmap appears under Highlight on Likely AI results and shows which areas influenced the detector most.")
        }
    }
}
