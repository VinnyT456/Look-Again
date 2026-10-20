import SwiftUI

/// Clears My Checks after confirmation. The dialog is attached here so it
/// animates from the button that triggered it.
struct ClearHistoryButton: View {
    @Bindable var viewModel: HistoryViewModel

    var body: some View {
        Button("Clear", role: .destructive, action: viewModel.confirmClear)
            .disabled(viewModel.isEmpty)
            .confirmationDialog(
                "Clear all checks?",
                isPresented: $viewModel.isConfirmingClear,
                titleVisibility: .visible
            ) {
                Button("Clear All", role: .destructive, action: viewModel.clearAll)
            } message: {
                Text("This removes every check and uploaded photo from this iPhone.")
            }
    }
}
