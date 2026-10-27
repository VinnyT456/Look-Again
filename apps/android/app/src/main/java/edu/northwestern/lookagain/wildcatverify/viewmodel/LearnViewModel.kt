package edu.northwestern.lookagain.wildcatverify.viewmodel

import androidx.compose.foundation.ScrollState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import edu.northwestern.lookagain.wildcatverify.data.SettingsStore
import edu.northwestern.lookagain.wildcatverify.model.ClueGroup
import edu.northwestern.lookagain.wildcatverify.model.PracticeAnswer
import edu.northwestern.lookagain.wildcatverify.model.PracticeBank
import edu.northwestern.lookagain.wildcatverify.model.PracticeQuestion

/** Screens pushed inside the Learn tab. */
sealed interface LearnRoute {
    /** The clue guide, opened on one group (`ClueGroup.id`). */
    data class ClueGuide(val groupId: String) : LearnRoute
}

/** The Learn tab: the Look Again round (played in place) and the clue guide. */
class LearnViewModel(
    /** Where the best score is kept; null keeps it in memory only (tests). */
    private val settings: SettingsStore? = null,
    val clueGroups: List<ClueGroup> = ClueGroup.guide,
    questions: List<PracticeQuestion> = PracticeBank.questions,
) {
    var path by mutableStateOf<List<LearnRoute>>(emptyList())
    val practice = PracticeViewModel(questions)

    private var sessionBest by mutableIntStateOf(0)
    /** The round that just ended beat the previous best. */
    var lastRoundWasNewBest by mutableStateOf(false)
        private set

    /**
     * The Learn home's scroll position. Kept here because the home leaves
     * composition while the Clue Guide is pushed or another tab shows.
     */
    val scroll = ScrollState(0)
    /** The last answer the home reacted to, so coming back doesn't buzz or scroll again. */
    var handledAnswerCount = 0
    /** The round and post the home last scrolled to the top for. */
    var shownPosition: Pair<Int, Int>? = null

    /** "What the answers mean" is open. Closed again for each new round. */
    var showsDefinitions by mutableStateOf(false)
    /** The end-of-round list shows every miss, not just the first few. */
    var showsAllMisses by mutableStateOf(false)
    /** The missed case open in the review sheet, with what the user picked. */
    var reviewing by mutableStateOf<Pair<PracticeQuestion, PracticeAnswer>?>(null)

    init {
        practice.onFinish = ::recordScore
    }

    val clueCount: Int get() = clueGroups.sumOf { it.clues.size }

    /** Best finished-round score, or null before the first round ends. */
    val bestScore: Int?
        get() = (settings?.bestPracticeScore ?: sessionBest).takeIf { it > 0 }

    /** Starts a fresh round in place. */
    fun startPractice() {
        showsDefinitions = false
        showsAllMisses = false
        reviewing = null
        practice.restart()
    }

    fun openGuide(group: ClueGroup) {
        path = path + LearnRoute.ClueGuide(group.id)
    }

    /** After a round: the guide on what was missed most (or the first group). */
    fun openGuideForMisses() {
        // On a tie, the first miss decides; never the type the player aced.
        val missed = practice.mostMissed ?: practice.misses.firstOrNull()?.first?.answer
        val group = missed?.let { ClueGroup.groupFor(it.guideFocus, clueGroups) } ?: clueGroups.firstOrNull()
        group?.let(::openGuide)
    }

    private fun recordScore(score: Int) {
        // The first finished round sets a best; it isn't "new" yet.
        lastRoundWasNewBest = bestScore?.let { score > it } ?: false
        if (settings != null) {
            settings.bestPracticeScore = maxOf(settings.bestPracticeScore, score)
        } else {
            sessionBest = maxOf(sessionBest, score)
        }
    }
}

/** One Look Again round: a balanced draw of cases, the user's picks, and a score. */
class PracticeViewModel(private val bank: List<PracticeQuestion>, private val shuffle: Boolean = true) {
    sealed interface Phase {
        /** Waiting for the user to pick an answer. */
        data object Answering : Phase
        /** The user picked; showing whether it was right and why. */
        data class Revealed(val picked: PracticeAnswer) : Phase
        /** Every question in the round is done. */
        data object Finished : Phase
    }

    var round by mutableStateOf<List<PracticeQuestion>>(emptyList())
        private set
    var index by mutableIntStateOf(0)
        private set
    var score by mutableIntStateOf(0)
        private set
    var phase by mutableStateOf<Phase>(Phase.Answering)
        private set
    /** Bumped on each answer, so views can play feedback once per pick. */
    var answerCount by mutableIntStateOf(0)
        private set
    var lastAnswerWasCorrect by mutableStateOf(false)
        private set
    /** What the user picked for each answered question, in round order. */
    var picks by mutableStateOf<List<PracticeAnswer>>(emptyList())
        private set
    /** Bumped on each new round, so views can tell a restart from the first post. */
    var roundNumber by mutableIntStateOf(0)
        private set
    /** Called once with the score when a round finishes. */
    var onFinish: ((Int) -> Unit)? = null

    /** Cases from the previous round, skipped when the bank has enough others. */
    private var lastRoundIds: Set<String> = emptySet()

    init {
        restart()
    }

    val current: PracticeQuestion? get() = round.getOrNull(index)

    val progressText: String get() = "${minOf(index + 1, round.size)} of ${round.size}"

    val isLastQuestion: Boolean get() = index >= round.size - 1

    /** A round has started but isn't finished. */
    val isInProgress: Boolean get() = phase != Phase.Finished && (picks.isNotEmpty() || index > 0)

    /** Questions answered wrong, with what the user picked. */
    val misses: List<Pair<PracticeQuestion, PracticeAnswer>>
        get() = round.zip(picks).filter { (question, picked) -> question.answer != picked }

    /** The answer missed most this round. Null when nothing was missed or misses are tied. */
    val mostMissed: PracticeAnswer?
        get() {
            val counts = misses.groupingBy { it.first.answer }.eachCount()
            val top = counts.values.maxOrNull() ?: return null
            if (counts.values.count { it == top } != 1) return null
            return counts.entries.first { it.value == top }.key
        }

    /** The answer type the user got all of, if any, to lead the summary with something they did well. */
    val strongest: PracticeAnswer?
        get() {
            val answered = round.zip(picks)
            return PracticeAnswer.entries.firstOrNull { answer ->
                val cases = answered.filter { it.first.answer == answer }
                cases.isNotEmpty() && cases.all { it.first.answer == it.second }
            }
        }

    /** End-of-round headline. */
    val scoreLine: String get() = "$score of ${round.size} right"

    /** What to take from the round. */
    val summary: String
        get() {
            if (misses.isEmpty()) return "Every one right."
            val parts = mutableListOf<String>()
            strongest?.let { parts += "You caught every ${it.singularNoun}." }
            parts += mostMissed?.let { "Most misses were ${it.pluralNoun}." } ?: "Your misses were spread across answer types."
            return parts.joinToString(" ")
        }

    fun select(answer: PracticeAnswer) {
        val current = current
        if (phase != Phase.Answering || current == null) return
        lastAnswerWasCorrect = answer == current.answer
        if (lastAnswerWasCorrect) score += 1
        picks = picks + answer
        answerCount += 1
        phase = Phase.Revealed(answer)
    }

    fun next() {
        if (phase !is Phase.Revealed) return
        if (isLastQuestion) {
            phase = Phase.Finished
            onFinish?.invoke(score)
        } else {
            index += 1
            phase = Phase.Answering
        }
    }

    fun restart() {
        round = draw(bank, lastRoundIds, shuffle)
        lastRoundIds = round.map { it.id }.toSet()
        roundNumber += 1
        index = 0
        score = 0
        picks = emptyList()
        phase = if (round.isEmpty()) Phase.Finished else Phase.Answering
    }

    companion object {
        const val ROUND_LENGTH = 8

        /**
         * An even mix of answers (two of each for a round of eight), preferring
         * cases not in `avoiding`, topped up from the rest when a type runs short.
         */
        fun draw(bank: List<PracticeQuestion>, avoiding: Set<String>, shuffle: Boolean): List<PracticeQuestion> {
            val perAnswer = ROUND_LENGTH / PracticeAnswer.entries.size
            val picked = mutableListOf<PracticeQuestion>()
            for (answer in PracticeAnswer.entries) {
                val pool = bank.filter { it.answer == answer }
                val fresh = pool.filter { it.id !in avoiding }
                val stale = pool.filter { it.id in avoiding }
                val ordered = (if (shuffle) fresh.shuffled() else fresh) + (if (shuffle) stale.shuffled() else stale)
                picked += ordered.take(perAnswer)
            }
            if (picked.size < ROUND_LENGTH) {
                val pickedIds = picked.map { it.id }.toSet()
                val rest = bank.filter { it.id !in pickedIds }
                picked += (if (shuffle) rest.shuffled() else rest).take(ROUND_LENGTH - picked.size)
            }
            return if (shuffle) picked.shuffled() else picked
        }
    }
}
