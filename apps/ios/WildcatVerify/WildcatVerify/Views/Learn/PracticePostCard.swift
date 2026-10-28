import SwiftUI

/// A practice case drawn like a post in the Feed: avatar, name, handle and
/// time, the caption, then the photo full width (or its description while
/// there's no photo), its credit, and any reply-style context.
struct PracticePostCard: View {
    let question: PracticeQuestion
    /// After answering: mark the clue areas on the photo.
    var showsHotspots = false

    @ScaledMetric(relativeTo: .body) private var avatarSize = 36.0
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var isZoomed = false

    /// Tall enough to see detail, short enough to leave the answers in view.
    private static let photoMaxHeight = 440.0

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            header
            Text(question.caption)
                .fixedSize(horizontal: false, vertical: true)
            photo
            if let context = question.context {
                Label(context, systemImage: "arrowshape.turn.up.left")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .fullScreenCover(isPresented: $isZoomed) {
            if let name = question.resolvedImageName {
                PracticePhotoViewer(
                    imageName: name,
                    description: question.spokenImageDescription,
                    credit: question.credit,
                    hotspots: showsHotspots ? question.hotspots : []
                )
            }
        }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Monogram(name: question.author, size: min(avatarSize, 52))
            VStack(alignment: .leading, spacing: 1) {
                Text(question.author)
                    .font(.subheadline)
                    .bold()
                    .lineLimit(dynamicTypeSize.isAccessibilitySize ? 2 : 1)
                meta
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Post by \(question.author), \(Self.spokenTime(question.posted)). \(Self.sentence(question.caption))")
    }

    /// Handle and time, as the Feed shows them. The handle never wraps (a
    /// broken handle reads as a different account).
    @ViewBuilder
    private var meta: some View {
        if dynamicTypeSize.isAccessibilitySize {
            VStack(alignment: .leading, spacing: 0) {
                Text("@\(question.handle)").lineLimit(1).truncationMode(.middle)
                Text(question.posted)
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
        } else {
            Text("@\(question.handle) · \(question.posted)")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.middle)
        }
    }

    @ViewBuilder
    private var photo: some View {
        if let name = question.resolvedImageName {
            VStack(alignment: .leading, spacing: 4) {
                Button {
                    isZoomed = true
                } label: {
                    Image(name)
                        .resizable()
                        .scaledToFit()
                        // Marks sit on the fitted image itself, so their 0–1
                        // coordinates land on the right pixels.
                        .overlay {
                            if showsHotspots {
                                PracticeHotspotOverlay(hotspots: question.hotspots)
                                    .transition(.opacity)
                            }
                        }
                        .clipShape(.rect(cornerRadius: Metrics.photoRadius))
                        .overlay {
                            RoundedRectangle(cornerRadius: Metrics.photoRadius)
                                .strokeBorder(Color(.separator), lineWidth: 0.5)
                        }
                        .frame(maxWidth: .infinity, maxHeight: Self.photoMaxHeight)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Photo: \(question.spokenImageDescription)")
                .accessibilityHint("Opens the photo full screen to zoom in")

                if let credit = question.credit {
                    Text(credit)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        } else {
            Label {
                Text(question.imageDescription)
                    .fixedSize(horizontal: false, vertical: true)
            } icon: {
                Image(systemName: "photo")
                    .foregroundStyle(.secondary)
            }
            .font(.callout)
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.tertiarySystemFill), in: .rect(cornerRadius: Metrics.photoRadius))
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Photo: \(question.imageDescription)")
        }
    }

    /// "40m" → "40 minutes ago" so VoiceOver doesn't read meters.
    static func spokenTime(_ short: String) -> String {
        guard let unit = short.last, let value = Int(short.dropLast()) else { return "posted \(short)" }
        let word: String
        switch unit {
        case "m": word = value == 1 ? "minute" : "minutes"
        case "h": word = value == 1 ? "hour" : "hours"
        case "d": word = value == 1 ? "day" : "days"
        default: return "posted \(short)"
        }
        return "\(value) \(word) ago"
    }

    /// Ends a caption with exactly one sentence mark, so the label doesn't
    /// read "today!!. Photo".
    static func sentence(_ caption: String) -> String {
        let trimmed = caption.trimmingCharacters(in: .whitespaces)
        guard let last = trimmed.last, !".!?".contains(last) else { return trimmed }
        return trimmed + "."
    }
}

#Preview("With photo, revealed") {
    PracticePostCard(
        question: PracticeQuestion(
            id: "preview",
            author: "Preview Account",
            handle: "preview.example",
            posted: "2h",
            caption: "Look at this little guy",
            imageDescription: "The app's magnifier mascot.",
            imageName: "FaceCheckMagnifier",
            credit: "Illustration: Look Again",
            hotspots: [
                PracticeHotspot(x: 0.2, y: 0.15, width: 0.55, height: 0.5, label: "Lens"),
                PracticeHotspot(x: 0.55, y: 0.65, width: 0.3, height: 0.25, label: "Normal: handle", isDecoy: true),
            ],
            answer: .real,
            explanation: "",
            clues: []
        ),
        showsHotspots: true
    )
    .padding()
}
