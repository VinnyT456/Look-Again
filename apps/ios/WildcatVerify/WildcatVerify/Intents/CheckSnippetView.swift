import AppIntents
import SwiftUI

/// The Siri card: the post's photo, the verdict and confidence, and Open.
/// Drawn by the system, so the photo is passed in rather than loaded.
struct CheckSnippetView: View {
    let item: VerificationCase
    let thumbnail: UIImage?

    private static let side = 72.0

    /// Pixel size for a sharp 72 pt square on any iPhone.
    static func thumbnailPixels(for size: CGSize) -> CGSize {
        let target = side * 3
        let scale = target / max(min(size.width, size.height), 1)
        return CGSize(width: size.width * scale, height: size.height * scale)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Group {
                    if let thumbnail {
                        Image(uiImage: thumbnail)
                            .resizable()
                            .scaledToFill()
                    } else {
                        NoPhotoPlaceholder(verdict: item.verdict)
                    }
                }
                .frame(width: Self.side, height: Self.side)
                .clipShape(.rect(cornerRadius: Metrics.thumbnailRadius))
                .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: 4) {
                    VerdictBadge(verdict: item.verdict)
                    Text("\(item.confidencePercentage)% confidence")
                        .font(.headline)
                    Text(item.displayHandle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
            }

            if item.isDemo {
                Text("Demo result: the detector isn't installed in this build.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Button(intent: OpenCheckIntent(caseID: item.id)) {
                Label("Open in WildcatVerify", systemImage: "arrow.up.forward.app")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(.northwesternPurple)
        }
        .padding()
    }
}
