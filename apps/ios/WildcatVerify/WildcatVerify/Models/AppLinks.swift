import Foundation

/// External links the app shows. Each is a fixed, known-good literal.
enum AppLinks {
    /// Public copy of PRIVACY.md (also entered in App Store Connect).
    static let privacyPolicy = URL(string: "https://github.com/VinnyT456/Look-Again/blob/main/apps/ios/WildcatVerify/PRIVACY.md")
    /// Public copy of TERMS.md.
    static let terms = URL(string: "https://github.com/VinnyT456/Look-Again/blob/main/apps/ios/WildcatVerify/TERMS.md")
    static let blueskyPrivacy = URL(string: "https://bsky.social/about/support/privacy-policy")
    static let support = URL(string: "https://github.com/VinnyT456/Look-Again/issues")
    /// Detector credits: model card, paper and original code.
    static let detectorModel = URL(string: "https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT")
    static let detectorPaper = URL(string: "https://arxiv.org/abs/2411.04125")
    static let detectorCode = URL(string: "https://github.com/JeongsooP/Community-Forensics")
    /// Opens a blank shortcut in the Shortcuts editor (Apple's documented scheme).
    static let newShortcut = URL(string: "shortcuts://create-shortcut")
    /// iCloud link to the "Check This Post" shortcut (Take Screenshot → Check Image).
    /// Create it on an iPhone (Shortcuts → share → Copy iCloud Link) and paste it
    /// here; until then Set Up Siri shows the build-it-yourself steps only.
    static let checkThisPostShortcut: URL? = nil
}
