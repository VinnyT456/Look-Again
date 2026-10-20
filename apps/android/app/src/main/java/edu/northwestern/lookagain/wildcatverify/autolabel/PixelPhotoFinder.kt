package edu.northwestern.lookagain.wildcatverify.autolabel

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Finds photos in a screen capture from the pixels alone (the screen-capture
 * tab has no view tree to ask). App chrome is mostly the background colour with
 * sparse text; a photo is a solid block of varied pixels. The screen is cut
 * into small cells, cells that are nearly all non-background are joined into
 * blocks, and blocks the size and shape of a photo are kept.
 */
object PixelPhotoFinder {
    /** Cell side, in capture pixels. */
    private const val CELL = 4
    /** A pixel differs from the background by more than this (sum over RGB). */
    private const val COLOR_TOLERANCE = 36
    /** Share of a cell's pixels that must differ from the background. */
    private const val DENSE = 0.8
    /** Share of a block's bounding box its cells must fill. */
    private const val FILL = 0.7

    /**
     * @param argb capture pixels, row-major.
     * @param scale capture pixels per screen pixel (the capture may be smaller than the screen).
     * @return photo bounds in screen pixels, filtered like [PhotoFinder].
     */
    fun find(argb: IntArray, width: Int, height: Int, scale: Float, screen: Box, density: Float): List<Box> {
        val background = dominantColor(argb, width, height)
        val cols = width / CELL
        val rows = height / CELL
        if (cols < 2 || rows < 2) return emptyList()

        var grid = BooleanArray(cols * rows) { i ->
            val cx = (i % cols) * CELL
            val cy = (i / cols) * CELL
            var differ = 0
            for (y in cy until cy + CELL) for (x in cx until cx + CELL) {
                if (distance(argb[y * width + x], background) > COLOR_TOLERANCE) differ++
            }
            differ >= DENSE * CELL * CELL
        }
        // Closing (grow, then shrink) fills small background-coloured patches inside photos, like a white sky.
        grid = erode(dilate(grid, cols, rows), cols, rows)

        val boxes = components(grid, cols, rows)
            .filter { (box, cells) -> cells >= FILL * (box.width.toLong() * box.height) }
            .map { (box, _) ->
                Box(
                    (box.left * CELL / scale).toInt(),
                    (box.top * CELL / scale).toInt(),
                    (box.right * CELL / scale).toInt(),
                    (box.bottom * CELL / scale).toInt(),
                )
            }
        return PhotoFinder.filter(boxes, screen, density)
    }

    /** The most common colour (coarsely quantised), sampled on a sparse grid. */
    fun dominantColor(argb: IntArray, width: Int, height: Int): Int {
        val counts = HashMap<Int, Int>()
        val step = max(1, min(width, height) / 64)
        for (y in 0 until height step step) for (x in 0 until width step step) {
            val key = argb[y * width + x] and 0xF0F0F0
            counts[key] = (counts[key] ?: 0) + 1
        }
        val top = counts.maxByOrNull { it.value }?.key ?: 0xFFFFFF
        return top or 0x080808
    }

    private fun distance(a: Int, b: Int): Int =
        abs(((a shr 16) and 0xFF) - ((b shr 16) and 0xFF)) +
            abs(((a shr 8) and 0xFF) - ((b shr 8) and 0xFF)) +
            abs((a and 0xFF) - (b and 0xFF))

    private fun dilate(grid: BooleanArray, cols: Int, rows: Int) = BooleanArray(grid.size) { i ->
        val x = i % cols; val y = i / cols
        (max(0, y - 1)..min(rows - 1, y + 1)).any { yy -> (max(0, x - 1)..min(cols - 1, x + 1)).any { xx -> grid[yy * cols + xx] } }
    }

    private fun erode(grid: BooleanArray, cols: Int, rows: Int) = BooleanArray(grid.size) { i ->
        val x = i % cols; val y = i / cols
        (max(0, y - 1)..min(rows - 1, y + 1)).all { yy -> (max(0, x - 1)..min(cols - 1, x + 1)).all { xx -> grid[yy * cols + xx] } }
    }

    /** Connected blocks of set cells: bounding box (in cells) and cell count. */
    private fun components(grid: BooleanArray, cols: Int, rows: Int): List<Pair<Box, Int>> {
        val seen = BooleanArray(grid.size)
        val out = mutableListOf<Pair<Box, Int>>()
        val stack = IntArray(grid.size)
        for (start in grid.indices) {
            if (!grid[start] || seen[start]) continue
            var size = 0
            var minX = cols; var minY = rows; var maxX = 0; var maxY = 0; var count = 0
            stack[size++] = start; seen[start] = true
            while (size > 0) {
                val i = stack[--size]
                val x = i % cols; val y = i / cols
                count++
                minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y)
                for ((nx, ny) in arrayOf(x - 1 to y, x + 1 to y, x to y - 1, x to y + 1)) {
                    if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue
                    val n = ny * cols + nx
                    if (grid[n] && !seen[n]) { seen[n] = true; stack[size++] = n }
                }
            }
            out += Box(minX, minY, maxX + 1, maxY + 1) to count
        }
        return out
    }
}
