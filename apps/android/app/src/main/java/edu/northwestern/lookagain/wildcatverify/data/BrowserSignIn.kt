package edu.northwestern.lookagain.wildcatverify.data

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.browser.customtabs.CustomTabsIntent
import kotlinx.coroutines.CompletableDeferred
import java.lang.ref.WeakReference

/**
 * Shows Bluesky's sign-in page in a Custom Tab and waits for its redirect
 * back to the app (`io.github.vinnyt456:/oauth/callback`), which
 * [MainActivity][edu.northwestern.lookagain.wildcatverify.MainActivity]
 * hands to [deliver]. The tab shares the browser's cookies, so people already
 * signed in to bsky.app just tap Authorize, like iOS's shared web session.
 */
class BrowserSignIn(
    /** A redirect arrived but nothing was waiting (the app was restarted while the tab was open). */
    private val onInterrupted: () -> Unit = {},
) {
    private class Waiting(val state: String, val reply: CompletableDeferred<String>)

    private var waiting: Waiting? = null
    private var activity = WeakReference<Activity>(null)

    /**
     * The activity the tab opens over; MainActivity keeps this current. Looked
     * up when the tab opens, after sign-in's network steps, so a rotation in
     * between doesn't leave the tab in a separate task.
     */
    fun attach(activity: Activity) {
        this.activity = WeakReference(activity)
    }

    /**
     * Returns the redirect URL carrying `state`; throws [BlueskyAuthException]
     * (cancelled) if the user closes the tab.
     */
    suspend fun open(url: String, state: String): String {
        val reply = CompletableDeferred<String>()
        waiting?.reply?.completeExceptionally(BlueskyAuthException(BlueskyAuthException.Reason.CANCELLED))
        val current = Waiting(state, reply)
        waiting = current
        try {
            launch(Uri.parse(url))
            return reply.await()
        } finally {
            if (waiting === current) waiting = null
        }
    }

    /**
     * A redirect reached the app. Returns false for anything that isn't ours.
     * One for another request (a different `state`, e.g. sent by another app)
     * is ignored and the sign-in keeps waiting.
     */
    fun deliver(uri: Uri?): Boolean {
        if (uri?.scheme != BlueskyOAuthConfig.CALLBACK_SCHEME || uri.path != "/oauth/callback") return false
        val current = waiting
        when {
            current == null -> onInterrupted()
            BlueskyOAuthClient.queryOf(uri.toString())["state"] == current.state -> current.reply.complete(uri.toString())
        }
        return true
    }

    /**
     * The app came back to the front. A redirect arrives before this, so if
     * one is still awaited the user closed the tab instead.
     */
    fun appResumed() {
        waiting?.reply?.completeExceptionally(BlueskyAuthException(BlueskyAuthException.Reason.CANCELLED))
    }

    private fun launch(uri: Uri) {
        val from = activity.get()?.takeUnless { it.isFinishing || it.isDestroyed }
            ?: throw BlueskyAuthException(BlueskyAuthException.Reason.CANCELLED)
        try {
            CustomTabsIntent.Builder().setShowTitle(true).build().launchUrl(from, uri)
        } catch (e: ActivityNotFoundException) {
            // No browser supports Custom Tabs; any browser will do.
            try {
                from.startActivity(Intent(Intent.ACTION_VIEW, uri))
            } catch (e: ActivityNotFoundException) {
                throw BlueskyAuthException(BlueskyAuthException.Reason.BAD_RESPONSE)
            }
        }
    }
}
