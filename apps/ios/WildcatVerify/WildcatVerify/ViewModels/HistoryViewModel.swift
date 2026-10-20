import Observation

/// My Checks: search, verdict scopes, delete and clear.
@MainActor
@Observable
final class HistoryViewModel {
    var path: [VerificationCase] = []
    var searchQuery = ""
    var scope: VerdictFilter = .all
    var isConfirmingClear = false

    private let store: HistoryStore

    init(store: HistoryStore) {
        self.store = store
    }

    var isEmpty: Bool { store.cases.isEmpty }

    var visibleCases: [VerificationCase] {
        let query = searchQuery.trimmingCharacters(in: .whitespaces)
        return store.cases.filter { item in
            guard scope.matches(item) else { return false }
            guard !query.isEmpty else { return true }
            return item.authorHandle.localizedStandardContains(query)
                || item.title.localizedStandardContains(query)
                || item.caption.localizedStandardContains(query)
        }
    }

    var isFiltering: Bool {
        scope != .all || !searchQuery.trimmingCharacters(in: .whitespaces).isEmpty
    }

    func open(_ item: VerificationCase) {
        path.append(item)
    }

    func delete(_ item: VerificationCase) {
        store.remove(item)
    }

    func confirmClear() {
        isConfirmingClear = true
    }

    func clearAll() {
        store.clear()
        path.removeAll()
        searchQuery = ""
        scope = .all
    }
}
