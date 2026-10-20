package edu.northwestern.lookagain.wildcatverify.autolabel

import kotlin.math.max
import kotlin.math.min

/** A rectangle in screen pixels. Plain so the selection rules run on the JVM in tests. */
data class Box(val left: Int, val top: Int, val right: Int, val bottom: Int) {
    val width: Int get() = right - left
    val height: Int get() = bottom - top
    val area: Long get() = width.toLong() * height

    fun intersectionOverUnion(other: Box): Double {
        val w = min(right, other.right) - max(left, other.left)
        val h = min(bottom, other.bottom) - max(top, other.top)
        if (w <= 0 || h <= 0) return 0.0
        val overlap = w.toLong() * h
        return overlap.toDouble() / (area + other.area - overlap)
    }

    /** Within `tolerance` px on every side: the same photo after a tiny relayout. */
    fun closeTo(other: Box, tolerance: Int = 4): Boolean =
        kotlin.math.abs(left - other.left) <= tolerance && kotlin.math.abs(top - other.top) <= tolerance &&
            kotlin.math.abs(right - other.right) <= tolerance && kotlin.math.abs(bottom - other.bottom) <= tolerance
}

/** An image-like node from the accessibility tree. */
data class ImageNode(val className: String, val box: Box, val visible: Boolean)

/**
 * Decides which image nodes on screen are photos worth labelling: post images,
 * not avatars, icons, or photos half scrolled off screen.
 */
object PhotoFinder {
    /** Class names apps report for images: native views, and web images in Chrome. */
    private val imageClasses = setOf("android.widget.ImageView", "android.widget.Image")

    /** Smaller than this (in dp) is an avatar, icon or thumbnail strip. */
    const val MIN_SIDE_DP = 120
    /** Photos touching these screen bands are partly hidden (status bar, toolbars, tab bar). */
    const val EDGE_MARGIN_DP = 8
    /** At most this many photos are labelled at once; feeds rarely show more. */
    const val MAX_PHOTOS = 6

    fun isImageClass(className: CharSequence?): Boolean = className?.toString() in imageClasses

    /**
     * @param screen the visible area of the app window, in screen pixels.
     * @param density pixels per dp.
     */
    fun select(nodes: List<ImageNode>, screen: Box, density: Float): List<Box> =
        filter(nodes.filter { it.visible && it.className in imageClasses }.map { it.box }, screen, density)

    /** Keeps photo-sized boxes fully on screen, merges duplicates, top to bottom. */
    fun filter(boxes: List<Box>, screen: Box, density: Float): List<Box> {
        val minSide = (MIN_SIDE_DP * density).toInt()
        val margin = (EDGE_MARGIN_DP * density).toInt()
        val candidates = boxes
            .filter { it.width >= minSide && it.height >= minSide }
            // Clipped by the screen edge: the bounds only cover the visible part.
            .filter { it.top > screen.top + margin && it.bottom < screen.bottom - margin }
            .filter { it.left >= screen.left && it.right <= screen.right }
            .sortedByDescending { it.area }

        // Wrappers and the image inside them report nearly the same bounds; keep one.
        val kept = mutableListOf<Box>()
        for (box in candidates) {
            if (kept.none { it.intersectionOverUnion(box) > 0.6 }) kept += box
        }
        return kept.sortedWith(compareBy({ it.top }, { it.left })).take(MAX_PHOTOS)
    }
}

/**
 * A 64-bit difference hash: shrink to 9×8 grey pixels and record whether each
 * pixel is brighter than its right neighbour. The same photo hashes the same
 * after scrolling away and back, so its label shows instantly.
 */
object ImageHash {
    /** @param argb 9×8 pixels, row-major. */
    fun dHash(argb: IntArray): Long {
        require(argb.size == 72)
        var hash = 0L
        var bit = 0
        for (y in 0 until 8) {
            for (x in 0 until 8) {
                if (luma(argb[y * 9 + x]) > luma(argb[y * 9 + x + 1])) hash = hash or (1L shl bit)
                bit++
            }
        }
        return hash
    }

    fun distance(a: Long, b: Long): Int = java.lang.Long.bitCount(a xor b)

    private fun luma(p: Int): Int = (((p shr 16) and 0xFF) * 299 + ((p shr 8) and 0xFF) * 587 + (p and 0xFF) * 114) / 1000
}
