import SwiftUI

/// Preferences passed through the environment, so shared views (also used by
/// the share extension, which has no settings) don't depend on the app's
/// settings store. Defaults match a fresh install.
extension EnvironmentValues {
    @Entry var hapticsEnabled = true
    @Entry var heatmapEnabled = true
}
