package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.data.DetectorPreprocessor
import edu.northwestern.lookagain.wildcatverify.data.TfliteImageClassifier
import edu.northwestern.lookagain.wildcatverify.model.PatchHeatmap
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerialName
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import javax.imageio.ImageIO
import kotlin.math.abs

/** Expected values come from fixtures/reference.json, produced in Python with the model's own Hugging Face image processor. */
@Serializable
private data class Reference(
    @SerialName("fake_prob") val fakeProb: Double,
    @SerialName("tensor_mean") val tensorMean: Double,
    @SerialName("channel_means") val channelMeans: List<Double>,
    @SerialName("patch_map") val patchMap: List<Double>,
)

private object Fixtures {
    fun pixels(name: String): Triple<IntArray, Int, Int> {
        val stream = requireNotNull(javaClass.classLoader?.getResourceAsStream("fixtures/$name.png")) { "Missing $name.png" }
        val image = ImageIO.read(stream)
        return Triple(image.getRGB(0, 0, image.width, image.height, null, 0, image.width), image.width, image.height)
    }

    fun reference(name: String): Reference {
        val text = requireNotNull(javaClass.classLoader?.getResourceAsStream("fixtures/reference.json")).bufferedReader().readText()
        return Json { ignoreUnknownKeys = true }.decodeFromString<Map<String, Reference>>(text).getValue(name)
    }
}

class DetectorPreprocessorTest {
    @Test fun tensorHasTheModelsShape() {
        val tensor = DetectorPreprocessor.tensor(IntArray(800 * 500) { 0xFF336699.toInt() }, 800, 500)
        assertEquals(3 * 384 * 384, tensor.size)
    }

    @Test fun whitePixelsNormaliseWithClipMeanAndStd() {
        val tensor = DetectorPreprocessor.tensor(IntArray(500 * 500) { -1 }, 500, 500)
        val plane = 384 * 384
        for (channel in 0 until 3) {
            val expected = (1 - DetectorPreprocessor.MEAN[channel]) / DetectorPreprocessor.STD[channel]
            assertEquals("channel $channel", expected, tensor[channel * plane + 100 * 384 + 100], 1e-4f)
        }
    }

    @Test fun tinyImagesAreScaledUpNotRejected() {
        val tensor = DetectorPreprocessor.tensor(IntArray(12 * 9) { 0xFF808080.toInt() }, 12, 9)
        assertEquals(3 * 384 * 384, tensor.size)
    }

    @Test fun resizeMatchesHuggingFaceSizes() {
        assertEquals(440 to 660, DetectorPreprocessor.resizedSize(1000, 1500))
        assertEquals(586 to 440, DetectorPreprocessor.resizedSize(1333, 1000))
        assertEquals(440 to 440, DetectorPreprocessor.resizedSize(7, 7))
    }

    /** Same filter as PIL, so this agrees far more closely than the iOS app's Core Graphics resize (0.03). */
    @Test fun matchesPythonPreprocessing() {
        for (name in listOf("gradient", "plasma", "soft_noise")) {
            val reference = Fixtures.reference(name)
            val (pixels, width, height) = Fixtures.pixels(name)
            val tensor = DetectorPreprocessor.tensor(pixels, width, height)
            val plane = 384 * 384
            for (channel in 0 until 3) {
                var sum = 0.0
                for (i in 0 until plane) sum += tensor[channel * plane + i]
                val mean = sum / plane
                assertEquals("$name channel $channel", reference.channelMeans[channel], mean, 0.002)
            }
            assertEquals("$name tensor mean", reference.tensorMean, tensor.average(), 0.002)
        }
    }
}

class VerdictMappingTest {
    @Test fun highProbabilityIsAI() {
        val result = TfliteImageClassifier.result(0.93)
        assertEquals(VerdictType.AI, result.verdict)
        assertEquals(0.93, result.confidence, 1e-9)
        assertNull("The model doesn't localize, so no highlight is invented", result.hotspot)
    }

    @Test fun lowProbabilityIsReal() {
        val result = TfliteImageClassifier.result(0.2)
        assertEquals(VerdictType.REAL, result.verdict)
        assertEquals(0.8, result.confidence, 1e-9)
    }

    @Test fun thresholdBelongsToAI() {
        assertEquals(VerdictType.AI, TfliteImageClassifier.result(0.5).verdict)
        assertEquals(VerdictType.REAL, TfliteImageClassifier.result(0.4999).verdict)
    }

    @Test fun outOfRangeOutputIsClamped() {
        assertEquals(1.0, TfliteImageClassifier.result(1.7).confidence, 0.0)
        assertEquals(1.0, TfliteImageClassifier.result(-0.3).confidence, 0.0)
    }

    @Test fun modelNeverSaysEdited() {
        for (step in 0..20) assertNotEquals(VerdictType.TAMPERED, TfliteImageClassifier.result(step / 20.0).verdict)
    }
}

class PatchHeatmapTest {
    @Test fun rejectsWrongSize() {
        assertNull(PatchHeatmap.fromValues(FloatArray(10)))
    }

    @Test fun intensitiesKeepOnlyPositiveInfluence() {
        val values = FloatArray(576) { -1f }.also { it[0] = 2f; it[1] = 1f }
        val heatmap = PatchHeatmap.fromValues(values)!!
        assertTrue(heatmap.hasSignal)
        assertEquals(1.0, heatmap.intensities[0], 1e-9)
        assertEquals(0.5, heatmap.intensities[1], 1e-9)
        assertEquals(0.0, heatmap.intensities[2], 1e-9)
    }

    @Test fun allNegativeHasNoSignal() {
        assertFalse(PatchHeatmap.fromValues(FloatArray(576) { -0.1f })!!.hasSignal)
    }

    @Test fun coveredRegionIsTheCenterCrop() {
        val square = PatchHeatmap.coveredRegion(1000, 1000)
        assertEquals(384.0 / 440, square.width, 1e-9)
        assertEquals((1 - 384.0 / 440) / 2, square.x, 1e-9)
        val wide = PatchHeatmap.coveredRegion(2000, 1000)
        assertEquals(384.0 / 440, wide.height, 1e-9)
        assertTrue(abs(wide.width - 384.0 / 440 / 2) < 1e-9)
    }
}
