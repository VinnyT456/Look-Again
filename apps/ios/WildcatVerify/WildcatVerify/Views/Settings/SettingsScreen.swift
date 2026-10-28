import SwiftUI

/// Preferences, what the detector can and can't do, privacy, and data controls.
struct SettingsScreen: View {
    @Environment(AppViewModel.self) private var app

    var body: some View {
        @Bindable var app = app

        NavigationStack(path: $app.settingsPath) {
            List {
                if BlueskyOAuthConfig.isSignInAvailable || app.account.isSignedIn {
                    SettingsAccountSection()
                }
                SettingsSiriSection()
                SettingsHistorySection()
                SettingsPreferencesSection(settings: app.settings)
                SettingsFeedSection(settings: app.settings)
                SettingsDetectorSection()
                SettingsAboutSection()
                SettingsEraseSection()
            }
            .listStyle(.insetGrouped)
            .brandToolbar(AppTab.settings.title, onShowAbout: app.showAbout)
            .navigationDestination(for: SettingsRoute.self) { route in
                switch route {
                case .siriSetup: SiriSetupView()
                case .privacyPolicy: PrivacyPolicyView()
                case .credits: CreditsView()
                case .terms: TermsView()
                case .hiddenAccounts: HiddenAccountsView(settings: app.settings)
                case .waysToCheck: WaysToCheckView()
                }
            }
        }
    }
}
