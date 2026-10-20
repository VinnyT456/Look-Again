import SwiftUI

/// Checks one feed post when opened, then shows its result. The result is
/// added to My Checks like any other check.
struct FeedCheckScreen: View {
    let post: FeedPost

    @Environment(\.dismiss) private var dismiss
    @State private var viewModel: ShareViewModel

    init(post: FeedPost, onResult: @escaping @MainActor (VerificationCase) -> Void) {
        self.post = post
        _viewModel = State(initialValue: ShareViewModel(onResult: onResult))
    }

    var body: some View {
        Group {
            switch viewModel.phase {
            case .reading, .analyzing:
                AnalyzingView(image: viewModel.analyzingImage, onCancel: close)
                    .navigationTitle("Checking")
                    .navigationBarTitleDisplayMode(.inline)
            case .result(let item):
                CaseResultsScreen(item: item, onCheckAnother: nil)
            case .failed(let message):
                ContentUnavailableView {
                    Label("Couldn't Check This Post", systemImage: "exclamationmark.magnifyingglass")
                } description: {
                    Text(message)
                } actions: {
                    Button("Try Again", action: retry)
                        .buttonStyle(.borderedProminent)
                }
            }
        }
        .task { await viewModel.check(.link(post.postURL.absoluteString)) }
    }

    private func close() {
        dismiss()
    }

    private func retry() {
        Task { await viewModel.check(.link(post.postURL.absoluteString)) }
    }
}
