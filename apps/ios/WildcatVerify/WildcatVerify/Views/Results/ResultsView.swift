import SwiftUI

/// The verdict for one image, answer first: what the model concluded and how
/// sure it is, the photo, then why and what to do behind one tap.
struct ResultsView: View {
    @Bindable var viewModel: CheckResultsViewModel
    let onCheckAnother: (() -> Void)?
    var onAdjustArea: (() -> Void)?
    /// Every image of a multi-image post; empty for a single image.
    var postImages: [VerificationCase] = []
    var imageSelection: Binding<Int> = .constant(0)

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var showsDetails = false

    private var item: VerificationCase { viewModel.item }
    private static let photoID = "photo"

    var body: some View {
        ScrollViewReader { proxy in
            List {
                // The answer first: verdict, confidence, one paragraph.
                Section {
                    VerdictSummary(item: item)
                } footer: {
                    Text("A verdict is an estimate, not proof. Please don't use it on its own to accuse anyone.")
                }
                .listRowBackground(item.verdict.background)

                if item.isDemo {
                    Section {
                        DemoNotice()
                    }
                }

                if viewModel.hasPhoto {
                    Section {
                        ResultPhoto(viewModel: viewModel)
                            .listRowInsets(EdgeInsets())
                            .id(Self.photoID)
                        if viewModel.canToggleHighlight {
                            Picker("Photo view", selection: $viewModel.layer) {
                                ForEach(PhotoLayer.allCases) { layer in
                                    Text(layer.title).tag(layer)
                                }
                            }
                            .pickerStyle(.segmented)
                            .accessibilityHint("Highlight shows the areas that influenced the verdict")
                        }
                    }
                }

                if let onAdjustArea {
                    Section {
                        Button("Adjust the Checked Area", systemImage: "crop", action: onAdjustArea)
                    } footer: {
                        Text("Look Again found the photo in your screenshot by itself. If it picked the wrong area, box it yourself.")
                    }
                }

                if postImages.count > 1 {
                    Section {
                        PostImageStrip(images: postImages, selection: imageSelection)
                    } header: {
                        Text("\(postImages.count) images in this post")
                    } footer: {
                        Text("Each image is checked on its own. The most suspicious one opens first.")
                    }
                }

                if let credentials = item.credentials {
                    CredentialsSection(credentials: credentials)
                }

                // Everything else waits behind one tap.
                Section {
                    Button {
                        withAnimation(reduceMotion ? nil : .smooth(duration: 0.25)) { showsDetails.toggle() }
                    } label: {
                        HStack {
                            Text(showsDetails ? "Hide Details" : "Why This Verdict?")
                            Spacer()
                            Image(systemName: "chevron.down")
                                .rotationEffect(.degrees(showsDetails ? 180 : 0))
                                .foregroundStyle(.secondary)
                                .accessibilityHidden(true)
                        }
                        .contentShape(.rect)
                    }
                    .accessibilityIdentifier("resultDetails")
                }

                if showsDetails {
                    FindingsSection(item: item, canShowOnPhoto: viewModel.canShowOnPhoto) {
                        showOnPhoto(proxy)
                    }

                    Section("What to do") {
                        Text(item.suggestedAction)
                    }

                    SourceSection(item: item)
                }

                if let onCheckAnother {
                    Section {
                        Button("Check Another Image", systemImage: "arrow.counterclockwise", action: onCheckAnother)
                    }
                }
            }
            .listStyle(.insetGrouped)
        }
        .animation(reduceMotion ? nil : .smooth(duration: 0.25), value: viewModel.layer)
        .navigationTitle("Result")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            // Extensions can't present a second share sheet over the first.
            #if !SHARE_EXTENSION
            ToolbarItem(placement: .topBarTrailing) {
                ShareLink("Share Result", item: item.shareText)
            }
            #endif
        }
        .task(id: ObjectIdentifier(viewModel)) { await viewModel.loadImage() }
    }

    private func showOnPhoto(_ proxy: ScrollViewProxy) {
        viewModel.showOnPhoto()
        withAnimation(reduceMotion ? nil : .smooth) {
            proxy.scrollTo(Self.photoID, anchor: .top)
        }
    }
}

#Preview("Edited") {
    NavigationStack {
        CaseResultsScreen(item: SampleData.protestBanner, onCheckAnother: {})
    }
}

#Preview("AI · Dark") {
    NavigationStack {
        CaseResultsScreen(item: SampleData.monorail, onCheckAnother: {})
    }
    .preferredColorScheme(.dark)
}
