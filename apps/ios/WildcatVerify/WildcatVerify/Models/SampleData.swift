import Foundation

/// Example cases shown in the Learn tab, one per verdict. They carry no photos
/// and are always marked as demos.
enum SampleData {
    static let lakefill = VerificationCase(
        title: "Lakefill Storm Clouds",
        authorHandle: "dailynorthwestern.bsky.social",
        postURL: URL(string: "https://bsky.app/profile/dailynorthwestern.bsky.social"),
        caption: "Graduates celebrate on the Lakefill as storm clouds roll over the Evanston shoreline.",
        timeAgo: "5h ago",
        verdict: .real,
        confidencePercentage: 96,
        plainSummary: "Natural sunlight, consistent shadows, and clean lens focus throughout. No signs of digital editing or synthesis.",
        suggestedAction: "Fine to share. Still check that the caption matches the event.",
        keyFindings: [
            "Consistent natural lighting and shadows across subjects",
            "Realistic depth of field between foreground and background",
            "Standard camera noise texture with no spliced seams",
        ],
        isDemo: true
    )

    static let protestBanner = VerificationCase(
        title: "Altered Student Council Sign",
        authorHandle: "wildcat_watch.bsky.social",
        postURL: URL(string: "https://bsky.app/profile/wildcat_watch.bsky.social"),
        caption: "Edited banner text circulating in student group chats ahead of the council vote.",
        timeAgo: "3h ago",
        verdict: .tampered,
        confidencePercentage: 89,
        plainSummary: "Text on the center banner shows sharp edge seams and uneven compression compared to the surrounding fabric folds.",
        suggestedAction: "Look for the original photo before sharing it.",
        detectedIssue: "Replaced banner text",
        hotspot: HotspotArea(xRatio: 0.30, yRatio: 0.34, widthRatio: 0.40, heightRatio: 0.26, label: "Edited text"),
        keyFindings: [
            "Letters look pasted over the natural cloth folds",
            "Blurry seam where the original text was covered up",
            "Mismatched pixel resolution along the banner's edge",
        ],
        isDemo: true
    )

    static let monorail = VerificationCase(
        title: "Lake Michigan Monorail Concept",
        authorHandle: "chicago_future.bsky.social",
        postURL: URL(string: "https://bsky.app/profile/chicago_future.bsky.social"),
        caption: "Viral post claiming the city approved an elevated monorail along Lake Shore Drive.",
        timeAgo: "1h ago",
        verdict: .ai,
        confidencePercentage: 98,
        plainSummary: "Structural inconsistencies typical of generative AI: tracks float without support piers, and water reflections don't match the buildings.",
        suggestedAction: "Don't share it as real. Reply with a note that it appears to be AI-generated.",
        detectedIssue: "Generated structures",
        hotspot: HotspotArea(xRatio: 0.18, yRatio: 0.45, widthRatio: 0.55, heightRatio: 0.40, label: "Floating track"),
        keyFindings: [
            "Elevated rails float over open water without support columns",
            "Water reflections blur into melted patterns",
            "Background buildings have warped, painted textures",
        ],
        isDemo: true
    )

    /// One example per verdict, in the order the Learn tab explains them.
    static let examples: [VerificationCase] = [monorail, protestBanner, lakefill]
}
