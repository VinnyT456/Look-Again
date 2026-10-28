import AppIntents
import UniformTypeIdentifiers

/// "Check Image with Look Again": the action in the "Check This Post"
/// shortcut (Take Screenshot → Check Image). The image arrives in memory, so
/// no Photos access is needed. The app opens so the user can box the photo.
struct CheckImageIntent: AppIntent {
    static let title: LocalizedStringResource = "Check Image"
    static var description: IntentDescription {
        IntentDescription(
            "Opens Look Again so you can box the photo in an image, such as a screenshot of a Bluesky post, and check whether it's real or AI. The image stays on this iPhone.",
            categoryName: "Checking"
        )
    }
    static let openAppWhenRun = true

    /// Added right after Take Screenshot, Shortcuts fills this with the
    /// screenshot instead of asking for a file.
    /// Optional so that running this action on its own (for example, picked
    /// directly for the Action Button) explains the setup instead of opening
    /// a file picker.
    @Parameter(title: "Image", supportedContentTypes: [.image], inputConnectionBehavior: .connectToPreviousIntentResult)
    var image: IntentFile?

    static var parameterSummary: some ParameterSummary {
        Summary("Check \(\.$image) with Look Again")
    }

    @MainActor
    func perform() async throws -> some IntentResult {
        guard let image else {
            AppViewModel.live.showMissingScreenshotHelp()
            return .result()
        }
        guard let picture = await ImageRepository.downsample(image.data, maxPixelSize: ImageRepository.fullPixelSize) else {
            throw SiriCheckError.unreadableImage
        }
        await AppViewModel.live.receiveScreenshot(picture)
        return .result()
    }
}
