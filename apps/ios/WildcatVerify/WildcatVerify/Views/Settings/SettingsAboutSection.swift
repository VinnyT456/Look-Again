import SwiftUI

/// Privacy policy, terms, credits, support and version.
struct SettingsAboutSection: View {
    var body: some View {
        Section("About") {
            NavigationLink(value: SettingsRoute.privacyPolicy) {
                Label("Privacy Policy", systemImage: "hand.raised")
            }
            NavigationLink(value: SettingsRoute.terms) {
                Label("Terms of Use", systemImage: "doc.text")
            }
            .accessibilityIdentifier("termsRow")
            NavigationLink(value: SettingsRoute.credits) {
                Label("Credits", systemImage: "text.book.closed")
            }
            .accessibilityIdentifier("creditsRow")
            if let url = AppLinks.support {
                Link(destination: url) {
                    Label("Contact Support", systemImage: "envelope")
                }
            }
            LabeledContent("Version", value: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0")
        }
    }
}
