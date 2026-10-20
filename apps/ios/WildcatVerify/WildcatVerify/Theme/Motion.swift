import SwiftUI

/// One motion vocabulary for the whole app: springs for things that move,
/// short durations, exits faster than entrances.
enum Motion {
    /// Sections and cards arriving.
    static let enter = Animation.spring(duration: 0.4, bounce: 0.15)
    /// Small state changes: validation, toggles.
    static let quick = Animation.snappy(duration: 0.2)
    /// Delay between staggered items.
    static let stagger = 0.04
    /// How far a tab's content travels when switching tabs.
    static let tabOffset = 28.0
}
