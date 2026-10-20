import Foundation
import UIKit

/// Turns a Bluesky link or raw image data into a `VerificationCase`. Shared by
/// the app's Check tab and the share extension so both give identical results.
@MainActor
struct CheckPipeline {
    let bluesky: any BlueskyFetching
    let classifier: any ImageClassifying
    let images: ImageRepository

    init(
        bluesky: any BlueskyFetching = BlueskyService(),
        classifier: any ImageClassifying = ClassifierFactory.make(),
        images: ImageRepository = .shared
    ) {
        self.bluesky = bluesky
        self.classifier = classifier
        self.images = images
    }

    /// Fetches every photo in the post and classifies each. Returns the most
    /// suspicious one, with all of them in `postImages` when there's more than one.
    /// - Parameter onImage: called once the first photo is loaded, before classification.
    func checkPost(link: String, onImage: (UIImage) -> Void = { _ in }) async throws -> VerificationCase {
        let post = try await bluesky.fetchPost(from: link)
        var cases: [VerificationCase] = []
        for (index, url) in post.imageURLs.enumerated() {
            try Task.checkCancellation()
            let image = try await images.image(for: url)
            if index == 0 { onImage(image) }
            let result = try await classifier.classify(image)
            cases.append(makeCase(
                result: result,
                title: Self.title(from: post.text),
                handle: post.authorHandle,
                postURL: post.postURL,
                caption: post.text,
                imageURL: url
            ))
        }
        guard var lead = cases.max(by: { Self.suspicion($0) < Self.suspicion($1) }) else {
            throw BlueskyError.noImage
        }
        if cases.count > 1 { lead.postImages = cases }
        return lead
    }

    /// Orders verdicts by how strongly they point at a fake: a confident "AI"
    /// first, a confident "Real" last. Earlier images win ties.
    static func suspicion(_ item: VerificationCase) -> Int {
        switch item.verdict {
        case .ai: 200 + item.confidencePercentage
        case .tampered: 100 + item.confidencePercentage
        case .real: 100 - item.confidencePercentage
        }
    }

    /// Decodes image data (downsampled, metadata dropped), keeps it in memory
    /// only, and classifies it.
    func checkImage(data: Data, onImage: (UIImage) -> Void = { _ in }) async throws -> VerificationCase {
        guard let image = await ImageRepository.downsample(data, maxPixelSize: ImageRepository.fullPixelSize) else {
            throw CheckError.unreadablePhoto
        }
        // Credentials live in the file's metadata, which decoding drops, so
        // read them from the original bytes first.
        let credentials = await Task.detached(priority: .userInitiated) {
            ContentCredentialsReader.read(data)
        }.value
        var item = try await checkImage(image, onImage: onImage)
        item.credentials = credentials
        return item
    }

    /// Classifies an already-decoded image (e.g. the area boxed in a screenshot),
    /// keeping it in memory only.
    func checkImage(
        _ image: UIImage,
        title: String = "Uploaded photo",
        onImage: (UIImage) -> Void = { _ in }
    ) async throws -> VerificationCase {
        let id = UUID()
        let url = URL.inMemoryImage(id)
        images.storeUpload(image, for: url)
        onImage(image)
        let result = try await classifier.classify(image)
        var item = makeCase(
            result: result,
            title: title,
            handle: "",
            postURL: nil,
            caption: "",
            imageURL: url
        )
        item.id = id
        return item
    }

    /// Confidence as shown to people. Never certainty: 99.9% would otherwise
    /// round to "100%".
    nonisolated static func displayConfidence(_ confidence: Double) -> Int {
        min(99, max(0, Int((confidence * 100).rounded())))
    }

    /// First line of the post, trimmed to fit a list row.
    static func title(from text: String) -> String {
        let firstLine = text.split(whereSeparator: \.isNewline).first.map(String.init) ?? ""
        guard !firstLine.isEmpty else { return "Bluesky post" }
        return firstLine.count > 60 ? String(firstLine.prefix(59)) + "…" : firstLine
    }

    private func makeCase(
        result: ClassificationResult,
        title: String,
        handle: String,
        postURL: URL?,
        caption: String,
        imageURL: URL
    ) -> VerificationCase {
        let copy = VerdictCopy.for(result.verdict)
        return VerificationCase(
            title: title,
            authorHandle: handle,
            postURL: postURL,
            caption: caption,
            timeAgo: "Just now",
            imageURL: imageURL,
            verdict: result.verdict,
            confidencePercentage: Self.displayConfidence(result.confidence),
            plainSummary: copy.summary,
            suggestedAction: copy.action,
            detectedIssue: result.hotspot?.label,
            hotspot: result.hotspot,
            heatmap: result.heatmap,
            keyFindings: copy.findings,
            isDemo: classifier.isDemo
        )
    }
}
