package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import androidx.preference.Preference
import androidx.preference.PreferenceCategory
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.SwitchPreferenceCompat
import androidx.appcompat.app.AlertDialog
import com.fahadali.oneos.session.RemoveJob
import com.fahadali.oneos.R
import com.fahadali.oneos.session.LogJob
import com.fahadali.oneos.session.SessionPrefs
import dev.oneuiproject.oneui.R as OuiIcons

/** SESL9 preference rows, the same settings component used by Twidget. */
class SettingsPreferenceFragment : InsetPreferenceFragment() {
    override fun onResume() { super.onResume(); onCreatePreferences(null, null) }

    // Remove OneOS data says while it runs and how it ended (0.4.43, UX audit: no feedback at all before).
    private var unsubscribe: (() -> Unit)? = null
    private var lastRemove: RemoveJob.Phase? = null
    override fun onStart() {
        super.onStart()
        lastRemove = RemoveJob.state.phase
        unsubscribe = RemoveJob.observe { st ->
            if (!isAdded) return@observe
            val ended = lastRemove == RemoveJob.Phase.REMOVING && (st.phase == RemoveJob.Phase.DONE || st.phase == RemoveJob.Phase.FAILED)
            lastRemove = st.phase
            onCreatePreferences(null, null)
            if (ended) st.message?.let { msg ->
                AlertDialog.Builder(requireContext()).setTitle(R.string.remove_title).setMessage(msg).setPositiveButton(android.R.string.ok, null).show()
            }
        }
    }
    override fun onStop() { unsubscribe?.invoke(); unsubscribe = null; super.onStop() }
    override fun onCreatePreferences(state: Bundle?, rootKey: String?) {
        val ctx = preferenceManager.context
        preferenceScreen = preferenceManager.createPreferenceScreen(ctx)
        fun category(title: Int) = PreferenceCategory(ctx).apply { setTitle(title); preferenceScreen.addPreference(this) }
        fun row(group: PreferenceCategory, title: Int, summary: Int? = null, icon: Int = 0, target: Class<*>) {
            group.addDescribedPreference(Preference(ctx).apply {
                key = "setting_$title"
                setTitle(title)
                if (summary != null) setSummary(summary)
                isIconSpaceReserved = icon != 0
                if (icon != 0) setIcon(icon)
                setOnPreferenceClickListener { startActivity(Intent(ctx, target)); true }
            })
        }
        val setup = category(R.string.advanced_card_system)
        row(setup, R.string.image_title, R.string.advanced_file_summary, OuiIcons.drawable.ic_oui_folder_open, ImageActivity::class.java)
        row(setup, R.string.space_title, R.string.advanced_space_summary, OuiIcons.drawable.ic_oui_manage_storage_outline, OldStagesActivity::class.java)
        row(setup, R.string.prepare_title, R.string.advanced_setup_summary, OuiIcons.drawable.ic_oui_refresh, PrepareActivity::class.java)
        setup.addDescribedPreference(Preference(ctx).apply {
            key = "remove_data"
            val rs = RemoveJob.state
            setTitle(if (rs.busy) R.string.remove_running else R.string.remove_title)
            if (!rs.busy && rs.message != null) summary = rs.message else setSummary(R.string.remove_summary)
            isEnabled = !rs.busy
            setIcon(OuiIcons.drawable.ic_oui_delete_outline)
            setOnPreferenceClickListener {
                if (!RemoveJob.canStart()) android.widget.Toast.makeText(ctx, R.string.remove_busy, android.widget.Toast.LENGTH_LONG).show()
                else AlertDialog.Builder(ctx).setTitle(R.string.remove_confirm_title).setMessage(R.string.remove_confirm_message)
                    .setPositiveButton(R.string.remove_confirm_run) { _, _ -> RemoveJob.start(ctx) }
                    .setNegativeButton(android.R.string.cancel, null).show()
                true
            }
        })
        fun toggle(group: PreferenceCategory, title: Int, summary: Int, value: Boolean, save: (Boolean) -> Unit) {
            group.addDescribedPreference(SwitchPreferenceCompat(ctx).apply {
                key = "setting_$title"
                setTitle(title); setSummary(summary); isIconSpaceReserved = false; isPersistent = false; isChecked = value
                setOnPreferenceChangeListener { _, next -> save(next as Boolean); true }
            })
        }
        val sessions = category(R.string.advanced_card_sessions)
        row(sessions, R.string.last_title, target = LastSessionActivity::class.java)
        toggle(sessions, R.string.advanced_heat_cap_title, R.string.advanced_heat_cap_summary, SessionPrefs.heatCap(ctx)) { SessionPrefs.setHeatCap(ctx, it) }
        val experimental = category(R.string.settings_experimental)
        toggle(experimental, R.string.advanced_sec_ims_title, R.string.advanced_sec_ims_summary, SessionPrefs.secIms(ctx)) { SessionPrefs.setSecIms(ctx, it) }
        toggle(experimental, R.string.advanced_edm_stub_title, R.string.advanced_edm_stub_summary, SessionPrefs.edmStub(ctx)) { SessionPrefs.setEdmStub(ctx, it) }
        toggle(experimental, R.string.verbose_boot_title, R.string.verbose_boot_summary, SessionPrefs.verboseBoot(ctx)) { SessionPrefs.setVerboseBoot(ctx, it) }
        val risky = category(R.string.advanced_card_risky)
        toggle(risky, R.string.advanced_allow_lock_title, R.string.advanced_allow_lock_summary, SessionPrefs.allowScreenLock(ctx)) { SessionPrefs.setAllowScreenLock(ctx, it) }
        LogJob.latestZip(ctx)?.let { zip ->
            sessions.addDescribedPreference(Preference(ctx).apply {
                key = "session_logs"
                setTitle(R.string.logs_title)
                setSummary(R.string.advanced_logs_summary)
                isIconSpaceReserved = false
                setOnPreferenceClickListener {
                    startActivity(Intent(ctx, FindingsActivity::class.java).putExtra(FindingsActivity.EXTRA_ZIP, zip.path)); true
                }
            })
        }
        if (SessionRestore.offered(ctx)) {
            sessions.addDescribedPreference(Preference(ctx).apply {
                setTitle(R.string.last_restore_title); isIconSpaceReserved = false
                setOnPreferenceClickListener { activity?.let { SessionRestore.confirm(it) }; true }
            })
        }
        val help = category(R.string.settings_help)
        row(help, R.string.about_title, target = AboutActivity::class.java)
        row(help, R.string.team_title, R.string.advanced_team_summary, target = DebugSettingsActivity::class.java)
        preferenceScreen.addBottomInset()
    }
}
