package edu.northwestern.lookagain.wildcatverify.data

import android.graphics.Bitmap
import edu.northwestern.lookagain.wildcatverify.model.CheckException
import edu.northwestern.lookagain.wildcatverify.model.ClassificationResult
import edu.northwestern.lookagain.wildcatverify.model.FeedPost
import edu.northwestern.lookagain.wildcatverify.model.InMemoryImage
import edu.northwestern.lookagain.wildcatverify.model.VerdictCopy
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.UUID
import kotlin.math.roundToInt

/**
 * Turns a Bluesky link or raw image data into a [VerificationCase]. Shared by
 * the Check tab, the Feed and the share sheet so all give identical results.
 */
class CheckPipeline(
    private val bluesky: BlueskyService,
    /** Loaded on first use, off the main thread (the model is ~84 MB). */
    private val classifierProvider: () -> ImageClassifier,
    private val images: ImageRepository,
) {
    private suspend fun classifier(): ImageClassifier = withContext(Dispatchers.Default) { classifierProvider() }

    /**
     * Fetches every photo in the post and classifies each. Returns the most
     * suspicious one, with all of them in `postImages` when there's more than one.
     * @param onImage called once the first photo is loaded, before classification.
     */
    suspend fun checkPost(link: String, onImage: (Bitmap) -> Unit = {}): VerificationCase {
        val post = bluesky.fetchPost(link)
        return checkImages(post.imageUrls, post.text, post.authorHandle, post.postUrl, onImage)
    }

    /** Checks a post already loaded from a feed: no thread lookup, straight to its photos. */
    suspend fun checkFeedPost(post: FeedPost): VerificationCase =
        checkImages(post.imageUrls, post.text, post.authorHandle, post.postUrl)

    private suspend fun checkImages(
        urls: List<String>,
        text: String,
        handle: String,
        postUrl: String,
        onImage: (Bitmap) -> Unit = {},
    ): VerificationCase {
        // Loaded after the first photo arrives, so its preview shows while the detector loads.
        var detector: ImageClassifier? = null
        val cases = urls.mapIndexed { index, url ->
            val image = try {
                images.image(url)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                throw CheckException.Network
            }
            if (index == 0) onImage(image)
            val model = detector ?: classifier().also { detector = it }
            makeCase(
                isDemo = model.isDemo,
                result = model.classify(image),
                title = title(text),
                handle = handle,
                postUrl = postUrl,
                caption = text,
                imageUrl = url,
            )
        }
        // Most suspicious first; on a tie the earlier image wins.
        val lead = cases.withIndex().maxWithOrNull(compareBy<IndexedValue<VerificationCase>> { suspicion(it.value) }.thenByDescending { it.index })?.value
            ?: throw CheckException.NoImage
        return if (cases.size > 1) lead.copy(postImages = cases) else lead
    }

    /**
     * Decodes image data (downsampled, metadata dropped), keeps it in memory only, and classifies it.
     * @param onStored called with the in-memory address of the photo, so a caller can drop it later.
     */
    suspend fun checkImage(data: ByteArray, onStored: (String) -> Unit = {}, onImage: (Bitmap) -> Unit = {}): VerificationCase {
        val image = ImageRepository.downsample(data, ImageRepository.FULL_PIXEL_SIZE)
            ?: throw CheckException.UnreadablePhoto
        // Credentials live in the file's metadata, which decoding drops, so read them from the original bytes.
        val credentials = withContext(Dispatchers.Default) { ContentCredentialsReader.read(data) }
        return checkImage(image, onStored = onStored, onImage = onImage).copy(credentials = credentials)
    }

    /** Classifies an already-decoded image (e.g. a photo area on screen), keeping it in memory only. */
    suspend fun checkImage(
        image: Bitmap,
        title: String = "Uploaded photo",
        onStored: (String) -> Unit = {},
        onImage: (Bitmap) -> Unit = {},
    ): VerificationCase {
        val id = UUID.randomUUID().toString()
        val url = InMemoryImage.url(id)
        images.storeUpload(image, url)
        onStored(url)
        onImage(image)
        val classifier = classifier()
        val result = classifier.classify(image)
        return makeCase(classifier.isDemo, result, title, handle = "", postUrl = null, caption = "", imageUrl = url).copy(id = id)
    }

    private fun makeCase(
        isDemo: Boolean,
        result: ClassificationResult,
        title: String,
        handle: String,
        postUrl: String?,
        caption: String,
        imageUrl: String,
    ): VerificationCase {
        val copy = VerdictCopy.forVerdict(result.verdict)
        return VerificationCase(
            title = title,
            authorHandle = handle,
            postUrl = postUrl,
            caption = caption,
            timeAgo = "Just now",
            imageUrl = imageUrl,
            verdict = result.verdict,
            // Never display certainty: 99.9% would otherwise round to "100%".
            confidencePercentage = displayConfidence(result.confidence),
            plainSummary = copy.summary,
            suggestedAction = copy.action,
            detectedIssue = result.hotspot?.label,
            hotspot = result.hotspot,
            heatmap = result.heatmap,
            keyFindings = copy.findings,
            isDemo = isDemo,
        )
    }

    /** A quick check of one image URL (the Feed's automatic checks). Returns the result and whether it's a demo. */
    suspend fun classifyUrl(url: String): Pair<ClassificationResult, Boolean> {
        val image = images.image(url, maxPixelSize = 1024)
        val classifier = classifier()
        return classifier.classify(image) to classifier.isDemo
    }

    companion object {
        /** 0–99: never displays certainty, since 99.9% would otherwise round to "100%". */
        fun displayConfidence(confidence: Double): Int = (confidence * 100).roundToInt().coerceIn(0, 99)

        /**
         * Orders verdicts by how strongly they point at a fake: a confident "AI"
         * first, a confident "Real" last.
         */
        fun suspicion(item: VerificationCase): Int = when (item.verdict) {
            VerdictType.AI -> 200 + item.confidencePercentage
            VerdictType.TAMPERED -> 100 + item.confidencePercentage
            VerdictType.REAL -> 100 - item.confidencePercentage
        }

        /** First line of the post, trimmed to fit a list row. */
        fun title(text: String): String {
            val firstLine = text.lineSequence().firstOrNull { it.isNotEmpty() } ?: ""
            if (firstLine.isEmpty()) return "Bluesky post"
            return if (firstLine.length > 60) firstLine.take(59) + "…" else firstLine
        }
    }
}
