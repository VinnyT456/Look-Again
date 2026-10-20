/// Search scope for My Checks.
enum VerdictFilter: Hashable, CaseIterable, Identifiable {
    case all
    case real
    case tampered
    case ai

    var id: Self { self }

    var title: String {
        switch self {
        case .all: "All"
        case .real: VerdictType.real.shortLabel
        case .tampered: VerdictType.tampered.shortLabel
        case .ai: VerdictType.ai.shortLabel
        }
    }

    func matches(_ item: VerificationCase) -> Bool {
        switch self {
        case .all: true
        case .real: item.verdict == .real
        case .tampered: item.verdict == .tampered
        case .ai: item.verdict == .ai
        }
    }
}
