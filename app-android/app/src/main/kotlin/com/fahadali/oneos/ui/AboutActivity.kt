package com.fahadali.oneos.ui

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R

/** About: what this version does, the tested scope, safety, credits. */
class AboutActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.about_title)

    override fun createFragment(): Fragment = AboutFragment()
}

class AboutFragment : PreferenceFragmentCompat() {
    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.about, rootKey)
        findPreference<Preference>("version")?.summary =
            BuildConfig.VERSION_NAME
        findPreference<Preference>("before_you_start")?.setOnPreferenceClickListener {
            startActivity(Intent(requireContext(), BeforeYouStartActivity::class.java))
            true
        }
        findPreference<Preference>("credit_onelineage")?.setOnPreferenceClickListener {
            openInBrowser(getString(R.string.about_credit_onelineage_url))
            true
        }
        findPreference<Preference>("credit_fold8")?.setOnPreferenceClickListener {
            openInBrowser(getString(R.string.about_credit_fold8_url))
            true
        }
        findPreference<Preference>("credit_infinityx")?.setOnPreferenceClickListener {
            openInBrowser(getString(R.string.about_credit_infinityx_url))
            true
        }
    }

    /** Hands the link to the browser; the app itself has no INTERNET permission. */
    private fun openInBrowser(url: String) {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).addCategory(Intent.CATEGORY_BROWSABLE)
        try {
            startActivity(intent)
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(requireContext(), R.string.about_no_browser, Toast.LENGTH_SHORT).show()
        }
    }
}
