package edu.northwestern.lookagain.wildcatverify.autolabel

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.ComponentName
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.Build
import android.util.Log
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityManager
import android.view.accessibility.AccessibilityNodeInfo
import edu.northwestern.lookagain.wildcatverify.container
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume

/**
 * Auto-Label: while the user browses Bluesky (the app, or bsky.app in Chrome),
 * finds the photos on screen, checks each one on this device, and pins a
 * Real / AI badge to it.
 *
 * - Where photos are comes from the accessibility tree (bounds of image views).
 * - What they look like comes from one screenshot per settled screen, cropped to
 *   those bounds. Screenshots and crops stay in memory.
 * - Each crop is hashed, so a photo scrolled away and back is labelled instantly.
 * - Badges hide while the feed moves and come back once it settles.
 *
 * Nothing is recorded in My Checks unless the user taps a badge.
 */
class AutoLabelService : AccessibilityService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private lateinit var overlay: BadgeOverlay
    private val labeler by lazy { PhotoLabeler(this, scope) }

    private var settleJob: Job? = null
    private var lastBoxes: List<Box> = emptyList()
    private var movedSinceScan = true
    /** Photos on screen at the last scan, and their hashes. */
    private var current: Map<Box, Long> = emptyMap()
    private var chromeOnBluesky = false

    override fun onServiceConnected() {
        overlay = BadgeOverlay(this, { labeler.open(it) })
        scope.launch { container.warmUpDetector() }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val pkg = event.packageName?.toString() ?: return
        if (pkg == packageName || !::overlay.isInitialized) return
        if (container.settings.autoLabelPaused) {
            reset()
            return
        }
        if (pkg == CHROME) updateChromeUrl()
        if (!isWatching(pkg)) {
            reset()
            return
        }
        when (event.eventType) {
            AccessibilityEvent.TYPE_VIEW_SCROLLED -> {
                movedSinceScan = true
                overlay.hideAll()
            }
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                movedSinceScan = true
                overlay.clear()
            }
        }
        settleJob?.cancel()
        settleJob = scope.launch {
            delay(SETTLE_MS)
            scan()
        }
    }

    override fun onInterrupt() = reset()

    override fun onDestroy() {
        scope.cancel()
        if (::overlay.isInitialized) overlay.clear()
        labeler.release()
        super.onDestroy()
    }

    private fun isWatching(pkg: String): Boolean = when (pkg) {
        BLUESKY -> true
        CHROME -> chromeOnBluesky
        else -> false
    }

    /** Chrome is only watched while bsky.app is the open page. */
    private fun updateChromeUrl() {
        val root = rootInActiveWindow ?: return
        if (root.packageName?.toString() != CHROME) return
        val url = root.findAccessibilityNodeInfosByViewId("$CHROME:id/url_bar").firstOrNull()?.text?.toString() ?: return
        val host = url.removePrefix("https://").removePrefix("http://").substringBefore('/').lowercase()
        chromeOnBluesky = host == "bsky.app" || host.endsWith(".bsky.app")
    }

    private fun reset() {
        settleJob?.cancel()
        if (::overlay.isInitialized) overlay.clear()
        lastBoxes = emptyList()
        current = emptyMap()
        movedSinceScan = true
    }

    private suspend fun scan() {
        val root = rootInActiveWindow ?: return
        if (!isWatching(root.packageName?.toString() ?: return)) return
        val window = Rect().also(root::getBoundsInScreen)
        val nodes = mutableListOf<ImageNode>()
        collectImages(root, nodes, depth = 0)
        val boxes = PhotoFinder.select(nodes, window.toBox(), resources.displayMetrics.density)

        // Content changed but nothing moved (videos, counters): keep the badges as they are.
        if (!movedSinceScan && boxes.size == lastBoxes.size && boxes.zip(lastBoxes).all { (a, b) -> a.closeTo(b) }) {
            current.forEach { (box, hash) -> showFor(box, hash) }
            return
        }
        movedSinceScan = false
        lastBoxes = boxes
        if (boxes.isEmpty()) {
            overlay.clear()
            current = emptyMap()
            return
        }

        // The screenshot must not contain our own badges.
        overlay.hideAll()
        delay(BADGE_HIDE_MS)
        val shot = screenshot() ?: return
        val found = linkedMapOf<Box, Long>()
        val crops = mutableListOf<Pair<Long, Bitmap>>()
        withContext(Dispatchers.Default) {
            for (box in boxes) {
                val left = box.left.coerceIn(0, shot.width - 1)
                val top = box.top.coerceIn(0, shot.height - 1)
                val width = box.width.coerceAtMost(shot.width - left)
                val height = box.height.coerceAtMost(shot.height - top)
                if (width < 16 || height < 16) continue
                val crop = Bitmap.createBitmap(shot, left, top, width, height)
                val hash = PhotoLabeler.hashOf(crop)
                found[box] = hash
                crops += hash to crop
            }
        }
        if (crops.none { it.second === shot }) shot.recycle()
        if (movedSinceScan) return // Scrolled while we were capturing; the next scan takes over.

        current = found
        overlay.retain(found.keys)
        found.forEach { (box, hash) -> showFor(box, hash) }
        for ((hash, crop) in crops) labeler.request(hash, crop, ::onLabel)
    }

    private fun showFor(box: Box, hash: Long) {
        overlay.show(box, labeler.cached(hash)?.let { Badge.Result(it) } ?: Badge.Checking)
    }

    private fun onLabel(hash: Long, item: VerificationCase) {
        if (movedSinceScan) return
        current.entries.firstOrNull { ImageHash.distance(it.value, hash) <= PhotoLabeler.SAME_PHOTO_BITS }?.let { (box, _) ->
            overlay.show(box, Badge.Result(item))
        }
    }

    private fun collectImages(node: AccessibilityNodeInfo, out: MutableList<ImageNode>, depth: Int) {
        if (depth > MAX_DEPTH || out.size > MAX_NODES) return
        if (PhotoFinder.isImageClass(node.className)) {
            val rect = Rect().also(node::getBoundsInScreen)
            out += ImageNode(node.className.toString(), rect.toBox(), node.isVisibleToUser)
        }
        for (i in 0 until node.childCount) {
            node.getChild(i)?.let { collectImages(it, out, depth + 1) }
        }
    }

    /** One screenshot of the display, as a software bitmap. Android 11+. */
    private suspend fun screenshot(): Bitmap? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return null
        repeat(2) { attempt ->
            val bitmap = suspendCancellableCoroutine { continuation ->
                takeScreenshot(
                    Display.DEFAULT_DISPLAY,
                    mainExecutor,
                    object : TakeScreenshotCallback {
                        override fun onSuccess(result: ScreenshotResult) {
                            val buffer = result.hardwareBuffer
                            val image = Bitmap.wrapHardwareBuffer(buffer, result.colorSpace)?.copy(Bitmap.Config.ARGB_8888, false)
                            buffer.close()
                            continuation.resume(image)
                        }

                        override fun onFailure(errorCode: Int) {
                            Log.d(TAG, "Screenshot failed: $errorCode")
                            continuation.resume(null)
                        }
                    },
                )
            }
            if (bitmap != null) return bitmap
            // Android allows about three screenshots a second; wait and try once more.
            if (attempt == 0) delay(SCREENSHOT_RETRY_MS)
        }
        return null
    }

    private fun Rect.toBox() = Box(left, top, right, bottom)

    companion object {
        private const val TAG = "AutoLabel"
        const val BLUESKY = "xyz.blueskyweb.app"
        const val CHROME = "com.android.chrome"
        /** Quiet time after the last scroll before photos are looked at. */
        private const val SETTLE_MS = 350L
        /** Long enough for one frame without badges to reach the screen. */
        private const val BADGE_HIDE_MS = 50L
        private const val SCREENSHOT_RETRY_MS = 400L
        private const val MAX_DEPTH = 80
        /** Stop collecting after this many image nodes; a feed screen has far fewer. */
        private const val MAX_NODES = 400

        /** Whether the user has turned Auto-Label on in system Accessibility settings. */
        fun isEnabled(context: Context): Boolean {
            val manager = context.getSystemService(AccessibilityManager::class.java) ?: return false
            val ours = ComponentName(context, AutoLabelService::class.java)
            return manager.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
                .any { it.resolveInfo?.serviceInfo?.let { info -> ComponentName(info.packageName, info.name) } == ours }
        }

        /** Screenshots for accessibility services arrived in Android 11. */
        val isSupported: Boolean get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
    }
}
