import ImageIO
import UIKit

/// Loads and caches images for cases. Decoding happens off the main actor and
/// is downsampled to the size it will be drawn at. Uploaded photos live only in
/// memory (never written to disk) and are dropped when history is cleared.
@MainActor
final class ImageRepository {
    static let shared = ImageRepository()

    /// Longest edge, in pixels, for images shown full-width or sent to the classifier.
    static let fullPixelSize = 2048.0

    private let cache = NSCache<NSString, UIImage>()
    private let rawData = NSCache<NSURL, NSData>()
    private var uploads: [URL: UIImage] = [:]
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
        cache.countLimit = 80
        rawData.countLimit = 20
    }

    func storeUpload(_ image: UIImage, for url: URL) {
        uploads[url] = image
    }

    func removeUpload(for url: URL) {
        uploads[url] = nil
    }

    func removeAllUploads() {
        uploads.removeAll()
    }

    func cachedImage(for url: URL, maxPixelSize: Double = fullPixelSize) -> UIImage? {
        uploads[url] ?? cache.object(forKey: Self.key(url, maxPixelSize))
    }

    /// Returns the image at `url`, decoded no larger than `maxPixelSize` on its longest edge.
    func image(for url: URL, maxPixelSize: Double = fullPixelSize) async throws -> UIImage {
        if let cached = cachedImage(for: url, maxPixelSize: maxPixelSize) { return cached }
        guard !url.isInMemoryImage else { throw URLError(.fileDoesNotExist) }

        let data: Data
        if let cachedData = rawData.object(forKey: url as NSURL) {
            data = cachedData as Data
        } else if url.isFileURL {
            // Photos saved by "Keep My Checks".
            data = try Data(contentsOf: url)
        } else {
            let (fetched, response) = try await session.data(from: url)
            if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                throw URLError(.badServerResponse)
            }
            rawData.setObject(fetched as NSData, forKey: url as NSURL)
            data = fetched
        }

        guard let image = await Self.downsample(data, maxPixelSize: maxPixelSize) else {
            throw URLError(.cannotDecodeContentData)
        }
        cache.setObject(image, forKey: Self.key(url, maxPixelSize))
        return image
    }

    /// Decodes and downsizes image data with ImageIO. Being `nonisolated async`,
    /// it runs off the main actor, so a 48 MP library photo never blocks the UI.
    nonisolated static func downsample(_ data: Data, maxPixelSize: Double) async -> UIImage? {
        let sourceOptions = [kCGImageSourceShouldCache: false] as CFDictionary
        guard let source = CGImageSourceCreateWithData(data as CFData, sourceOptions) else { return nil }
        let options = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceThumbnailMaxPixelSize: maxPixelSize,
        ] as CFDictionary
        guard let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, options) else { return nil }
        return UIImage(cgImage: cgImage)
    }

    private static func key(_ url: URL, _ size: Double) -> NSString {
        "\(Int(size))|\(url.absoluteString)" as NSString
    }
}
