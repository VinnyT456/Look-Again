import Foundation

/// Uploaded photos live only in memory and are addressed with this scheme.
extension URL {
    static func inMemoryImage(_ id: UUID) -> URL {
        var components = URLComponents()
        components.scheme = "memory"
        components.host = "upload"
        components.path = "/\(id.uuidString)"
        // Components built from a fixed scheme, host and UUID always form a valid URL.
        guard let url = components.url else { fatalError("Invalid in-memory image URL for \(id)") }
        return url
    }

    var isInMemoryImage: Bool { scheme == "memory" }
}
