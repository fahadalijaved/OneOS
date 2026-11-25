package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosConf
import com.fahadali.oneos.session.OneiosConfJob
import com.fahadali.oneos.session.OneiosJob
import dev.oneuiproject.oneui.layout.ToolbarLayout
import dev.oneuiproject.oneui.widget.SwitchItemView

/**
 * Switches (docs/oneios.md, "UI (2026-11-25)"): xnuhost's settings in the staged image's overlay/userland/xnuhost.conf,
 * from the staged runtime's catalog ([OneiosConf], [OneiosConfJob]), grouped by the catalog's groups. A toggle for an
 * on/off switch (a choice with an `off` value too: on is the default), a picker for the others; the help as the
 * summary, a badge for a switch not tested on a phone, its warning; a dot and Reset for one not at its default. Every
 * change is root's `conf set` or `conf unset` and the list is read again from root's answer. A runtime without the
 * catalog gets only Edit file. The primary button is Edit file.
 */
class OneiosSwitchesActivity : EdgeToEdgeActivity() {
    private lateinit var toolbar: ToolbarLayout
    private var unsubscribe: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_oneios_screen)
        toolbar = findViewById(R.id.oneios_toolbar)
        OneiosScreens.setUp(this, toolbar, getString(R.string.oneios_switches))
        applyEdgeToEdgeInsets(toolbar)
        toolbar.expandedSubtitle = getString(R.string.oneios_switches_next)
        findViewById<Button>(R.id.oneios_primary).apply {
            setText(R.string.oneios_switches_edit)
            setOnClickListener { startActivity(OneiosConfEditActivity.intent(this@OneiosSwitchesActivity)) }
        }
    }

    override fun onStart() {
        super.onStart()
        // The list, its values and every answer of root (not the seconds of a write).
        unsubscribe = OneiosConfJob.observeBy({ listOf(it.loading, it.writing, it.loaded, it.catalog, it.noCatalog, it.show, it.problem, it.lastOp) }) { render() }
        // Read whenever the screen opens: the file may have changed (Edit file, a new image set, a PC's stage).
        if (!OneiosConfJob.state.busy) OneiosConfJob.load(this)
    }

    override fun onStop() {
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun render() {
        if (isDestroyed) return
        val c = OneiosConfJob.state
        val column = findViewById<LinearLayout>(R.id.oneios_column)
        val scroll = findViewById<NestedScrollView>(R.id.oneios_scroll)
        val at = scroll.scrollY
        column.removeAllViews()
        val session = OneiosJob.state.status?.sessionOpen == true
        val canWrite = !c.busy && !session && OneiosConfJob.canWrite()

        val head = PrebootCards.section(column, gap = false)
        when {
            c.loading && !c.loaded -> PrebootCards.row(head, getString(R.string.oneios_switches_loading))
            c.writing -> PrebootCards.row(head, getString(R.string.oneios_switches_saving))
            c.problem != null -> PrebootCards.row(head, getString(R.string.oneios_tool_not_started), c.problem)
            session -> PrebootCards.row(head, getString(R.string.oneios_page_sub_open), getString(R.string.oneios_switches_session))
            c.loaded && c.noCatalog -> PrebootCards.row(head, getString(R.string.oneios_switches_old, OneiosConf.FIRST_RUNTIME), getString(R.string.oneios_switches_old_line))
            else -> PrebootCards.row(head, getString(R.string.oneios_switches_next), getString(R.string.oneios_switches_line))
        }
        if (head.childCount <= 1) column.removeView(head)

        val show = c.show
        if (show != null && show.errors.isNotEmpty()) {
            // Serious: xnuhost refuses the whole file with one of these (OneiOS's conf: a line without =, a key it does
            // not read, a bad value), so the next switch does not start iOS. Edit file fixes them.
            val bad = PrebootCards.section(column, getString(R.string.oneios_switches_problems))
            PrebootCards.row(bad, getString(R.string.oneios_switches_edit), getString(R.string.oneios_switches_problems_line), chevron = true) {
                startActivity(OneiosConfEditActivity.intent(this))
            }
            for (e in show.errors) PrebootCards.row(bad, e.line?.let { getString(R.string.oneios_conf_line, it, e.message) } ?: e.message)
        }
        if (show != null && show.warnings.isNotEmpty()) {
            // Warnings stop nothing (a key given twice: the last one is used).
            val warn = PrebootCards.section(column, getString(R.string.oneios_conf_warnings))
            for (w in show.warnings) PrebootCards.row(warn, w.line?.let { getString(R.string.oneios_conf_line, it, w.message) } ?: w.message)
        }
        for (g in c.groups) {
            val card = PrebootCards.section(column, g.name)
            for (r in g.rows) row(card, r, canWrite)
        }
        invalidateOptionsMenu()
        scroll.post { scroll.scrollTo(0, at) }
    }

    /** The summary: the help, the value of a picker, the kernel's need, the phone badge and the warning in colour. */
    private fun summary(r: OneiosConf.Row): CharSequence {
        val s = r.switch
        val b = SpannableStringBuilder()
        fun line(text: CharSequence, color: Int? = null) {
            if (b.isNotEmpty()) b.append('\n')
            val from = b.length
            b.append(text)
            if (color != null) b.setSpan(ForegroundColorSpan(getColor(color)), from, b.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
        s.badge?.let { line(it.replaceFirstChar { c -> c.uppercase() }, if (it == "broken") R.color.oneios_check_fail else R.color.oneios_check_skipped) }
        s.help?.let { line(it) }
        if (s.control != OneiosConf.Control.TOGGLE) {
            line(getString(R.string.oneios_switches_value, r.value ?: getString(R.string.oneios_switches_default_none), s.default ?: getString(R.string.oneios_switches_default_none)),
                if (r.changed) R.color.preboot_primary else null)
        } else if (r.changed) line(getString(R.string.oneios_switches_changed), R.color.preboot_primary)
        if (s.needsKernel) line(getString(R.string.oneios_switches_kernel))
        s.warning?.let { line(it, R.color.oneios_check_fail) }
        return b
    }

    private fun row(card: LinearLayout, r: OneiosConf.Row, canWrite: Boolean) {
        val s = r.switch
        val summary = summary(r)
        if (s.control == OneiosConf.Control.TOGGLE) {
            val v = SwitchItemView(this)
            val previous = card.getChildAt(card.childCount - 1)
            v.showTopDivider = previous is SwitchItemView || previous is dev.oneuiproject.oneui.widget.CardItemView
            v.title = s.title
            v.summaryOn = summary
            v.summaryOff = summary
            v.isChecked = r.on == true
            v.showBadge = r.changed
            v.isEnabled = canWrite
            v.onCheckedChangedListener = { _: Int, on: Boolean -> OneiosConf.toggle(r, on)?.let { OneiosConfJob.change(this, listOf(it)) } }
            if (r.changed) v.setOnLongClickListener { confirmReset(r); true }
            v.contentDescription = listOf(s.title, summary).joinToString(", ")
            card.addView(v, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        } else {
            val v = PrebootCards.row(card, s.title, summary, chevron = true, enabled = canWrite) { pick(r) }
            if (r.changed) v.setOnLongClickListener { confirmReset(r); true }
        }
    }

    /** A picker for a choice, a number or a text; Reset when the switch is not at its default. */
    private fun pick(r: OneiosConf.Row) {
        val s = r.switch
        val d = AlertDialog.Builder(this).setTitle(s.title)
        if (s.control == OneiosConf.Control.CHOICE && !s.values.isNullOrEmpty()) {
            val values = s.values!!
            val labels = values.map { v -> if (v == s.default) getString(R.string.oneios_switches_is_default, v) else v }.toTypedArray()
            d.setSingleChoiceItems(labels, values.indexOf(r.value)) { dialog, i ->
                OneiosConf.change(r, values[i])?.let { OneiosConfJob.change(this, listOf(it)) }
                dialog.dismiss()
            }
        } else {
            val input = EditText(this).apply {
                isSingleLine = true
                setText(r.value.orEmpty())
                if (s.control == OneiosConf.Control.NUMBER) {
                    inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_SIGNED
                    if (s.min != null && s.max != null) hint = getString(R.string.oneios_switches_number_hint, s.min!!.toInt(), s.max!!.toInt())
                }
            }
            val frame = FrameLayout(this).apply {
                val p = PrebootCards.dp(input, 24)
                setPadding(p, p / 3, p, 0)
                addView(input)
            }
            d.setView(frame).setPositiveButton(android.R.string.ok, null)
            val dialog = d.setNegativeButton(android.R.string.cancel, null).create()
            dialog.setOnShowListener {
                dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                    val v = input.text?.toString().orEmpty().trim()
                    val why = s.problem(v)
                    if (why != null) input.error = why
                    else {
                        OneiosConf.change(r, v)?.let { OneiosConfJob.change(this, listOf(it)) }
                        dialog.dismiss()
                    }
                }
            }
            if (r.changed) dialog.setButton(AlertDialog.BUTTON_NEUTRAL, getString(R.string.oneios_switches_reset)) { _, _ -> OneiosConfJob.change(this, listOf(OneiosConf.reset(r))) }
            dialog.show()
            return
        }
        d.setNegativeButton(android.R.string.cancel, null)
        if (r.changed) d.setNeutralButton(R.string.oneios_switches_reset) { _, _ -> OneiosConfJob.change(this, listOf(OneiosConf.reset(r))) }
        d.show()
    }

    private fun confirmReset(r: OneiosConf.Row) {
        if (!OneiosConfJob.canWrite()) return
        AlertDialog.Builder(this).setTitle(r.switch.title)
            .setMessage(getString(R.string.oneios_switches_value, r.value.orEmpty(), r.switch.default ?: getString(R.string.oneios_switches_default_none)))
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.oneios_switches_reset) { _, _ -> OneiosConfJob.change(this, listOf(OneiosConf.reset(r))) }.show()
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        val c = OneiosConfJob.state
        menu.add(Menu.NONE, M_RELOAD, Menu.NONE, R.string.oneios_switches_reload).apply {
            setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER)
            isEnabled = !c.busy
        }
        val changed = c.groups.flatMap { it.rows }.filter { it.changed }
        if (changed.isNotEmpty()) menu.add(Menu.NONE, M_RESET_ALL, Menu.NONE, R.string.oneios_switches_reset_all).apply {
            setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER)
            isEnabled = OneiosConfJob.canWrite() && OneiosJob.state.status?.sessionOpen != true
        }
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            M_RELOAD -> OneiosConfJob.load(this)
            M_RESET_ALL -> {
                val changed = OneiosConfJob.state.groups.flatMap { it.rows }.filter { it.changed }
                AlertDialog.Builder(this).setTitle(R.string.oneios_switches_reset_all).setMessage(R.string.oneios_switches_reset_all_confirm)
                    .setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(R.string.oneios_switches_reset) { _, _ ->
                        changed.chunked(OneiosConf.MAX_CHANGES).firstOrNull()?.let { OneiosConfJob.change(this, it.map(OneiosConf::reset)) }
                    }.show()
            }
            else -> return super.onOptionsItemSelected(item)
        }
        return true
    }

    companion object {
        private const val M_RELOAD = 1
        private const val M_RESET_ALL = 2

        fun intent(ctx: Context): Intent = Intent(ctx, OneiosSwitchesActivity::class.java)
    }
}
