import SwiftUI

/// Full-screen practice photo to look closely: pinch or double-tap to zoom,
/// drag to move around. Clue marks appear once the case is answered.
struct PracticePhotoViewer: View {
    let imageName: String
    let description: String
    let credit: String?
    let hotspots: [PracticeHotspot]

    @Environment(\.dismiss) private var dismiss
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var scale = 1.0
    @State private var settledScale = 1.0
    @State private var offset = CGSize.zero
    @State private var settledOffset = CGSize.zero

    private static let maxScale = 5.0

    var body: some View {
        NavigationStack {
            Image(imageName)
                .resizable()
                .scaledToFit()
                .overlay {
                    if !hotspots.isEmpty {
                        PracticeHotspotOverlay(hotspots: hotspots)
                    }
                }
                .scaleEffect(scale)
                .offset(offset)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .contentShape(.rect)
                .gesture(zoom.simultaneously(with: pan))
                .onTapGesture(count: 2, perform: toggleZoom)
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("Photo: \(description)")
                .accessibilityAction(named: "Zoom in") { setScale(min(scale * 2, Self.maxScale)) }
                .accessibilityAction(named: "Zoom out") { setScale(max(scale / 2, 1)) }
                .background(.black)
                .safeAreaInset(edge: .bottom) {
                    if let credit {
                        Text(credit)
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.8))
                            .padding(.bottom, 8)
                    }
                }
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { dismiss() }
                    }
                }
                .toolbarBackground(.black, for: .navigationBar)
                .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    private var zoom: some Gesture {
        MagnifyGesture()
            .onChanged { value in
                scale = min(max(settledScale * value.magnification, 1), Self.maxScale)
            }
            .onEnded { _ in
                settledScale = scale
                if scale == 1 { resetOffset() }
            }
    }

    private var pan: some Gesture {
        DragGesture()
            .onChanged { value in
                guard scale > 1 else { return }
                offset = CGSize(width: settledOffset.width + value.translation.width,
                                height: settledOffset.height + value.translation.height)
            }
            .onEnded { _ in settledOffset = offset }
    }

    private func toggleZoom() {
        setScale(scale > 1 ? 1 : 2.5)
    }

    private func setScale(_ value: Double) {
        withAnimation(reduceMotion ? nil : .snappy) {
            scale = value
            settledScale = value
            if value == 1 { resetOffset() }
        }
    }

    private func resetOffset() {
        offset = .zero
        settledOffset = .zero
    }
}
