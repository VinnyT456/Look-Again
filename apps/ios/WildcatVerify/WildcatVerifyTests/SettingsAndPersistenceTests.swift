import Foundation
import Testing
@testable import WildcatVerify

@MainActor
struct SettingsStoreTests {
    @Test func freshInstallDefaults() {
        let settings = isolatedSettings()
        #expect(!settings.keepHistory, "Saving history is opt-in")
        #expect(settings.hapticsEnabled)
        #expect(settings.heatmapEnabled)
    }

    @Test func choicesSurviveRelaunch() throws {
        let suite = "WildcatVerifyTests-\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: suite))
        let first = SettingsStore(defaults: defaults)
        first.keepHistory = true
        first.hapticsEnabled = false
        let second = SettingsStore(defaults: defaults)
        #expect(second.keepHistory)
        #expect(!second.hapticsEnabled)
    }

    @Test func resetRestoresDefaults() {
        let settings = isolatedSettings()
        settings.keepHistory = true
        settings.heatmapEnabled = false
        settings.reset()
        #expect(!settings.keepHistory)
        #expect(settings.heatmapEnabled)
    }
}

@MainActor
struct HistoryPersistenceTests {
    private func makeUpload(in images: ImageRepository) -> VerificationCase {
        var item = SampleData.monorail
        item.id = UUID()
        item.isDemo = false
        item.imageURL = URL.inMemoryImage(item.id)
        item.heatmap = PatchHeatmap(values: (0..<576).map { Float($0) / 576 })
        images.storeUpload(TestImages.solid(width: 1600, height: 1200), for: item.imageURL!)
        return item
    }

    @Test func roundTripKeepsEverything() throws {
        let persistence = HistoryPersistence(directory: temporaryDirectory())
        let images = ImageRepository()
        let upload = makeUpload(in: images)
        try persistence.save([upload, SampleData.lakefill], images: images)

        let loaded = persistence.load()
        #expect(loaded.map(\.id) == [upload.id, SampleData.lakefill.id])
        #expect(loaded[0].heatmap == upload.heatmap)
        #expect(loaded[0].verdict == upload.verdict)
    }

    @Test func uploadedPhotosAreSavedSmallAndRepointed() async throws {
        let persistence = HistoryPersistence(directory: temporaryDirectory())
        let images = ImageRepository()
        let upload = makeUpload(in: images)
        let stored = try persistence.save([upload], images: images)

        let fileURL = try #require(stored.first?.imageURL)
        #expect(fileURL.isFileURL)
        #expect(FileManager.default.fileExists(atPath: fileURL.path()))
        let saved = try await ImageRepository().image(for: fileURL)
        #expect(max(saved.size.width, saved.size.height) <= HistoryPersistence.savedPhotoSize, "Saved copies are capped at 1024 px")
    }

    @Test func removingACheckDeletesItsPhoto() throws {
        let persistence = HistoryPersistence(directory: temporaryDirectory())
        let images = ImageRepository()
        let upload = makeUpload(in: images)
        let stored = try persistence.save([upload], images: images)
        let fileURL = try #require(stored.first?.imageURL)

        try persistence.save([], images: images)
        #expect(!FileManager.default.fileExists(atPath: fileURL.path()))
    }

    @Test func savedFolderIsExcludedFromBackups() throws {
        let directory = temporaryDirectory().appending(path: "History", directoryHint: .isDirectory)
        let persistence = HistoryPersistence(directory: directory)
        try persistence.save([SampleData.lakefill], images: ImageRepository())
        let values = try directory.resourceValues(forKeys: [.isExcludedFromBackupKey])
        #expect(values.isExcludedFromBackup == true)
    }

    @Test func eraseDeletesEverything() throws {
        let directory = temporaryDirectory()
        let persistence = HistoryPersistence(directory: directory)
        try persistence.save([SampleData.lakefill], images: ImageRepository())
        persistence.erase()
        #expect(!FileManager.default.fileExists(atPath: directory.path()))
        #expect(persistence.load().isEmpty)
    }

    @Test func corruptFileLoadsAsEmpty() throws {
        let directory = temporaryDirectory()
        try Data("not json".utf8).write(to: directory.appending(path: "history.json"))
        #expect(HistoryPersistence(directory: directory).load().isEmpty)
    }
}

@MainActor
struct KeepHistoryTests {
    @Test func offByDefaultWritesNothing() {
        let directory = temporaryDirectory().appending(path: "History")
        let app = AppViewModel(settings: isolatedSettings(), persistence: HistoryPersistence(directory: directory), feedService: StubFeed())
        app.history.record(SampleData.lakefill)
        #expect(!app.history.isSaving)
        #expect(!FileManager.default.fileExists(atPath: directory.path()))
    }

    @Test func turningOnSavesAndSurvivesRelaunch() throws {
        let suite = "WildcatVerifyTests-\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: suite))
        let persistence = HistoryPersistence(directory: temporaryDirectory().appending(path: "History"))

        let app = AppViewModel(settings: SettingsStore(defaults: defaults), persistence: persistence, feedService: StubFeed())
        app.history.record(SampleData.lakefill)
        app.setKeepHistory(true)
        app.history.record(SampleData.monorail)

        let relaunched = AppViewModel(settings: SettingsStore(defaults: defaults), persistence: persistence, feedService: StubFeed())
        #expect(relaunched.history.cases.map(\.id) == [SampleData.monorail.id, SampleData.lakefill.id])
    }

    @Test func turningOffDeletesSavedChecks() {
        let directory = temporaryDirectory().appending(path: "History")
        let app = AppViewModel(settings: isolatedSettings(), persistence: HistoryPersistence(directory: directory), feedService: StubFeed())
        app.setKeepHistory(true)
        app.history.record(SampleData.lakefill)
        #expect(FileManager.default.fileExists(atPath: directory.path()))

        app.setKeepHistory(false)
        #expect(!FileManager.default.fileExists(atPath: directory.path()))
        #expect(app.history.cases.count == 1, "Turning it off keeps this session's checks in memory")
    }

    @Test func eraseAllDataResetsEverything() {
        let directory = temporaryDirectory().appending(path: "History")
        let app = AppViewModel(settings: isolatedSettings(), persistence: HistoryPersistence(directory: directory), feedService: StubFeed())
        app.setKeepHistory(true)
        app.settings.hapticsEnabled = false
        app.history.record(SampleData.lakefill)

        app.eraseAllData()
        #expect(app.history.cases.isEmpty)
        #expect(!app.settings.keepHistory)
        #expect(app.settings.hapticsEnabled)
        #expect(!FileManager.default.fileExists(atPath: directory.path()))
    }
}

@MainActor
struct HeatmapSettingTests {
    @Test func turningHeatmapOffHidesIt() {
        var item = SampleData.monorail
        item.imageURL = URL.inMemoryImage(UUID())
        item.hotspot = nil
        item.heatmap = PatchHeatmap(values: (0..<576).map { Float($0 % 5) })
        let model = CheckResultsViewModel(item: item, images: ImageRepository())
        #expect(model.showsHeatmap)
        model.heatmapEnabled = false
        #expect(!model.showsHeatmap)
        #expect(!model.canToggleHighlight)
    }
}
