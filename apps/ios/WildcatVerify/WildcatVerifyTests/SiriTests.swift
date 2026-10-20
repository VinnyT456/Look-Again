import Foundation
import Testing
import UIKit
@testable import WildcatVerify

struct CropBoxTests {
    private func approx(_ a: CGRect, _ b: CGRect, tolerance: Double = 1e-9) -> Bool {
        abs(a.minX - b.minX) < tolerance && abs(a.minY - b.minY) < tolerance
            && abs(a.width - b.width) < tolerance && abs(a.height - b.height) < tolerance
    }

    @Test func outOfRangeBoxesAreClampedInside() {
        let box = CropBox(rect: CGRect(x: -0.5, y: 0.8, width: 2, height: 0.5))
        #expect(approx(box.rect, CGRect(x: 0, y: 0.5, width: 1, height: 0.5)))
    }

    @Test func tinyOrBrokenBoxesBecomeUsable() {
        #expect(abs(CropBox(rect: CGRect(x: 0.5, y: 0.5, width: 0, height: 0)).rect.width - CropBox.minSide) < 1e-9)
        #expect(CropBox(rect: CGRect(x: CGFloat.nan, y: 0, width: 1, height: 1)) == .whole)
    }

    @Test func movingStopsAtTheEdges() {
        let box = CropBox(rect: CGRect(x: 0.2, y: 0.2, width: 0.5, height: 0.5))
        #expect(approx(box.moved(by: CGSize(width: 1, height: -1)).rect, CGRect(x: 0.5, y: 0, width: 0.5, height: 0.5)))
        #expect(approx(box.moved(by: CGSize(width: 0.1, height: 0.1)).rect, CGRect(x: 0.3, y: 0.3, width: 0.5, height: 0.5)), "Moving keeps the size")
    }

    @Test func draggingACornerKeepsTheOppositeCornerFixed() {
        let box = CropBox(rect: CGRect(x: 0.2, y: 0.2, width: 0.5, height: 0.5))
        let grown = box.resized(.bottomTrailing, by: CGSize(width: 0.1, height: 0.2))
        #expect(approx(grown.rect, CGRect(x: 0.2, y: 0.2, width: 0.6, height: 0.7)))
        let shrunk = box.resized(.topLeading, by: CGSize(width: 0.1, height: 0.1))
        #expect(approx(shrunk.rect, CGRect(x: 0.3, y: 0.3, width: 0.4, height: 0.4)))
    }

    @Test func cornersCantCrossOrLeaveTheImage() {
        let box = CropBox(rect: CGRect(x: 0.2, y: 0.2, width: 0.5, height: 0.5))
        let crossed = box.resized(.topLeading, by: CGSize(width: 2, height: 2))
        #expect(abs(crossed.rect.width - CropBox.minSide) < 1e-9)
        #expect(abs(crossed.rect.maxX - 0.7) < 1e-9, "The opposite edge stays put")
        let outside = box.resized(.topTrailing, by: CGSize(width: 5, height: -5))
        #expect(outside.rect.maxX == 1)
        #expect(outside.rect.minY == 0)
    }

    @Test func scalingStaysCenteredAndInside() {
        let box = CropBox(rect: CGRect(x: 0.4, y: 0.4, width: 0.2, height: 0.2))
        let bigger = box.scaled(by: 2)
        #expect(approx(bigger.rect, CGRect(x: 0.3, y: 0.3, width: 0.4, height: 0.4)))
        #expect(CropBox.whole.scaled(by: 2) == .whole)
        #expect(abs(box.scaled(by: 0.01).rect.width - CropBox.minSide) < 1e-9)
    }

    @Test func pixelRectRoundsToWholePixels() {
        let box = CropBox(rect: CGRect(x: 0.25, y: 0.5, width: 0.5, height: 0.5))
        #expect(box.pixelRect(in: CGSize(width: 101, height: 200)) == CGRect(x: 25, y: 100, width: 51, height: 100))
    }
}

struct ImageCropperTests {
    /// Left half red, right half blue.
    private func halves() -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: CGSize(width: 200, height: 100), format: format).image { context in
            UIColor.red.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 100, height: 100))
            UIColor.blue.setFill()
            context.fill(CGRect(x: 100, y: 0, width: 100, height: 100))
        }
    }

    private func centerColor(_ image: UIImage) -> (red: UInt8, blue: UInt8)? {
        guard let cgImage = image.cgImage else { return nil }
        var pixel = [UInt8](repeating: 0, count: 4)
        guard let context = CGContext(data: &pixel, width: 1, height: 1, bitsPerComponent: 8, bytesPerRow: 4,
                                      space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
        context.draw(cgImage, in: CGRect(x: -Double(cgImage.width) / 2, y: -Double(cgImage.height) / 2,
                                         width: Double(cgImage.width), height: Double(cgImage.height)))
        return (pixel[0], pixel[2])
    }

    @Test func cropsOnlyTheBoxedPixels() throws {
        let box = CropBox(rect: CGRect(x: 0.5, y: 0, width: 0.5, height: 1))
        let cropped = try #require(ImageCropper.crop(halves(), to: box))
        #expect(cropped.size == CGSize(width: 100, height: 100))
        let color = try #require(centerColor(cropped))
        #expect(color.blue > 200 && color.red < 50, "The right half is blue")
    }

    @Test func wholeBoxKeepsTheFullImage() throws {
        let cropped = try #require(ImageCropper.crop(halves(), to: .whole))
        #expect(cropped.size == CGSize(width: 200, height: 100))
    }

    @Test func rotatedImagesAreCroppedAsDisplayed() throws {
        let base = try #require(halves().cgImage)
        let rotated = UIImage(cgImage: base, scale: 1, orientation: .right)
        #expect(rotated.size == CGSize(width: 100, height: 200))
        let cropped = try #require(ImageCropper.crop(rotated, to: CropBox(rect: CGRect(x: 0, y: 0, width: 1, height: 0.5))))
        #expect(cropped.size == CGSize(width: 100, height: 100))
    }
}

struct PhotoAreaFinderTests {
    /// A fake Bluesky screenshot: white page, grey text lines, and a photo
    /// (a colourful gradient) in a known place.
    private static let photoRect = CGRect(x: 40, y: 500, width: 1100, height: 800)

    private func screenshot() -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: CGSize(width: 1179, height: 2556), format: format).image { context in
            UIColor.white.setFill()
            context.fill(CGRect(x: 0, y: 0, width: 1179, height: 2556))
            UIColor.lightGray.setFill()
            for row in 0..<6 {
                context.fill(CGRect(x: 40, y: 200 + row * 45, width: 900 - row * 60, height: 22))
            }
            let photo = UIBezierPath(roundedRect: Self.photoRect, cornerRadius: 24)
            photo.addClip()
            let colors = [UIColor.systemOrange.cgColor, UIColor.systemPurple.cgColor, UIColor.systemTeal.cgColor] as CFArray
            if let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: colors, locations: nil) {
                context.cgContext.drawLinearGradient(gradient, start: Self.photoRect.origin,
                                                     end: CGPoint(x: Self.photoRect.maxX, y: Self.photoRect.maxY), options: [])
            }
        }
    }

    @Test func suggestsABoxAroundThePhoto() async {
        let image = screenshot()
        let box = await PhotoAreaFinder.suggest(in: image)
        let expected = CGRect(x: Self.photoRect.minX / image.size.width, y: Self.photoRect.minY / image.size.height,
                              width: Self.photoRect.width / image.size.width, height: Self.photoRect.height / image.size.height)
        let overlap = box.rect.intersection(expected)
        let union = box.rect.union(expected)
        let iou = overlap.isNull ? 0 : (overlap.width * overlap.height) / (union.width * union.height)
        #expect(iou > 0.6, "Suggested \(box.rect), expected about \(expected)")
    }

    @Test func blankImagesStillGetABox() async {
        let box = await PhotoAreaFinder.suggest(in: TestImages.solid(.white, width: 300, height: 600))
        #expect(box.rect.width >= CropBox.minSide && box.rect.height >= CropBox.minSide)
    }
}

@MainActor
struct ScreenshotCropViewModelTests {
    @Test func resetReturnsToTheSuggestion() async {
        let model = ScreenshotCropViewModel(image: TestImages.solid(width: 300, height: 600))
        #expect(model.isSuggesting)
        await model.suggest()
        #expect(!model.isSuggesting)
        let suggestion = model.box
        model.box = model.box.moved(by: CGSize(width: 0.3, height: 0.3))
        model.useWholeImage()
        #expect(model.isWholeImage)
        model.reset()
        #expect(model.box == suggestion)
    }

    @Test func croppedImageMatchesTheBox() throws {
        let model = ScreenshotCropViewModel(image: TestImages.solid(width: 400, height: 800))
        model.box = CropBox(rect: CGRect(x: 0, y: 0, width: 0.5, height: 0.25))
        let cropped = try #require(model.croppedImage())
        #expect(cropped.size == CGSize(width: 200, height: 200))
        #expect(model.aspectRatio == 0.5)
    }
}

@MainActor
struct SiriRoutingTests {
    private func makeApp() -> AppViewModel {
        AppViewModel(
            settings: isolatedSettings(),
            persistence: HistoryPersistence(directory: temporaryDirectory()),
            feedService: StubFeed(),
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier()
        )
    }

    @Test func aScreenshotOpensTheBoxScreenOnAFreshCheckTab() async {
        let app = makeApp()
        app.selectedTab = .learn
        app.check.inputURL = "half typed"
        await app.receiveScreenshot(TestImages.solid())
        #expect(app.pendingScreenshot != nil)
        #expect(app.selectedTab == .check)
        #expect(app.check.inputURL.isEmpty)
    }

    @Test func theBoxedAreaIsCheckedAndRecorded() async throws {
        let app = makeApp()
        await app.receiveScreenshot(TestImages.solid(width: 400, height: 800))
        app.checkBoxedArea(TestImages.solid(width: 200, height: 200))
        #expect(app.pendingScreenshot == nil)
        try await waitUntil { !app.check.path.isEmpty }
        let item = try #require(app.check.path.last)
        #expect(item.title == VerificationCase.screenshotTitle)
        #expect(item.displayHandle == "From a screenshot")
        #expect(item.imageURL?.isInMemoryImage == true, "Screenshots stay in memory")
        #expect(app.history.cases.first?.id == item.id, "Siri checks appear in My Checks")
    }

    @Test func openCaseShowsItInMyChecks() {
        let app = makeApp()
        app.history.record(SampleData.lakefill)
        #expect(app.openCase(id: SampleData.lakefill.id))
        #expect(app.selectedTab == .history)
        #expect(app.historyList.path == [SampleData.lakefill])
    }

    @Test func openingAMissingCaseFallsBackToMyChecks() {
        let app = makeApp()
        #expect(!app.openCase(id: UUID()))
        #expect(app.selectedTab == .history)
        #expect(app.historyList.path.isEmpty)
    }

    @Test func siriSetupOpensInSettings() {
        let app = makeApp()
        app.showSiriSetup()
        #expect(app.selectedTab == .settings)
        #expect(app.settingsPath == [.siriSetup])
    }

    @Test func copiedLinkCheckIsRecordedWithoutTouchingTheCheckTab() async throws {
        let images = ImageRepository.shared
        let imageURL = URL.inMemoryImage(UUID())
        images.storeUpload(TestImages.solid(), for: imageURL)
        defer { images.removeUpload(for: imageURL) }
        let post = BlueskyPost(
            authorHandle: "bob.bsky.social",
            text: "Sunset",
            postURL: URL(string: "https://bsky.app/profile/bob.bsky.social/post/1") ?? imageURL,
            imageURL: imageURL
        )
        let app = AppViewModel(
            settings: isolatedSettings(),
            persistence: HistoryPersistence(directory: temporaryDirectory()),
            feedService: StubFeed(),
            bluesky: StubBluesky(result: .success(post)),
            classifier: StubClassifier()
        )
        var thumbnail: UIImage?
        let item = try await app.check.checkInBackground(link: "https://bsky.app/profile/bob.bsky.social/post/1") {
            thumbnail = $0
        }
        #expect(thumbnail != nil)
        #expect(app.history.cases.first?.id == item.id)
        #expect(app.check.path.isEmpty)
        #expect(app.check.phase == .input)
    }
}

@MainActor
struct SiriTipTests {
    @Test func tipIsShownUntilDismissedAndRemembered() throws {
        let suite = "WildcatVerifyTests-\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: suite))
        let first = SettingsStore(defaults: defaults)
        #expect(!first.siriTipDismissed)
        first.siriTipDismissed = true
        #expect(SettingsStore(defaults: defaults).siriTipDismissed)
    }

    @Test func eraseAllDataBringsTheTipBack() {
        let settings = isolatedSettings()
        settings.siriTipDismissed = true
        settings.reset()
        #expect(!settings.siriTipDismissed)
    }
}

@MainActor
struct SiriCopyTests {
    @Test func errorsKeepTheAppsWording() {
        let wrapped = SiriCheckError.wrapping(BlueskyError.network)
        guard case .failed(let message) = wrapped else {
            Issue.record("Expected a wrapped message")
            return
        }
        #expect(message == BlueskyError.network.errorDescription)
        guard case .noCopiedLink = SiriCheckError.wrapping(SiriCheckError.noCopiedLink) else {
            Issue.record("Siri errors pass through")
            return
        }
    }

    @Test func snippetThumbnailsAreSharpButSmall() {
        let size = CheckSnippetView.thumbnailPixels(for: CGSize(width: 2000, height: 1000))
        #expect(size.height == 216)
        #expect(size.width == 432)
    }

    @Test func clipboardTextWithALinkIsFound() {
        #expect(ShareInput.blueskyLink(in: "look https://bsky.app/profile/a.bsky.social/post/3k") != nil)
        #expect(ShareInput.blueskyLink(in: "just some copied words") == nil)
    }
}

@MainActor
struct MissingScreenshotTests {
    @Test func checkImageWithoutAScreenshotExplainsTheSetup() {
        let app = AppViewModel(
            settings: isolatedSettings(),
            persistence: HistoryPersistence(directory: temporaryDirectory()),
            feedService: StubFeed(),
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier()
        )
        app.showMissingScreenshotHelp()
        #expect(app.showsMissingScreenshotHelp)
        #expect(app.selectedTab == .settings)
        #expect(app.settingsPath == [.siriSetup])
        #expect(!app.isShowingWelcome)
    }
}
