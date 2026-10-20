import SwiftUI

/// Stand-in for a case without a photo: the verdict's tint and glyph, so rows
/// stay scannable by result instead of showing a broken image.
struct NoPhotoPlaceholder: View {
    let verdict: VerdictType
    var glyph: Font = .title2
    var caption: String?

    var body: some View {
        ZStack {
            verdict.background
            VStack(spacing: 8) {
                Image(systemName: verdict.icon)
                    .font(glyph)
                    .foregroundStyle(verdict.color)
                if let caption {
                    Text(caption)
                        .font(.footnote)
                        .bold()
                        .foregroundStyle(verdict.textColor)
                }
            }
            .padding()
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(caption ?? "")
        .accessibilityHidden(caption == nil)
    }
}

#Preview {
    VStack {
        NoPhotoPlaceholder(verdict: .ai).frame(width: 56, height: 56)
        NoPhotoPlaceholder(verdict: .tampered, glyph: .largeTitle, caption: "No photo attached").frame(height: 160)
    }
    .padding()
}
