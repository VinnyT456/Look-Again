import CoreGraphics
import Foundation
import Testing
@testable import WildcatVerify

struct PatchHeatmapTests {
    private func map(_ fill: (Int) -> Float) -> PatchHeatmap? {
        PatchHeatmap(values: (0..<576).map(fill))
    }

    @Test func needsAFullGrid() {
        #expect(PatchHeatmap(values: []) == nil)
        #expect(PatchHeatmap(values: Array(repeating: 0, count: 575)) == nil)
        #expect(PatchHeatmap(values: Array(repeating: 0, count: 576)) != nil)
    }

    @Test func intensitiesKeepOnlyPushesTowardAI() throws {
        let heatmap = try #require(map { $0 == 0 ? 2 : ($0 == 1 ? 1 : -3) })
        let intensities = heatmap.intensities
        #expect(intensities[0] == 1, "Strongest cell is full intensity")
        #expect(intensities[1] == 0.5)
        #expect(intensities[2] == 0, "Cells pushing toward real are not shown")
        #expect(heatmap.hasSignal)
    }

    @Test func allNegativeMapHasNothingToShow() throws {
        let heatmap = try #require(map { _ in -1 })
        #expect(!heatmap.hasSignal)
        #expect(heatmap.intensities.allSatisfy { $0 == 0 })
    }

    @Test func coveredRegionMatchesTheCenterCrop() {
        // Square image: the model sees the centre 384/440 of each side.
        let square = PatchHeatmap.coveredRegion(imageSize: CGSize(width: 1000, height: 1000))
        let side = 384.0 / 440.0
        #expect(abs(square.width - side) < 1e-9)
        #expect(abs(square.x - (1 - side) / 2) < 1e-9)

        // Landscape: full crop of the short side, a narrower slice of the long side.
        let wide = PatchHeatmap.coveredRegion(imageSize: CGSize(width: 2000, height: 1000))
        #expect(abs(wide.height - side) < 1e-9)
        #expect(abs(wide.width - side / 2) < 1e-9)
        #expect(abs(wide.x + wide.width / 2 - 0.5) < 1e-9, "Centred horizontally")
    }

    @Test func degenerateSizeCoversEverything() {
        let region = PatchHeatmap.coveredRegion(imageSize: .zero)
        #expect(region.width == 1 && region.height == 1)
    }
}

@MainActor
struct HeatmapVisibilityTests {
    private func item(verdict: VerdictType, heatmap: PatchHeatmap?) -> VerificationCase {
        var item = verdict == .ai ? SampleData.monorail : SampleData.lakefill
        item.imageURL = URL.inMemoryImage(UUID())
        item.hotspot = nil
        item.isDemo = false
        item.heatmap = heatmap
        return item
    }

    private let strong = PatchHeatmap(values: (0..<576).map { Float($0 % 7) - 2 })

    @Test func aiVerdictWithMapShowsHeatmap() {
        let model = CheckResultsViewModel(item: item(verdict: .ai, heatmap: strong), images: ImageRepository())
        #expect(model.showsHeatmap)
        #expect(model.canToggleHighlight)
        #expect(model.canShowOnPhoto, "Show on Photo jumps to the heatmap")
    }

    @Test func realVerdictNeverShowsHeatmap() {
        let model = CheckResultsViewModel(item: item(verdict: .real, heatmap: strong), images: ImageRepository())
        #expect(!model.showsHeatmap, "On a Real verdict the map would only be noise")
        #expect(model.canToggleHighlight, "Real still offers 'No signs of AI generation found'")
        #expect(!model.canShowOnPhoto)
    }

    @Test func aiVerdictWithoutMapHasNoHighlight() {
        let model = CheckResultsViewModel(item: item(verdict: .ai, heatmap: nil), images: ImageRepository())
        #expect(!model.showsHeatmap)
        #expect(!model.canToggleHighlight)
    }

    @Test func flatMapIsNotShown() {
        let flat = PatchHeatmap(values: Array(repeating: -0.5, count: 576))
        let model = CheckResultsViewModel(item: item(verdict: .ai, heatmap: flat), images: ImageRepository())
        #expect(!model.showsHeatmap)
    }

    @Test func pipelineCarriesTheMapIntoResults() async throws {
        let pipeline = CheckPipeline(
            bluesky: StubBluesky(result: .failure(.network)),
            classifier: StubClassifier(result: ClassificationResult(verdict: .ai, confidence: 0.9, heatmap: strong)),
            images: ImageRepository()
        )
        let result = try await pipeline.checkImage(data: TestImages.pngData())
        #expect(result.heatmap == strong)
    }
}
