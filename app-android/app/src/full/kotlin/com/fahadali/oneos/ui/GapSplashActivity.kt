package com.fahadali.oneos.ui

import android.annotation.SuppressLint
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.widget.TextView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.session.SessionPrefs

/**
 * The Figma handoff frame: OneOS icon and the target system name.
 * The optional root renderer takes over with live process events during teardown.
 * The switch script waits for this activity's first frame before freezing surfaceflinger.
 * All content is bound synchronously and the real handoff has no animation.
 * The debug preview only shows this UI for five seconds, then returns.
 */
// Not a launch screen: root starts it in the middle of a switch.
@SuppressLint("CustomSplashScreen")
class GapSplashActivity : EdgeToEdgeActivity() {
    private val main = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // A switch can find the screen off or on the keyguard.
        setShowWhenLocked(true)
        setTurnScreenOn(true)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.attributes = window.attributes.apply {
            layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
        }
        // Target SDK 36 draws edge to edge: the black reaches behind the bars and the cutout.

        // Everything is set here, before the first frame (surfaceflinger freezes on it).
        setContentView(R.layout.splash_gap)
        val preview = if (DebugPreview.enabled(this)) intent.getStringExtra(SetupProgressActivity.EXTRA_PREVIEW_IMAGE)?.let(Images::byId) else null
        val launch = SessionPrefs.lastLaunch(this)?.takeIf { SystemClock.elapsedRealtime() - it.elapsedMs in 0L..FRESH_MS && !it.rebootedSince() }
        val image = preview ?: launch?.let { Images.byId(it.imageId) } ?: SessionPrefs.homeSnapshot(this)?.image
        findViewById<TextView>(R.id.splash_wordmark).text = getString(R.string.splash_launching_into, Images.systemName(image))
        findViewById<TextView>(R.id.splash_starting).setText(if (launch?.dryRun == true && preview == null) R.string.splash_test_status else R.string.splash_shutdown)
        findViewById<android.view.View>(R.id.splash_preview).visibility = if (preview != null) android.view.View.VISIBLE else android.view.View.GONE
        if (!SessionPrefs.verboseBoot(this)) findViewById<TextView>(R.id.splash_starting).visibility = android.view.View.GONE
        // The debug path only displays this same UI and returns; no root or launch action.
        if (preview != null) main.postDelayed(::finish, 5_000L)

        window.insetsController?.let { c ->
            c.hide(WindowInsets.Type.systemBars())
            c.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
        if (preview == null) main.postDelayed(::finish, GIVE_UP_MS)
    }

    override fun onDestroy() {
        main.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    override fun finish() {
        super.finish()
        if (Build.VERSION.SDK_INT >= 34) {
            overrideActivityTransition(OVERRIDE_TRANSITION_CLOSE, 0, 0)
        } else {
            @Suppress("DEPRECATION")
            overridePendingTransition(0, 0)
        }
    }

    private companion object {
        // The IMS gate alone can wait 90 s before the freeze.
        const val GIVE_UP_MS = 180_000L

        // The launch is committed just before root runs, and root starts this
        // screen early in the switch (its gates included), well inside this.
        const val FRESH_MS = 10 * 60_000L

    }
}
