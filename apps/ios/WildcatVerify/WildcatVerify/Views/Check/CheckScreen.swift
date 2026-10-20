import SwiftUI

/// The Check tab: the brand header and check card (or analysis in progress)
/// at the root, results pushed on top.
struct CheckScreen: View {
    @Environment(AppViewModel.self) private var app
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Bindable var viewModel: CheckViewModel

    var body: some View {
        NavigationStack(path: $viewModel.path) {
            ZStack {
                if viewModel.phase == .analyzing {
                    AnalyzingView(image: viewModel.analyzingImage, onCancel: viewModel.cancelAnalysis)
                        .transition(.opacity)
                } else {
                    CheckPage(viewModel: viewModel)
                        .transition(.opacity)
                }
            }
            .animation(reduceMotion ? nil : .smooth(duration: 0.25), value: viewModel.phase)
            .safeAreaInset(edge: .top, spacing: 0) {
                CheckHeader(onShowAbout: app.showAbout)
            }
            .toolbar(.hidden, for: .navigationBar)
            .navigationTitle(AppTab.check.title)
            .navigationDestination(for: VerificationCase.self) { item in
                CaseResultsScreen(item: item, onCheckAnother: app.startNewCheck, onAdjustArea: adjustArea(for: item))
            }
            .alert("Couldn't Check Image", isPresented: $viewModel.isShowingError) {
            } message: {
                Text(viewModel.errorMessage)
            }
        }
    }

    /// Screenshots boxed automatically can be re-boxed by hand.
    private func adjustArea(for item: VerificationCase) -> (() -> Void)? {
        guard item.title == VerificationCase.screenshotTitle, app.lastScreenshot != nil else { return nil }
        return { app.adjustLastScreenshot() }
    }
}
