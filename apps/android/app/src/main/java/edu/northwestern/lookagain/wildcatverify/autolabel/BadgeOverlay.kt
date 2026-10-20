package edu.northwestern.lookagain.wildcatverify.autolabel

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.TextView
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import edu.northwestern.lookagain.wildcatverify.model.VerificationCase

/** What a badge says. */
sealed interface Badge {
    data object Checking : Badge
    data class Result(val item: VerificationCase) : Badge
}

/**
 * Small pills pinned to the top-left corner of each photo, drawn in overlay
 * windows. Each badge is its own tiny window so taps elsewhere still reach Bluesky.
 */
class BadgeOverlay(
    private val context: Context,
    private val onTap: (VerificationCase) -> Unit,
    /** Accessibility overlays need no permission; the screen tab uses "Display over other apps". */
    private val windowType: Int = WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
) {
    private val windows = context.getSystemService(WindowManager::class.java)
    private val badges = mutableMapOf<Box, TextView>()
    private val density = context.resources.displayMetrics.density

    val boxes: Set<Box> get() = badges.keys

    /** Shows or updates the badge for the photo at `box`. */
    fun show(box: Box, badge: Badge) {
        val view = badges.getOrPut(box) { createView().also { windows.addView(it, params(box)) } }
        style(view, badge)
        view.visibility = View.VISIBLE
    }

    /** Removes badges for photos no longer on screen. */
    fun retain(keep: Collection<Box>) {
        (badges.keys - keep.toSet()).forEach(::remove)
    }

    /** While the feed scrolls the badges would lag behind their photos, so they hide until it settles. */
    fun hideAll() {
        badges.values.forEach { it.visibility = View.INVISIBLE }
    }

    fun clear() {
        badges.keys.toList().forEach(::remove)
    }

    private fun remove(box: Box) {
        badges.remove(box)?.let { runCatching { windows.removeView(it) } }
    }

    private fun params(box: Box) = WindowManager.LayoutParams(
        WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.WRAP_CONTENT,
        windowType,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.START
        x = box.left + dp(8)
        y = box.top + dp(8)
        layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
    }

    private fun createView() = TextView(context).apply {
        setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f)
        typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
        setTextColor(Color.WHITE)
        setPadding(dp(10), dp(5), dp(10), dp(5))
        elevation = dp(3).toFloat()
        maxLines = 1
    }

    private fun style(view: TextView, badge: Badge) {
        val (text, color, description) = when (badge) {
            Badge.Checking -> Triple("◌ Checking…", 0xB3000000.toInt(), "WildcatVerify is checking this photo")
            is Badge.Result -> {
                val item = badge.item
                val color = when (item.verdict) {
                    VerdictType.REAL -> 0xF016A34A.toInt()
                    VerdictType.TAMPERED -> 0xF0D97706.toInt()
                    VerdictType.AI -> 0xF0DC2626.toInt()
                }
                val glyph = when (item.verdict) {
                    VerdictType.REAL -> "✓"
                    VerdictType.TAMPERED -> "⚠"
                    VerdictType.AI -> "✦"
                }
                Triple(
                    "$glyph ${item.verdict.shortLabel} ${item.confidencePercentage}%",
                    color,
                    "WildcatVerify: ${item.verdict.label}, ${item.confidencePercentage} percent confidence. Double tap for details.",
                )
            }
        }
        view.text = text
        view.contentDescription = description
        view.background = GradientDrawable().apply {
            cornerRadius = dp(14).toFloat()
            setColor(color)
            setStroke(dp(1), 0x59FFFFFF)
        }
        view.setOnClickListener((badge as? Badge.Result)?.let { result -> View.OnClickListener { onTap(result.item) } })
        view.isClickable = badge is Badge.Result
    }

    private fun dp(value: Int): Int = (value * density).toInt()
}
