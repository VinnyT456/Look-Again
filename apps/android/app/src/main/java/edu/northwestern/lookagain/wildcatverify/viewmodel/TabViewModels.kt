package edu.northwestern.lookagain.wildcatverify.viewmodel

import android.graphics.Bitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import edu.northwestern.lookagain.wildcatverify.data.HistoryStore
import edu.northwestern.lookagain.wildcatverify.data.ImageRepository
import edu.northwestern.lookagain.wildcatverify.model.VerdictFilter
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import edu.northwestern.lookagain.wildcatverify.model.userMessage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

/** My Checks: search, verdict scopes, delete and clear. */
class HistoryViewModel(private val store: HistoryStore) {
    var path by mutableStateOf<List<VerificationCase>>(emptyList())
    var searchQuery by mutableStateOf("")
    var scope by mutableStateOf(VerdictFilter.ALL)
    var isConfirmingClear by mutableStateOf(false)

    val isEmpty: Boolean get() = store.cases.isEmpty()

    val visibleCases: List<VerificationCase>
        get() {
            val query = searchQuery.trim()
            return store.cases.filter { item ->
                scope.matches(item) && (
                    query.isEmpty() ||
                        item.authorHandle.contains(query, ignoreCase = true) ||
                        item.title.contains(query, ignoreCase = true) ||
                        item.caption.contains(query, ignoreCase = true)
                    )
            }
        }

    fun open(item: VerificationCase) {
        path = path + item
    }

    fun delete(item: VerificationCase) {
        store.remove(item)
    }

    fun clearAll() {
        store.clear()
        path = emptyList()
        searchQuery = ""
        scope = VerdictFilter.ALL
    }
}

/** What the results photo shows: the plain image, or the image with the region that drove the verdict highlighted. */
enum class PhotoLayer(val title: String) { PHOTO("Photo"), HIGHLIGHT("Highlight") }

/** State for one results screen: the case, its loaded image, and the overlay mode. */
class CheckResultsViewModel(val item: VerificationCase, private val images: ImageRepository) {
    var layer by mutableStateOf(PhotoLayer.PHOTO)
    /** Settings → Show Heatmap. */
    var heatmapEnabled by mutableStateOf(true)
    var image by mutableStateOf<Bitmap?>(null)
        private set
    var imageFailed by mutableStateOf(false)
        private set

    /** Whether this case has a photo at all. Without one there is nothing to highlight. */
    val hasPhoto: Boolean get() = item.imageUrl != null

    /** Show the detector's heatmap only when it backs an AI verdict; on a Real verdict the same map would just be noise. */
    val showsHeatmap: Boolean
        get() = heatmapEnabled && hasPhoto && item.verdict == VerdictType.AI && (item.heatmap?.hasSignal ?: false)

    val canShowOnPhoto: Boolean
        get() = hasPhoto && item.verdict.hasAnomaly && (item.hotspot != null || showsHeatmap)

    /**
     * The Photo/Highlight toggle only appears when the highlight says something
     * true: a marked area, a heatmap, or "nothing found" on a Real verdict.
     */
    val canToggleHighlight: Boolean
        get() = hasPhoto && (item.hotspot != null || item.verdict == VerdictType.REAL || showsHeatmap)

    suspend fun loadImage() {
        val url = item.imageUrl
        if (image != null || url == null) return
        images.cachedImage(url)?.let { image = it; return }
        try {
            image = images.image(url)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Throwable) {
            imageFailed = true
        }
    }

    fun showOnPhoto() {
        layer = PhotoLayer.HIGHLIGHT
    }
}

/** What another app shared with WildcatVerify, reduced to something checkable. */
sealed interface ShareInput {
    /** Raw image bytes (a photo or screenshot). */
    class Image(val data: ByteArray) : ShareInput
    /** A Bluesky post link. */
    data class Link(val link: String) : ShareInput
}

/** Drives a one-off check (share sheet, or a Feed post): check it, show the verdict. */
class ShareViewModel(
    private val pipeline: CheckPipeline,
    /** Called with each finished check, e.g. so the Feed can add it to My Checks. */
    private val onResult: ((VerificationCase) -> Unit)? = null,
) {
    sealed interface Phase {
        data object Reading : Phase
        data object Analyzing : Phase
        data class Result(val item: VerificationCase) : Phase
        data class Failed(val message: String) : Phase
    }

    var phase by mutableStateOf<Phase>(Phase.Reading)
        private set
    var analyzingImage by mutableStateOf<Bitmap?>(null)
        private set

    suspend fun check(input: ShareInput) {
        phase = Phase.Analyzing
        analyzingImage = null
        try {
            val item = when (input) {
                is ShareInput.Image -> pipeline.checkImage(input.data) { analyzingImage = it }
                is ShareInput.Link -> pipeline.checkPost(input.link) { analyzingImage = it }
            }
            phase = Phase.Result(item)
            onResult?.invoke(item)
        } catch (e: CancellationException) {
            // The screen was closed; nothing to show.
            throw e
        } catch (e: Throwable) {
            fail(e)
        }
    }

    fun fail(error: Throwable) {
        phase = Phase.Failed(error.userMessage("Something went wrong checking that item. Please try again."))
    }
}
