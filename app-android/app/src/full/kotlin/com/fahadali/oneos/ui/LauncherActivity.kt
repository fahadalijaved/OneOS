package com.fahadali.oneos.ui

import android.content.Intent
import android.view.Menu
import android.view.MenuItem
import com.fahadali.oneos.R
import dev.oneuiproject.oneui.R as OuiIcons
import dev.oneuiproject.oneui.ktx.startPopOverActivity
import dev.oneuiproject.oneui.popover.PopOverOptions

class LauncherActivity : SystemsActivity() {
    override val screenTitle: CharSequence get() = android.text.SpannableString(getString(R.string.app_name)).apply {
        setSpan(android.text.style.ForegroundColorSpan(getColor(R.color.oneos_blue)), length - 2, length, android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
    }
    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)
        toolbarLayout.toolbar.apply {
            setLogo(R.drawable.toolbar_brand_logo)
            logoDescription = getString(R.string.app_name)
            titleMarginStart = (12 * resources.displayMetrics.density).toInt()
        }
    }
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
