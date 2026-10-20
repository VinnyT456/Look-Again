package edu.northwestern.lookagain.wildcatverify.model

import edu.northwestern.lookagain.wildcatverify.data.DetectorPreprocessor
import kotlinx.serialization.Serializable
import kotlin.math.max
import kotlin.math.min

/**
 * The detector's per-patch map: how much each 16×16 patch of the 384×384
 * center crop pushed the decision toward "AI" (positive) or away (negative),
 * in logit units. It covers only part of the decision; the rest comes from
 * whole-image features that have no location.
 */
@Serializable
data class PatchHeatmap(
    /** Row-major, `GRID_SIZE × GRID_SIZE`. */
    val values: List<Float>,
) {
    init {
        require(values.size == GRID_SIZE * GRID_SIZE) { "Expected a 24×24 grid" }
    }

    /** Whether any patch pushed toward "AI" at all. */
    val hasSignal: Boolean get() = (values.maxOrNull() ?: 0f) > 0f

    /**
     * 0–1 per cell: positive contributions relative to the strongest one.
     * Cells that pushed toward "real" are 0, so only suspicious areas show.
     */
    val intensities: List<Double>
        get() {
            val peak = values.maxOrNull() ?: 0f
            if (peak <= 0f) return List(values.size) { 0.0 }
            return values.map { (max(it, 0f) / peak).toDouble() }
        }

    /** A rectangle as fractions of an image's width and height. */
    data class Region(val x: Double, val y: Double, val width: Double, val height: Double)

    companion object {
        const val GRID_SIZE = 24

        fun fromValues(values: FloatArray): PatchHeatmap? =
            if (values.size == GRID_SIZE * GRID_SIZE) PatchHeatmap(values.toList()) else null

        /**
         * The part of the full image the model actually looked at. Mirrors
         * [DetectorPreprocessor]: the short edge is resized to 440 and the centre
         * 384×384 is kept.
         */
        fun coveredRegion(width: Int, height: Int): Region {
            if (width <= 0 || height <= 0) return Region(0.0, 0.0, 1.0, 1.0)
            val side = DetectorPreprocessor.CROP_SIZE.toDouble() / DetectorPreprocessor.SHORT_EDGE * min(width, height)
            val fx = min(side / width, 1.0)
            val fy = min(side / height, 1.0)
            return Region((1 - fx) / 2, (1 - fy) / 2, fx, fy)
        }
    }
}
