import Foundation

/// One checked image: where it came from, what the classifier said, and why.
struct VerificationCase: Identifiable, Hashable, Sendable, Codable {
    var id = UUID()
    var title: String
    var authorHandle: String
    var postURL: URL?
    var caption: String
    var timeAgo: String
    /// Nil when there is no photo to show (e.g. the bundled examples).
    var imageURL: URL?
    var localImageName: String?
    var verdict: VerdictType
    var confidencePercentage: Int
    var plainSummary: String
    var suggestedAction: String
    var detectedIssue: String?
    var hotspot: HotspotArea?
    /// Where the detector found what pushed it toward "AI" (detector results only).
    var heatmap: PatchHeatmap?
    var keyFindings: [String]
    var checksCount: String?
    /// True when the verdict did not come from the trained model (bundled
    /// examples, or the placeholder classifier). Always shown to the user.
    var isDemo = false
    /// Every image in a multi-image post, in post order, each with its own
    /// verdict. Nil for single images. The case itself is the most suspicious one.
    var postImages: [VerificationCase]?
    /// Content Credentials (C2PA) found in the original file, if any.
    var credentials: ContentCredentials?

    /// Title of checks boxed from a Siri or Shortcuts screenshot.
    static let screenshotTitle = "Screenshot"

    /// Uploaded photos have no author.
    var displayHandle: String {
        guard authorHandle.isEmpty else { return "@\(authorHandle)" }
        return title == Self.screenshotTitle ? "From a screenshot" : "From your photo library"
    }

    /// Plain-text summary used by the share sheet.
    var shareText: String {
        var lines = [
            "WildcatVerify\(isDemo ? " (demo result)" : ""): \(verdict.label), \(confidencePercentage)% confidence",
            title,
        ]
        if !authorHandle.isEmpty { lines.append("Posted by @\(authorHandle)") }
        lines.append(plainSummary)
        if let postURL { lines.append(postURL.absoluteString) }
        lines.append("An automated estimate, not proof.")
        return lines.joined(separator: "\n")
    }
}
