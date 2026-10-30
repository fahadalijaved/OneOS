package com.fahadali.oneos.guest

import android.app.Activity
import android.app.AlertDialog
import android.app.StatusBarManager
import android.content.ComponentName
import android.content.Intent
import android.graphics.drawable.Icon
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.TextView
import java.io.IOException

/**
 * "You're in {system}" and one large "Back to One UI" button
 * (GuestReturn.dc.html), then the other ways back: the Quick Settings tile
 * and Volume Up + Volume Down. A tap (or the tile) asks first; on Return it
 * writes the request ([ReturnRequest]) and the session's watcher on the host
 * takes the phone back to One UI. 0.4.30: How's it going? opens the
 * checklist ([ChecklistActivity]) kept for Send to the OneOS team.
 */
class MainActivity : Activity() {

    private lateinit var back: Button
    private lateinit var status: TextView
    private lateinit var addTile: Button
    private var confirm: AlertDialog? = null
    private var confirmReason: String? = null
    private val handler = Handler(Looper.getMainLooper())
    private val noAnswer = Runnable { status.setText(R.string.status_no_answer) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        val system = GuestName.read()
        findViewById<TextView>(R.id.title).text =
            if (system != null) getString(R.string.title_in, system) else getString(R.string.title_in_other)
        // Edge to edge (target 35+): keep the content clear of the system bars and cutouts.
        findViewById<View>(R.id.root).setOnApplyWindowInsetsListener { v, insets ->
            val b = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            v.setPadding(b.left, b.top, b.right, b.bottom)
            insets
        }
        back = findViewById(R.id.back)
        status = findViewById(R.id.status)
        addTile = findViewById(R.id.add_tile)
        back.setOnClickListener { ask(ReturnRequest.REASON_APP) }
        findViewById<Button>(R.id.checklist).setOnClickListener { startActivity(Intent(this, ChecklistActivity::class.java)) }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            addTile.setOnClickListener { requestTile() }
        } else {
            addTile.visibility = View.GONE
        }
        showState()
        if (savedInstanceState != null) {
            // Rotated or folded while the question was open: ask again.
            savedInstanceState.getString(STATE_CONFIRM)?.let { ask(it) }
        } else {
            fromTile(intent)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        fromTile(intent)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        confirmReason?.let { outState.putString(STATE_CONFIRM, it) }
    }

    override fun onDestroy() {
        handler.removeCallbacks(noAnswer)
        confirm?.let {
            it.setOnDismissListener(null)
            it.dismiss()
        }
        confirm = null
        super.onDestroy()
    }

    private fun fromTile(i: Intent?) {
        if (i?.getStringExtra(EXTRA_REASON) == ReturnRequest.REASON_TILE) ask(ReturnRequest.REASON_TILE)
    }

    /** "Return to One UI now? Unsaved work in apps will be lost." Cancel from the tile closes the screen again. */
    private fun ask(reason: String) {
        if (ReturnRequest.pending(this)) {
            showState()
            return
        }
        confirm?.let {
            it.setOnDismissListener(null)
            it.dismiss()
        }
        var answered = false
        val dialog = AlertDialog.Builder(this)
            .setTitle(R.string.confirm_title)
            .setMessage(R.string.confirm_message)
            .setPositiveButton(R.string.confirm_return) { _, _ ->
                answered = true
                send(reason)
            }
            .setNegativeButton(android.R.string.cancel, null)
            .create()
        dialog.setOnDismissListener {
            confirm = null
            confirmReason = null
            // Cancel (button, back, outside): from the tile, back to where the user was.
            if (reason == ReturnRequest.REASON_TILE && !answered) finish()
        }
        confirm = dialog
        confirmReason = reason
        dialog.show()
    }

    private fun send(reason: String) {
        try {
            ReturnRequest.send(this, reason)
        } catch (e: IOException) {
            handler.removeCallbacks(noAnswer)
            back.isEnabled = true
            status.text = getString(R.string.status_failed, e.message ?: e.javaClass.simpleName)
            status.visibility = View.VISIBLE
            return
        }
        showState()
    }

    /** A request is pending until the watcher takes it (and the phone restarts into One UI). */
    private fun showState() {
        val pending = ReturnRequest.pending(this)
        back.isEnabled = !pending
        handler.removeCallbacks(noAnswer)
        if (pending) {
            status.setText(R.string.status_returning)
            status.visibility = View.VISIBLE
            handler.postDelayed(noAnswer, NO_ANSWER_MS)
        } else {
            status.visibility = View.GONE
        }
    }

    /** Android 13+: SystemUI asks the user to add the tile (onCreate hides the button before). */
    private fun requestTile() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        getSystemService(StatusBarManager::class.java).requestAddTileService(
            ComponentName(this, ReturnTileService::class.java),
            getString(R.string.tile_label),
            Icon.createWithResource(this, R.drawable.ic_tile),
            mainExecutor,
        ) { result ->
            if (result == StatusBarManager.TILE_ADD_REQUEST_RESULT_TILE_ADDED ||
                result == StatusBarManager.TILE_ADD_REQUEST_RESULT_TILE_ALREADY_ADDED
            ) {
                addTile.setText(R.string.tile_added)
                addTile.contentDescription = getString(R.string.tile_added_description)
                addTile.isEnabled = false
            }
        }
    }

    companion object {
        const val EXTRA_REASON = "com.fahadali.oneos.guest.REASON"
        private const val STATE_CONFIRM = "confirm"

        /** The watcher looks every second, but its diagnostics can hold it up for a while. */
        private const val NO_ANSWER_MS = 30_000L
    }
}
