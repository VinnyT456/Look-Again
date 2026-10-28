import SwiftUI

/// Under each Feed post: the automatic verdict once it's in, "Checking…"
/// while it runs, or the plain tap-to-check prompt.
struct FeedVerdictLine: View {
    let verdict: FeedVerdict?
    var pause: AutoCheckPause?

    var body: some View {
        switch verdict {
        case .done(let verdict, let confidence, let isDemo):
            HStack(spacing: 8) {
                VerdictBadge(verdict: verdict)
                Text("\(confidence)%\(isDemo ? " · demo" : "")")
                    .font(.subheadline)
                    .monospacedDigit()
                    .foregroundStyle(.secondary)
                Spacer(minLength: 4)
                Text("Details")
                    .font(.subheadline)
                    .bold()
                    .foregroundStyle(.tint)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("\(verdict.label), \(confidence) percent\(isDemo ? ", demo result" : ""). Tap for details.")
        case .checking:
            HStack(spacing: 8) {
                ProgressView()
                    .controlSize(.small)
                Text("Checking…")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        case .failed:
            Label("Couldn't check. Tap to try again", systemImage: "arrow.clockwise")
                .font(.subheadline)
                .bold()
                .foregroundStyle(.tint)
        case nil:
            Label(pause?.explanation == nil ? "Check this post" : "Tap to check", systemImage: "checkmark.shield")
                .font(.subheadline)
                .bold()
                .foregroundStyle(.tint)
        }
    }
}
