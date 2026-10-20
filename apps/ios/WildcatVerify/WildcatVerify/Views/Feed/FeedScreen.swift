import SwiftUI

/// Image posts from the user's Following timeline (signed in) or Bluesky's
/// public What's Hot feed, checked as they scroll by. Tap one for details.
struct FeedScreen: View {
    @Environment(AppViewModel.self) private var app
    @Bindable var viewModel: FeedViewModel

    var body: some View {
        NavigationStack(path: $viewModel.path) {
            content
                .brandToolbar(AppTab.feed.title, onShowAbout: app.showAbout)
                .navigationDestination(for: FeedPost.self) { post in
                    FeedCheckScreen(post: post, onResult: app.history.record)
                }
                .safeAreaInset(edge: .top, spacing: 0) {
                    if viewModel.availableSources.count > 1 {
                        Picker("Feed", selection: $viewModel.selectedSource) {
                            ForEach(viewModel.availableSources, id: \.self) { source in
                                Text(source.title).tag(source)
                            }
                        }
                        .pickerStyle(.segmented)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(.bar)
                        .accessibilityIdentifier("feedSource")
                    }
                }
                .task(id: viewModel.source) { await viewModel.loadIfNeeded() }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.status {
        case .idle, .loading:
            if viewModel.posts.isEmpty {
                ProgressView("Loading posts…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Color(.systemGroupedBackground))
            } else {
                FeedList(viewModel: viewModel)
            }
        case .failed(let message):
            ContentUnavailableView {
                Label("Couldn't Load the Feed", systemImage: "wifi.exclamationmark")
            } description: {
                Text(message)
            } actions: {
                if viewModel.source == .following && !app.account.isSignedIn {
                    BlueskySignInButton(title: "Sign In Again")
                        .buttonStyle(.borderedProminent)
                } else {
                    Button("Try Again", action: retry)
                        .buttonStyle(.borderedProminent)
                }
            }
            .background(Color(.systemGroupedBackground))
        default:
            FeedList(viewModel: viewModel)
        }
    }

    private func retry() {
        Task { await viewModel.refresh() }
    }
}
