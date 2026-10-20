import SwiftUI

/// For posts with several images: every image with its verdict. Tap one to
/// see its result.
struct PostImageStrip: View {
    let images: [VerificationCase]
    @Binding var selection: Int

    var body: some View {
        ScrollView(.horizontal) {
            HStack(spacing: 12) {
                ForEach(images.indices, id: \.self) { index in
                    let item = images[index]
                    Button {
                        selection = index
                    } label: {
                        VStack(spacing: 6) {
                            CaseThumbnail(item: item, baseSize: 64)
                                .overlay {
                                    RoundedRectangle(cornerRadius: Metrics.thumbnailRadius)
                                        .strokeBorder(index == selection ? Color.accentColor : .clear, lineWidth: 3)
                                }
                            Label(item.verdict.shortLabel, systemImage: item.verdict.icon)
                                .labelStyle(.compact)
                                .font(.caption)
                                .bold()
                                .foregroundStyle(item.verdict.textColor)
                        }
                        .contentShape(.rect)
                    }
                    .buttonStyle(.pressableCard)
                    .accessibilityLabel("Image \(index + 1): \(item.verdict.label), \(item.confidencePercentage) percent")
                    .accessibilityAddTraits(index == selection ? .isSelected : [])
                }
            }
            .padding(.vertical, 4)
        }
        .scrollIndicators(.hidden)
    }
}
