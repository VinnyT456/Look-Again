import SwiftUI

/// A missed case, shown again with its answer, from the end-of-round list.
struct PracticeReviewSheet: View {
    let question: PracticeQuestion
    let picked: PracticeAnswer

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    PracticePostCard(question: question, showsHotspots: true)
                    PracticeAnswerButtons(picked: picked, answer: question.answer) { _ in }
                    PracticeFeedback(question: question, picked: picked, answerCount: 0, isLive: false)
                }
                .padding(20)
            }
            .navigationTitle("Take Another Look")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
