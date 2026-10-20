// Visual Intelligence is device-only; the Simulator SDK doesn't include it.
#if canImport(VisualIntelligence)
import AppIntents
import UIKit

/// What WildcatVerify offers in Visual Intelligence results: "Check with
/// WildcatVerify", showing the image it would check.
@available(iOS 26.0, *)
struct VisualCheckEntity: AppEntity {
    static let typeDisplayRepresentation: TypeDisplayRepresentation = "Image Check"
    static let defaultQuery = VisualCheckEntityQuery()

    var id: UUID
    /// Small JPEG preview for the result row.
    var thumbnail: Data?

    var displayRepresentation: DisplayRepresentation {
        DisplayRepresentation(
            title: "Check with WildcatVerify",
            subtitle: "Box the photo and see if it's real or AI",
            image: thumbnail.map { .init(data: $0) }
        )
    }
}

@available(iOS 26.0, *)
struct VisualCheckEntityQuery: EntityQuery {
    @MainActor
    func entities(for identifiers: [UUID]) async throws -> [VisualCheckEntity] {
        identifiers
            .filter { VisualCheckStore.shared.image(for: $0) != nil }
            .map { VisualCheckEntity(id: $0, thumbnail: nil) }
    }
}
#endif
