import Testing
import UIKit
@testable import WildcatVerify

@MainActor
struct PracticeViewModelTests {
    private let bank = PracticeBank.questions

    private func makeRound() -> PracticeViewModel {
        PracticeViewModel(questions: bank, shuffle: false)
    }

    @Test func roundIsCappedAtEightQuestions() {
        let model = makeRound()
        #expect(model.round.count == PracticeViewModel.roundLength)
        #expect(model.phase == .answering)
        #expect(model.progressText == "1 of 8")
    }

    @Test func shortBankUsesEveryQuestion() {
        let model = PracticeViewModel(questions: Array(bank.prefix(3)), shuffle: false)
        #expect(model.round.count == 3)
    }

    @Test func emptyBankFinishesImmediately() {
        let model = PracticeViewModel(questions: [])
        #expect(model.phase == .finished)
        #expect(model.current == nil)
        model.select(.ai)
        #expect(model.score == 0, "Nothing to answer")
    }

    @Test func rightAnswerScores() throws {
        let model = makeRound()
        let question = try #require(model.current)
        model.select(question.answer)
        #expect(model.score == 1)
        #expect(model.lastAnswerWasCorrect)
        #expect(model.phase == .revealed(picked: question.answer))
    }

    @Test func wrongAnswerDoesNotScore() throws {
        let model = makeRound()
        let question = try #require(model.current)
        let wrong = try #require(PracticeAnswer.allCases.first { $0 != question.answer })
        model.select(wrong)
        #expect(model.score == 0)
        #expect(!model.lastAnswerWasCorrect)
    }

    @Test func cannotAnswerTwice() throws {
        let model = makeRound()
        let question = try #require(model.current)
        model.select(question.answer)
        model.select(question.answer)
        #expect(model.score == 1)
        #expect(model.answerCount == 1)
    }

    @Test func cannotSkipWithoutAnswering() {
        let model = makeRound()
        model.next()
        #expect(model.index == 0)
        #expect(model.phase == .answering)
    }

    @Test func perfectRoundEndsWithFullScore() throws {
        let model = makeRound()
        for _ in 0..<PracticeViewModel.roundLength {
            let question = try #require(model.current)
            model.select(question.answer)
            model.next()
        }
        #expect(model.phase == .finished)
        #expect(model.score == 8)
        #expect(model.summary == "Every one right.")
        #expect(model.scoreLine == "8 of 8 right")
    }

    @Test func lowScoreSuggestsTheGuide() throws {
        let model = makeRound()
        for _ in 0..<PracticeViewModel.roundLength {
            let question = try #require(model.current)
            let wrong = try #require(PracticeAnswer.allCases.first { $0 != question.answer })
            model.select(wrong)
            model.next()
        }
        #expect(model.score == 0)
        #expect(model.mostMissed == nil, "Two misses of each answer is a tie")
        #expect(model.summary == "Your misses were spread across answer types.")
    }

    @Test func restartResetsTheRound() throws {
        let model = makeRound()
        let question = try #require(model.current)
        model.select(question.answer)
        model.next()
        model.restart()
        #expect(model.index == 0)
        #expect(model.score == 0)
        #expect(model.phase == .answering)
    }

    @Test func shuffledRoundsUseOnlyBankQuestions() {
        let model = PracticeViewModel(questions: bank)
        let bankIDs = Set(bank.map(\.id))
        #expect(model.round.allSatisfy { bankIDs.contains($0.id) })
        #expect(Set(model.round.map(\.id)).count == model.round.count, "No repeats in a round")
    }
}

@MainActor
struct LearnContentTests {
    @Test func questionBankIsWellFormed() {
        let bank = PracticeBank.questions
        #expect(bank.count >= PracticeViewModel.roundLength, "Enough for a full round")
        #expect(Set(bank.map(\.id)).count == bank.count, "Question ids are unique")
        #expect(Set(bank.map(\.answer)) == Set(PracticeAnswer.allCases), "Every answer appears")
        for question in bank {
            #expect(!question.caption.isEmpty && !question.imageDescription.isEmpty, "\(question.id)")
            #expect(question.handle.hasSuffix(".example"), "\(question.id) must not name a real account")
            #expect(question.explanation.count > 40, "\(question.id) explains its answer")
            #expect(!question.clues.isEmpty, "\(question.id)")
        }
    }

    @Test func answersAreReasonablyBalanced() {
        let bank = PracticeBank.questions
        for answer in PracticeAnswer.allCases {
            let count = bank.count(where: { $0.answer == answer })
            #expect(count >= 4, "\(answer.label) needs enough cases for two rounds without repeats")
        }
    }

    @Test func clueGuideIsComplete() {
        let guide = ClueGroup.guide
        #expect(guide.count == 3)
        #expect(Set(guide.map(\.id)).count == guide.count)
        for group in guide {
            #expect(group.clues.count >= 4, "\(group.title)")
            #expect(Set(group.clues.map(\.id)).count == group.clues.count, "Unique clue titles in \(group.title)")
        }
    }

    @Test func startingPracticeAlwaysBeginsFresh() throws {
        let learn = LearnViewModel()
        let question = try #require(learn.practice.current)
        learn.practice.select(question.answer)
        learn.practice.next()

        learn.startPractice()
        #expect(learn.path.isEmpty, "Rounds are played in place")
        #expect(learn.practice.index == 0)
        #expect(learn.practice.score == 0)
    }

    @Test func clueCountMatchesGuide() {
        let learn = LearnViewModel()
        #expect(learn.clueCount == ClueGroup.guide.reduce(0) { $0 + $1.clues.count })
    }
}

@MainActor
struct LearnHomeTests {
    private func finishRound(_ practice: PracticeViewModel, wrongOn wrong: Set<Int> = []) throws {
        for i in 0..<practice.round.count {
            let question = try #require(practice.current)
            let pick: PracticeAnswer = wrong.contains(i) ? (question.answer == .ai ? .real : .ai) : question.answer
            practice.select(pick)
            practice.next()
        }
    }

    @Test func answeringRevealsInPlace() throws {
        let learn = LearnViewModel()
        let question = try #require(learn.practice.current)
        #expect(!learn.practice.isInProgress)
        learn.practice.select(question.answer)
        #expect(learn.path.isEmpty)
        #expect(learn.practice.phase == .revealed(picked: question.answer))
        #expect(learn.practice.isInProgress)
    }

    @Test func playAgainStartsAFreshRound() throws {
        let learn = LearnViewModel()
        try finishRound(learn.practice)
        learn.startPractice()
        #expect(learn.practice.phase == .answering)
        #expect(learn.practice.picks.isEmpty)
    }

    @Test func picksTrackEachAnswerAndMisses() throws {
        let practice = PracticeViewModel(questions: PracticeBank.questions, shuffle: false)
        try finishRound(practice, wrongOn: [0, 2])
        #expect(practice.picks.count == practice.round.count)
        #expect(practice.misses.map(\.question.id) == [practice.round[0].id, practice.round[2].id])
        #expect(practice.score == practice.round.count - 2)
        #expect(!practice.isInProgress)
    }

    @Test func mostMissedPointsAtTheRightGuide() throws {
        let practice = PracticeViewModel(questions: PracticeBank.questions, shuffle: false)
        let aiIndices = Set(practice.round.indices.filter { practice.round[$0].answer == .ai })
        try finishRound(practice, wrongOn: aiIndices)
        #expect(practice.mostMissed == .ai)
        #expect(ClueGroup.group(for: .ai)?.title == "Signs of AI")
    }

    @Test func perfectRoundHasNothingToReview() throws {
        let learn = LearnViewModel()
        try finishRound(learn.practice)
        #expect(learn.practice.misses.isEmpty)
        #expect(learn.practice.mostMissed == nil)
        learn.openGuideForMisses()
        #expect(learn.path == [.clueGuide(ClueGroup.guide[0].id)])
    }

    @Test func bestScoreIsKeptAndOnlyGoesUp() throws {
        let settings = isolatedSettings()
        let learn = LearnViewModel(settings: settings)
        #expect(learn.bestScore == nil)
        try finishRound(learn.practice, wrongOn: [1])
        #expect(learn.bestScore == PracticeViewModel.roundLength - 1)
        learn.startPractice()
        try finishRound(learn.practice, wrongOn: [0, 1, 2])
        #expect(settings.bestPracticeScore == PracticeViewModel.roundLength - 1)
        settings.reset()
        #expect(learn.bestScore == nil, "Erase All Data clears it")
    }

    @Test func summaryLeadsWithAStrengthThenTheMisses() throws {
        let practice = PracticeViewModel(questions: PracticeBank.questions, shuffle: false)
        let misleading = Set(practice.round.indices.filter { practice.round[$0].answer == .misleading })
        try finishRound(practice, wrongOn: misleading)
        #expect(practice.mostMissed == .misleading)
        #expect(practice.strongest == .real)
        #expect(practice.summary == "You caught every real photo. Most misses were false stories.")
    }

    @Test func roundsAreBalancedAcrossAllFourAnswers() {
        let practice = PracticeViewModel(questions: PracticeBank.questions)
        for answer in PracticeAnswer.allCases {
            #expect(practice.round.count(where: { $0.answer == answer }) == 2, "\(answer.label)")
        }
    }

    @Test func playAgainAvoidsLastRoundsPosts() {
        let practice = PracticeViewModel(questions: PracticeBank.questions)
        let first = Set(practice.round.map(\.id))
        practice.restart()
        #expect(first.isDisjoint(with: practice.round.map(\.id)), "30 cases is enough for two fresh rounds")
    }

    @Test func smallBanksStillFillARound() {
        let few = Array(PracticeBank.questions.filter { $0.answer == .ai })
        let round = PracticeViewModel.draw(from: few, avoiding: [], shuffle: false)
        #expect(round.count == PracticeViewModel.roundLength, "Tops up from whatever is left")
    }

    @Test func newBestIsReportedOnlyWhenBeaten() throws {
        let learn = LearnViewModel(settings: isolatedSettings())
        try finishRound(learn.practice, wrongOn: [0, 1, 2])
        #expect(!learn.lastRoundWasNewBest, "A first round sets a best, it doesn't beat one")
        learn.startPractice()
        try finishRound(learn.practice, wrongOn: [0, 1])
        #expect(learn.lastRoundWasNewBest)
        learn.startPractice()
        try finishRound(learn.practice, wrongOn: [0, 1])
        #expect(!learn.lastRoundWasNewBest, "Matching the best isn't a new best")
    }

    @Test func falseStoriesPointAtSourceClues() {
        #expect(PracticeAnswer.misleading.guideFocus == .real)
        #expect(ClueGroup.group(for: PracticeAnswer.misleading.guideFocus)?.shortTitle == "Source")
    }

    @Test func spokenTimesAvoidMeters() {
        #expect(PracticePostCard.spokenTime("40m") == "40 minutes ago")
        #expect(PracticePostCard.spokenTime("1h") == "1 hour ago")
        #expect(PracticePostCard.spokenTime("3d") == "3 days ago")
        #expect(PracticePostCard.spokenTime("now") == "posted now")
        #expect(PracticePostCard.sentence("Wild today!!") == "Wild today!!")
        #expect(PracticePostCard.sentence("Sunset tonight 🌅") == "Sunset tonight 🌅.")
    }

    @Test func everyNamedPracticeImageShipsInTheApp() {
        for question in PracticeBank.questions {
            guard let name = question.imageName else { continue }
            #expect(UIImage(named: name) != nil, "\(question.id) names a missing image: \(name)")
        }
    }

    @Test func practiceCopyAvoidsGiveaways() {
        for question in PracticeBank.questions {
            for text in [question.caption, question.imageDescription, question.explanation] + question.clues {
                #expect(!text.contains("—"), "\(question.id): no em dashes")
            }
            #expect(question.clues.count >= 2, "\(question.id)")
        }
        #expect(Set(PracticeBank.questions.map(\.caption)).count == PracticeBank.questions.count)
    }

    @Test func everyGuideGroupHasAFocusAndShortName() {
        #expect(Set(ClueGroup.guide.map(\.focus)) == Set(VerdictType.allCases))
        #expect(ClueGroup.guide.allSatisfy { !$0.shortTitle.isEmpty })
    }
}

@MainActor
struct LearnRoundThreeTests {
    @Test func tiedMissesStillOpenTheGuideForSomethingMissed() throws {
        let learn = LearnViewModel()
        let practice = learn.practice
        // Miss exactly one edited and one false-story case: a tie.
        var missedEdited = false, missedStory = false
        for _ in 0..<practice.round.count {
            let q = try #require(practice.current)
            if q.answer == .edited && !missedEdited { practice.select(.real); missedEdited = true }
            else if q.answer == .misleading && !missedStory { practice.select(.ai); missedStory = true }
            else { practice.select(q.answer) }
            practice.next()
        }
        #expect(practice.mostMissed == nil)
        learn.openGuideForMisses()
        let first = try #require(practice.misses.first?.question.answer)
        let group = try #require(ClueGroup.group(for: first.guideFocus))
        #expect(learn.path == [.clueGuide(group.id)])
    }

    @Test func caseIDsMatchTheirAnswerList() {
        for question in PracticeBank.questions {
            let prefix = switch question.answer {
            case .ai: "ai-"
            case .edited: "edit-"
            case .real: "real-"
            case .misleading: "mis-"
            }
            #expect(question.id.hasPrefix(prefix), "\(question.id)")
        }
    }
}

@MainActor
struct PracticePhotoReadinessTests {
    private func question(imageName: String?, altText: String? = nil) -> PracticeQuestion {
        PracticeQuestion(
            id: "t", author: "T", handle: "t.example", posted: "1h", caption: "c",
            imageDescription: "Text-mode description naming the tell.",
            imageName: imageName, altText: altText,
            answer: .ai, explanation: String(repeating: "x", count: 50), clues: ["a", "b"]
        )
    }

    @Test func missingImagesFallBackToTheDescription() {
        let missing = question(imageName: "No Such Practice Photo")
        #expect(missing.resolvedImageName == nil)
        #expect(missing.spokenImageDescription == missing.imageDescription)
    }

    @Test func photosUseNeutralAltTextForVoiceOver() {
        let withPhoto = question(imageName: "FaceCheckMagnifier", altText: "A neutral description.")
        #expect(withPhoto.resolvedImageName == "FaceCheckMagnifier")
        #expect(withPhoto.spokenImageDescription == "A neutral description.", "VoiceOver doesn't hear the giveaway")
        #expect(question(imageName: "FaceCheckMagnifier").spokenImageDescription == "Text-mode description naming the tell.")
    }

    @Test func hotspotsStayInsideTheImage() {
        #expect(PracticeHotspot(x: 0.1, y: 0.1, width: 0.5, height: 0.5, label: "ok").isInsideImage)
        #expect(!PracticeHotspot(x: 0.8, y: 0.1, width: 0.5, height: 0.2, label: "off the edge").isInsideImage)
        #expect(!PracticeHotspot(x: 0.1, y: 0.1, width: 0, height: 0.2, label: "empty").isInsideImage)
        for question in PracticeBank.questions {
            #expect(!question.hotspots.contains { !$0.isInsideImage }, "\(question.id) has a hotspot outside its photo")
        }
    }

    @Test func factsAPhotoCantShowLiveInContext() {
        for question in PracticeBank.questions {
            for phrase in ["In the replies", "News sites ran", "posted two more"] {
                #expect(!question.imageDescription.contains(phrase), "\(question.id): move “\(phrase)” to context")
            }
        }
        #expect(PracticeBank.questions.contains { $0.context != nil })
    }

    @Test func photoCasesCarryACredit() {
        for question in PracticeBank.questions where question.imageName != nil {
            #expect(question.credit?.isEmpty == false, "\(question.id) needs a photo credit")
        }
    }
}
