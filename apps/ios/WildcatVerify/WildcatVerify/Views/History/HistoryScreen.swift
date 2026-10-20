import SwiftUI

/// Every check the user ran this session: searchable, filterable by verdict,
/// swipe to delete.
struct HistoryScreen: View {
    @Environment(AppViewModel.self) private var app
    @Bindable var viewModel: HistoryViewModel

    var body: some View {
        NavigationStack(path: $viewModel.path) {
            List {
                ForEach(viewModel.visibleCases) { item in
                    NavigationLink(value: item) {
                        CaseRow(item: item)
                    }
                    .swipeActions {
                        Button("Delete", systemImage: "trash", role: .destructive) {
                            viewModel.delete(item)
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
            .overlay {
                HistoryEmptyState(viewModel: viewModel)
            }
            .searchable(text: $viewModel.searchQuery, prompt: "Search by author or topic")
            .searchScopes($viewModel.scope) {
                ForEach(VerdictFilter.allCases) { filter in
                    Text(filter.title).tag(filter)
                }
            }
            .brandToolbar(AppTab.history.title, onShowAbout: app.showAbout)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    ClearHistoryButton(viewModel: viewModel)
                }
            }
            .navigationDestination(for: VerificationCase.self) { item in
                CaseResultsScreen(item: item, onCheckAnother: app.startNewCheck)
            }
        }
    }
}
