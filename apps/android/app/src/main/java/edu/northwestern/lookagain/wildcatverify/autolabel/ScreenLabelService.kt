package edu.northwestern.lookagain.wildcatverify.autolabel

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.view.WindowManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.core.content.IntentCompat
import edu.northwestern.lookagain.wildcatverify.MainActivity
import edu.northwestern.lookagain.wildcatverify.R
import edu.northwestern.lookagain.wildcatverify.container
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.abs

/**
 * The label tab: a screen-capture session (Android's MediaProjection, which
 * the user approves each time it starts) plus a small tab at the screen edge.
 * When the screen settles, photos are found from the pixels, checked on this
 * device, and get the same Real / AI badges as everywhere else.
 *
 * On Android 14+ the user can share a single app (Bluesky), so nothing else is seen.
 * Frames stay in memory and are replaced as new ones arrive.
 */
class ScreenLabelService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val main = Handler(Looper.getMainLooper())
    private lateinit var overlay: BadgeOverlay
    private lateinit var tab: FloatingTab
    private lateinit var labeler: PhotoLabeler

    private var projection: MediaProjection? = null
    private var display: VirtualDisplay? = null
    private var reader: ImageReader? = null
    private var captureThread: HandlerThread? = null

    private var captureWidth = 0
    private var captureHeight = 0
    private var screen = Box(0, 0, 0, 0)

    private var latest: Bitmap? = null
    private var lastSignature: IntArray? = null
    private var settleJob: Job? = null
    private var current: Map<Box, Long> = emptyMap()
    private var lastAnalyzed = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        labeler = PhotoLabeler(this, scope)
        overlay = BadgeOverlay(this, { labeler.open(it) }, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY)
        tab = FloatingTab(this, onTap = ::togglePause)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_TOGGLE -> {
                togglePause()
                return START_NOT_STICKY
            }
        }
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, 0) ?: 0
        val data = intent?.let { IntentCompat.getParcelableExtra(it, EXTRA_DATA, Intent::class.java) }
        if (data == null || projection != null) return START_NOT_STICKY

        // Must be in the foreground with the media-projection type before asking for the projection.
        val notification = notification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
        val manager = getSystemService(MediaProjectionManager::class.java)
        val granted = runCatching { manager.getMediaProjection(resultCode, data) }.getOrNull()
        if (granted == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        projection = granted
        granted.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                main.post { stopSelf() }
            }

            override fun onCapturedContentVisibilityChanged(isVisible: Boolean) {
                // Sharing a single app: it went to the background, so its photos aren't on screen.
                if (!isVisible) main.post { clearBadges() }
            }
        }, main)
        startCapture(granted)
        tab.show()
        isRunning = true
        isPaused = false
        scope.launch { container.warmUpDetector() }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        isRunning = false
        scope.cancel()
        settleJob?.cancel()
        display?.release()
        reader?.close()
        captureThread?.quitSafely()
        projection?.stop()
        projection = null
        if (::overlay.isInitialized) overlay.clear()
        if (::tab.isInitialized) tab.hide()
        if (::labeler.isInitialized) labeler.release()
        latest = null
        super.onDestroy()
    }

    private fun startCapture(projection: MediaProjection) {
        val (screenWidth, screenHeight) = screenSize()
        screen = Box(0, 0, screenWidth, screenHeight)
        // Half resolution is plenty to find photos and to feed a 384 px model, and halves the work.
        captureWidth = (screenWidth * CAPTURE_SCALE).toInt()
        captureHeight = (screenHeight * CAPTURE_SCALE).toInt()
        val thread = HandlerThread("ScreenLabelCapture").also { it.start() }
        captureThread = thread
        val imageReader = ImageReader.newInstance(captureWidth, captureHeight, PixelFormat.RGBA_8888, 2)
        reader = imageReader
        imageReader.setOnImageAvailableListener({ source ->
            val image = runCatching { source.acquireLatestImage() }.getOrNull() ?: return@setOnImageAvailableListener
            val bitmap = try {
                val plane = image.planes[0]
                val rowPixels = plane.rowStride / plane.pixelStride
                val padded = Bitmap.createBitmap(rowPixels, captureHeight, Bitmap.Config.ARGB_8888)
                padded.copyPixelsFromBuffer(plane.buffer)
                if (rowPixels == captureWidth) padded else Bitmap.createBitmap(padded, 0, 0, captureWidth, captureHeight)
            } finally {
                image.close()
            }
            val signature = signature(bitmap)
            main.post { onFrame(bitmap, signature) }
        }, Handler(thread.looper))
        display = projection.createVirtualDisplay(
            "Look Again labels",
            captureWidth,
            captureHeight,
            (resources.displayMetrics.densityDpi * CAPTURE_SCALE).toInt(),
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader.surface,
            null,
            null,
        )
    }

    private fun screenSize(): Pair<Int, Int> {
        val windows = getSystemService(WindowManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val bounds = windows.maximumWindowMetrics.bounds
            return bounds.width() to bounds.height()
        }
        val metrics = android.util.DisplayMetrics()
        @Suppress("DEPRECATION")
        windows.defaultDisplay.getRealMetrics(metrics)
        return metrics.widthPixels to metrics.heightPixels
    }

    /**
     * A new frame. Big changes (scrolling, switching screens) hide the badges and
     * wait for the screen to settle; small ones (a playing video, our own badges)
     * are ignored so labels don't flicker.
     */
    private fun onFrame(frame: Bitmap, signature: IntArray) {
        latest = frame
        val previous = lastSignature
        lastSignature = signature
        if (isPaused) return
        val moved = previous == null || changedShare(previous, signature) > MOTION_SHARE
        if (moved) {
            overlay.hideAll()
            scheduleAnalysis()
        } else if (settleJob?.isActive != true && SystemClock.elapsedRealtime() - lastAnalyzed > IDLE_RESCAN_MS) {
            // Something small changed long after the last look (a photo finished loading): look again.
            scheduleAnalysis()
        }
    }

    private fun scheduleAnalysis() {
        settleJob?.cancel()
        settleJob = scope.launch {
            delay(SETTLE_MS)
            latest?.let { analyze(it) }
        }
    }

    private suspend fun analyze(frame: Bitmap) {
        lastAnalyzed = SystemClock.elapsedRealtime()
        val density = resources.displayMetrics.density
        val found = withContext(Dispatchers.Default) {
            val pixels = IntArray(frame.width * frame.height)
            frame.getPixels(pixels, 0, frame.width, 0, 0, frame.width, frame.height)
            val boxes = PixelPhotoFinder.find(pixels, frame.width, frame.height, CAPTURE_SCALE, screen, density)
            boxes.mapNotNull { box ->
                val left = (box.left * CAPTURE_SCALE).toInt().coerceIn(0, frame.width - 1)
                val top = (box.top * CAPTURE_SCALE).toInt().coerceIn(0, frame.height - 1)
                val width = (box.width * CAPTURE_SCALE).toInt().coerceAtMost(frame.width - left)
                val height = (box.height * CAPTURE_SCALE).toInt().coerceAtMost(frame.height - top)
                if (width < 16 || height < 16) return@mapNotNull null
                val crop = Bitmap.createBitmap(frame, left, top, width, height)
                Triple(box, PhotoLabeler.hashOf(crop), crop)
            }
        }
        if (isPaused) return
        current = found.associate { (box, hash, _) -> box to hash }
        overlay.retain(current.keys)
        for ((box, hash, crop) in found) {
            overlay.show(box, labeler.cached(hash)?.let { Badge.Result(it) } ?: Badge.Checking)
            labeler.request(hash, crop, ::onLabel)
        }
    }

    private fun onLabel(hash: Long, item: VerificationCase) {
        if (isPaused || settleJob?.isActive == true) return
        current.entries.firstOrNull { ImageHash.distance(it.value, hash) <= PhotoLabeler.SAME_PHOTO_BITS }?.let { (box, _) ->
            overlay.show(box, Badge.Result(item))
        }
    }

    private fun togglePause() {
        isPaused = !isPaused
        tab.setPaused(isPaused)
        if (isPaused) clearBadges() else scheduleAnalysis()
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, notification())
    }

    private fun clearBadges() {
        settleJob?.cancel()
        overlay.clear()
        current = emptyMap()
    }

    private fun notification(): Notification {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL, "Label tab", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Shown while the label tab is reading the screen."
            },
        )
        fun service(action: String, code: Int) = PendingIntent.getService(
            this, code, Intent(this, ScreenLabelService::class.java).setAction(action), PendingIntent.FLAG_IMMUTABLE,
        )
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK), PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(if (isPaused) "Label tab paused" else "Labeling photos on screen")
            .setContentText("Checked on this device. Nothing is recorded or uploaded.")
            .setOngoing(true)
            .setContentIntent(open)
            .addAction(0, if (isPaused) "Resume" else "Pause", service(ACTION_TOGGLE, 1))
            .addAction(0, "Stop", service(ACTION_STOP, 2))
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    companion object {
        private const val CHANNEL = "label_tab"
        private const val NOTIFICATION_ID = 7
        private const val EXTRA_RESULT_CODE = "resultCode"
        private const val EXTRA_DATA = "data"
        private const val ACTION_STOP = "edu.northwestern.lookagain.wildcatverify.STOP_LABEL_TAB"
        private const val ACTION_TOGGLE = "edu.northwestern.lookagain.wildcatverify.TOGGLE_LABEL_TAB"
        private const val CAPTURE_SCALE = 0.5f
        /** Quiet time after the last big change before photos are looked at. */
        private const val SETTLE_MS = 400L
        /** Share of the screen that must change between frames to count as scrolling. */
        private const val MOTION_SHARE = 0.12
        private const val IDLE_RESCAN_MS = 1_500L
        private const val SIGNATURE_W = 27
        private const val SIGNATURE_H = 60

        /** Whether the tab is running; read by Settings. */
        var isRunning by mutableStateOf(false)
            private set
        var isPaused by mutableStateOf(false)
            private set

        /** Starts the session with the user's screen-capture consent. */
        fun start(context: Context, resultCode: Int, data: Intent) {
            ContextCompat.startForegroundService(
                context,
                Intent(context, ScreenLabelService::class.java)
                    .putExtra(EXTRA_RESULT_CODE, resultCode)
                    .putExtra(EXTRA_DATA, data),
            )
        }

        fun stop(context: Context) {
            context.startService(Intent(context, ScreenLabelService::class.java).setAction(ACTION_STOP))
        }

        /** A tiny greyscale thumbnail of a frame, for telling scrolling from small changes. */
        private fun signature(frame: Bitmap): IntArray {
            val small = Bitmap.createScaledBitmap(frame, SIGNATURE_W, SIGNATURE_H, true)
            val pixels = IntArray(SIGNATURE_W * SIGNATURE_H)
            small.getPixels(pixels, 0, SIGNATURE_W, 0, 0, SIGNATURE_W, SIGNATURE_H)
            return IntArray(pixels.size) { i ->
                val p = pixels[i]
                (((p shr 16) and 0xFF) + ((p shr 8) and 0xFF) + (p and 0xFF)) / 3
            }
        }

        /** Share of thumbnail cells that changed noticeably. */
        internal fun changedShare(a: IntArray, b: IntArray): Double {
            if (a.size != b.size) return 1.0
            var changed = 0
            for (i in a.indices) if (abs(a[i] - b[i]) > 24) changed++
            return changed.toDouble() / a.size
        }
    }
}
