import SwiftUI

/// Draws the 24×24 patch map as soft red cells. Weak cells are skipped so
/// noise doesn't tint the whole photo; a blur turns the grid into a smooth map.
struct HeatmapCanvas: View {
    let heatmap: PatchHeatmap

    /// Cells below this share of the strongest one aren't drawn.
    static let floor = 0.2

    var body: some View {
        let intensities = heatmap.intensities
        Canvas { context, size in
            let grid = PatchHeatmap.gridSize
            let cellWidth = size.width / Double(grid)
            let cellHeight = size.height / Double(grid)
            for row in 0..<grid {
                for column in 0..<grid {
                    let value = intensities[row * grid + column]
                    guard value >= Self.floor else { continue }
                    let rect = CGRect(x: Double(column) * cellWidth, y: Double(row) * cellHeight, width: cellWidth, height: cellHeight)
                    context.fill(Path(rect), with: .color(Self.color(for: value)))
                }
            }
        }
        // About half a cell: smooths the grid without washing out where it is.
        .blur(radius: 6)
    }

    /// Yellow for weaker influence through red for the strongest, so the
    /// most important areas stand out on any photo.
    static func color(for value: Double) -> Color {
        let t = min(max((value - floor) / (1 - floor), 0), 1)
        return Color(hue: 0.14 * (1 - t), saturation: 1, brightness: 1)
            .opacity(0.45 + 0.5 * t)
    }
}
