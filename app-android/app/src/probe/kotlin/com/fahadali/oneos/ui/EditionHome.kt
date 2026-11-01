package com.fahadali.oneos.ui

import android.view.Menu
import android.view.MenuItem
import androidx.fragment.app.Fragment
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.R

/**
 * The probe edition (OneOS Probe) keeps its small Home: no switching, so
 * only the shared rows of res/xml/home.xml (src/probe): Check this phone,
 * Run tests, Before you start, About. No footer, no menu.
 */
internal object EditionHome {
    fun onboarding(a: MainActivity) = android.content.Intent(a, BeforeYouStartActivity::class.java)

    fun redirect(a: MainActivity): android.content.Intent? = null

    val layoutRes: Int get() = R.layout.activity_toolbar

    fun createFragment(): Fragment = HomeFragment()

    fun created(a: MainActivity) = Unit

    fun createMenu(a: MainActivity, menu: Menu): Boolean = false

    fun menuItem(a: MainActivity, item: MenuItem): Boolean = false

    fun bind(f: PreferenceFragmentCompat) = Unit

    fun resume(f: PreferenceFragmentCompat) = Unit
}
