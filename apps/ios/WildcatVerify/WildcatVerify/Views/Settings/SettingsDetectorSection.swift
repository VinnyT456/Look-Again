import SwiftUI

/// What the detector is, where it runs, and what it can't do.
struct SettingsDetectorSection: View {
    private let usingRealModel = !ClassifierFactory.make().isDemo

    var body: some View {
        Section {
            LabeledContent("Model", value: usingRealModel ? "CommunityForensics ViT" : "Demo (model not loaded)")
            LabeledContent("Runs on", value: "This iPhone")
            LabeledContent("Answers", value: "Likely Real or Likely AI")
            LabeledContent("Calls it AI at", value: "\(Int(CoreMLImageClassifier.threshold * 100))% or higher")
        } header: {
            Text("Detector")
        } footer: {
            Text("The detector looks for signs of AI generation. It can't tell whether a real photo was edited or shared with a misleading caption, and no detector is always right.")
        }
    }
}
