import SwiftUI

/// "Bluesky Post Link": the field, paste/clear, and the Check Post button.
struct CheckLinkInput: View {
    @Bindable var viewModel: CheckViewModel

    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @FocusState private var isFocused: Bool

    /// TextField shrinks text that overflows, so large text sizes get a prompt
    /// that fits instead of one scaled back down.
    private var prompt: String {
        dynamicTypeSize.isAccessibilitySize ? "Post link" : "Paste link to Bluesky post..."
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ViewThatFits(in: .horizontal) {
                HStack {
                    CheckLinkTitle()
                    Spacer()
                    hostLabel
                }
                VStack(alignment: .leading, spacing: 4) {
                    CheckLinkTitle()
                    hostLabel
                }
            }

            HStack(spacing: 4) {
                TextField("Bluesky post link", text: $viewModel.inputURL, prompt: Text(prompt))
                    .font(.body)
                    .accessibilityIdentifier("linkField")
                    .textContentType(.URL)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .submitLabel(.go)
                    .focused($isFocused)
                    .onSubmit(submit)

                if viewModel.inputURL.isEmpty {
                    PasteButton(payloadType: String.self, onPaste: paste)
                        .labelStyle(.iconOnly)
                        .buttonBorderShape(.circle)
                        .tint(.northwesternPurple)
                } else {
                    Button("Clear Link", systemImage: "xmark.circle.fill", action: clear)
                        .labelStyle(.iconOnly)
                        .foregroundStyle(.tertiary)
                        .frame(width: 44, height: 44)
                }
            }
            .padding(.leading, 16)
            .padding(.trailing, 4)
            .frame(minHeight: Metrics.controlHeight)
            .background(Color(.tertiarySystemFill), in: .rect(cornerRadius: Metrics.fieldRadius))
            .overlay {
                RoundedRectangle(cornerRadius: Metrics.fieldRadius)
                    .strokeBorder(isFocused ? Color.accentColor : .clear, lineWidth: 1.5)
            }

            Button("Check Post", systemImage: "arrow.right", action: submit)
                .buttonStyle(.primary)
                .disabled(!viewModel.canCheckPost)
        }
    }

    private var hostLabel: some View {
        Text("bsky.app")
            .font(.caption)
            .bold()
            .foregroundStyle(.secondary)
            .accessibilityHidden(true)
    }

    private func submit() {
        isFocused = false
        viewModel.checkPost()
    }

    /// Pasting a Bluesky post link checks it straight away.
    private func paste(_ strings: [String]) {
        guard let first = strings.first else { return }
        isFocused = false
        viewModel.checkPasted(first)
    }

    private func clear() {
        viewModel.inputURL = ""
    }
}
