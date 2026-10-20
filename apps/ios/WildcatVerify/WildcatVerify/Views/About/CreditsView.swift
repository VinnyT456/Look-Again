import SwiftUI

/// Who made the detector, and the license it ships under. The MIT license asks
/// for its notice to travel with every copy, so the full text is bundled.
struct CreditsView: View {
    private let licenseText = Bundle.main
        .url(forResource: "community-forensics-vit-MIT", withExtension: "txt")
        .flatMap { try? String(contentsOf: $0, encoding: .utf8) }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 6) {
                    Text("CommunityForensics ViT")
                        .font(.headline)
                    Text("The detector is built on the Community Forensics model by Jeongsoo Park and Andrew Owens, trained on images from 4,803 generators. Hugging Face conversion by Han Yoon, Borderless / Ethix R&D.")
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 4)
                Text("WildcatVerify adds a linear probe and the patch heatmap on top, and runs everything on this iPhone.")
                    .foregroundStyle(.secondary)
            } header: {
                Text("Detection model")
            }

            Section("Paper") {
                Text("Park, J. and Owens, A. “Community Forensics: Using Thousands of Generators to Train Fake Image Detectors.” CVPR 2025, pp. 8245–8257.")
                if let url = AppLinks.detectorPaper {
                    Link("Read the Paper", destination: url)
                }
                if let url = AppLinks.detectorCode {
                    Link("Original Code", destination: url)
                }
                if let url = AppLinks.detectorModel {
                    Link("Model on Hugging Face", destination: url)
                }
            }

            if let licenseText {
                Section("License (MIT)") {
                    Text(licenseText)
                        .font(.footnote.monospaced())
                        .textSelection(.enabled)
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle("Credits")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        CreditsView()
    }
}
