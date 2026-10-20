package edu.northwestern.lookagain.wildcatverify

import android.app.Application
import android.content.Context
import edu.northwestern.lookagain.wildcatverify.data.BlueskyAccount
import edu.northwestern.lookagain.wildcatverify.data.BlueskyFeedService
import edu.northwestern.lookagain.wildcatverify.data.SessionVault
import edu.northwestern.lookagain.wildcatverify.data.BlueskyService
import edu.northwestern.lookagain.wildcatverify.data.CheckPipeline
import edu.northwestern.lookagain.wildcatverify.data.ClipboardProbe
import edu.northwestern.lookagain.wildcatverify.data.DemoImageClassifier
import edu.northwestern.lookagain.wildcatverify.data.DeviceConditions
import edu.northwestern.lookagain.wildcatverify.data.HistoryPersistence
import edu.northwestern.lookagain.wildcatverify.data.ImageClassifier
import edu.northwestern.lookagain.wildcatverify.data.ImageRepository
import edu.northwestern.lookagain.wildcatverify.data.SettingsStore
import edu.northwestern.lookagain.wildcatverify.data.TfliteImageClassifier
import edu.northwestern.lookagain.wildcatverify.viewmodel.AppViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Process-wide objects. The detector is loaded once (it's ~84 MB) and lazily,
 * so launching the app doesn't wait for it. If it can't be loaded the labelled
 * demo classifier is used, so results are never silently fake.
 */
class AppContainer(context: Context) {
    val images = ImageRepository()
    val bluesky = BlueskyService()
    val feedService = BlueskyFeedService()
    val classifier: ImageClassifier by lazy { TfliteImageClassifier.load(context) ?: DemoImageClassifier() }
    val settings = SettingsStore(context.getSharedPreferences("settings", Context.MODE_PRIVATE))
    val persistence = HistoryPersistence(File(context.noBackupFilesDir, "History"))
    val conditions = DeviceConditions(context)
    val clipboard = ClipboardProbe.system(context)
    val account = BlueskyAccount(SessionVault(context.getSharedPreferences("account", Context.MODE_PRIVATE)))

    fun pipeline() = CheckPipeline(bluesky, { classifier }, images)

    /** Loads the detector and runs it once in the background, so the first real check isn't the slow one. */
    suspend fun warmUpDetector() = withContext(Dispatchers.Default) {
        (classifier as? TfliteImageClassifier)?.warmUp()
    }

    /** The app's single coordinator, shared by the activity and its intents. */
    val app: AppViewModel by lazy { AppViewModel(this) }
}

class WildcatVerifyApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}

val Context.container: AppContainer get() = (applicationContext as WildcatVerifyApp).container
