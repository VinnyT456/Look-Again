import SwiftUI

/// Places its first subview at a rectangle given as fractions (0–1) of the
/// space it is offered. Laid over an aspect-fit image, that space is exactly
/// the image, so hotspot ratios map straight onto pixels.
struct NormalizedRectLayout: Layout {
    var x: Double
    var y: Double
    var width: Double
    var height: Double

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        proposal.replacingUnspecifiedDimensions()
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        guard let subview = subviews.first else { return }
        subview.place(
            at: CGPoint(x: bounds.minX + x * bounds.width, y: bounds.minY + y * bounds.height),
            anchor: .topLeading,
            proposal: ProposedViewSize(width: width * bounds.width, height: height * bounds.height)
        )
    }
}
