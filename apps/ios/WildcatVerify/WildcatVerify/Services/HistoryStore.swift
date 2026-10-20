import Observation

/// The user's checks. Kept in memory by default; when "Keep My Checks" is on,
/// every change is also written to disk through `HistoryPersistence`.
@MainActor
@Observable
final class HistoryStore {
    private(set) var cases: [VerificationCase]
    /// Checks added since the user last opened My Checks; drives the tab badge.
    private(set) var unseenCount = 0
    private(set) var isSaving: Bool

    private let images: ImageRepository
    private var persistence: HistoryPersistence?

    init(cases: [VerificationCase] = [], images: ImageRepository = .shared, persistence: HistoryPersistence? = nil) {
        self.images = images
        self.persistence = persistence
        self.isSaving = persistence != nil
        self.cases = persistence.map { $0.load() } ?? cases
    }

    /// Adds a case to the top of history, or moves it there if already present.
    func record(_ item: VerificationCase) {
        cases.removeAll { $0.id == item.id }
        cases.insert(item, at: 0)
        unseenCount += 1
        save()
    }

    func markSeen() {
        unseenCount = 0
    }

    func remove(_ item: VerificationCase) {
        cases.removeAll { $0.id == item.id }
        if let url = item.imageURL, url.isInMemoryImage {
            images.removeUpload(for: url)
        }
        save()
    }

    func clear() {
        cases.removeAll()
        unseenCount = 0
        images.removeAllUploads()
        save()
    }

    /// Turns saving on (writes the current checks) or off (deletes what was saved).
    func setPersistence(_ newValue: HistoryPersistence?) {
        if let newValue {
            persistence = newValue
            isSaving = true
            save()
        } else {
            persistence?.erase()
            persistence = nil
            isSaving = false
        }
    }

    private func save() {
        guard let persistence else { return }
        if let stored = try? persistence.save(cases, images: images) {
            cases = stored
        }
    }
}
