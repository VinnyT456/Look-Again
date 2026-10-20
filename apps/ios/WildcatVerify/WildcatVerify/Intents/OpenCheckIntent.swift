import AppIntents

/// The Siri card's Open button: shows that check in My Checks. Hidden from the
/// Shortcuts app.
struct OpenCheckIntent: AppIntent {
    static let title: LocalizedStringResource = "Open Check"
    static let openAppWhenRun = true
    static let isDiscoverable = false

    @Parameter(title: "Check")
    var caseID: String

    init() {}

    init(caseID: UUID) {
        self.caseID = caseID.uuidString
    }

    @MainActor
    func perform() async throws -> some IntentResult {
        if let id = UUID(uuidString: caseID) {
            AppViewModel.live.openCase(id: id)
        }
        return .result()
    }
}
