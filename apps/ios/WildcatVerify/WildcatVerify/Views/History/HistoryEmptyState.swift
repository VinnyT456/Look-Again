import SwiftUI

/// Empty states for My Checks: nothing checked yet, or nothing matching.
struct HistoryEmptyState: View {
    @Environment(AppViewModel.self) private var app
    let viewModel: HistoryViewModel

    var body: some View {
        if viewModel.isEmpty {
            ContentUnavailableView {
                Label("No Checks Yet", systemImage: "clock")
            } description: {
                Text("Paste a Bluesky link or choose a photo. Your results show up here and stay on this iPhone.")
            } actions: {
                Button("Check an Image") { app.selectedTab = .check }
                    .buttonStyle(.borderedProminent)
            }
        } else if viewModel.visibleCases.isEmpty {
            if viewModel.searchQuery.isEmpty {
                ContentUnavailableView(
                    "No \(viewModel.scope.title) Checks",
                    systemImage: "line.3.horizontal.decrease.circle",
                    description: Text("Try a different filter.")
                )
            } else {
                ContentUnavailableView.search
            }
        }
    }
}
