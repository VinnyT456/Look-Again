package edu.northwestern.lookagain.wildcatverify

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.SystemClock
import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import edu.northwestern.lookagain.wildcatverify.data.DetectorPreprocessor
import edu.northwestern.lookagain.wildcatverify.data.TfliteImageClassifier
import kotlinx.coroutines.runBlocking
import org.junit.Test
import org.junit.runner.RunWith

/** Prints how long each stage takes (`adb logcat -s DetectorBenchmark`). Not a pass/fail test. */
@RunWith(AndroidJUnit4::class)
class DetectorBenchmark {
    @Test fun timeStages() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val assets = InstrumentationRegistry.getInstrumentation().context.assets
        val small = assets.open("fixtures/plasma.png").use { BitmapFactory.decodeStream(it) }
        // A typical phone photo after the app's 2048 px downsample.
        val large = Bitmap.createScaledBitmap(small, 2048, 1536, true)

        var start = SystemClock.elapsedRealtime()
        val classifier = requireNotNull(TfliteImageClassifier.load(context))
        log("load", start)

        for (image in listOf(large, large, small)) {
            val pixels = IntArray(image.width * image.height)
            image.getPixels(pixels, 0, image.width, 0, 0, image.width, image.height)
            start = SystemClock.elapsedRealtime()
            DetectorPreprocessor.tensor(pixels, image.width, image.height)
            log("preprocess ${image.width}x${image.height}", start)
            start = SystemClock.elapsedRealtime()
            classifier.predict(image)
            log("predict total ${image.width}x${image.height}", start)
        }
    }

    private fun log(what: String, start: Long) {
        Log.i("DetectorBenchmark", "$what: ${SystemClock.elapsedRealtime() - start} ms")
    }
}
