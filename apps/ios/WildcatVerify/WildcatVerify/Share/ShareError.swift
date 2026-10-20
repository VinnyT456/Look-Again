import Foundation

enum ShareError: LocalizedError, Equatable {
    /// Nothing shared was an image or a Bluesky link.
    case unsupported

    var errorDescription: String? {
        "WildcatVerify can check photos, screenshots and Bluesky post links. Try sharing the image itself or the post's link."
    }
}
