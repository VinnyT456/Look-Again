import Foundation
import UniformTypeIdentifiers

/// Reads the share sheet's attachments and picks the best thing to check:
/// an image first, then a Bluesky URL, then a Bluesky link inside shared text.
@MainActor
enum ShareItemLoader {
    static func input(from providers: [NSItemProvider]) async -> ShareInput? {
        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.image.identifier) {
            if let data = await loadData(provider, type: .image) {
                return .image(data)
            }
        }
        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
            if let url = await loadURL(provider), BlueskyService.parse(url.absoluteString) != nil {
                return .link(url.absoluteString)
            }
        }
        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
            if let text = await loadText(provider), let link = ShareInput.blueskyLink(in: text) {
                return .link(link)
            }
        }
        return nil
    }

    private static func loadData(_ provider: NSItemProvider, type: UTType) async -> Data? {
        await withCheckedContinuation { continuation in
            _ = provider.loadDataRepresentation(for: type) { data, _ in
                continuation.resume(returning: data)
            }
        }
    }

    private static func loadURL(_ provider: NSItemProvider) async -> URL? {
        await withCheckedContinuation { continuation in
            _ = provider.loadObject(ofClass: URL.self) { url, _ in
                continuation.resume(returning: url)
            }
        }
    }

    private static func loadText(_ provider: NSItemProvider) async -> String? {
        await withCheckedContinuation { continuation in
            _ = provider.loadObject(ofClass: String.self) { text, _ in
                continuation.resume(returning: text)
            }
        }
    }
}
