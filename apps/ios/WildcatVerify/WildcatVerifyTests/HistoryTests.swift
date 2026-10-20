import Foundation
import Testing
@testable import WildcatVerify

@MainActor
struct HistoryTests {
    private func makeStore() -> HistoryStore {
        HistoryStore(cases: [SampleData.lakefill, SampleData.protestBanner, SampleData.monorail])
    }

    @Test func startsEmptyByDefault() {
        #expect(HistoryStore().cases.isEmpty)
    }

    @Test func recordMovesExistingCaseToTop() {
        let store = makeStore()
        store.record(SampleData.monorail)
        #expect(store.cases.first?.id == SampleData.monorail.id)
        #expect(store.cases.count == 3)
        #expect(store.unseenCount == 1)
        store.markSeen()
        #expect(store.unseenCount == 0)
    }

    @Test func scopeFiltersByVerdict() {
        let model = HistoryViewModel(store: makeStore())
        model.scope = .tampered
        #expect(model.visibleCases.map(\.verdict) == [.tampered])
    }

    @Test func searchMatchesAuthorAndTitle() {
        let model = HistoryViewModel(store: makeStore())
        model.searchQuery = "DAILYNORTHWESTERN"
        #expect(model.visibleCases.map(\.id) == [SampleData.lakefill.id])
        model.searchQuery = "monorail"
        #expect(model.visibleCases.map(\.id) == [SampleData.monorail.id])
    }

    @Test func searchIgnoresSurroundingSpacesAndCase() {
        let model = HistoryViewModel(store: makeStore())
        model.searchQuery = "   STORM  "
        #expect(model.visibleCases.map(\.id) == [SampleData.lakefill.id])
        #expect(model.isFiltering)
        model.searchQuery = "   "
        #expect(model.visibleCases.count == 3, "Blank search shows everything")
        #expect(!model.isFiltering)
    }

    @Test func searchAndScopeCombine() {
        let model = HistoryViewModel(store: makeStore())
        model.scope = .real
        model.searchQuery = "monorail"
        #expect(model.visibleCases.isEmpty, "Monorail is AI, so the Real scope hides it")
    }

    @Test func noMatchesIsDistinctFromEmptyHistory() {
        let model = HistoryViewModel(store: makeStore())
        model.searchQuery = "zzz-no-match"
        #expect(model.visibleCases.isEmpty)
        #expect(!model.isEmpty)
    }

    @Test func deletingACheckRemovesItsPhotoFromMemory() {
        let images = ImageRepository()
        var upload = SampleData.lakefill
        upload.imageURL = URL.inMemoryImage(upload.id)
        images.storeUpload(TestImages.solid(), for: upload.imageURL!)
        let store = HistoryStore(cases: [upload, SampleData.monorail], images: images)
        let model = HistoryViewModel(store: store)

        model.delete(upload)
        #expect(store.cases.map(\.id) == [SampleData.monorail.id])
        #expect(images.cachedImage(for: upload.imageURL!) == nil)
    }

    @Test func clearAllNeedsConfirmationFirst() {
        let store = makeStore()
        let model = HistoryViewModel(store: store)
        model.confirmClear()
        #expect(model.isConfirmingClear)
        #expect(store.cases.count == 3, "Asking to clear doesn't clear yet")
    }

    @Test func clearAllResetsEverything() {
        let model = HistoryViewModel(store: makeStore())
        model.scope = .ai
        model.searchQuery = "x"
        model.clearAll()
        #expect(model.isEmpty)
        #expect(model.scope == .all)
        #expect(model.searchQuery.isEmpty)
    }
}
