import SwiftUI

/// Scrollable body of the Check tab: the copied-link offer, the check card
/// and the Siri tip. Past checks live in My Checks.
struct CheckPage: View {
    @Bindable var viewModel: CheckViewModel
    @Environment(AppViewModel.self) private var app
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                if viewModel.offersCopiedLink {
                    CopiedLinkOffer(
                        onPaste: { viewModel.checkPasted($0, explainIfNotBluesky: true) },
                        onDismiss: viewModel.dismissCopiedLinkOffer
                    )
                    .transition(.move(edge: .top).combined(with: .opacity))
                }
                CheckCard(viewModel: viewModel)
                    .staggeredAppear(0)
                if !app.settings.siriTipDismissed {
                    CheckSiriTip(onOpen: app.showSiriSetup, onDismiss: dismissTip)
                        .staggeredAppear(1)
                        .transition(.opacity)
                }
            }
            .padding(16)
                .frame(maxWidth: 640)
                .frame(maxWidth: .infinity)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(Color(.systemGroupedBackground))
        .animation(reduceMotion ? nil : .smooth, value: viewModel.offersCopiedLink)
        .task { await viewModel.refreshCopiedLinkOffer() }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else { return }
            Task { await viewModel.refreshCopiedLinkOffer() }
        }
    }

    private func dismissTip() {
        withAnimation(reduceMotion ? nil : .smooth) {
            app.settings.siriTipDismissed = true
        }
    }
}

#Preview {
    NavigationStack {
        CheckPage(viewModel: AppViewModel().check)
    }
    .environment(AppViewModel())
}
