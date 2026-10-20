import SwiftUI

struct AboutView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack(spacing: 16) {
                        LogoTile(scale: 2)
                        VStack(alignment: .leading, spacing: 2) {
                            Text("WildcatVerify")
                                .font(.title2)
                                .bold()
                            Text("Version \(Bundle.main.shortVersion)")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .accessibilityElement(children: .combine)
                    Text("Helps you judge whether a photo on Bluesky is genuine, edited, or AI-generated.")
                }

                Section("How it works") {
                    Label("Pick a post in Feed, paste a link, or choose a photo.", systemImage: "link")
                    Label("Read the verdict and the clues behind it.", systemImage: "text.magnifyingglass")
                    Label("Turn on Highlight to see the suspect area.", systemImage: "eye")
                }

                Section {
                    Text("Photos are analyzed on this iPhone and never uploaded. They're only saved if you turn on Keep My Checks in Settings.")
                    NavigationLink("Privacy Policy", value: AboutRoute.privacyPolicy)
                    NavigationLink("Terms of Use", value: AboutRoute.terms)
                } header: {
                    Text("Privacy")
                }

                Section {
                    NavigationLink("Credits", value: AboutRoute.credits)
                } footer: {
                    Text("Detector based on Community Forensics by Jeongsoo Park and Andrew Owens (CVPR 2025).")
                }
            }
            .navigationDestination(for: AboutRoute.self) { route in
                switch route {
                case .privacyPolicy: PrivacyPolicyView()
                case .credits: CreditsView()
                case .terms: TermsView()
                }
            }
            .navigationTitle("About")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done", action: close)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    private func close() {
        dismiss()
    }
}

private extension Bundle {
    var shortVersion: String {
        object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0"
    }
}

#Preview {
    AboutView()
}
