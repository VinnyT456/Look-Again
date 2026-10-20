/// The one place that decides which classifier the app and the share extension use.
///
/// Uses the bundled Core ML detector (`Resources/Models/WildcatDetector.mlpackage`,
/// exported from `ml/checkpoints/coreml`). Falls back to the labelled demo
/// classifier only if the model can't be found or loaded, so results are never
/// silently fake.
enum ClassifierFactory {
    /// Loaded once per process; the model is ~42 MB.
    private static let shared: any ImageClassifying = CoreMLImageClassifier.load() ?? DemoImageClassifier()

    static func make() -> any ImageClassifying {
        shared
    }
}
