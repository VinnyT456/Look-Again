import SwiftUI

/// One feed post: who posted it, when, its text, the image, and a check cue.
struct FeedPostRow: View {
    let post: FeedPost
    /// The automatic check of the first image, when there is one.
    var verdict: FeedVerdict?

    @ScaledMetric(relativeTo: .body) private var avatarSize = 36.0

    /// Previews are at most square so tall images don't fill the screen; the
    /// check itself always uses the full image.
    private var imageRatio: Double {
        min(max(post.aspectRatio ?? 4.0 / 3.0, 1.0), 2.0)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                RemoteImage(url: post.avatarURL, pointSize: avatarSize)
                    .frame(width: avatarSize, height: avatarSize)
                    .clipShape(.circle)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 1) {
                    Text(post.authorName)
                        .font(.subheadline)
                        .bold()
                        .lineLimit(1)
                    HStack(spacing: 4) {
                        Text("@\(post.authorHandle)")
                            .lineLimit(1)
                            .truncationMode(.middle)
                        if let postedAt = post.postedAt {
                            Text("·")
                            Text(postedAt, format: .relative(presentation: .named))
                                .lineLimit(1)
                        }
                    }
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                }
            }

            if !post.text.isEmpty {
                Text(post.text)
                    .font(.body)
                    .lineLimit(4)
            }

            Color.clear
                .aspectRatio(imageRatio, contentMode: .fit)
                .frame(maxWidth: .infinity)
                .overlay {
                    RemoteImage(url: post.thumbURL, pointSize: 400)
                }
                .clipShape(.rect(cornerRadius: Metrics.photoRadius))
                .overlay(alignment: .topTrailing) {
                    if post.imageCount > 1 {
                        Text("1 of \(post.imageCount)")
                            .font(.caption)
                            .bold()
                            .foregroundStyle(.white)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(.black.opacity(0.6), in: .capsule)
                            .padding(8)
                    }
                }
                .accessibilityLabel(post.imageAlt.isEmpty ? "Post image" : post.imageAlt)

            FeedVerdictLine(verdict: verdict)
        }
        .padding(.vertical, 6)
        .contentShape(.rect)
        .accessibilityElement(children: .combine)
        .accessibilityHint(post.imageCount > 1 ? "Checks all \(post.imageCount) images in this post" : "Checks the image in this post")
    }
}
