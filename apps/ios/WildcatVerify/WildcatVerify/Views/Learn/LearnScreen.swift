import SwiftUI

/// Learn to spot fakes: a Look Again round played in place, and the clue guide.
struct LearnScreen: View {
    @Environment(AppViewModel.self) private var app
    @Environment(\.hapticsEnabled) private var hapticsEnabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Bindable var viewModel: LearnViewModel

    private var practice: PracticeViewModel { viewModel.practice }

    var body: some View {
        NavigationStack(path: $viewModel.path) {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 32) {
                        PracticeRoundCard(viewModel: viewModel)
                            .id("round")
                        ClueIndex(groups: viewModel.clueGroups)
                    }
                    .padding(16)
                    .frame(maxWidth: 640)
                    .frame(maxWidth: .infinity)
                }
                .background(Color(.systemGroupedBackground))
                .onChange(of: practice.index) {
                    // A new post starts at the top of the card.
                    proxy.scrollTo("round", anchor: .top)
                }
                .onChange(of: practice.answerCount) {
                    // VoiceOver moves to the result headline (PracticeFeedback),
                    // which reads it; no separate announcement.
                    // Bring the answers and the result into view without
                    // pushing the headline off screen at large text sizes.
                    withAnimation(reduceMotion ? nil : .smooth) {
                        proxy.scrollTo(PracticeRoundCard.answersID, anchor: UnitPoint(x: 0.5, y: 0.3))
                    }
                }
            }
            .brandToolbar(AppTab.learn.title, onShowAbout: app.showAbout)
            .navigationDestination(for: LearnRoute.self) { route in
                switch route {
                case .clueGuide(let id):
                    ClueGuideView(groups: viewModel.clueGroups, initial: id)
                }
            }
            .sensoryFeedback(trigger: practice.answerCount) { _, _ in
                guard hapticsEnabled else { return nil }
                return practice.lastAnswerWasCorrect ? .success : .impact(weight: .light)
            }
        }
    }
}

#Preview {
    LearnScreen(viewModel: LearnViewModel())
        .environment(AppViewModel())
}
