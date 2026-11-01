package com.fahadali.oneos.ui

import android.content.Intent
import android.view.Menu
import android.view.MenuItem
import com.fahadali.oneos.R
import dev.oneuiproject.oneui.R as OuiIcons
import dev.oneuiproject.oneui.ktx.startPopOverActivity
import dev.oneuiproject.oneui.popover.PopOverOptions

class LauncherActivity : SystemsActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.app_name)
    override val showBack = false
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(0, 900, 0, R.string.catalog_settings).apply {
            setIcon(OuiIcons.drawable.ic_oui_settings_outline)
            setShowAsAction(MenuItem.SHOW_AS_ACTION_ALWAYS)
        }
        return true
    }
    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == 900) {
            val target = Intent(this, AdvancedActivity::class.java)
            if (resources.configuration.smallestScreenWidthDp >= 600) {
                startPopOverActivity(target, PopOverOptions.centerRightAnchored(this))
            } else startActivity(target)
            return true
        }
        return super.onOptionsItemSelected(item)
    }
}
