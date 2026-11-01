package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import androidx.fragment.app.Fragment
import androidx.preference.PreferenceFragmentCompat
import com.fahadali.oneos.R

/**
 * The "Before you start" acknowledgement, kept in app-private
 * SharedPreferences (allowBackup is off and data_extraction_rules.xml
 * excludes it from backup and device transfer). Bump [VERSION] when the
 * screen's content changes so everyone reads it again.
 */
object BeforeYouStart {
    const val VERSION = 3
    private const val PREFS = "oneos"
    private const val KEY_ACK_VERSION = "before_you_start_ack_version"

    fun isAcknowledged(context: Context): Boolean = prefs(context).getInt(KEY_ACK_VERSION, 0) >= VERSION

    fun acknowledge(context: Context) {
        prefs(context).edit().putInt(KEY_ACK_VERSION, VERSION).apply()
    }

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}

/**
 * Before you start: shown at every launch until the user ticks the checkbox
 * and taps Continue (Back closes the app). Opened again from Home or About
 * once acknowledged, it is read-only with a back arrow.
 */
class BeforeYouStartActivity : ToolbarActivity() {
    private val firstRun: Boolean by lazy { !BeforeYouStart.isAcknowledged(this) }

    override val screenTitle: CharSequence get() = getString(R.string.before_title)
    override val showBack: Boolean get() = !firstRun
    override val layoutRes: Int get() = R.layout.activity_before_you_start

    override fun createFragment(): Fragment = BeforeYouStartFragment()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!firstRun) {
            findViewById<View>(R.id.before_footer).visibility = View.GONE
            return
        }
        val ack = findViewById<CheckBox>(R.id.before_ack)
        val next = findViewById<Button>(R.id.before_continue)
        // The checkbox restores its own state after onCreate; the listener follows it.
        next.isEnabled = ack.isChecked
        ack.setOnCheckedChangeListener { _, checked -> next.isEnabled = checked }
        next.setOnClickListener {
            if (!ack.isChecked) return@setOnClickListener
            BeforeYouStart.acknowledge(this)
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }
}

class BeforeYouStartFragment : PreferenceFragmentCompat() {
    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        setPreferencesFromResource(R.xml.before_you_start, rootKey)
    }
}
