import SwiftUI

/// The Check page's main card: link input, divider, photo drop zone and the
/// privacy line.
struct CheckCard: View {
    @Bindable var viewModel: CheckViewModel
    @Environment(AppViewModel.self) private var app

    var body: some View {
        VStack(spacing: 20) {
            CheckLinkInput(viewModel: viewModel)
            OrUploadDivider()
            PhotoDropzone(viewModel: viewModel)
            Label {
                Text(app.settings.keepHistory
                     ? "Checks saved on this iPhone • Change in Settings"
                     : "Private • Photos are not stored")
            } icon: {
                Image(systemName: "checkmark.shield.fill")
                    .foregroundStyle(.tint)
            }
            .font(.footnote)
            .foregroundStyle(.secondary)
        }
        .padding(20)
        .background(Color(.secondarySystemGroupedBackground), in: .rect(cornerRadius: Metrics.cardRadius))
        .overlay {
            RoundedRectangle(cornerRadius: Metrics.cardRadius)
                .strokeBorder(Color(.separator).opacity(0.5), lineWidth: 0.5)
        }
    }
}
