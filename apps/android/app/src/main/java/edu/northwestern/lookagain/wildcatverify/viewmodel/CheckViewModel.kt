package edu.northwestern.lookagain.wildcatverify.viewmodel

import android.graphics.Bitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import edu.northwestern.lookagain.wildcatverify.data.BlueskyService
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import edu.northwestern.lookagain.wildcatverify.data.ClipboardProbe
import edu.northwestern.lookagain.wildcatverify.data.HistoryStore
import edu.northwestern.lookagain.wildcatverify.model.CheckException
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import edu.northwestern.lookagain.wildcatverify.model.userMessage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

/** Drives the Check tab: link and photo input, analysis, and pushed results. */
class CheckViewModel(
    private val history: HistoryStore,
    private val pipeline: CheckPipeline,
    private val scope: CoroutineScope,
    private val clipboard: ClipboardProbe = ClipboardProbe.none,
) {
    enum class Phase { INPUT, ANALYZING }

    var inputUrl by mutableStateOf("")
    /** Results (fresh or recent) pushed on the Check tab's stack. */
    var path by mutableStateOf<List<VerificationCase>>(emptyList())
    var isShowingError by mutableStateOf(false)
    var phase by mutableStateOf(Phase.INPUT)
        private set
    var errorMessage by mutableStateOf("")
        private set
    /** Preview of what is being analyzed, shown in the loading state. */
    var analyzingImage by mutableStateOf<Bitmap?>(null)
        private set
    /** Bumped with each finished check, for screen-reader announcements. */
    var lastResult by mutableStateOf<VerificationCase?>(null)
        private set

    /** A link was copied since the app last offered one: show "Check the link you copied". */
    var offersCopiedLink by mutableStateOf(false)
        private set
    /** Clipboard contents already offered, used or dismissed. */
    private var handledChangeToken: Long? = null

    val canCheckPost: Boolean get() = inputUrl.isNotBlank() && phase != Phase.ANALYZING

    /** On open: offer the copied link if something new looks like a link. */
    fun refreshCopiedLinkOffer() {
        val token = clipboard.changeToken()
        offersCopiedLink = token != null && token != handledChangeToken && phase == Phase.INPUT && path.isEmpty() &&
            clipboard.hasProbableLink()
    }

    fun dismissCopiedLinkOffer() {
        handledChangeToken = clipboard.changeToken()
        offersCopiedLink = false
    }

    /** The offer's Paste button: reads the clipboard, which the user asked for by tapping. */
    fun pasteCopiedLink() {
        clipboard.read()?.let { checkPasted(it, explainIfNotBluesky = true) }
            ?: dismissCopiedLinkOffer()
    }

    /**
     * The user pasted (via the offer or the field's Paste button). A Bluesky
     * post link is checked straight away; anything else just fills the field.
     */
    fun checkPasted(text: String, explainIfNotBluesky: Boolean = false) {
        handledChangeToken = clipboard.changeToken()
        offersCopiedLink = false
        val link = BlueskyService.linkIn(text)
        if (link == null) {
            inputUrl = text.trim()
            if (explainIfNotBluesky) {
                errorMessage = "The copied link isn't a Bluesky post. In Bluesky, tap Share on a post, then Copy Link."
                isShowingError = true
            }
            return
        }
        inputUrl = link
        checkPost()
    }

    private var job: Job? = null

    fun checkPost() {
        if (!canCheckPost) return
        val link = inputUrl
        run { pipeline.checkPost(link) { analyzingImage = it } }
    }

    /** @param load reads the picked photo's bytes (from the system photo picker). */
    fun analyzePhoto(load: suspend () -> ByteArray?) {
        run {
            val data = load() ?: throw CheckException.UnreadablePhoto
            pipeline.checkImage(data) { analyzingImage = it }
        }
    }

    /** Returns to an empty form, cancelling any analysis in flight. */
    fun reset() {
        cancelAnalysis()
        inputUrl = ""
        isShowingError = false
        path = emptyList()
    }

    fun cancelAnalysis() {
        job?.cancel()
        job = null
        analyzingImage = null
        phase = Phase.INPUT
    }

    fun open(item: VerificationCase) {
        path = path + item
    }

    fun pop() {
        path = path.dropLast(1)
    }

    private fun run(work: suspend () -> VerificationCase) {
        job?.cancel()
        isShowingError = false
        analyzingImage = null
        phase = Phase.ANALYZING

        job = scope.launch {
            try {
                val item = work()
                history.record(item)
                inputUrl = ""
                phase = Phase.INPUT
                path = path + item
                lastResult = item
            } catch (e: CancellationException) {
                // Superseded by the user (Cancel, a new check, or Check Another).
                // Whatever they did owns the state now.
                throw e
            } catch (e: Throwable) {
                errorMessage = e.userMessage()
                phase = Phase.INPUT
                isShowingError = true
            }
        }
    }
}
