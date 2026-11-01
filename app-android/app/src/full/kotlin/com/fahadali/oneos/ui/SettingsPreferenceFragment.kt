package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import androidx.preference.Preference
import androidx.preference.PreferenceCategory
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.R
import com.fahadali.oneos.session.LogJob
import com.fahadali.oneos.session.SessionPrefs
import dev.oneuiproject.oneui.R as OuiIcons

/** SESL9 preference rows, the same settings component used by Twidget. */
class SettingsPreferenceFragment : PreferenceFragmentCompat() {
    override fun onCreatePreferences(state: Bundle?, rootKey: String?) {
        val ctx = preferenceManager.context
        preferenceScreen = preferenceManager.createPreferenceScreen(ctx)
        fun category(title: Int) = PreferenceCategory(ctx).apply { setTitle(title); preferenceScreen.addPreference(this) }
        fun row(group: PreferenceCategory, title: Int, summary: Int? = null, icon: Int = 0, target: Class<*>) {
            group.addPreference(Preference(ctx).apply {
                setTitle(title)
                if (summary != null) setSummary(summary)
                isIconSpaceReserved = icon != 0
                if (icon != 0) setIcon(icon)
                setOnPreferenceClickListener { startActivity(Intent(ctx, target)); true }
            })
        }
        val setup = category(R.string.advanced_card_system)
        row(setup, R.string.settings_load_gsi, R.string.advanced_file_summary, OuiIcons.drawable.ic_oui_folder_open, ImageActivity::class.java)
        row(setup, R.string.settings_storage, R.string.advanced_space_summary, OuiIcons.drawable.ic_oui_manage_storage_outline, OldStagesActivity::class.java)
        row(setup, R.string.settings_repair, R.string.advanced_setup_summary, OuiIcons.drawable.ic_oui_refresh, PrepareActivity::class.java)
        val sessions = category(R.string.advanced_card_sessions)
        row(sessions, R.string.last_title, target = LastSessionActivity::class.java)
        LogJob.latestZip(ctx)?.let { zip ->
            sessions.addPreference(Preference(ctx).apply {
                setTitle(R.string.logs_title)
                setSummary(R.string.advanced_logs_summary)
                isIconSpaceReserved = false
                setOnPreferenceClickListener {
                    startActivity(Intent(ctx, FindingsActivity::class.java).putExtra(FindingsActivity.EXTRA_ZIP, zip.path)); true
                }
            })
        }
        if (SessionRestore.offered(ctx)) {
            sessions.addPreference(Preference(ctx).apply {
                setTitle(R.string.last_restore_title); isIconSpaceReserved = false
                setOnPreferenceClickListener { activity?.let { SessionRestore.confirm(it) }; true }
            })
        }
        val help = category(R.string.settings_help)
        row(help, R.string.about_title, target = AboutActivity::class.java)
        row(help, R.string.settings_onboarding, target = OnboardingActivity::class.java)
        row(help, R.string.settings_debug, R.string.advanced_team_summary, target = TeamActivity::class.java)
    }
}
