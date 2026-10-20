import SwiftUI

/// The fastest ways to check a post, shortest first. Shown once on first
/// launch and kept under Settings → Ways to Check.
struct WaysToCheckView: View {
    /// Set on first launch: shows the start button instead of nothing.
    var onDone: (() -> Void)?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack(spacing: 14) {
                    LogoTile(scale: 1.8)
                    Text("Check a post in one or two taps")
                        .font(.title2)
                        .bold()
                        .fixedSize(horizontal: false, vertical: true)
                }

                WayRow(
                    number: 1,
                    title: "Hold the photo, tap Share",
                    detail: "In Bluesky, Safari, Photos or Messages, press and hold any image, tap Share, then Check with WildcatVerify."
                )
                WayRow(
                    number: 2,
                    title: "Copy the link, open WildcatVerify",
                    detail: "In Bluesky, tap Share on a post, then Copy Link. Open WildcatVerify and tap Paste."
                )
                WayRow(
                    number: 3,
                    title: "Ask Siri",
                    detail: "Say “Check the copied link with WildcatVerify,” or set up “Check This Post” in Settings → Siri & Shortcuts."
                )

                Text("Photos are checked on this iPhone and never uploaded.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding(24)
            .frame(maxWidth: 560, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .safeAreaInset(edge: .bottom) {
            if let onDone {
                Button("Start Checking", action: onDone)
                    .buttonStyle(.primary)
                    .padding(.horizontal, 24)
                    .padding(.bottom, 12)
                    .accessibilityIdentifier("welcomeDone")
            }
        }
        .navigationTitle(onDone == nil ? "Ways to Check" : "")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct WayRow: View {
    let number: Int
    let title: String
    let detail: String

    @ScaledMetric(relativeTo: .headline) private var badge = 30.0

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 14) {
            Text(number, format: .number)
                .font(.headline)
                .foregroundStyle(.white)
                .frame(width: badge, height: badge)
                .background(.tint, in: .circle)
                .alignmentGuide(.firstTextBaseline) { $0[VerticalAlignment.center] + 6 }
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.headline)
                Text(detail)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

#Preview {
    WaysToCheckView(onDone: {})
}
