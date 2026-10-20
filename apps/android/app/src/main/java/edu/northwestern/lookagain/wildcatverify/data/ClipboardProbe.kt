package edu.northwestern.lookagain.wildcatverify.data

import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.os.Build
import android.view.textclassifier.TextClassifier

/**
 * Asks whether the clipboard holds something that looks like a link, from its
 * description only (no contents, so Android shows no "pasted" notice). The
 * text is read only when the user taps Paste.
 */
class ClipboardProbe(
    /** Changes whenever something new is copied. */
    val changeToken: () -> Long?,
    val hasProbableLink: () -> Boolean,
    /** Reads the copied text. Only called from a user's tap. */
    val read: () -> String?,
) {
    companion object {
        fun system(context: Context): ClipboardProbe {
            val clipboard = context.getSystemService(ClipboardManager::class.java)
            return ClipboardProbe(
                changeToken = { clipboard?.primaryClipDescription?.timestamp },
                hasProbableLink = {
                    val description = clipboard?.primaryClipDescription
                    when {
                        description == null -> false
                        !description.hasMimeType(ClipDescription.MIMETYPE_TEXT_PLAIN) &&
                            !description.hasMimeType(ClipDescription.MIMETYPE_TEXT_HTML) &&
                            !description.hasMimeType(ClipDescription.MIMETYPE_TEXT_URILIST) -> false
                        // Android 12+ classifies copied text without handing it to apps.
                        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
                            description.classificationStatus == ClipDescription.CLASSIFICATION_COMPLETE ->
                            description.getConfidenceScore(TextClassifier.TYPE_URL) >= 0.5f
                        else -> true
                    }
                },
                read = { clipboard?.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(context)?.toString() },
            )
        }

        /** No clipboard at all (tests, the share screen). */
        val none = ClipboardProbe({ null }, { false }, { null })
    }
}
