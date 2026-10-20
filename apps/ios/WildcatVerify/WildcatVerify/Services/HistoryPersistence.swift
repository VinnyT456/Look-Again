import Foundation
import UIKit

/// Saves My Checks on this iPhone when the user turns on "Keep My Checks".
///
/// - Results go to `Application Support/History/history.json`.
/// - Uploaded and shared photos (which otherwise live only in memory) are saved
///   as small JPEGs next to it, so their results still show the photo.
/// - The folder is excluded from iCloud/iTunes backups and uses complete file
///   protection, so it stays on this device and is encrypted while locked.
/// - Turning the setting off, or clearing My Checks, deletes the folder.
struct HistoryPersistence: Sendable {
    let directory: URL

    /// Longest edge of saved photos, in pixels.
    static let savedPhotoSize = 1024.0

    static var standard: HistoryPersistence {
        HistoryPersistence(directory: URL.applicationSupportDirectory.appending(path: "History", directoryHint: .isDirectory))
    }

    private var indexURL: URL { directory.appending(path: "history.json") }
    private var photosURL: URL { directory.appending(path: "Photos", directoryHint: .isDirectory) }

    func photoURL(for id: UUID) -> URL {
        photosURL.appending(path: "\(id.uuidString).jpg")
    }

    /// Saved checks, newest first. Missing or unreadable files give an empty list.
    func load() -> [VerificationCase] {
        guard let data = try? Data(contentsOf: indexURL) else { return [] }
        return (try? JSONDecoder().decode([VerificationCase].self, from: data)) ?? []
    }

    /// Writes the list, saving any in-memory photo it refers to and pointing the
    /// saved copy at it. Returns the cases as stored.
    @MainActor
    @discardableResult
    func save(_ cases: [VerificationCase], images: ImageRepository) throws -> [VerificationCase] {
        try prepareDirectory()
        var stored: [VerificationCase] = []
        var keptPhotos = Set<String>()

        for item in cases {
            var copy = item
            if let url = item.imageURL, url.isInMemoryImage, let image = images.cachedImage(for: url) {
                let file = photoURL(for: item.id)
                if !FileManager.default.fileExists(atPath: file.path()) {
                    try Self.jpegData(for: image)?.write(to: file, options: [.atomic, .completeFileProtection])
                }
                copy.imageURL = file
            }
            if let url = copy.imageURL, url.isFileURL {
                keptPhotos.insert(url.lastPathComponent)
            }
            stored.append(copy)
        }

        let data = try JSONEncoder().encode(stored)
        try data.write(to: indexURL, options: [.atomic, .completeFileProtection])
        removePhotos(except: keptPhotos)
        return stored
    }

    /// Deletes everything saved.
    func erase() {
        try? FileManager.default.removeItem(at: directory)
    }

    private func prepareDirectory() throws {
        try FileManager.default.createDirectory(at: photosURL, withIntermediateDirectories: true)
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        var folder = directory
        try folder.setResourceValues(values)
    }

    /// Deletes photos whose checks were removed.
    private func removePhotos(except kept: Set<String>) {
        let files = (try? FileManager.default.contentsOfDirectory(at: photosURL, includingPropertiesForKeys: nil)) ?? []
        for file in files where !kept.contains(file.lastPathComponent) {
            try? FileManager.default.removeItem(at: file)
        }
    }

    private static func jpegData(for image: UIImage) -> Data? {
        let longest = max(image.size.width * image.scale, image.size.height * image.scale)
        guard longest > savedPhotoSize else { return image.jpegData(compressionQuality: 0.8) }
        let factor = savedPhotoSize / longest
        let size = CGSize(width: image.size.width * image.scale * factor, height: image.size.height * image.scale * factor)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        let resized = UIGraphicsImageRenderer(size: size, format: format).image { _ in
            image.draw(in: CGRect(origin: .zero, size: size))
        }
        return resized.jpegData(compressionQuality: 0.8)
    }
}
