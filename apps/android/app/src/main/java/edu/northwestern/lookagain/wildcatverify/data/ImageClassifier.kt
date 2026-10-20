package edu.northwestern.lookagain.wildcatverify.data

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import edu.northwestern.lookagain.wildcatverify.model.ClassificationResult
import edu.northwestern.lookagain.wildcatverify.model.HotspotArea
import edu.northwestern.lookagain.wildcatverify.model.PatchHeatmap
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.security.MessageDigest

/** Abstraction over the on-device classifier, so the model can be swapped without touching view models. */
interface ImageClassifier {
    /** True for stand-in classifiers whose output must be labelled as a demo. */
    val isDemo: Boolean get() = false
    suspend fun classify(image: Bitmap): ClassificationResult
}

/**
 * The on-device detector: CommunityForensics ViT with a linear probe, exported
 * from `ml/` to TFLite (LiteRT). It outputs the probability the image is fake
 * (AI-generated), so it answers Real or AI but not Edited, plus — in the heatmap
 * export — a 24×24 `patch_map` of which areas pushed it toward "AI".
 */
class TfliteImageClassifier(private val interpreter: Interpreter) : ImageClassifier {
    // An Interpreter must not run two inferences at once.
    private val lock = Mutex()

    private val probabilityOutput: Int
    private val heatmapOutput: Int?

    init {
        // Tell the outputs apart by size: the exporter doesn't keep names.
        var probability = -1
        var heatmap: Int? = null
        for (i in 0 until interpreter.outputTensorCount) {
            when (interpreter.getOutputTensor(i).numElements()) {
                1 -> probability = i
                PatchHeatmap.GRID_SIZE * PatchHeatmap.GRID_SIZE -> heatmap = i
            }
        }
        require(probability >= 0) { "Model has no fake_prob output" }
        probabilityOutput = probability
        heatmapOutput = heatmap
    }

    val hasHeatmap: Boolean get() = heatmapOutput != null

    /**
     * Runs one throwaway inference. The first run packs the weights for
     * XNNPACK and gets the preprocessing compiled, which otherwise lands on the
     * user's first check as several extra seconds.
     */
    suspend fun warmUp() {
        predict(Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888))
    }

    override suspend fun classify(image: Bitmap): ClassificationResult {
        val (probability, heatmap) = predict(image)
        return result(probability, heatmap)
    }

    /** Both outputs. `heatmap` is null for the older export without `patch_map`. */
    suspend fun predict(image: Bitmap): Pair<Double, PatchHeatmap?> = withContext(Dispatchers.Default) {
        val pixels = IntArray(image.width * image.height)
        image.getPixels(pixels, 0, image.width, 0, 0, image.width, image.height)
        val tensor = DetectorPreprocessor.tensor(pixels, image.width, image.height)

        val input = ByteBuffer.allocateDirect(tensor.size * 4).order(ByteOrder.nativeOrder())
        input.asFloatBuffer().put(tensor)
        val outputs = HashMap<Int, Any>()
        val probability = ByteBuffer.allocateDirect(4).order(ByteOrder.nativeOrder())
        outputs[probabilityOutput] = probability
        val heatmapBuffer = heatmapOutput?.let {
            ByteBuffer.allocateDirect(PatchHeatmap.GRID_SIZE * PatchHeatmap.GRID_SIZE * 4).order(ByteOrder.nativeOrder())
                .also { buffer -> outputs[it] = buffer }
        }
        lock.withLock { interpreter.runForMultipleInputsOutputs(arrayOf(input), outputs) }

        probability.rewind()
        val heatmap = heatmapBuffer?.let {
            it.rewind()
            val values = FloatArray(PatchHeatmap.GRID_SIZE * PatchHeatmap.GRID_SIZE)
            it.asFloatBuffer().get(values)
            PatchHeatmap.fromValues(values)
        }
        probability.float.toDouble() to heatmap
    }

    companion object {
        /** Above this, the image is called AI-generated. */
        const val THRESHOLD = 0.5
        const val ASSET_NAME = "wildcat_detector.tflite"

        /** Memory-maps the model from the APK (it's stored uncompressed). */
        fun load(context: Context): TfliteImageClassifier? = try {
            val buffer = context.assets.openFd(ASSET_NAME).use { fd ->
                FileInputStream(fd.fileDescriptor).channel.use { channel ->
                    channel.map(FileChannel.MapMode.READ_ONLY, fd.startOffset, fd.declaredLength) as MappedByteBuffer
                }
            }
            val options = Interpreter.Options()
                .setNumThreads(threadCount())
                .setUseXNNPACK(true)
            TfliteImageClassifier(Interpreter(buffer, options))
        } catch (e: Exception) {
            Log.w("WildcatVerify", "Couldn't load the detector; using the demo classifier", e)
            null
        }

        /**
         * Leaves two cores free so the phone's own UI keeps up while photos are
         * labelled in the background, and stops at 4: past that, phones'
         * efficiency cores slow the matrix multiplies down rather than up.
         */
        private fun threadCount(): Int = (Runtime.getRuntime().availableProcessors() - 2).coerceIn(1, 4)

        /**
         * Maps the probability onto the app's verdicts. No hotspot box: the model
         * gives a soft per-patch map instead, and the app never invents a box.
         */
        fun result(fakeProbability: Double, heatmap: PatchHeatmap? = null): ClassificationResult {
            val probability = fakeProbability.coerceIn(0.0, 1.0)
            val isFake = probability >= THRESHOLD
            return ClassificationResult(
                verdict = if (isFake) VerdictType.AI else VerdictType.REAL,
                confidence = if (isFake) probability else 1 - probability,
                hotspot = null,
                heatmap = heatmap,
            )
        }
    }
}

/**
 * Fallback if the model can't be loaded. Deterministic per image (hash of its
 * pixels) so re-checking the same photo gives the same answer. Every result it
 * produces is labelled as a demo.
 */
class DemoImageClassifier : ImageClassifier {
    override val isDemo: Boolean get() = true

    override suspend fun classify(image: Bitmap): ClassificationResult {
        delay(1200)
        val digest = withContext(Dispatchers.Default) {
            val small = Bitmap.createScaledBitmap(image, 32, 32, true)
            val pixels = IntArray(32 * 32)
            small.getPixels(pixels, 0, 32, 0, 0, 32, 32)
            val bytes = ByteBuffer.allocate(pixels.size * 4).apply { asIntBuffer().put(pixels) }.array()
            MessageDigest.getInstance("SHA-256").digest(bytes)
        }
        val verdict = VerdictType.entries[(digest[0].toInt() and 0xFF) % VerdictType.entries.size]
        val confidence = 0.80 + ((digest[1].toInt() and 0xFF) % 19) / 100.0
        val hotspot = when (verdict) {
            VerdictType.REAL -> null
            VerdictType.TAMPERED -> HotspotArea(0.28, 0.30, 0.44, 0.32, "Possible edit")
            VerdictType.AI -> HotspotArea(0.20, 0.22, 0.60, 0.50, "Synthetic texture")
        }
        return ClassificationResult(verdict, confidence, hotspot)
    }
}
