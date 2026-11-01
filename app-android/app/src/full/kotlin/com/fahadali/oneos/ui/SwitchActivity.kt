package com.fahadali.oneos.ui

import android.os.Bundle
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.session.LaunchJob
import com.fahadali.oneos.session.SessionPrefs
import com.fahadali.oneos.session.StageCheck
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * All checks and Test run (For the OneOS team; Home's Details › All checks;
 * the card look): the ways back to One UI, every Switch gate as it is (BLOCK
 * has no override; the screen lock is read again at every draw and right
 * before root is asked), the warnings to tick (an untested phone and image,
 * calls on this carrier), for an image with Google services the row that
 * hides them for this session (off by default, never saved), then Test run
 * or Switch, each behind a dialog.
 */
class SwitchActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.switch_title)

    override fun createFragment(): Fragment = SwitchFragment()
}

class SwitchFragment : CardsFragment() {
    private val subs = mutableListOf<() -> Unit>()
    private val ticked = mutableSetOf<String>()

    /** This launch only: ONEOS_GUEST_HIDE_GMS=1 (owner: Google services stay on by default). */
    private var hideGms = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        savedInstanceState?.getStringArrayList(KEY_TICKED)?.let(ticked::addAll)
        hideGms = savedInstanceState?.getBoolean(KEY_HIDE_GMS) == true
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putStringArrayList(KEY_TICKED, ArrayList(ticked))
        outState.putBoolean(KEY_HIDE_GMS, hideGms)
    }

    override fun onStart() {
        super.onStart()
        subs += StageCheck.observe { redraw() }
        subs += LaunchJob.observe { redraw() }
    }

    override fun onResume() {
        super.onResume()
        // Back from Settings (screen lock removed?): the gates read it again.
        redraw()
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        super.onStop()
    }

    override fun build(column: LinearLayout) {
        val ctx = column.context
        val launch = LaunchJob.state
        val check = StageCheck.state
        val r = check.result
        val report = r?.takeIf { it.installd != null }?.let { StageCheck.gates(ctx, it, GatePhase.SWITCH) }
        // {system}: the staged image's name ("the other system" while none is known).
        val system = Images.systemName(report?.image, report?.profile)

        // The ways back: listed always, before anything else.
        val back = Cards.section(column, getString(R.string.switch_cat_back), rows = true)
        if (report?.set?.hasReturnApp == true) {
            Cards.row(back, R.drawable.ic_home_back_app, getString(R.string.home_sheet_back_app), getString(R.string.home_sheet_back_app_line, system))
        }
        Cards.row(back, R.drawable.ic_home_back_keys, getString(R.string.switch_back_keys_title), getString(R.string.switch_back_keys_summary, system))
        Cards.row(back, OuiIcons.drawable.ic_oui_time, getString(R.string.switch_back_auto_title), getString(R.string.switch_back_auto_summary, system))
        Cards.row(back, R.drawable.ic_home_back_power, getString(R.string.switch_back_force_title), getString(R.string.switch_back_force_summary))
        Cards.row(back, OuiIcons.drawable.ic_oui_security_outline, getString(R.string.switch_back_root_title), getString(R.string.switch_back_root_summary))

        // Every check, as it is.
        val levels = report?.report?.sorted?.map { it.level }.orEmpty()
        val checks = Cards.section(
            column, getString(R.string.switch_cat_checks),
            if (levels.isEmpty() || check.busy) null else getString(R.string.home_checks_count, levels.count { it == Level.OK }, levels.size),
            Cards.worst(levels),
            rows = true,
        )
        if (check.busy) {
            CardRows.tint(Cards.row(checks, OuiIcons.drawable.ic_oui_refresh, check.step ?: getString(R.string.prepare_checking), null), Level.INFO)
        } else {
            CardRows.row(
                checks, OuiIcons.drawable.ic_oui_refresh,
                getString(if (r == null) R.string.prepare_check_title else R.string.prepare_check_again),
                check.message ?: getString(R.string.switch_check_summary),
                enabled = !launch.busy,
            ) { if (!launch.busy) StageCheck.start(ctx, StageCheck.Mode.FULL) }
        }
        if (r == null) return
        if (report == null) {
            CardRows.status(checks, Level.BLOCK, getString(R.string.switch_need_full), null)
            return
        }
        val stale = r.ageMs > StageCheck.FRESH_MS
        for (f in report.report.sorted) CardRows.finding(checks, f)

        val toTick = report.toTick
        ticked.retainAll(toTick.mapNotNull { it.tickKey }.toSet())
        if (toTick.isNotEmpty()) {
            val warn = Cards.section(column, getString(R.string.switch_cat_tick), rows = true)
            for (g in toTick) {
                CardRows.tick(warn, g.ack!!, g.finding.title, g.tickKey in ticked) { on ->
                    g.tickKey?.let { if (on) ticked += it else ticked -= it }
                    redraw()
                }
            }
        }

        val go = Cards.section(column, getString(R.string.switch_cat_go), rows = true)
        // Only an image whose Google services may be hidden offers this (not the
        // Pixel image: its sessions present them); any other launch writes 0.
        if (report.image?.gmsHideable == true) {
            CardRows.toggle(
                go, getString(R.string.switch_hide_gms_title), getString(R.string.switch_hide_gms_summary, system), hideGms,
                enabled = !launch.busy && launch.phase != LaunchJob.Phase.LAUNCHED,
            ) { on ->
                hideGms = on
                redraw()
            }
        } else {
            hideGms = false
        }
        val allowed = !stale && report.allows(ticked) && !launch.busy && launch.phase != LaunchJob.Phase.LAUNCHED
        val why = when {
            stale -> getString(R.string.prepare_run_stale)
            report.blocked -> getString(R.string.switch_blocked)
            !report.allows(ticked) -> getString(R.string.switch_tick_first)
            else -> null
        }
        val setupNote = report.image?.presentsGms == true
        val backApp = report.set?.hasReturnApp == true
        CardRows.row(go, OuiIcons.drawable.ic_oui_labs_outline, getString(R.string.switch_dry_title), why ?: getString(R.string.switch_dry_summary, system), enabled = allowed) {
            if (allowed) confirm(dry = true, system = system, setupNote = setupNote, backApp = backApp)
        }
        val sw = CardRows.row(go, OuiIcons.drawable.ic_oui_power, getString(R.string.switch_go_title, system), why ?: getString(R.string.switch_go_summary, system), enabled = allowed) {
            if (allowed) confirm(dry = false, system = system, setupNote = setupNote, backApp = backApp)
        }
        if (allowed) CardRows.titleColor(sw, R.color.oneos_ok_text)
        when (launch.phase) {
            LaunchJob.Phase.RUNNING ->
                CardRows.tint(Cards.row(go, OuiIcons.drawable.ic_oui_refresh, launch.detail ?: getString(R.string.switch_starting), null), Level.INFO)
            LaunchJob.Phase.LAUNCHED -> CardRows.status(go, Level.OK, getString(R.string.switch_launched), launch.message)
            LaunchJob.Phase.FAILED -> CardRows.status(go, Level.BLOCK, getString(R.string.switch_not_started), launch.message)
            LaunchJob.Phase.IDLE -> Unit
        }
    }

    /**
     * [setupNote]: the image's own setup wizard runs on a new stage (Google services presented): what to skip in it.
     * [backApp]: the set has Back to One UI, so the switch dialog names it with the keys (as the ways back above).
     */
    private fun confirm(dry: Boolean, system: String, setupNote: Boolean, backApp: Boolean) {
        val hide = hideGms
        val back = if (backApp) getString(R.string.switch_go_dialog_back_app, system) else getString(R.string.switch_go_dialog_back_keys)
        val message = (if (dry) getString(R.string.switch_dry_dialog_message, system) else getString(R.string.switch_go_dialog_message, system, back)) +
            (if (!dry && setupNote) "\n\n" + getString(R.string.confirm_setup_wizard, system) else "") +
            (if (hide) "\n\n" + getString(R.string.switch_dialog_gms_hidden) else "") +
            if (!dry && !SessionPrefs.heatCap(requireContext())) "\n\n" + getString(R.string.confirm_heat_cap_off) else ""
        AlertDialog.Builder(requireContext())
            .setTitle(if (dry) getString(R.string.switch_dry_dialog_title) else getString(R.string.switch_go_dialog_title, system))
            .setMessage(message)
            .setPositiveButton(if (dry) getString(R.string.switch_dry_title) else getString(R.string.switch_go_title, system)) { _, _ ->
                LaunchJob.start(requireContext(), dry, ticked.toSet(), hide, SessionPrefs.secIms(requireContext()), SessionPrefs.edmStub(requireContext()))
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private companion object {
        const val KEY_TICKED = "ticked"
        const val KEY_HIDE_GMS = "hide_gms"
    }
}
