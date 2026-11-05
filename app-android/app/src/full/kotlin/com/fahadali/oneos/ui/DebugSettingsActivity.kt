package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.preference.EditTextPreference
import androidx.preference.Preference
import androidx.preference.SwitchPreferenceCompat
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.session.AppUpdater

class DebugSettingsActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.team_title)
    override val preferenceInsets = true
    override fun createFragment(): Fragment = DebugSettingsFragment()
}

class DebugSettingsFragment : InsetPreferenceFragment() {
    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        val ctx = preferenceManager.context
        preferenceScreen = preferenceManager.createPreferenceScreen(ctx)
        if (BuildConfig.DEBUG) {
            preferenceScreen.addDescribedPreference(SwitchPreferenceCompat(ctx).apply {
                key = "setup_preview"
                setTitle(R.string.setup_preview_setting)
                setSummary(R.string.setup_preview_setting_summary)
                isPersistent = false
                isIconSpaceReserved = false
                isChecked = DebugPreview.enabled(ctx)
                setOnPreferenceChangeListener { _, value -> DebugPreview.setEnabled(ctx, value as Boolean); true }
            })
        }
        fun category(title: Int) = androidx.preference.PreferenceCategory(ctx).apply {
            setTitle(title); preferenceScreen.addPreference(this)
        }
        fun entry(group: androidx.preference.PreferenceCategory, title: Int, summary: Int, target: Class<*>, team: Boolean = false) {
            group.addPreference(Preference(ctx).apply {
                setTitle(title); setSummary(summary); isIconSpaceReserved = false
                setOnPreferenceClickListener {
                    startActivity(Intent(ctx, target).apply { if (team) putExtra(ImageActivity.EXTRA_TEAM, true) }); true
                }
            })
        }
        val checks = category(R.string.team_card_checks)
        entry(checks, R.string.switch_title, R.string.team_switch_summary, SwitchActivity::class.java)
        entry(checks, R.string.report_title, R.string.team_phone_summary, DeviceReportActivity::class.java)
        entry(checks, R.string.tests_title, R.string.team_tests_summary, RunTestsActivity::class.java)
        val setup = category(R.string.team_card_setup)
        entry(setup, R.string.prepare_title_team, R.string.team_setup_summary, PrepareActivity::class.java, true)
        entry(setup, R.string.image_title_team, R.string.team_file_summary, ImageActivity::class.java, true)
        // 0.4.56: a code the owner enters (the test channel's Drive id), not a switch anyone can turn on.
        setup.addPreference(EditTextPreference(ctx).apply {
            key = "update_test_code"
            setTitle(R.string.team_update_test)
            isPersistent = false; isIconSpaceReserved = false
            fun summary() = setSummary(if (AppUpdater.testChannel(ctx)) R.string.team_update_test_on else R.string.team_update_test_summary)
            text = AppUpdater.testCode(ctx).orEmpty(); summary()
            setDialogMessage(R.string.team_update_test_dialog)
            setOnPreferenceChangeListener { _, value ->
                val ok = AppUpdater.setTestCode(ctx, value as String)
                if (!ok) Toast.makeText(ctx, R.string.team_update_test_invalid, Toast.LENGTH_LONG).show()
                summary(); ok
            }
        })
        preferenceScreen.addBottomInset()
    }
}
