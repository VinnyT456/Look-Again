import SwiftUI

/// An L-shaped corner grip with a 44 pt touch area.
struct CropHandle: View {
    let corner: CropCorner

    private let length = 22.0
    private let thickness = 4.0

    var body: some View {
        Path { path in
            path.move(to: CGPoint(x: 0, y: length))
            path.addLine(to: .zero)
            path.addLine(to: CGPoint(x: length, y: 0))
        }
        .stroke(.white, style: StrokeStyle(lineWidth: thickness, lineCap: .round, lineJoin: .round))
        .frame(width: length, height: length)
        .rotationEffect(rotation)
        .shadow(color: .black.opacity(0.4), radius: 2)
        .offset(inset)
        .frame(width: 44, height: 44)
        .contentShape(.rect)
    }

    /// The grip points into the box from its corner.
    private var rotation: Angle {
        switch corner {
        case .topLeading: .zero
        case .topTrailing: .degrees(90)
        case .bottomTrailing: .degrees(180)
        case .bottomLeading: .degrees(270)
        }
    }

    /// Nudges the L so its corner sits on the box corner.
    private var inset: CGSize {
        let d = length / 2 - thickness / 2
        switch corner {
        case .topLeading: return CGSize(width: d, height: d)
        case .topTrailing: return CGSize(width: -d, height: d)
        case .bottomLeading: return CGSize(width: d, height: -d)
        case .bottomTrailing: return CGSize(width: -d, height: -d)
        }
    }
}
