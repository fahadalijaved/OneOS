package com.fahadali.oneos.guest

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import dev.oneuiproject.oneui.utils.applyEdgeToEdge
import java.io.IOException

/** Commit the existing return request only after the Figma handoff frame is drawn. */
class ReturnSplashActivity : AppCompatActivity() {
    private val handler = Handler(Looper.getMainLooper())
    private var submitted = false
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applyEdgeToEdge()
        setShowWhenLocked(true)
        setTurnScreenOn(true)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContentView(R.layout.activity_return_splash)
        submitted = savedInstanceState?.getBoolean("submitted") == true || ReturnRequest.pending(this)
        if (submitted) scheduleNoAnswer()
        window.insetsController?.apply {
            hide(WindowInsets.Type.systemBars())
            systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
        val root = findViewById<View>(R.id.return_splash)
        root.viewTreeObserver.addOnPreDrawListener(object : android.view.ViewTreeObserver.OnPreDrawListener {
            override fun onPreDraw(): Boolean {
                root.viewTreeObserver.removeOnPreDrawListener(this)
                if (root.isHardwareAccelerated) root.viewTreeObserver.registerFrameCommitCallback { handler.post { submit() } }
                else root.post { submit() }
                return true
            }
        })
    }
    private fun submit() {
        if (submitted || isFinishing || isDestroyed) return
        try {
            val reason = if (intent.getStringExtra(MainActivity.EXTRA_REASON) == ReturnRequest.REASON_TILE) ReturnRequest.REASON_TILE else ReturnRequest.REASON_APP
            ReturnRequest.send(this, reason)
            submitted = true
            scheduleNoAnswer()
        } catch (e: IOException) {
            findViewById<TextView>(R.id.return_error).apply {
                text = getString(R.string.status_failed, e.message ?: e.javaClass.simpleName)
                visibility = View.VISIBLE
            }
        }
    }
    private fun scheduleNoAnswer() {
        handler.postDelayed({
            findViewById<TextView>(R.id.return_error).apply { setText(R.string.status_no_answer); visibility = View.VISIBLE }
        }, 30_000)
    }
    override fun onSaveInstanceState(outState: Bundle) { outState.putBoolean("submitted", submitted); super.onSaveInstanceState(outState) }
    override fun onDestroy() { handler.removeCallbacksAndMessages(null); super.onDestroy() }
}
