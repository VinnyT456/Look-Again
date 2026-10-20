import SwiftUI

/// The share sheet's content: progress, the verdict, or why it couldn't check.
struct ShareRootView: View {
    let viewModel: ShareViewModel
    let onDone: () -> Void

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.phase {
                case .reading:
                    ProgressView("Reading shared item…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                case .analyzing:
                    AnalyzingView(image: viewModel.analyzingImage, onCancel: onDone)
                case .result(let item):
                    CaseResultsScreen(item: item, onCheckAnother: nil)
                case .failed(let message):
                    ContentUnavailableView {
                        Label("Can't Check This", systemImage: "exclamationmark.magnifyingglass")
                    } description: {
                        Text(message)
                    }
                }
            }
            .background(Color(.systemGroupedBackground))
            .toolbar {
                LogoToolbarItem()
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done", action: onDone)
                }
            }
        }
        // Extensions don't inherit the app's global accent; set it explicitly.
        .tint(Color("AccentColor"))
    }
}
