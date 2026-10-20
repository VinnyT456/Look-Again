import SwiftUI

/// The scrolling list of feed posts, with pull to refresh and endless paging.
struct FeedList: View {
    let viewModel: FeedViewModel
    @Environment(AppViewModel.self) private var app

    var body: some View {
        List {
            if viewModel.source == .whatsHot, !app.account.isSignedIn, !app.settings.feedSignInDismissed {
                Section {
                    FeedSignInCard { app.settings.feedSignInDismissed = true }
                }
            }
            Section {
                ForEach(viewModel.visiblePosts) { post in
                    Button {
                        viewModel.open(post)
                    } label: {
                        FeedPostRow(post: post, verdict: viewModel.verdict(for: post))
                    }
                    .buttonStyle(.plain)
                    .overlay(alignment: .topTrailing) {
                        FeedPostMenu(post: post, viewModel: viewModel)
                    }
                    .task {
                        viewModel.autoCheck?.request(post)
                        await viewModel.loadMore(after: post)
                    }
                    .onDisappear { viewModel.autoCheck?.cancel(post) }
                }
                if viewModel.isLoadingMore {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                }
            } header: {
                Text(viewModel.source == .following ? "Posts you follow" : "Trending on Bluesky")
            } footer: {
                Text("Image posts from Bluesky's public What's Hot feed. Posts carrying content labels are hidden. Posts are checked on this iPhone as they appear; tap one for every image and the details. Use ••• on a post to hide it, hide that account, or report it.")
            }
        }
        .listStyle(.insetGrouped)
        .refreshable { await viewModel.refresh() }
        .overlay {
            if viewModel.visiblePosts.isEmpty, viewModel.status == .loaded {
                ContentUnavailableView(
                    "No Image Posts Right Now",
                    systemImage: "photo.on.rectangle",
                    description: Text("Pull down to refresh.")
                )
            }
        }
    }
}
