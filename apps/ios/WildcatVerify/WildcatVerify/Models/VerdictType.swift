import SwiftUI

/// The three classes produced by the ViT image-authenticity classifier,
/// phrased for everyday users.
enum VerdictType: String, CaseIterable, Hashable, Codable, Sendable {
    case real
    case tampered
    case ai

    /// Full verdict, e.g. on the results screen.
    var label: String {
        switch self {
        case .real: "Likely Real"
        case .tampered: "Likely Edited"
        case .ai: "Likely AI"
        }
    }

    /// One-word form for badges and filters.
    var shortLabel: String {
        switch self {
        case .real: "Real"
        case .tampered: "Edited"
        case .ai: "AI"
        }
    }

    /// What this verdict means, in one sentence.
    var explanation: String {
        switch self {
        case .real: "Nothing in the photo points to editing or generation."
        case .tampered: "A real photo where part of the image was changed, added or removed."
        case .ai: "The whole image looks generated rather than photographed."
        }
    }

    var icon: String {
        switch self {
        case .real: "checkmark.shield.fill"
        case .tampered: "exclamationmark.triangle.fill"
        case .ai: "cpu"
        }
    }

    /// Glyph for each finding in "What we noticed".
    var findingIcon: String {
        self == .real ? "checkmark.circle" : "exclamationmark.circle"
    }

    /// Base hue for solid fills, borders and glyphs.
    var color: Color {
        switch self {
        case .real: .verdictReal
        case .tampered: .verdictTampered
        case .ai: .verdictAI
        }
    }

    /// Contrast-safe hue for text drawn on `background`.
    var textColor: Color {
        switch self {
        case .real: .verdictRealText
        case .tampered: .verdictTamperedText
        case .ai: .verdictAIText
        }
    }

    var background: Color {
        switch self {
        case .real: .verdictRealBackground
        case .tampered: .verdictTamperedBackground
        case .ai: .verdictAIBackground
        }
    }

    /// Whether the classifier flagged something worth pointing at on the photo.
    var hasAnomaly: Bool { self != .real }
}
