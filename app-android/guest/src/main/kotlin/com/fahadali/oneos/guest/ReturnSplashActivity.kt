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
    private val restarting get()=intent.getBooleanExtra(GuestRestart.EXTRA_RESTART,false)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applyEdgeToEdge()
        setShowWhenLocked(true)
        setTurnScreenOn(true)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        setContentView(R.layout.activity_return_splash)
        if(restarting)findViewById<TextView>(R.id.transition_title).text=getString(R.string.restart_splash_title,GuestName.read() ?: "guest")
        submitted = savedInstanceState?.getBoolean("submitted") == true || if(restarting)GuestRestart.pending(this) else ReturnRequest.pending(this)
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
            if(restarting)GuestRestart.send(this) else ReturnRequest.send(this, reason)
            submitted = true
            scheduleNoAnswer()
        } catch (e: IOException) {
            findViewById<TextView>(R.id.return_error).apply {
                text = getString(if(restarting)R.string.restart_request_failed else R.string.status_failed, e.message ?: e.javaClass.simpleName)
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
