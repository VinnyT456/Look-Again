import SwiftUI

struct RootView: View {
    @Bindable var app: AppViewModel

    var body: some View {
        TabView(selection: $app.selectedTab) {
            Tab(AppTab.feed.title, systemImage: AppTab.feed.icon, value: .feed) {
                FeedScreen(viewModel: app.feed)
                    .tabEntrance(.feed, selection: app.selectedTab)
            }
            Tab(AppTab.learn.title, systemImage: AppTab.learn.icon, value: .learn) {
                LearnScreen(viewModel: app.learn)
                    .tabEntrance(.learn, selection: app.selectedTab)
            }
            Tab(AppTab.check.title, systemImage: AppTab.check.icon, value: .check) {
                CheckScreen(viewModel: app.check)
                    .tabEntrance(.check, selection: app.selectedTab)
            }
            Tab(AppTab.history.title, systemImage: AppTab.history.icon, value: .history) {
                HistoryScreen(viewModel: app.historyList)
                    .tabEntrance(.history, selection: app.selectedTab)
            }
            .badge(app.history.unseenCount)
            Tab(AppTab.settings.title, systemImage: AppTab.settings.icon, value: .settings) {
                SettingsScreen()
                    .tabEntrance(.settings, selection: app.selectedTab)
            }
        }
        .sensoryFeedback(trigger: app.selectedTab) { _, _ in
            app.settings.hapticsEnabled ? .selection : nil
        }
        .environment(app)
        .environment(\.hapticsEnabled, app.settings.hapticsEnabled)
        .environment(\.heatmapEnabled, app.settings.heatmapEnabled)
        .sheet(isPresented: $app.isShowingAbout) {
            AboutView()
        }
        .sheet(isPresented: $app.isShowingWelcome, onDismiss: app.finishWelcome) {
            WaysToCheckView(onDone: app.finishWelcome)
        }
        .fullScreenCover(item: $app.pendingScreenshot) { pending in
            ScreenshotCropScreen(
                image: pending.image,
                onCheck: app.checkBoxedArea,
                onCancel: { app.pendingScreenshot = nil }
            )
        }
    }
}

#Preview("Light") {
    RootView(app: AppViewModel())
}

#Preview("Dark") {
    RootView(app: AppViewModel())
        .preferredColorScheme(.dark)
}
