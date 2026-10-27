package edu.northwestern.lookagain.wildcatverify.data

import android.graphics.Bitmap
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import edu.northwestern.lookagain.wildcatverify.model.InMemoryImage
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import kotlinx.serialization.encodeToString
import java.io.File
import java.io.FileOutputStream

/**
 * Saves My Checks on this device when the user turns on "Keep My Checks".
 *
 * - Results go to `noBackupFiles/History/history.json`.
 * - Uploaded and shared photos (which otherwise live only in memory) are saved
 *   as small JPEGs next to it, so their results still show the photo.
 * - The folder is in the app's no-backup storage, so it is never copied to the
 *   cloud or another device; Android encrypts app storage at rest.
 * - Turning the setting off, or clearing My Checks, deletes the folder.
 */
class HistoryPersistence(val directory: File) {
    private val indexFile get() = File(directory, "history.json")
    private val photosDir get() = File(directory, "Photos")

    fun photoFile(id: String) = File(photosDir, "$id.jpg")

    /** Saved checks, newest first. Missing or unreadable files give an empty list. */
    fun load(): List<VerificationCase> = try {
        lenientJson.decodeFromString<List<VerificationCase>>(indexFile.readText())
    } catch (e: Exception) {
        emptyList()
    }

    /**
     * Writes the list, saving any in-memory photo it refers to and pointing the
     * saved copy at it. Returns the cases as stored.
     */
    fun save(cases: List<VerificationCase>, images: ImageRepository): List<VerificationCase> {
        photosDir.mkdirs()
        val kept = mutableSetOf<String>()
        val stored = cases.map { item ->
            var copy = item
            val url = item.imageUrl
            if (url != null && InMemoryImage.isInMemory(url)) {
                images.cachedImage(url)?.let { image ->
                    val file = photoFile(item.id)
                    if (!file.exists()) writeJpeg(image, file)
                    copy = item.copy(imageUrl = file.toURI().toString())
                }
            }
            copy.imageUrl?.takeIf { it.startsWith("file:") }?.let { kept += it.substringAfterLast('/') }
            copy
        }
        val temp = File(directory, "history.json.tmp")
        temp.writeText(lenientJson.encodeToString(stored))
        // A rename can fail (e.g. the target is busy); never leave the old list in place silently.
        if (!temp.renameTo(indexFile)) {
            temp.copyTo(indexFile, overwrite = true)
            temp.delete()
        }
        photosDir.listFiles()?.filter { it.name !in kept }?.forEach { it.delete() }
        return stored
    }

    /** Deletes everything saved. */
    fun erase() {
        directory.deleteRecursively()
    }

    private fun writeJpeg(image: Bitmap, file: File) {
        val small = ImageRepository.scaledDown(image, SAVED_PHOTO_SIZE)
        FileOutputStream(file).use { small.compress(Bitmap.CompressFormat.JPEG, 80, it) }
    }

    companion object {
        /** Longest edge of saved photos, in pixels. */
        const val SAVED_PHOTO_SIZE = 1024
    }
}

/**
 * The user's checks. Kept in memory by default; when "Keep My Checks" is on,
 * every change is also written to disk through [HistoryPersistence].
 */
class HistoryStore(
    private val images: ImageRepository,
    private var persistence: HistoryPersistence? = null,
) {
    var cases by mutableStateOf(persistence?.load() ?: emptyList())
        private set

    /** Checks added since the user last opened My Checks; drives the tab badge. */
    var unseenCount by mutableIntStateOf(0)
        private set

    val isSaving: Boolean get() = persistence != null

    /** Adds a case to the top of history, or moves it there if already present. */
    fun record(item: VerificationCase) {
        cases = listOf(item) + cases.filter { it.id != item.id }
        unseenCount += 1
        save()
    }

    fun markSeen() {
        unseenCount = 0
    }

    fun remove(item: VerificationCase) {
        cases = cases.filter { it.id != item.id }
        item.imageUrl?.takeIf(InMemoryImage::isInMemory)?.let(images::removeUpload)
        save()
    }

    fun clear() {
        cases = emptyList()
        unseenCount = 0
        images.removeAllUploads()
        save()
    }

    /** Turns saving on (writes the current checks) or off (deletes what was saved). */
    fun setPersistence(newValue: HistoryPersistence?) {
        if (newValue != null) {
            persistence = newValue
            save()
        } else {
            persistence?.erase()
            persistence = null
        }
    }

    private fun save() {
        val persistence = persistence ?: return
        try {
            cases = persistence.save(cases, images)
        } catch (e: Exception) {
            Log.w("WildcatVerify", "Couldn't save My Checks", e)
        }
    }
}
