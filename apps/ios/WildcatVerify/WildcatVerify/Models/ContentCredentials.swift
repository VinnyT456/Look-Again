import Foundation

/// What a photo's Content Credentials (C2PA) say about where it came from.
/// Read from the file; the signature isn't verified, so it's a clue, not proof.
struct ContentCredentials: Codable, Hashable, Sendable {
    enum Source: String, Codable, Sendable {
        /// Made entirely by generative AI.
        case aiGenerated
        /// A real or edited image with AI-generated parts.
        case aiEdited
        /// Captured by a camera.
        case camera
        /// Credentials present but don't say.
        case unspecified
    }

    /// The app or device that wrote the credentials, e.g. "Adobe Firefly".
    var generator: String?
    var source: Source
    /// Human-readable edit history, e.g. ["Created", "Cropped"].
    var actions: [String]
}
