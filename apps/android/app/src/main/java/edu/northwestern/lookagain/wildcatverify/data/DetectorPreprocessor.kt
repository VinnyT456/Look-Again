package edu.northwestern.lookagain.wildcatverify.data

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Turns an image into the tensor the detector expects. Mirrors the model's
 * Hugging Face image processor (what the probe was trained with): resize so the
 * short edge is 440 with PIL's antialiased bicubic filter, center-crop 384×384,
 * scale to 0–1, then normalize with CLIP mean/std.
 * Source: ml/checkpoints/tflite/community_forensics_vit_rich_probe.json.
 *
 * The resize is PIL's own algorithm (separable, horizontal pass first, 22-bit
 * fixed-point weights, 8-bit rounding between passes), and only the pixels that
 * survive the crop are computed. Works on packed ARGB pixels so it runs (and is
 * tested) on the plain JVM.
 */
object DetectorPreprocessor {
    const val SHORT_EDGE = 440
    const val CROP_SIZE = 384
    val MEAN = floatArrayOf(0.48145466f, 0.4578275f, 0.40821073f)
    val STD = floatArrayOf(0.26862954f, 0.26130258f, 0.27577711f)

    /** PIL's fixed-point precision for 8-bit images. */
    private const val PRECISION_BITS = 32 - 8 - 2

    /** Size after the short-edge resize, as Hugging Face computes it (long edge truncated). */
    fun resizedSize(width: Int, height: Int): Pair<Int, Int> =
        if (width <= height) {
            SHORT_EDGE to (SHORT_EDGE.toLong() * height / width).toInt()
        } else {
            (SHORT_EDGE.toLong() * width / height).toInt() to SHORT_EDGE
        }

    /**
     * Returns 1×3×384×384 float32 values in channel-first RGB order.
     * @param argb row-major pixels, `0xAARRGGBB`; alpha is ignored like PIL's `convert("RGB")`.
     */
    fun tensor(argb: IntArray, width: Int, height: Int): FloatArray {
        val rgb = croppedRgb(argb, width, height)
        val plane = CROP_SIZE * CROP_SIZE
        val out = FloatArray(3 * plane)
        // (v / 255 − mean) / std, as one multiply-add per value.
        val scale = FloatArray(3) { 1f / (255f * STD[it]) }
        val offset = FloatArray(3) { -MEAN[it] / STD[it] }
        for (i in 0 until plane) {
            val p = rgb[i]
            out[i] = ((p shr 16) and 0xFF) * scale[0] + offset[0]
            out[plane + i] = ((p shr 8) and 0xFF) * scale[1] + offset[1]
            out[2 * plane + i] = (p and 0xFF) * scale[2] + offset[2]
        }
        return out
    }

    /** Resized and center-cropped pixels, 384×384, packed `0x00RRGGBB`. */
    fun croppedRgb(argb: IntArray, width: Int, height: Int): IntArray {
        require(width > 0 && height > 0 && argb.size >= width * height) { "No pixels" }
        val (newWidth, newHeight) = resizedSize(width, height)
        // Hugging Face center_crop: offsets rounded down. Never negative, since 440 > 384.
        val left = (newWidth - CROP_SIZE) / 2
        val top = (newHeight - CROP_SIZE) / 2

        val columns = Coefficients(width, newWidth, left, CROP_SIZE)
        val rows = Coefficients(height, newHeight, top, CROP_SIZE)

        // Horizontal pass, only over the source rows the vertical pass will read.
        val firstRow = rows.start[0]
        val lastRow = rows.start[CROP_SIZE - 1] + rows.count[CROP_SIZE - 1]
        val bandHeight = lastRow - firstRow
        val band = IntArray(CROP_SIZE * bandHeight)
        if (newWidth == width) {
            for (y in 0 until bandHeight) System.arraycopy(argb, (firstRow + y) * width + left, band, y * CROP_SIZE, CROP_SIZE)
        } else {
            for (y in 0 until bandHeight) {
                val rowBase = (firstRow + y) * width
                for (x in 0 until CROP_SIZE) band[y * CROP_SIZE + x] = columns.apply(argb, rowBase, 1, x)
            }
        }

        // Vertical pass.
        val out = IntArray(CROP_SIZE * CROP_SIZE)
        if (newHeight == height) {
            for (y in 0 until CROP_SIZE) System.arraycopy(band, (top + y - firstRow) * CROP_SIZE, out, y * CROP_SIZE, CROP_SIZE)
        } else {
            for (y in 0 until CROP_SIZE) {
                for (x in 0 until CROP_SIZE) {
                    out[y * CROP_SIZE + x] = rows.apply(band, x - firstRow * CROP_SIZE, CROP_SIZE, y)
                }
            }
        }
        return out
    }

    /**
     * PIL's `precompute_coeffs` for the outputs `[first, first + count)` of a
     * resize from `inSize` to `outSize`, as fixed-point integers.
     */
    private class Coefficients(inSize: Int, outSize: Int, first: Int, count: Int) {
        val start = IntArray(count)
        val count = IntArray(count)
        private val taps: Int
        private val weights: IntArray

        init {
            val scale = inSize.toDouble() / outSize
            val filterScale = max(scale, 1.0)
            val support = 2.0 * filterScale
            taps = (support * 2 + 1).toInt() + 1
            weights = IntArray(count * taps)
            val k = DoubleArray(taps)
            for (i in 0 until count) {
                val center = (first + i + 0.5) * scale
                val xmin = max((center - support + 0.5).toInt(), 0)
                val n = min((center + support + 0.5).toInt(), inSize) - xmin
                var total = 0.0
                for (j in 0 until n) {
                    k[j] = cubic((j + xmin - center + 0.5) / filterScale)
                    total += k[j]
                }
                for (j in 0 until n) {
                    val w = if (total != 0.0) k[j] / total else 0.0
                    weights[i * taps + j] = if (w < 0) (-0.5 + w * (1 shl PRECISION_BITS)).toInt() else (0.5 + w * (1 shl PRECISION_BITS)).toInt()
                }
                start[i] = xmin
                this.count[i] = n
            }
        }

        /** One output pixel: taps read from `src[base + (start + k) * stride]`. */
        fun apply(src: IntArray, base: Int, stride: Int, i: Int): Int {
            var r = 1 shl (PRECISION_BITS - 1)
            var g = r
            var b = r
            var index = base + start[i] * stride
            val w = i * taps
            for (k in 0 until count[i]) {
                val p = src[index]
                val weight = weights[w + k]
                r += ((p shr 16) and 0xFF) * weight
                g += ((p shr 8) and 0xFF) * weight
                b += (p and 0xFF) * weight
                index += stride
            }
            return (clip8(r) shl 16) or (clip8(g) shl 8) or clip8(b)
        }

        private fun clip8(value: Int): Int {
            val v = value shr PRECISION_BITS
            return if (v < 0) 0 else if (v > 255) 255 else v
        }
    }

    /** PIL's bicubic kernel (a = -0.5). */
    private fun cubic(x: Double): Double {
        val a = -0.5
        val t = abs(x)
        return when {
            t < 1.0 -> ((a + 2.0) * t - (a + 3.0)) * t * t + 1
            t < 2.0 -> (((t - 5) * t + 8) * t - 4) * a
            else -> 0.0
        }
    }
}
