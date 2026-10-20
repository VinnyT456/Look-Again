package edu.northwestern.lookagain.wildcatverify.data

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.util.LruCache
import androidx.exifinterface.media.ExifInterface
import edu.northwestern.lookagain.wildcatverify.model.InMemoryImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayInputStream
import java.io.File
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * Loads and caches images for cases. Decoding happens off the main thread and
 * is downsampled to the size it will be drawn at. Uploaded photos live only in
 * memory (never written to disk) and are dropped when history is cleared.
 */
class ImageRepository(private val http: HttpClient = UrlConnectionHttpClient) {
    private val cache = object : LruCache<String, Bitmap>(64 * 1024 * 1024) {
        override fun sizeOf(key: String, value: Bitmap) = value.allocationByteCount
    }
    private val rawData = LruCache<String, ByteArray>(20)
    private val uploads = ConcurrentHashMap<String, Bitmap>()

    fun storeUpload(image: Bitmap, url: String) {
        uploads[url] = image
    }

    fun removeUpload(url: String) {
        uploads.remove(url)
    }

    fun removeAllUploads() {
        uploads.clear()
    }

    fun cachedImage(url: String, maxPixelSize: Int = FULL_PIXEL_SIZE): Bitmap? =
        uploads[url] ?: cache.get(key(url, maxPixelSize))

    /** Returns the image at `url`, decoded no larger than `maxPixelSize` on its longest edge. */
    suspend fun image(url: String, maxPixelSize: Int = FULL_PIXEL_SIZE): Bitmap {
        cachedImage(url, maxPixelSize)?.let { return it }
        if (InMemoryImage.isInMemory(url)) throw IOException("Upload no longer in memory")

        val data = rawData.get(url) ?: if (url.startsWith("file:")) {
            // Photos saved by "Keep My Checks".
            withContext(Dispatchers.IO) { File(java.net.URI(url)).readBytes() }
        } else {
            val (status, body) = http.get(url)
            if (status !in 200..299) throw IOException("HTTP $status")
            rawData.put(url, body)
            body
        }
        val image = downsample(data, maxPixelSize) ?: throw IOException("Couldn't decode image")
        cache.put(key(url, maxPixelSize), image)
        return image
    }

    private fun key(url: String, size: Int) = "$size|$url"

    companion object {
        /** Longest edge, in pixels, for images shown full-width or sent to the classifier. */
        const val FULL_PIXEL_SIZE = 2048

        /**
         * Decodes and downsizes image data, applying the EXIF rotation so the
         * pixels are upright. Metadata is dropped. Runs off the main thread, so a
         * 50 MP photo never blocks the UI.
         */
        suspend fun downsample(data: ByteArray, maxPixelSize: Int): Bitmap? = withContext(Dispatchers.Default) {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(data, 0, data.size, bounds)
            if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return@withContext null

            var sample = 1
            while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxPixelSize) sample *= 2
            val options = BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            val decoded = BitmapFactory.decodeByteArray(data, 0, data.size, options) ?: return@withContext null

            val matrix = Matrix()
            val longest = max(decoded.width, decoded.height)
            if (longest > maxPixelSize) {
                val factor = maxPixelSize.toFloat() / longest
                matrix.postScale(factor, factor)
            }
            val orientation = try {
                ExifInterface(ByteArrayInputStream(data)).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            } catch (e: Exception) {
                ExifInterface.ORIENTATION_NORMAL
            }
            when (orientation) {
                ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
                ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
                ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
                ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matrix.postScale(-1f, 1f)
                ExifInterface.ORIENTATION_FLIP_VERTICAL -> matrix.postScale(1f, -1f)
                ExifInterface.ORIENTATION_TRANSPOSE -> { matrix.postRotate(90f); matrix.postScale(-1f, 1f) }
                ExifInterface.ORIENTATION_TRANSVERSE -> { matrix.postRotate(270f); matrix.postScale(-1f, 1f) }
            }
            if (matrix.isIdentity) decoded
            else Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
        }

        /** Scales so the longest edge is at most `maxPixelSize`. */
        fun scaledDown(image: Bitmap, maxPixelSize: Int): Bitmap {
            val longest = max(image.width, image.height)
            if (longest <= maxPixelSize) return image
            val factor = maxPixelSize.toDouble() / longest
            return Bitmap.createScaledBitmap(
                image,
                (image.width * factor).roundToInt().coerceAtLeast(1),
                (image.height * factor).roundToInt().coerceAtLeast(1),
                true,
            )
        }
    }
}
