import PhotosUI
import SwiftUI

/// Dashed drop zone that opens the system photo picker.
struct PhotoDropzone: View {
    @Bindable var viewModel: CheckViewModel

    var body: some View {
        PhotosPicker(selection: $viewModel.photoSelection, matching: .images, photoLibrary: .shared()) {
            PhotoDropzoneLabel()
        }
        .buttonStyle(.pressableCard)
        .accessibilityLabel("Choose photo or screenshot to check")
    }
}
