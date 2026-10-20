import UIKit

/// Images handed over by Visual Intelligence, kept in memory just long enough
/// for the user to tap the result. Only the last few are kept.
@MainActor
final class VisualCheckStore {
    static let shared = VisualCheckStore()
    private static let limit = 3

    private var images: [(id: UUID, image: UIImage)] = []

    func add(_ image: UIImage) -> UUID {
        let id = UUID()
        images.append((id, image))
        if images.count > Self.limit { images.removeFirst(images.count - Self.limit) }
        return id
    }

    func image(for id: UUID) -> UIImage? {
        images.first { $0.id == id }?.image
    }
}
