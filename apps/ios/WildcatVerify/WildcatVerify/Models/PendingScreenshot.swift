import UIKit

/// A screenshot handed over by Siri or Shortcuts, waiting for the user to box
/// the photo in it. Lives in memory only.
struct PendingScreenshot: Identifiable {
    let id = UUID()
    let image: UIImage
}
