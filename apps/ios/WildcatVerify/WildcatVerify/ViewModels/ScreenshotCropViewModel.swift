import Observation
import UIKit

/// The box screen: suggests where the photo is, lets the user adjust it, and
/// cuts out what's inside.
@MainActor
@Observable
final class ScreenshotCropViewModel {
    let image: UIImage
    var box: CropBox = .whole
    private(set) var isSuggesting = true
    private var suggestion: CropBox = .whole

    init(image: UIImage) {
        self.image = image
    }

    /// Width ÷ height of the screenshot, for laying it out.
    var aspectRatio: Double {
        guard image.size.height > 0 else { return 1 }
        return image.size.width / image.size.height
    }

    var isWholeImage: Bool { box == .whole }

    func suggest() async {
        let found = await PhotoAreaFinder.suggest(in: image)
        suggestion = found
        box = found
        isSuggesting = false
    }

    /// Back to Vision's suggestion.
    func reset() {
        box = suggestion
    }

    func useWholeImage() {
        box = .whole
    }

    func croppedImage() -> UIImage? {
        ImageCropper.crop(image, to: box)
    }
}
