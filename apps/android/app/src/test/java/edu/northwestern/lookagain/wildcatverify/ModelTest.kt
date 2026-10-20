package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.model.PracticeBank
import edu.northwestern.lookagain.wildcatverify.model.SampleData
import edu.northwestern.lookagain.wildcatverify.model.VerdictFilter
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import edu.northwestern.lookagain.wildcatverify.viewmodel.PracticeViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.LearnViewModel
import edu.northwestern.lookagain.wildcatverify.viewmodel.LearnRoute
import edu.northwestern.lookagain.wildcatverify.model.PracticeAnswer
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PracticeTest {
    @Test fun bankIsWellFormed() {
        val questions = PracticeBank.questions
        assertEquals(questions.size, questions.map { it.id }.toSet().size)
        for (answer in PracticeAnswer.entries) {
            assertTrue("$answer needs 2+ cases", questions.count { it.answer == answer } >= 2)
        }
        assertTrue(questions.all { it.explanation.isNotBlank() && it.clues.isNotEmpty() })
        assertTrue("Practice handles never name a real account", questions.all { it.handle.endsWith(".example") })
    }

    @Test fun roundsAreBalancedAcrossAnswers() {
        val round = PracticeViewModel.draw(PracticeBank.questions, emptySet(), shuffle = true)
        assertEquals(PracticeViewModel.ROUND_LENGTH, round.size)
        for (answer in PracticeAnswer.entries) assertEquals(2, round.count { it.answer == answer })
    }

    @Test fun nextRoundAvoidsTheLastOne() {
        val first = PracticeViewModel.draw(PracticeBank.questions, emptySet(), shuffle = false)
        val second = PracticeViewModel.draw(PracticeBank.questions, first.map { it.id }.toSet(), shuffle = false)
        assertTrue(first.map { it.id }.intersect(second.map { it.id }.toSet()).isEmpty())
    }

    @Test fun roundScoresAndFinishes() {
        var finished = -1
        val vm = PracticeViewModel(PracticeBank.questions, shuffle = false).apply { onFinish = { finished = it } }
        repeat(PracticeViewModel.ROUND_LENGTH) {
            vm.select(vm.current!!.answer)
            vm.next()
        }
        assertEquals(PracticeViewModel.Phase.Finished, vm.phase)
        assertEquals(PracticeViewModel.ROUND_LENGTH, finished)
        assertEquals("Every one right.", vm.summary)
    }

    @Test fun summaryNamesStrengthsAndMisses() {
        val vm = PracticeViewModel(PracticeBank.questions, shuffle = false)
        repeat(PracticeViewModel.ROUND_LENGTH) {
            val question = vm.current!!
            // Miss every AI case, get everything else right.
            vm.select(if (question.answer == PracticeAnswer.AI) PracticeAnswer.REAL else question.answer)
            vm.next()
        }
        assertEquals(PracticeAnswer.AI, vm.mostMissed)
        assertEquals(2, vm.misses.size)
        assertTrue(vm.summary, vm.summary.contains("Most misses were AI images."))
        assertTrue(vm.summary, vm.summary.startsWith("You caught every"))
    }

    @Test fun answeringTwiceCountsOnce() {
        val vm = PracticeViewModel(PracticeBank.questions, shuffle = false)
        val wrong = PracticeAnswer.entries.first { it != vm.current!!.answer }
        vm.select(wrong)
        vm.select(vm.current!!.answer)
        assertEquals(0, vm.score)
        assertEquals(1, vm.answerCount)
        assertFalse(vm.lastAnswerWasCorrect)
    }

    @Test fun bestScoreIsRememberedAndNewBestFlagged() {
        val learn = LearnViewModel()
        fun play(correct: Int) {
            learn.startPractice()
            repeat(PracticeViewModel.ROUND_LENGTH) { i ->
                val q = learn.practice.current!!
                learn.practice.select(if (i < correct) q.answer else PracticeAnswer.entries.first { it != q.answer })
                learn.practice.next()
            }
        }
        play(3)
        assertEquals(3, learn.bestScore)
        assertFalse("The first round isn't a new best", learn.lastRoundWasNewBest)
        play(6)
        assertTrue(learn.lastRoundWasNewBest)
        assertEquals(6, learn.bestScore)
    }

    @Test fun reviewOpensTheGuideForWhatWasMissed() {
        val learn = LearnViewModel()
        val practice = learn.practice
        repeat(PracticeViewModel.ROUND_LENGTH) {
            val q = practice.current!!
            practice.select(if (q.answer == PracticeAnswer.EDITED) PracticeAnswer.AI else q.answer)
            practice.next()
        }
        learn.openGuideForMisses()
        assertEquals(LearnRoute.ClueGuide("Signs of editing"), learn.path.single())
    }
}

class MultiImageTest {
    private fun item(verdict: VerdictType, confidence: Int) = SampleData.lakefill.copy(verdict = verdict, confidencePercentage = confidence)

    @Test fun suspicionOrdersAIThenEditedThenReal() {
        val ranked = listOf(item(VerdictType.REAL, 99), item(VerdictType.REAL, 55), item(VerdictType.TAMPERED, 60), item(VerdictType.AI, 51))
            .sortedByDescending(CheckPipeline::suspicion)
        assertEquals(listOf(VerdictType.AI, VerdictType.TAMPERED, VerdictType.REAL, VerdictType.REAL), ranked.map { it.verdict })
        assertEquals("A confident Real is the least suspicious", 99, ranked.last().confidencePercentage)
    }
}

class VerificationCaseTest {
    @Test fun roundTripsThroughJson() {
        val json = Json { ignoreUnknownKeys = true }
        val item = SampleData.protestBanner
        assertEquals(item, json.decodeFromString<VerificationCase>(json.encodeToString(VerificationCase.serializer(), item)))
    }

    @Test fun filtersMatchVerdicts() {
        assertTrue(VerdictFilter.ALL.matches(SampleData.monorail))
        assertTrue(VerdictFilter.AI.matches(SampleData.monorail))
        assertFalse(VerdictFilter.REAL.matches(SampleData.monorail))
    }

    @Test fun shareTextMarksDemos() {
        assertTrue(SampleData.lakefill.shareText.startsWith("WildcatVerify (demo result): Likely Real, 96% confidence"))
        assertTrue(SampleData.lakefill.shareText.endsWith("An automated estimate, not proof."))
    }

    @Test fun uploadsHaveNoAuthor() {
        val upload = SampleData.lakefill.copy(authorHandle = "", title = "Uploaded photo")
        assertEquals("From your photos", upload.displayHandle)
        assertEquals("Labeled while browsing Bluesky", upload.copy(title = VerificationCase.AUTO_LABEL_TITLE).displayHandle)
    }
}
