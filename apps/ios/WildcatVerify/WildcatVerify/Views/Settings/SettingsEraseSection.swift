import SwiftUI

/// Erase checks, saved photos and preferences, after confirmation. The dialog
/// is attached to the button so it animates from it.
struct SettingsEraseSection: View {
    @Environment(AppViewModel.self) private var app
    @State private var isConfirming = false

    var body: some View {
        Section {
            Button("Erase All Data", systemImage: "trash", role: .destructive, action: confirm)
                .confirmationDialog("Erase all data?", isPresented: $isConfirming, titleVisibility: .visible) {
                    Button("Erase All Data", role: .destructive, action: app.eraseAllData)
                } message: {
                    Text("Deletes My Checks, any saved photos, and resets settings.")
                }
        }
    }

    private func confirm() {
        isConfirming = true
    }
}
