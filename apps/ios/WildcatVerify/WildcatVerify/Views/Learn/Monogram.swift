import SwiftUI

/// Initials in a circle, colored per name, standing in for an avatar.
struct Monogram: View {
    let name: String
    let size: Double

    /// Hues dark enough for white initials (3:1 or better at this size).
    private static let palette: [Color] = [.blue, .indigo, .purple, .brown, .red, Color(.systemGray)]

    private var initials: String {
        name.split(separator: " ")
            .compactMap { $0.first(where: \.isLetter) }
            .prefix(2)
            .map(String.init)
            .joined()
    }

    private var color: Color {
        let sum = name.unicodeScalars.reduce(0) { $0 + Int($1.value) }
        return Self.palette[sum % Self.palette.count]
    }

    var body: some View {
        Text(initials)
            .font(.system(size: size * 0.4, weight: .semibold))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(color, in: .circle)
            .accessibilityHidden(true)
    }
}
