package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.text.style.BackgroundColorSpan
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosConf
import com.fahadali.oneos.session.OneiosConfJob
import com.fahadali.oneos.session.OneiosJob
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * Edit file (docs/oneios.md, "UI (2026-11-25)"): the staged image's overlay/userland/xnuhost.conf as text, in a
 * monospace editor. Save is root's `conf write` (the staged oneios-tool checks it first: its errors are shown at
 * their lines, and the lines are marked in the text); Save anyway (`write-force`) asks first; Check is `conf check`
 * without saving; Restore previous is `conf restore`. With a runtime older than `conf` Save writes the text as it is
 * (root's plain write, no checks), and Restore previous takes the file before the last save back.
 */
class OneiosConfEditActivity : EdgeToEdgeActivity() {
    private lateinit var toolbar: ToolbarLayout
    private lateinit var editor: EditText
    private var unsubscribe: (() -> Unit)? = null

    /** The text as root last gave it; the editor's differs from it when the user changed something. */
    private var base: String? = null
    private var dirty = false
    private var savesAtOpen = 0
    private var quiet = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_oneios_conf_edit)
        toolbar = findViewById(R.id.oneios_toolbar)
        OneiosScreens.setUp(this, toolbar, getString(R.string.oneios_switches_edit))
        applyEdgeToEdgeInsets(toolbar)
        toolbar.expandedSubtitle = OneiosConf.FILE
        editor = findViewById(R.id.oneios_conf_text)
        savesAtOpen = savedInstanceState?.getInt(KEY_SAVES) ?: OneiosConfJob.state.saves
        base = savedInstanceState?.getString(KEY_BASE)
        dirty = savedInstanceState?.getBoolean(KEY_DIRTY) == true
        savedInstanceState?.getString(KEY_TEXT)?.let { quietly { editor.setText(it) } }
        editor.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
            override fun afterTextChanged(s: Editable?) {
                if (quiet) return
                dirty = s?.toString() != base
                render()
            }
        })
        findViewById<Button>(R.id.oneios_primary).setOnClickListener { save(force = false) }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (!dirty) return finish()
                AlertDialog.Builder(this@OneiosConfEditActivity).setTitle(R.string.oneios_conf_discard)
                    .setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(R.string.oneios_conf_discard_run) { _, _ -> finish() }.show()
            }
        })
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putString(KEY_TEXT, editor.text?.toString())
        outState.putString(KEY_BASE, base)
        outState.putBoolean(KEY_DIRTY, dirty)
        outState.putInt(KEY_SAVES, savesAtOpen)
    }

    override fun onStart() {
        super.onStart()
        unsubscribe = OneiosConfJob.observeBy({ listOf(it.busy, it.show, it.answer, it.problem, it.saves, it.lastOp, it.tool) }) { taken(it) }
        if (base == null && !OneiosConfJob.state.busy) OneiosConfJob.load(this)
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun quietly(body: () -> Unit) {
        quiet = true
        try { body() } finally { quiet = false }
    }

    /** Root answered: a saved or restored file replaces the editor's text; an unsaved edit is kept. */
    private fun taken(c: OneiosConfJob.State) {
        val text = c.show?.text
        if (text != null && !c.busy && (!dirty || (c.lastOk && c.lastOp in WRITES))) {
            if (editor.text?.toString() != text) quietly { editor.setText(text) }
            base = text
            dirty = false
        }
        render()
    }

    private fun save(force: Boolean) {
        val text = editor.text?.toString().orEmpty()
        if (force) {
            AlertDialog.Builder(this).setTitle(R.string.oneios_conf_save_anyway).setMessage(R.string.oneios_conf_save_anyway_confirm)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.oneios_conf_save_anyway) { _, _ -> OneiosConfJob.write(this, text, force = true) }.show()
        } else OneiosConfJob.write(this, text, force = false)
    }

    private fun render() {
        if (isDestroyed) return
        val c = OneiosConfJob.state
        val session = OneiosJob.state.status?.sessionOpen == true
        val column = findViewById<LinearLayout>(R.id.oneios_column)
        column.removeAllViews()
        val card = PrebootCards.section(column, gap = false)
        when {
            c.loading && base == null -> PrebootCards.row(card, getString(R.string.oneios_switches_loading))
            c.writing -> PrebootCards.row(card, getString(R.string.oneios_switches_saving))
            session -> PrebootCards.row(card, getString(R.string.oneios_page_sub_open), getString(R.string.oneios_switches_session))
        }
        // The tool's errors at their lines (a refused Save or a Check), else the file's own as conf show read them.
        val errors = c.answer?.errors?.takeIf { it.isNotEmpty() } ?: c.show?.errors.orEmpty()
        c.answer?.error?.let { PrebootCards.row(card, getString(R.string.oneios_conf_errors), it) }
        if (c.problem != null && c.answer?.error == null) PrebootCards.row(card, getString(R.string.oneios_tool_not_started), c.problem)
        // Errors make xnuhost refuse the whole file (the next switch does not start iOS); warnings stop nothing.
        if (errors.isNotEmpty() && c.answer?.error == null) PrebootCards.row(card, getString(R.string.oneios_switches_problems), getString(R.string.oneios_switches_problems_line))
        val warnings = c.answer?.warnings?.takeIf { it.isNotEmpty() } ?: c.show?.warnings.orEmpty()
        for (e in errors + warnings) {
            val line = e.line
            val title = line?.let { getString(R.string.oneios_conf_line, it, e.message) } ?: e.message
            PrebootCards.row(card, title, if (e in warnings && e !in errors) getString(R.string.oneios_conf_warnings) else null, chevron = line != null) { if (line != null) goTo(line) }
        }
        if (!c.busy && c.lastOp == "check" && c.answer?.ok == true && errors.isEmpty()) PrebootCards.row(card, getString(R.string.oneios_conf_ok))
        if (!c.busy && c.saves > savesAtOpen && c.lastOk && c.lastOp in WRITES && !dirty) PrebootCards.row(card, getString(R.string.oneios_conf_saved))
        if (c.loaded && !c.tool) PrebootCards.row(card, getString(R.string.oneios_conf_plain))
        if (card.childCount <= 1) column.removeView(card)
        mark(errors)
        editor.isEnabled = !c.writing && base != null
        findViewById<Button>(R.id.oneios_primary).isEnabled = dirty && OneiosConfJob.canWrite() && !session
        findViewById<View>(R.id.oneios_primary_spinner).visibility = if (c.writing) View.VISIBLE else View.GONE
        invalidateOptionsMenu()
    }

    /** The lines with errors marked in the text (the marks go when the text is read again). */
    private fun mark(errors: List<OneiosConf.LineError>) {
        val e = editor.text ?: return
        for (span in e.getSpans(0, e.length, BackgroundColorSpan::class.java)) e.removeSpan(span)
        val text = e.toString()
        val color = (getColor(R.color.oneios_check_fail) and 0x00FFFFFF) or 0x33000000
        for (line in errors.mapNotNull { it.line }.distinct()) {
            val (from, to) = lineRange(text, line) ?: continue
            if (to > from) e.setSpan(BackgroundColorSpan(color), from, to, android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }

    private fun lineRange(text: String, line: Int): Pair<Int, Int>? {
        if (line < 1) return null
        var start = 0
        repeat(line - 1) {
            val nl = text.indexOf('\n', start)
            if (nl < 0) return null
            start = nl + 1
        }
        val end = text.indexOf('\n', start).let { if (it < 0) text.length else it }
        return start to end
    }

    private fun goTo(line: Int) {
        val r = lineRange(editor.text?.toString().orEmpty(), line) ?: return
        editor.requestFocus()
        editor.setSelection(r.first, r.second)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        val c = OneiosConfJob.state
        val writable = OneiosConfJob.canWrite() && OneiosJob.state.status?.sessionOpen != true && base != null
        fun item(id: Int, title: Int, enabled: Boolean) = menu.add(Menu.NONE, id, Menu.NONE, title).apply {
            setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER)
            isEnabled = enabled
        }
        if (c.tool) {
            item(M_CHECK, R.string.oneios_conf_check, !c.busy && base != null)
            item(M_FORCE, R.string.oneios_conf_save_anyway, writable)
        }
        // The tool keeps one backup (FILE.bak) and says whether it is there; the plain file's is root's own.
        item(M_RESTORE, R.string.oneios_conf_restore, writable && (!c.tool || c.show?.backup == true))
        item(M_RELOAD, R.string.oneios_switches_reload, !c.busy)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            M_CHECK -> OneiosConfJob.check(this, editor.text?.toString().orEmpty())
            M_FORCE -> save(force = true)
            M_RESTORE -> AlertDialog.Builder(this).setTitle(R.string.oneios_conf_restore).setMessage(R.string.oneios_conf_restore_confirm)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.oneios_conf_restore) { _, _ -> OneiosConfJob.restore(this) }.show()
            M_RELOAD -> {
                dirty = false
                base = null
                OneiosConfJob.load(this)
            }
            else -> return super.onOptionsItemSelected(item)
        }
        return true
    }

    companion object {
        private val WRITES = setOf("write", "write-force", "restore", "set", "unset")
        private const val KEY_TEXT = "conf_text"
        private const val KEY_BASE = "conf_base"
        private const val KEY_DIRTY = "conf_dirty"
        private const val KEY_SAVES = "conf_saves"
        private const val M_CHECK = 1
        private const val M_FORCE = 2
        private const val M_RESTORE = 3
        private const val M_RELOAD = 4

        fun intent(ctx: Context): Intent = Intent(ctx, OneiosConfEditActivity::class.java)
    }
}
