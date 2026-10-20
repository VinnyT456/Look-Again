package edu.northwestern.lookagain.wildcatverify.data

import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.edit
import kotlinx.serialization.json.Json

/** User preferences, saved in the app's own SharedPreferences. */
class SettingsStore(private val prefs: SharedPreferences) {
    private object Key {
        const val KEEP_HISTORY = "settings.keepHistory"
        const val HAPTICS = "settings.haptics"
        const val HEATMAP = "settings.heatmap"
        const val SHARE_TIP_DISMISSED = "settings.shareTipDismissed"
        const val AUTO_LABEL_PAUSED = "settings.autoLabelPaused"
        const val AUTO_CHECK_FEED = "feed.autoCheck"
        const val WELCOME_SEEN = "settings.welcomeSeen"
        const val BEST_PRACTICE_SCORE = "learn.bestScore"
        const val HIDDEN_ACCOUNTS = "feed.hiddenAccounts"
    }

    private var _keepHistory by mutableStateOf(prefs.getBoolean(Key.KEEP_HISTORY, false))
    private var _haptics by mutableStateOf(prefs.getBoolean(Key.HAPTICS, true))
    private var _heatmap by mutableStateOf(prefs.getBoolean(Key.HEATMAP, true))
    private var _shareTipDismissed by mutableStateOf(prefs.getBoolean(Key.SHARE_TIP_DISMISSED, false))
    private var _autoLabelPaused by mutableStateOf(prefs.getBoolean(Key.AUTO_LABEL_PAUSED, false))
    private var _autoCheckFeed by mutableStateOf(prefs.getBoolean(Key.AUTO_CHECK_FEED, true))
    private var _welcomeSeen by mutableStateOf(prefs.getBoolean(Key.WELCOME_SEEN, false))
    private var _bestPracticeScore by mutableStateOf(prefs.getInt(Key.BEST_PRACTICE_SCORE, 0))
    private var _hiddenAccounts by mutableStateOf(
        runCatching { Json.decodeFromString<Map<String, String>>(prefs.getString(Key.HIDDEN_ACCOUNTS, null) ?: "{}") }.getOrDefault(emptyMap()),
    )

    /** Save My Checks on this device between launches. Off by default. */
    var keepHistory: Boolean
        get() = _keepHistory
        set(value) { _keepHistory = value; prefs.edit { putBoolean(Key.KEEP_HISTORY, value) } }

    /** Light haptic taps on tab switches and practice answers. */
    var hapticsEnabled: Boolean
        get() = _haptics
        set(value) { _haptics = value; prefs.edit { putBoolean(Key.HAPTICS, value) } }

    /** Show the detector's heatmap under Highlight on Likely AI results. */
    var heatmapEnabled: Boolean
        get() = _heatmap
        set(value) { _heatmap = value; prefs.edit { putBoolean(Key.HEATMAP, value) } }

    /** The "Check posts without leaving Bluesky" tip on the Check page was closed. */
    var shareTipDismissed: Boolean
        get() = _shareTipDismissed
        set(value) { _shareTipDismissed = value; prefs.edit { putBoolean(Key.SHARE_TIP_DISMISSED, value) } }

    /** Auto-Label is on in system settings but the user paused the badges from the app. */
    var autoLabelPaused: Boolean
        get() = _autoLabelPaused
        set(value) { _autoLabelPaused = value; prefs.edit { putBoolean(Key.AUTO_LABEL_PAUSED, value) } }

    /**
     * Check Feed posts automatically as they scroll into view. On by default;
     * paused in Battery Saver and on metered or Data Saver connections.
     */
    var autoCheckFeed: Boolean
        get() = _autoCheckFeed
        set(value) { _autoCheckFeed = value; prefs.edit { putBoolean(Key.AUTO_CHECK_FEED, value) } }

    /** The first-run "fastest ways to check" screen was shown. */
    var welcomeSeen: Boolean
        get() = _welcomeSeen
        set(value) { _welcomeSeen = value; prefs.edit { putBoolean(Key.WELCOME_SEEN, value) } }

    /** Best Look Again score so far; 0 until a round is finished. */
    var bestPracticeScore: Int
        get() = _bestPracticeScore
        set(value) { _bestPracticeScore = value; prefs.edit { putInt(Key.BEST_PRACTICE_SCORE, value) } }

    /** Bluesky accounts hidden from the Feed, by DID, with the handle shown in Settings. Kept on this device only. */
    var hiddenAccounts: Map<String, String>
        get() = _hiddenAccounts
        set(value) { _hiddenAccounts = value; prefs.edit { putString(Key.HIDDEN_ACCOUNTS, Json.encodeToString(value)) } }

    /** Back to defaults; used by "Erase All Data". */
    fun reset() {
        keepHistory = false
        hapticsEnabled = true
        heatmapEnabled = true
        shareTipDismissed = false
        autoLabelPaused = false
        autoCheckFeed = true
        welcomeSeen = false
        bestPracticeScore = 0
        hiddenAccounts = emptyMap()
    }
}
