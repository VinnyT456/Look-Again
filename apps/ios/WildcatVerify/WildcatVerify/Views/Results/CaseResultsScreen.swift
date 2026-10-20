import SwiftUI

/// Navigation destination for a case. Owns its view model so the
/// Photo/Highlight choice survives parent re-renders.
struct CaseResultsScreen: View {
    /// One view model per image; a single-image case has exactly one.
    @State private var viewModels: [CheckResultsViewModel]
    @State private var selection: Int
    @Environment(\.heatmapEnabled) private var heatmapEnabled
    /// Nil hides "Check Another Image" (the share extension uses Done instead).
    let onCheckAnother: (() -> Void)?
    /// For screenshots boxed automatically: reopen the box screen.
    let onAdjustArea: (() -> Void)?
    private let postImages: [VerificationCase]

    init(item: VerificationCase, onCheckAnother: (() -> Void)?, onAdjustArea: (() -> Void)? = nil) {
        self.onAdjustArea = onAdjustArea
        let images = item.postImages ?? []
        postImages = images.count > 1 ? images : []
        let cases = postImages.isEmpty ? [item] : postImages
        _viewModels = State(initialValue: cases.map { CheckResultsViewModel(item: $0) })
        // Open on the most suspicious image, which is the case itself.
        _selection = State(initialValue: cases.firstIndex { $0.id == item.id } ?? 0)
        self.onCheckAnother = onCheckAnother
    }

    var body: some View {
        ResultsView(
            viewModel: viewModels[selection],
            onCheckAnother: onCheckAnother,
            onAdjustArea: onAdjustArea,
            postImages: postImages,
            imageSelection: $selection
        )
        .onChange(of: heatmapEnabled, initial: true) { _, isEnabled in
            viewModels.forEach { $0.heatmapEnabled = isEnabled }
        }
    }
}
