package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import androidx.fragment.app.Fragment
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.R

/**
 * Home. Each edition draws its own ([EditionHome], src/full and src/probe):
 * OneOS shows one status and one button (the system, Last time, Advanced,
 * and the footer button; About and How OneOS works in the menu); OneOS Probe
 * keeps [HomeFragment] with res/xml/home.xml (Check this phone, Run tests,
 * Before you start, About).
 */
class MainActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.app_name)
    override val showBack: Boolean get() = intent.getBooleanExtra("system_detail", false)
    override val layoutRes: Int get() = EditionHome.layoutRes

    override fun createFragment(): Fragment = EditionHome.createFragment()

    /** Until Before you start is acknowledged, every launch goes there first. */
    override fun redirect(): Intent? =
        if (BeforeYouStart.isAcknowledged(this)) EditionHome.redirect(this) else EditionHome.onboarding(this)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (isFinishing) return
        setExpandedSubtitle(getString(R.string.home_subtitle))
        EditionHome.created(this)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean = EditionHome.createMenu(this, menu) || super.onCreateOptionsMenu(menu)

    override fun onOptionsItemSelected(item: MenuItem): Boolean = EditionHome.menuItem(this, item) || super.onOptionsItemSelected(item)
}

/** OneOS Probe's Home: the rows of res/xml/home.xml. */
class HomeFragment : PreferenceFragmentCompat() {
    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.home, rootKey)
        EditionHome.bind(this)
        findPreference<Preference>("check_phone")?.setOnPreferenceClickListener {
            startActivity(Intent(requireContext(), DeviceReportActivity::class.java))
            true
        }
        findPreference<Preference>("run_tests")?.setOnPreferenceClickListener {
            startActivity(Intent(requireContext(), RunTestsActivity::class.java))
            true
        }
        findPreference<Preference>("before_you_start")?.setOnPreferenceClickListener {
            startActivity(Intent(requireContext(), BeforeYouStartActivity::class.java))
            true
        }
        findPreference<Preference>("about")?.setOnPreferenceClickListener {
            startActivity(Intent(requireContext(), AboutActivity::class.java))
            true
        }
    }

    override fun onResume() {
        super.onResume()
        EditionHome.resume(this)
    }
}
