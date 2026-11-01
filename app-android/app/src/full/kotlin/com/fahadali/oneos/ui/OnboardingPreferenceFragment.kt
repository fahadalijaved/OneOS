package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import androidx.preference.CheckBoxPreference
import androidx.preference.Preference
import androidx.preference.PreferenceCategory
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.R
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.RootKind
import com.fahadali.oneos.core.model.RootRules
import com.fahadali.oneos.core.root.RootProbe

class OnboardingPreferenceFragment : PreferenceFragmentCompat() {
    override fun onCreatePreferences(state: Bundle?, rootKey: String?) {
        val ctx = preferenceManager.context
        preferenceScreen = preferenceManager.createPreferenceScreen(ctx)
        val group = PreferenceCategory(ctx)
        preferenceScreen.addPreference(group)
        fun fact(title: Int, summary: CharSequence?, checked: Boolean, action: (() -> Unit)? = null) {
            group.addPreference(CheckBoxPreference(ctx).apply {
                setTitle(title); this.summary = summary; isChecked = checked; isPersistent = false
                isIconSpaceReserved = false
                setOnPreferenceChangeListener { _, _ -> false }
                setOnPreferenceClickListener { action?.invoke(); true }
            })
        }
        fun info(title: Int, summary: Int) {
            group.addPreference(Preference(ctx).apply {
                setTitle(title); setSummary(summary); setIcon(R.drawable.ic_catalog_device); isSelectable = false
            })
        }
        if (arguments?.getInt("page") == 1) {
            val root = RootRules.kind(RootProbe(ctx).signals())
            fact(R.string.onboarding_root, if (root == RootKind.NONE) getString(R.string.onboarding_no_root) else root.label, root != RootKind.NONE) {
                startActivity(Intent(ctx, DeviceReportActivity::class.java))
            }
            fact(R.string.onboarding_nearby, getString(R.string.onboarding_nearby_summary), true)
            fact(R.string.onboarding_lock, getString(R.string.onboarding_lock_summary), FactProbe.screenLockSet(ctx) == false) {
                startActivity(Intent(android.provider.Settings.ACTION_SECURITY_SETTINGS))
            }
        } else {
            info(R.string.onboarding_experimental, R.string.onboarding_experimental_summary)
            info(R.string.onboarding_backup, R.string.onboarding_backup_summary)
            info(R.string.onboarding_data, R.string.onboarding_data_summary)
        }
    }
}
