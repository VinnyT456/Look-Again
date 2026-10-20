import Foundation
import Testing
@testable import WildcatVerify

@MainActor
struct CheckResultsViewModelTests {
    @Test func examplesHaveNoPhotoToHighlight() async {
        let model = CheckResultsViewModel(item: SampleData.monorail, images: ImageRepository())
        #expect(!model.hasPhoto)
        #expect(!model.canShowOnPhoto, "No photo means no Show on Photo button")
        await model.loadImage()
        #expect(model.image == nil)
        #expect(!model.imageFailed, "A missing photo is not a failure")
    }

    @Test func loadsUploadedPhoto() async {
        let images = ImageRepository()
        var item = SampleData.protestBanner
        item.imageURL = URL.inMemoryImage(item.id)
        images.storeUpload(TestImages.solid(), for: item.imageURL!)

        let model = CheckResultsViewModel(item: item, images: images)
        #expect(model.canShowOnPhoto)
        await model.loadImage()
        #expect(model.image != nil)
        #expect(!model.imageFailed)
    }

    @Test func photoThatWentAwayShowsUnavailable() async {
        var item = SampleData.lakefill
        item.imageURL = URL.inMemoryImage(UUID())
        let model = CheckResultsViewModel(item: item, images: ImageRepository())
        await model.loadImage()
        #expect(model.image == nil)
        #expect(model.imageFailed)
    }

    @Test func realVerdictNeverOffersShowOnPhoto() {
        var item = SampleData.lakefill
        item.imageURL = URL.inMemoryImage(UUID())
        item.hotspot = HotspotArea(xRatio: 0, yRatio: 0, widthRatio: 1, heightRatio: 1, label: "x")
        #expect(!CheckResultsViewModel(item: item, images: ImageRepository()).canShowOnPhoto)
    }

    @Test func showOnPhotoTurnsOnHighlight() {
        let model = CheckResultsViewModel(item: SampleData.monorail, images: ImageRepository())
        #expect(model.layer == .photo)
        model.showOnPhoto()
        #expect(model.layer == .highlight)
    }
}

@MainActor
struct AppViewModelTests {
    @Test func startsOnCheckTab() {
        #expect(AppViewModel().selectedTab == .check)
    }

    @Test func openingMyChecksClearsTheBadge() {
        let app = AppViewModel()
        app.history.record(SampleData.lakefill)
        #expect(app.history.unseenCount == 1)
        app.selectedTab = .learn
        #expect(app.history.unseenCount == 1, "Other tabs leave the badge alone")
        app.selectedTab = .history
        #expect(app.history.unseenCount == 0)
    }

    @Test func checkAnotherUnwindsEveryTab() {
        let app = AppViewModel()
        app.selectedTab = .learn
        app.learn.path = [.clueGuide(ClueGroup.guide[0].id)]
        app.historyList.path = [SampleData.lakefill]
        app.check.path = [SampleData.protestBanner]
        app.check.inputURL = "something"

        app.startNewCheck()
        #expect(app.selectedTab == .check)
        #expect(app.learn.path.isEmpty)
        #expect(app.historyList.path.isEmpty)
        #expect(app.check.path.isEmpty)
        #expect(app.check.inputURL.isEmpty)
    }

    @Test func aboutOpens() {
        let app = AppViewModel()
        app.showAbout()
        #expect(app.isShowingAbout)
    }
}
