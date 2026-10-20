import SwiftUI

/// Shared layout constants, so every screen rounds and sizes the same way.
/// Colors live in the asset catalog (light, dark and Increase Contrast variants)
/// and are used through generated symbols such as `Color.verdictAI`.
enum Metrics {
    /// Thumbnails in lists.
    static let thumbnail = 56.0
    static let thumbnailRadius = 10.0
    /// Verdict glyph tile on the results screen.
    static let verdictTile = 44.0
    static let verdictTileRadius = 12.0
    /// Tallest the checked photo is drawn on the results screen.
    static let photoMaxHeight = 360.0
    /// Height of the placeholder when a case has no photo.
    static let placeholderHeight = 160.0
    static let photoRadius = 12.0
    /// Logo tile in the navigation bar.
    static let logo = 30.0
    /// Logo tile in the Check page header.
    static let headerLogo = 44.0
    /// Major containers, such as the Check card.
    static let cardRadius = 24.0
    /// Inputs, buttons and the photo drop zone.
    static let fieldRadius = 16.0
    /// Minimum height for full-width buttons and inputs.
    static let controlHeight = 52.0
}
