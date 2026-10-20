/// Tab order puts Check in the middle of five.
enum AppTab: String, CaseIterable, Hashable {
    case feed
    case learn
    case check
    case history
    case settings

    var title: String {
        switch self {
        case .feed: "Feed"
        case .learn: "Learn"
        case .check: "Check"
        case .history: "My Checks"
        case .settings: "Settings"
        }
    }

    var icon: String {
        switch self {
        case .feed: "flame"
        case .learn: "graduationcap"
        case .check: "checkmark.shield"
        case .history: "clock"
        case .settings: "gearshape"
        }
    }
}
