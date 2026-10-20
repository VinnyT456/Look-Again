package edu.northwestern.lookagain.wildcatverify

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import edu.northwestern.lookagain.wildcatverify.data.TfliteImageClassifier
import edu.northwestern.lookagain.wildcatverify.model.VerdictType
import kotlinx.coroutines.test.runTest
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Runs the bundled detector on the fixtures and compares with Python.
 * `TORCH_PROB` comes from the PyTorch probe (genai_plus_balance fine-tune) on the Hugging Face–preprocessed
 * fixtures (printed by ml/scripts/export/community_forensics_vit_heatmap_tflite.py);
 * `patch_map` in reference.json is from the iOS model, for a cross-platform check.
 */
@RunWith(AndroidJUnit4::class)
class DetectorModelTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    private val testAssets = InstrumentationRegistry.getInstrumentation().context.assets

    private fun fixture(name: String): Bitmap =
        testAssets.open("fixtures/$name.png").use { BitmapFactory.decodeStream(it) }

    private val reference by lazy {
        JSONObject(testAssets.open("fixtures/reference.json").bufferedReader().readText())
    }

    private val classifier by lazy { requireNotNull(TfliteImageClassifier.load(context)) { "Model must ship in the APK" } }

    @Test fun modelShipsWithHeatmap() {
        assertTrue(!classifier.isDemo)
        assertTrue("The bundled model must provide patch_map", classifier.hasHeatmap)
    }

    @Test fun matchesPythonProbability() = runTest {
        for ((name, expected) in TORCH_PROB) {
            val (probability, _) = classifier.predict(fixture(name))
            assertEquals("$name probability", expected, probability, 0.01)
            assertEquals(if (expected >= 0.5) VerdictType.AI else VerdictType.REAL, classifier.classify(fixture(name)).verdict)
        }
    }

    @Test fun heatmapMatchesIos() = runTest {
        for (name in TORCH_PROB.keys) {
            val (_, heatmap) = classifier.predict(fixture(name))
            assertNotNull(heatmap)
            val expected = reference.getJSONObject(name).getJSONArray("patch_map").let { array -> List(array.length()) { array.getDouble(it) } }
            val correlation = pearson(heatmap!!.values.map { it.toDouble() }, expected)
            assertTrue("$name heatmap correlation $correlation", correlation > 0.95)
        }
    }

    @Test fun sameImageSameAnswer() = runTest {
        val image = fixture("plasma")
        assertEquals(classifier.predict(image).first, classifier.predict(image).first, 1e-6)
    }

    private fun pearson(a: List<Double>, b: List<Double>): Double {
        val ma = a.average(); val mb = b.average()
        var cov = 0.0; var va = 0.0; var vb = 0.0
        for (i in a.indices) {
            cov += (a[i] - ma) * (b[i] - mb); va += (a[i] - ma) * (a[i] - ma); vb += (b[i] - mb) * (b[i] - mb)
        }
        return cov / sqrt(va * vb)
    }

    companion object {
        val TORCH_PROB = mapOf("gradient" to 0.90050, "plasma" to 0.76388, "soft_noise" to 0.99972)
    }
}
