import SwiftUI

/// The app mark: the FaceCheck magnifier on its tile. The asset has a dark
/// variant, so it never glows against a dark navigation bar.
struct LogoTile: View {
    @ScaledMetric(relativeTo: .headline) private var size = Metrics.logo
    var scale = 1.0

    var body: some View {
        Image(.faceCheckMagnifier)
            .resizable()
            .interpolation(.high)
            .scaledToFill()
            .frame(width: size * scale, height: size * scale)
            .clipShape(.rect(cornerRadius: size * scale * 0.24))
            .accessibilityHidden(true)
    }
}

#Preview {
    HStack {
        LogoTile()
        LogoTile(scale: 2)
    }
}
