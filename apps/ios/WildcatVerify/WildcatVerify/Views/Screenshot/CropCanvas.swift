import SwiftUI

/// The screenshot fitted to the space, dimmed outside the box, with a box that
/// moves when dragged and resizes from its corners.
struct CropCanvas: View {
    @Bindable var viewModel: ScreenshotCropViewModel

    /// The box when the current drag began; drags apply to it, not to the
    /// already-moved box, so the box tracks the finger exactly.
    @State private var dragStart: CropBox?

    var body: some View {
        GeometryReader { proxy in
            let size = fittedSize(in: proxy.size)
            let frame = viewModel.box.rect.scaled(to: size)

            ZStack(alignment: .topLeading) {
                Image(uiImage: viewModel.image)
                    .resizable()
                    .frame(width: size.width, height: size.height)
                    .accessibilityHidden(true)

                Path { path in
                    path.addRect(CGRect(origin: .zero, size: size))
                    path.addRect(frame)
                }
                .fill(.black.opacity(0.55), style: FillStyle(eoFill: true))
                .allowsHitTesting(false)

                Rectangle()
                    .strokeBorder(.white, lineWidth: 2)
                    .shadow(color: .black.opacity(0.4), radius: 2)
                    .frame(width: frame.width, height: frame.height)
                    .contentShape(.rect)
                    .offset(x: frame.minX, y: frame.minY)
                    .gesture(moveGesture(size: size))
                    .accessibilityElement()
                    .accessibilityLabel("Box")
                    .accessibilityValue(accessibilityValue)
                    .accessibilityHint("Swipe up or down to make it bigger or smaller")
                    .accessibilityAdjustableAction { direction in
                        switch direction {
                        case .increment: viewModel.box = viewModel.box.scaled(by: 1.15)
                        case .decrement: viewModel.box = viewModel.box.scaled(by: 1 / 1.15)
                        @unknown default: break
                        }
                    }

                ForEach(CropCorner.allCases, id: \.self) { corner in
                    CropHandle(corner: corner)
                        .position(corner.point(in: frame))
                        .gesture(resizeGesture(corner, size: size))
                        .accessibilityHidden(true)
                }

                if viewModel.isSuggesting {
                    ProgressView("Finding the photo…")
                        .padding(12)
                        .background(.regularMaterial, in: .rect(cornerRadius: 12))
                        .frame(width: size.width, height: size.height)
                }
            }
            .frame(width: size.width, height: size.height)
            .clipShape(.rect)
            .frame(width: proxy.size.width, height: proxy.size.height)
            .animation(dragStart == nil ? .snappy : nil, value: viewModel.box)
        }
    }

    private var accessibilityValue: String {
        let r = viewModel.box.rect
        return "\(Int((r.width * 100).rounded())) percent wide, \(Int((r.height * 100).rounded())) percent tall"
    }

    private func fittedSize(in space: CGSize) -> CGSize {
        let ratio = viewModel.aspectRatio
        guard space.width > 0, space.height > 0 else { return .zero }
        return space.width / space.height > ratio
            ? CGSize(width: space.height * ratio, height: space.height)
            : CGSize(width: space.width, height: space.width / ratio)
    }

    private func moveGesture(size: CGSize) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                let start = dragStart ?? viewModel.box
                dragStart = start
                viewModel.box = start.moved(by: value.translation.normalized(by: size))
            }
            .onEnded { _ in dragStart = nil }
    }

    private func resizeGesture(_ corner: CropCorner, size: CGSize) -> some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { value in
                let start = dragStart ?? viewModel.box
                dragStart = start
                viewModel.box = start.resized(corner, by: value.translation.normalized(by: size))
            }
            .onEnded { _ in dragStart = nil }
    }
}

private extension CGSize {
    func normalized(by size: CGSize) -> CGSize {
        guard size.width > 0, size.height > 0 else { return .zero }
        return CGSize(width: width / size.width, height: height / size.height)
    }
}

private extension CGRect {
    func scaled(to size: CGSize) -> CGRect {
        CGRect(x: minX * size.width, y: minY * size.height, width: width * size.width, height: height * size.height)
    }
}

private extension CropCorner {
    func point(in frame: CGRect) -> CGPoint {
        switch self {
        case .topLeading: CGPoint(x: frame.minX, y: frame.minY)
        case .topTrailing: CGPoint(x: frame.maxX, y: frame.minY)
        case .bottomLeading: CGPoint(x: frame.minX, y: frame.maxY)
        case .bottomTrailing: CGPoint(x: frame.maxX, y: frame.maxY)
        }
    }
}
