package edu.northwestern.lookagain.wildcatverify.data

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.os.PowerManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat

/**
 * Battery Saver and metered or Data Saver connections, so automatic Feed checks
 * can pause (the counterpart of iOS's Low Power Mode and expensive/constrained paths).
 */
class DeviceConditions(context: Context) {
    private val power = context.getSystemService(PowerManager::class.java)
    private val connectivity = context.getSystemService(ConnectivityManager::class.java)

    var isPowerSaving by mutableStateOf(power?.isPowerSaveMode == true)
        private set
    var isNetworkLimited by mutableStateOf(limited())
        private set

    /** Automatic background work should wait. */
    val shouldPause: Boolean get() = isPowerSaving || isNetworkLimited

    init {
        ContextCompat.registerReceiver(
            context.applicationContext,
            object : BroadcastReceiver() {
                override fun onReceive(context: Context?, intent: Intent?) {
                    isPowerSaving = power?.isPowerSaveMode == true
                }
            },
            IntentFilter(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        runCatching {
            connectivity?.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
                override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
                    isNetworkLimited = limited(capabilities)
                }

                override fun onLost(network: Network) {
                    isNetworkLimited = limited()
                }
            })
        }
    }

    private fun limited(
        capabilities: NetworkCapabilities? = runCatching { connectivity?.getNetworkCapabilities(connectivity.activeNetwork) }.getOrNull(),
    ): Boolean {
        val dataSaver = connectivity?.restrictBackgroundStatus == ConnectivityManager.RESTRICT_BACKGROUND_STATUS_ENABLED
        val metered = capabilities != null && !capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
        return dataSaver || metered
    }
}
