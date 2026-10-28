package edu.northwestern.lookagain.wildcatverify.autolabel

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import edu.northwestern.lookagain.wildcatverify.R
import kotlin.math.abs

/**
 * The label tab: a small handle on the right edge of the screen showing the
 * app's mark. Tap to pause or resume labels; drag up or down to move it.
 * Drawn with "Display over other apps".
 */
class FloatingTab(private val context: Context, private val onTap: () -> Unit) {
    private val windows = context.getSystemService(WindowManager::class.java)
    private val density = context.resources.displayMetrics.density
    private var view: FrameLayout? = null
    private val params = WindowManager.LayoutParams(
        dp(44),
        dp(56),
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.END
        x = 0
        y = (context.resources.displayMetrics.heightPixels * 0.35).toInt()
    }

    fun show() {
        if (view != null) return
        val icon = ImageView(context).apply {
            setImageResource(R.drawable.face_check_magnifier)
            scaleType = ImageView.ScaleType.CENTER_CROP
            clipToOutline = true
            background = GradientDrawable().apply { cornerRadius = dp(8).toFloat() }
        }
        view = FrameLayout(context).apply {
            background = tabBackground(paused = false)
            elevation = dp(6).toFloat()
            setPadding(dp(8), dp(10), dp(6), dp(10))
            addView(icon, FrameLayout.LayoutParams(dp(30), dp(30), Gravity.CENTER))
            contentDescription = "Look Again label tab. Double tap to pause labels."
            setOnClickListener { onTap() }
            setOnTouchListener(DragOrTap())
        }
        windows.addView(view, params)
    }

    fun hide() {
        view?.let { runCatching { windows.removeView(it) } }
        view = null
    }

    fun setPaused(paused: Boolean) {
        view?.apply {
            background = tabBackground(paused)
            alpha = if (paused) 0.6f else 1f
            contentDescription = if (paused) "Look Again label tab, paused. Double tap to resume labels." else "Look Again label tab. Double tap to pause labels."
        }
    }

    private fun tabBackground(paused: Boolean) = GradientDrawable().apply {
        val radius = dp(16).toFloat()
        cornerRadii = floatArrayOf(radius, radius, 0f, 0f, 0f, 0f, radius, radius)
        setColor(if (paused) 0xFF8E8E93.toInt() else 0xFF4E2A84.toInt())
    }

    private fun dp(value: Int) = (value * density).toInt()

    /** Vertical drag moves the tab; a touch that doesn't move is a tap. */
    private inner class DragOrTap : View.OnTouchListener {
        private val slop = ViewConfiguration.get(context).scaledTouchSlop
        private var downY = 0f
        private var startY = 0
        private var dragging = false

        @SuppressLint("ClickableViewAccessibility")
        override fun onTouch(v: View, event: MotionEvent): Boolean {
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downY = event.rawY
                    startY = params.y
                    dragging = false
                }
                MotionEvent.ACTION_MOVE -> {
                    val dy = event.rawY - downY
                    if (abs(dy) > slop) dragging = true
                    if (dragging) {
                        params.y = (startY + dy).toInt().coerceIn(0, context.resources.displayMetrics.heightPixels - params.height)
                        windows.updateViewLayout(v, params)
                    }
                }
                MotionEvent.ACTION_UP -> if (!dragging) v.performClick()
            }
            return true
        }
    }
}
