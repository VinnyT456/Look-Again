import SwiftUI

/// Shown when Siri or Shortcuts hands over a screenshot: the user boxes the
/// photo in it, and only that area is checked.
struct ScreenshotCropScreen: View {
    let onCheck: (UIImage) -> Void
    let onCancel: () -> Void

    @State private var viewModel: ScreenshotCropViewModel
    @State private var isShowingError = false

    init(image: UIImage, onCheck: @escaping (UIImage) -> Void, onCancel: @escaping () -> Void) {
        self.onCheck = onCheck
        self.onCancel = onCancel
        _viewModel = State(initialValue: ScreenshotCropViewModel(image: image))
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("Drag the corners to fit the photo. Only what's inside the box is checked.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)

                CropCanvas(viewModel: viewModel)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)

                HStack(spacing: 12) {
                    Button("Reset", systemImage: "arrow.counterclockwise", action: viewModel.reset)
                        .disabled(viewModel.isSuggesting)
                    Spacer()
                    Button("Whole Image", systemImage: "arrow.up.left.and.arrow.down.right", action: viewModel.useWholeImage)
                        .disabled(viewModel.isWholeImage)
                }
                .labelStyle(.compact)
                .buttonStyle(.bordered)
                .controlSize(.large)

                Button("Check This Area", systemImage: "checkmark.shield", action: check)
                    .buttonStyle(.primary)
                    .disabled(viewModel.isSuggesting)
            }
            .padding(16)
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Box the Photo")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                }
            }
            .task { await viewModel.suggest() }
            .alert("Couldn't Read That Area", isPresented: $isShowingError) {
            } message: {
                Text("Try a bigger box, or use the whole image.")
            }
        }
    }

    private func check() {
        guard let cropped = viewModel.croppedImage() else {
            isShowingError = true
            return
        }
        onCheck(cropped)
    }
}

#Preview {
    ScreenshotCropScreen(
        image: UIImage(systemName: "photo") ?? UIImage(),
        onCheck: { _ in },
        onCancel: {}
    )
}
