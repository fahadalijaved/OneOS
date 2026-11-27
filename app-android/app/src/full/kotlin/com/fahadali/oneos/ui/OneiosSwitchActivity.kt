package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.SystemClock
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.widget.Toolbar
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.core.root.OneiosSteps
import com.fahadali.oneos.session.OneiosJob

/**
 * Switching to iOS 27 (docs/oneios.md, "In the app"): the Android systems' boot screen
 * (activity_boot_progress) while [OneiosJob.switch] runs: this build's session scripts staged, then
 * root's `switch` with its preflight. It says what happens and, once more before One UI closes, how
 * to come back. Once root has started the switch One UI's framework stops and this app with it; a
 * refusal comes back here in plain words with its fix (nothing was changed, One UI keeps running).
 * There is no Cancel while it runs (the button says "Can't cancel now", as the boot screen does past
 * its point of no return): the switch is one root call, and its preflight refuses before any change.
 */
class OneiosSwitchActivity : EdgeToEdgeActivity() {
    private var unsubscribe: (() -> Unit)? = null
    private var shownResult = false
    private val ticker = android.os.Handler(android.os.Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            val s = OneiosJob.state
            if (isDestroyed || s.job != OneiosFlow.Job.SWITCH) return
            findViewById<TextView>(R.id.boot_status).text = switchStatusLine(s)
            ticker.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_boot_progress)
        findViewById<View>(R.id.boot_window).setOnApplyWindowInsetsListener { root, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            root.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        findViewById<OsArtworkView>(R.id.boot_artwork).bindArtwork(R.drawable.os_oneios)
        // The way back, said once more on the last screen before One UI closes.
        findViewById<TextView>(R.id.boot_back).setText(R.string.oneios_switching_back)
        findViewById<TextView>(R.id.boot_title).apply {
            setText(R.string.oneios_title)
            if (!resources.getBoolean(R.bool.home_two_pane)) visibility = View.GONE
        }
        findViewById<Toolbar>(R.id.boot_toolbar).apply {
            setNavigationIcon(dev.oneuiproject.oneui.R.drawable.ic_oui_back)
            setNavigationContentDescription(androidx.appcompat.R.string.abc_action_bar_up_description)
            if (!resources.getBoolean(R.bool.home_two_pane)) setTitle(R.string.oneios_title)
            setNavigationOnClickListener { leave() }
        }
        findViewById<Button>(R.id.boot_cancel).setOnClickListener { leave() }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() = leave()
        })
    }

    override fun onStart() {
        super.onStart()
        unsubscribe = OneiosJob.observe { s -> bind(s) }
    }

    override fun onStop() {
        ticker.removeCallbacks(tick)
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun switchStatusLine(s: OneiosJob.State): String {
        val base = s.message ?: getString(R.string.oneios_running_switch)
        val elapsed = s.since.takeIf { it > 0 }?.let { ((SystemClock.elapsedRealtime() - it) / 1000).toInt().coerceAtLeast(0) }
        return if (elapsed != null && elapsed > 0) "$base · ${OneiosSteps.elapsedWords(elapsed)}" else base
    }

    private fun bind(s: OneiosJob.State) {
        val switching = s.job == OneiosFlow.Job.SWITCH
        ticker.removeCallbacks(tick)
        if (switching) ticker.postDelayed(tick, 1000)
        findViewById<TextView>(R.id.boot_status).text = when {
            switching -> switchStatusLine(s)
            s.last == OneiosFlow.Job.SWITCH && s.failure == null -> getString(R.string.splash_shutdown)
            else -> s.message ?: getString(R.string.oneios_running_switch)
        }
        findViewById<Button>(R.id.boot_cancel).apply {
            // Root's switch is one call: once it runs, it cannot be taken back from here.
            isEnabled = !switching
            setText(if (switching) R.string.boot_cannot_cancel else R.string.setup_close)
        }
        if (s.busy || shownResult) return
        if (s.last != OneiosFlow.Job.SWITCH) {
            finish()
            return
        }
        val problem = s.flow.problem?.takeIf { s.failure != null }
        if (problem != null) {
            shownResult = true
            val b = AlertDialog.Builder(this).setTitle(problem.title)
                .setMessage(problem.line + "\n\n" + getString(R.string.oneios_switch_refused_tail))
                .setNegativeButton(R.string.setup_close) { _, _ -> finish() }
                .setOnCancelListener { finish() }
            // The fix runs on iOS 27's page (a session to end, the files to get again, a check to run).
            if (problem.fix != OneiosFix.NONE) b.setPositiveButton(problem.fixLabel) { _, _ ->
                startActivity(OneiosActivity.intent(this).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
                finish()
            }
            b.show()
        }
        // Started: One UI's framework stops in a moment and ends this app; nothing more to do here.
    }

    private fun leave() {
        if (OneiosJob.state.job == OneiosFlow.Job.SWITCH) {
            android.widget.Toast.makeText(this, R.string.boot_cannot_cancel_line, android.widget.Toast.LENGTH_LONG).show()
            return
        }
        finish()
    }

    companion object {
        fun intent(ctx: Context): Intent = Intent(ctx, OneiosSwitchActivity::class.java)
    }
}
