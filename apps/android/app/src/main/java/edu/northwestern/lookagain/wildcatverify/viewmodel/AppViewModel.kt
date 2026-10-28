package edu.northwestern.lookagain.wildcatverify.viewmodel

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import edu.northwestern.lookagain.wildcatverify.AppContainer
import edu.northwestern.lookagain.wildcatverify.BuildConfig
import edu.northwestern.lookagain.wildcatverify.data.HistoryStore
import edu.northwestern.lookagain.wildcatverify.data.SettingsStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Tab order puts Check in the middle of five. */
enum class AppTab(val title: String) {
    FEED("Feed"),
    LEARN("Learn"),
    CHECK("Check"),
    HISTORY("My Checks"),
    SETTINGS("Settings"),
}

/** Screens pushed inside the Settings tab. */
enum class SettingsRoute { SCREEN_LABELS, AUTO_LABEL, PRIVACY_POLICY, TERMS, CREDITS, HIDDEN_ACCOUNTS, WAYS_TO_CHECK }

/**
 * Root coordinator: owns tab selection, settings and the per-tab view models.
 * One per process (held by [AppContainer]), like the iOS app's `AppViewModel.live`.
 */
class AppViewModel(private val container: AppContainer) {
    /** Lives as long as the process; work is cancelled per screen where it matters. */
    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    private var _selectedTab by mutableStateOf(AppTab.CHECK)
    var selectedTab: AppTab
        get() = _selectedTab
        set(value) {
            _selectedTab = value
            if (value == AppTab.HISTORY) history.markSeen()
        }

    var isShowingAbout by mutableStateOf(false)
    /** First launch: the "fastest ways to check" screen. */
    var isShowingWelcome by mutableStateOf(!container.settings.welcomeSeen)
        private set
    var settingsPath by mutableStateOf<List<SettingsRoute>>(emptyList())

    val settings: SettingsStore = container.settings
    /** Why the Feed's automatic checks are paused right now (Battery Saver or Data Saver), or null. */
    val autoCheckPausedReason: String? get() = if (settings.autoCheckFeed) container.conditions.pauseReason else null
    val account = container.account
    private val persistence = container.persistence
    val history = HistoryStore(container.images, if (settings.keepHistory) persistence else null)
    val images = container.images
    val check = CheckViewModel(history, container.pipeline(), scope, container.clipboard)
    val feed = FeedViewModel(container.feedService, container.account, container.pipeline(), scope, container.settings).also { feed ->
        val pipeline = container.pipeline()
        val conditions = container.conditions
        feed.autoCheck = FeedAutoChecker(pipeline::classifyUrl, scope) {
            settings.autoCheckFeed && !conditions.shouldPause
        }
    }
    val learn = LearnViewModel(container.settings)
    val historyList = HistoryViewModel(history)

    /** Loads the detector if needed (off the main thread) and says whether it's the real one. */
    suspend fun isUsingRealModel(): Boolean = withContext(Dispatchers.Default) { !container.classifier.isDemo }

    /** A one-off check for a Feed post; the result goes to My Checks. */
    fun feedCheck(): ShareViewModel = ShareViewModel(container.pipeline(), onResult = history::record)

    /** "Check Another Image" from any results screen: unwinds every tab and lands on a fresh Check form. */
    fun startNewCheck() {
        feed.path = emptyList()
        learn.path = emptyList()
        historyList.path = emptyList()
        check.reset()
        selectedTab = AppTab.CHECK
    }

    /**
     * Opens a check from My Checks, e.g. one an Auto-Label badge just added.
     * Returns false when it's no longer there.
     */
    fun openCase(id: String): Boolean {
        // Arriving from a label skips the first-launch screen; it's in Settings.
        finishWelcome()
        val item = history.cases.firstOrNull { it.id == id } ?: run {
            selectedTab = AppTab.HISTORY
            return false
        }
        startNewCheck()
        historyList.path = listOf(item)
        selectedTab = AppTab.HISTORY
        return true
    }

    /** The Check page tip and Settings both lead here. */
    fun showLabelSetup() {
        settingsPath = listOf(if (BuildConfig.ACCESSIBILITY_AUTO_LABEL) SettingsRoute.AUTO_LABEL else SettingsRoute.SCREEN_LABELS)
        selectedTab = AppTab.SETTINGS
    }

    fun finishWelcome() {
        isShowingWelcome = false
        settings.welcomeSeen = true
    }

    fun showAbout() {
        isShowingAbout = true
    }

    /**
     * Sign in with Bluesky's own page in a browser tab, then open the Feed on
     * the user's timeline. `handle` is only for accounts hosted elsewhere.
     * Runs in the app's scope so leaving the screen doesn't cancel it.
     */
    fun signIn(handle: String? = null) {
        scope.launch {
            account.signIn(handle, container.browserSignIn::open)
            if (account.isSignedIn) feed.showFollowing()
        }
    }

    fun signOut() {
        account.signOut()
        feed.forgetFollowing()
    }

    /** Settings → Keep My Checks. */
    fun setKeepHistory(isOn: Boolean) {
        settings.keepHistory = isOn
        history.setPersistence(if (isOn) persistence else null)
    }

    /** Settings → Erase All Data: checks, saved photos and preferences. */
    fun eraseAllData() {
        history.clear()
        history.setPersistence(null)
        persistence.erase()
        settings.reset()
        signOut()
        historyList.path = emptyList()
    }
}
