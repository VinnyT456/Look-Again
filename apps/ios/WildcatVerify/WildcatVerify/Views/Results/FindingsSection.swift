import SwiftUI

/// The specific clues behind the verdict.
struct FindingsSection: View {
    let item: VerificationCase
    let canShowOnPhoto: Bool
    let onShowOnPhoto: () -> Void

    var body: some View {
        Section {
            ForEach(item.keyFindings, id: \.self) { finding in
                Label {
                    Text(finding)
                } icon: {
                    Image(systemName: item.verdict.findingIcon)
                        .foregroundStyle(item.verdict.textColor)
                }
            }
            if canShowOnPhoto {
                Button("Show on Photo", systemImage: "eye", action: onShowOnPhoto)
            }
        } header: {
            // Examples describe what was seen; detector results list things to
            // check, since the model doesn't report specific evidence.
            Text(item.isDemo ? "What we noticed" : "Things to check yourself")
        }
    }
}
