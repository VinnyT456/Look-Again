package edu.northwestern.lookagain.wildcatverify

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.lifecycleScope
import edu.northwestern.lookagain.wildcatverify.ui.RootScreen
import edu.northwestern.lookagain.wildcatverify.ui.theme.WildcatTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val app = container.app
        container.browserSignIn.attach(this)
        setContent {
            WildcatTheme { RootScreen(app) }
        }
        if (savedInstanceState == null) handle(intent)
        // Once the first screen is drawn, get the detector ready while the user picks something to check.
        window.decorView.post {
            lifecycleScope.launch {
                delay(1_000)
                container.warmUpDetector()
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handle(intent)
    }

    override fun onResume() {
        super.onResume()
        container.browserSignIn.attach(this)
        // Back from the Bluesky sign-in tab without a redirect: the user closed it.
        container.browserSignIn.appResumed()
    }

    private fun handle(intent: Intent?) {
        // Bluesky's sign-in page sending the user back.
        if (container.browserSignIn.deliver(intent?.data)) return
        // A tapped Auto-Label badge: show that photo's result.
        val id = intent?.getStringExtra(EXTRA_OPEN_CASE) ?: return
        container.app.openCase(id)
    }

    companion object {
        const val EXTRA_OPEN_CASE = "edu.northwestern.lookagain.wildcatverify.OPEN_CASE"
    }
}
