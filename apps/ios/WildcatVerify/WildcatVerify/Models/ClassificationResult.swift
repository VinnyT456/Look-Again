/// Output of the 3-class authenticity model.
struct ClassificationResult: Sendable {
    var verdict: VerdictType
    /// 0–1.
    var confidence: Double
    var hotspot: HotspotArea?
    /// Per-patch map from the detector, when the model provides one.
    var heatmap: PatchHeatmap?
}
