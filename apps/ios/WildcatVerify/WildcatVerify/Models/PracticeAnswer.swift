/// The four answers in Look Again. Practice-only: the detector still has
/// three verdicts, but the most common misleading Bluesky post is a real photo
/// with a false story, and players should learn to name it.
enum PracticeAnswer: String, CaseIterable, Hashable, Sendable {
    case real
    case edited
    case ai
    case misleading

    /// Button label.
    var label: String {
        switch self {
        case .real: "Real"
        case .edited: "Edited"
        case .ai: "AI"
        case .misleading: "False story"
        }
    }

    /// Reads after "It's …": "It's a real photo."
    var phrase: String {
        switch self {
        case .real: "a real photo"
        case .edited: "an edited photo"
        case .ai: "made by AI"
        case .misleading: "a real photo with a false story"
        }
    }

    /// Mid-sentence form: "You said AI", "You said edited".
    var inSentence: String {
        self == .ai ? label : label.lowercased()
    }

    /// One-line definition, shown before the first answer.
    var definition: String {
        switch self {
        case .real: "The photo is what the post says it is."
        case .edited: "A real photo with part of it changed."
        case .ai: "The whole image was generated."
        case .misleading: "A real, unedited photo with the wrong date, place or story."
        }
    }

    /// For "You caught every …": "AI image".
    var singularNoun: String {
        switch self {
        case .real: "real photo"
        case .edited: "edited photo"
        case .ai: "AI image"
        case .misleading: "false story"
        }
    }

    /// For "Most misses were …": "AI images".
    var pluralNoun: String {
        switch self {
        case .real: "real photos"
        case .edited: "edited photos"
        case .ai: "AI images"
        case .misleading: "false stories"
        }
    }

    /// Which clue group helps with this answer.
    var guideFocus: VerdictType {
        switch self {
        case .real, .misleading: .real
        case .edited: .tampered
        case .ai: .ai
        }
    }
}
