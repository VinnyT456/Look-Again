import SwiftUI

/// The ••• on each feed post: hide it, hide its author, or report it.
/// Feeds of other people's posts need all three (App Review Guideline 1.2).
struct FeedPostMenu: View {
    let post: FeedPost
    let viewModel: FeedViewModel

    @Environment(\.openURL) private var openURL

    var body: some View {
        Menu {
            Button("Hide This Post", systemImage: "eye.slash") {
                withAnimation { viewModel.hidePost(post) }
            }
            Button("Hide Posts from @\(post.authorHandle)", systemImage: "person.crop.circle.badge.xmark") {
                withAnimation { viewModel.hideAccount(of: post) }
            }
            Divider()
            Button("Report on Bluesky", systemImage: "exclamationmark.bubble") {
                openURL(post.postURL)
            }
            if let support = AppLinks.support {
                Button("Report to WildcatVerify", systemImage: "envelope") {
                    openURL(support)
                }
            }
        } label: {
            Image(systemName: "ellipsis")
                .font(.body.bold())
                .foregroundStyle(.secondary)
                .frame(width: 44, height: 44)
                .contentShape(.rect)
        }
        .accessibilityLabel("Post options")
        .accessibilityIdentifier("postMenu")
    }
}
