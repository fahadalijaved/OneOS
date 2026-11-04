package com.fahadali.oneos.guest

import dev.oneuiproject.oneui.utils.applyEdgeToEdge

import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AlertDialog
import android.app.StatusBarManager
import android.content.ComponentName
import android.content.Intent
import android.content.pm.ShortcutInfo
import android.content.pm.ShortcutManager
import android.graphics.drawable.Icon
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.TextView

/** Native guest landing page; all return entry points confirm before the handoff frame. */
class MainActivity : AppCompatActivity() {

    private lateinit var back: Button
    private lateinit var status: TextView
    private lateinit var addTile: dev.oneuiproject.oneui.widget.CardItemView
    private var confirm: AlertDialog? = null
    private var confirmReason: String? = null
    private val handler = Handler(Looper.getMainLooper())
    private val noAnswer = Runnable { status.setText(R.string.status_no_answer) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applyEdgeToEdge()
        setContentView(R.layout.activity_main)
        ensureReturnShortcut()
        for (id in listOf(R.id.add_tile, R.id.checklist)) {
            findViewById<dev.oneuiproject.oneui.widget.CardItemView>(id).showTopDivider = false
        }
        for (id in listOf(R.id.tile_card, R.id.report_card)) {
            findViewById<dev.oneuiproject.oneui.widget.RoundedLinearLayout>(id).apply {
                roundedCorners = androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_ALL
                val color = android.util.TypedValue()
                theme.resolveAttribute(androidx.appcompat.R.attr.roundedCornerColor, color, true)
                roundedCornersColor = color.data
            }
        }
        val system = GuestName.read()
        findViewById<GuestArtworkView>(R.id.guest_artwork).bind(system)
        // Where you are, in words (0.4.43, UX audit: the bare system name over artwork that repeats it).
        findViewById<TextView>(R.id.title).text = system?.let { getString(R.string.title_in, it) } ?: getString(R.string.title_in_other)
        val root = findViewById<View>(R.id.root)
        val footer = findViewById<View>(R.id.guest_footer)
        val scroll = findViewById<androidx.core.widget.NestedScrollView>(R.id.guest_scroll)
        val wide = root is android.widget.LinearLayout
        val left = root.paddingLeft; val top = root.paddingTop; val right = root.paddingRight; val bottom = root.paddingBottom
        root.setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            v.setPadding(left + bars.left, top + bars.top, right + bars.right, bottom + if (wide) bars.bottom else 0)
            if (!wide) {
                (footer.layoutParams as android.view.ViewGroup.MarginLayoutParams).apply { bottomMargin = bars.bottom; footer.layoutParams = this }
            }
            insets
        }
        scroll.seslSetFadingEdgeColor(getColor(R.color.guest_page_background))
        scroll.seslSetFadingEdgeWindowBottomAlignment(!wide)
        val fadeGap = (24 * resources.displayMetrics.density).toInt()
        val noFade = GuestName.read()?.contains("Infinity", ignoreCase = true) == true
        footer.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
            val nav = if (wide) 0 else (footer.layoutParams as android.view.ViewGroup.MarginLayoutParams).bottomMargin
            val clearance = if (wide) fadeGap else footer.height + nav + fadeGap
            if (scroll.paddingBottom != clearance) scroll.setPadding(0, 0, 0, clearance)
            // Not on Infinity-X (0.4.43): its own libhwui crashed on this screen's first frame
            // (SkCanvas::internalQuickReject, RenderThread, 37 times in report 71a26ead), so Back to
            // One UI could not be reached from the app there. The fade is cosmetic.
            if (!noFade) {
                scroll.seslSetFadingEdgeEnabled(true, fadeGap, clearance)
                if (!wide) scroll.seslForceBottomFadingEdgeClamped(clearance)
            }
        }
        back = findViewById(R.id.back)
        status = findViewById(R.id.status)
        addTile = findViewById(R.id.add_tile)
        findViewById<dev.oneuiproject.oneui.widget.CardItemView>(R.id.checklist).getEndImageView()?.apply {
            setImageResource(dev.oneuiproject.oneui.R.drawable.ic_oui_arrow_right)
            visibility = View.VISIBLE
        }
        back.setOnClickListener { ask(ReturnRequest.REASON_APP) }
        findViewById<dev.oneuiproject.oneui.widget.CardItemView>(R.id.checklist).apply {
            summary = getString(R.string.checklist_card_summary)
            setOnClickListener { startActivity(Intent(this@MainActivity, ChecklistActivity::class.java)) }
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            addTile.setOnClickListener { requestTile() }
        } else {
            // Only the tile row: the volume keys work on every Android (0.4.43).
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

    override fun onResume() { super.onResume(); if (::back.isInitialized) showState() }

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
        val reason = i?.getStringExtra(EXTRA_REASON) ?: return
        if (reason == ReturnRequest.REASON_TILE || reason == REASON_SHORTCUT) ask(reason)
    }

    /** Existing staged system apps can retain an older manifest-shortcut cache. */
    private fun ensureReturnShortcut() {
        val shortcuts = getSystemService(ShortcutManager::class.java) ?: return
        runCatching {
            if (shortcuts.manifestShortcuts.any { it.id == "return_to_oneui" }) return
            shortcuts.addDynamicShortcuts(listOf(
                ShortcutInfo.Builder(this, "return_to_oneui")
                    .setShortLabel(getString(R.string.return_shortcut))
                    .setLongLabel(getString(R.string.return_shortcut))
                    .setIcon(Icon.createWithResource(this, R.drawable.ic_tile))
                    .setActivity(ComponentName(this, MainActivity::class.java))
                    .setIntent(Intent(this, MainActivity::class.java)
                        .setAction(Intent.ACTION_VIEW).putExtra(EXTRA_REASON, REASON_SHORTCUT))
                    .build()
            ))
        }.onFailure { android.util.Log.w("OneOSGuest", "Could not refresh return shortcut", it) }
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
            if (reason in setOf(ReturnRequest.REASON_TILE, REASON_SHORTCUT) && !answered) finish()
        }
        confirm = dialog
        confirmReason = reason
        dialog.show()
    }

    private fun send(reason: String) {
        startActivity(Intent(this, ReturnSplashActivity::class.java).putExtra(EXTRA_REASON, reason))
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
                addTile.title = getString(R.string.tile_added)
                addTile.contentDescription = getString(R.string.tile_added_description)
                addTile.isEnabled = false
            }
        }
    }

    companion object {
        private const val REASON_SHORTCUT = "shortcut"
        const val EXTRA_REASON = "com.fahadali.oneos.guest.REASON"
        private const val STATE_CONFIRM = "confirm"

        /** The watcher looks every second, but its diagnostics can hold it up for a while. */
        private const val NO_ANSWER_MS = 30_000L
    }
}
