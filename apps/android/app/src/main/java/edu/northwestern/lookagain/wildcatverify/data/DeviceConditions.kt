package edu.northwestern.lookagain.wildcatverify.data

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.os.PowerManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat

/**
 * Battery Saver and Data Saver, the two settings where the user has asked the
 * phone to do less in the background, so automatic Feed checks can pause (the
 * counterpart of iOS's Low Power Mode and Low Data Mode). Plain mobile data
 * doesn't pause them: a thumbnail is about 20 KB.
 */
class DeviceConditions(context: Context) {
    private val power = context.getSystemService(PowerManager::class.java)
    private val connectivity = context.getSystemService(ConnectivityManager::class.java)

    var isPowerSaving by mutableStateOf(power?.isPowerSaveMode == true)
        private set
    var isDataSaving by mutableStateOf(dataSaverOn())
        private set

    /** Why automatic work should wait, in words for the Feed, or null when it can run. */
    val pauseReason: String?
        get() = when {
            isPowerSaving -> "Battery Saver is on"
            isDataSaving -> "Data Saver is on"
            else -> null
        }

    val shouldPause: Boolean get() = pauseReason != null

    init {
        fun listen(action: String, update: () -> Unit) = ContextCompat.registerReceiver(
            context.applicationContext,
            object : BroadcastReceiver() {
                override fun onReceive(context: Context?, intent: Intent?) = update()
            },
            IntentFilter(action),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        listen(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED) { isPowerSaving = power?.isPowerSaveMode == true }
        listen(ConnectivityManager.ACTION_RESTRICT_BACKGROUND_CHANGED) { isDataSaving = dataSaverOn() }
    }

    private fun dataSaverOn(): Boolean =
        runCatching { connectivity?.restrictBackgroundStatus == ConnectivityManager.RESTRICT_BACKGROUND_STATUS_ENABLED }.getOrDefault(false)
}
