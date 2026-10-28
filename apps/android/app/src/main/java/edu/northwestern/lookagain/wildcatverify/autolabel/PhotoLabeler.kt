package edu.northwestern.lookagain.wildcatverify.autolabel

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.util.Log
import edu.northwestern.lookagain.wildcatverify.MainActivity
import edu.northwestern.lookagain.wildcatverify.container
import edu.northwestern.lookagain.wildcatverify.model.InMemoryImage
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * The part of on-screen labelling both services share: remembers results by
 * photo hash, checks new photos one at a time, and opens a result when a badge
 * is tapped. Photos stay in memory unless the user opens one.
 */
class PhotoLabeler(private val context: Context, private val scope: CoroutineScope) {
    private val container = context.container
    private val pipeline by lazy { container.pipeline() }
    /** Most recently labelled photos by hash, oldest first. */
    private val results = LinkedHashMap<Long, VerificationCase>()
    private val inFlight = mutableSetOf<Long>()
    private val lock = Mutex()

    /** A label for this photo (or a near-identical one) if it was already checked. */
    fun cached(hash: Long): VerificationCase? =
        results[hash] ?: results.entries.firstOrNull { ImageHash.distance(it.key, hash) <= SAME_PHOTO_BITS }?.value

    /** Checks the photo unless it's known or already being checked; `onLabel` runs on the main thread. */
    fun request(hash: Long, crop: Bitmap, onLabel: (Long, VerificationCase) -> Unit) {
        if (cached(hash) != null || !inFlight.add(hash)) return
        scope.launch {
            try {
                val item = lock.withLock { pipeline.checkImage(crop, title = VerificationCase.AUTO_LABEL_TITLE) }
                remember(hash, item)
                onLabel(hash, item)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Log.w("Look Again", "Couldn't label a photo", e)
            } finally {
                inFlight.remove(hash)
            }
        }
    }

    /** Tapping a badge adds the check to My Checks and opens its result. */
    fun open(item: VerificationCase) {
        val history = container.app.history
        if (history.cases.none { it.id == item.id }) history.record(item)
        context.startActivity(
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra(MainActivity.EXTRA_OPEN_CASE, item.id),
        )
    }

    /** Drops every photo held only for labels. */
    fun release() {
        results.values.forEach(::dropPhoto)
        results.clear()
    }

    private fun remember(hash: Long, item: VerificationCase) {
        results[hash] = item
        while (results.size > MAX_REMEMBERED) {
            val oldest = results.entries.first()
            results.remove(oldest.key)
            dropPhoto(oldest.value)
        }
    }

    /** Keeps the photo if the user opened it (it's in My Checks now). */
    private fun dropPhoto(item: VerificationCase) {
        if (container.app.history.cases.any { it.id == item.id }) return
        item.imageUrl?.takeIf(InMemoryImage::isInMemory)?.let(container.images::removeUpload)
    }

    companion object {
        const val SAME_PHOTO_BITS = 5
        private const val MAX_REMEMBERED = 60

        /** 64-bit difference hash of a photo crop. */
        fun hashOf(crop: Bitmap): Long {
            val small = Bitmap.createScaledBitmap(crop, 9, 8, true)
            val pixels = IntArray(72)
            small.getPixels(pixels, 0, 9, 0, 0, 9, 8)
            return ImageHash.dHash(pixels)
        }
    }
}
