import UIKit

/// One Look Again case, shaped like a Bluesky post: who posted it, what
/// they wrote, and a plain description of the photo (or a bundled image).
/// Descriptions state what's visible without saying which detail matters;
/// the explanation and clues are only shown after answering.
struct PracticeQuestion: Identifiable, Hashable, Sendable {
    var id: String
    var author: String
    /// Practice handles use the reserved `.example` domain so no real
    /// account is ever labelled fake.
    var handle: String
    /// Relative time as Bluesky shows it, e.g. "2h".
    var posted: String
    var caption: String
    /// What the photo shows, for text-only play. It may name the deciding
    /// detail, because without a photo there's nothing else to look at.
    var imageDescription: String
    /// Optional bundled image shown instead of the description.
    var imageName: String?
    /// Neutral description for VoiceOver once there's a photo: says what's
    /// there without pointing at the giveaway. Falls back to `imageDescription`.
    var altText: String?
    /// Facts a photo can't show (replies, other coverage), drawn under the
    /// post like a reply. Shown in text and photo play alike.
    var context: String?
    /// Who took or made the photo and its license, e.g. "Photo: Jane Doe · CC BY 4.0".
    var credit: String?
    /// Regions to mark on the photo after answering.
    var hotspots: [PracticeHotspot] = []
    var answer: PracticeAnswer
    /// Why that answer is right, shown after the user picks.
    var explanation: String
    /// The specific clues, shown as a list under the explanation.
    var clues: [String]

    /// The bundled image to show, or nil when there isn't one or the name is
    /// missing from the app (then the text description is used instead).
    var resolvedImageName: String? {
        guard let imageName, UIImage(named: imageName) != nil else { return nil }
        return imageName
    }

    /// What VoiceOver reads for the photo.
    var spokenImageDescription: String {
        resolvedImageName == nil ? imageDescription : (altText ?? imageDescription)
    }
}
