package com.fahadali.oneos.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import androidx.annotation.LayoutRes
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * One screen = One UI collapsing [ToolbarLayout] + one preference fragment.
 * Target SDK 36 always draws edge to edge, and the 2022 ToolbarLayout does not
 * handle insets itself, so the content view is padded by the system bars.
 */
abstract class ToolbarActivity : AppCompatActivity() {
    protected lateinit var toolbarLayout: ToolbarLayout
        private set

    /** Title shown in the collapsing toolbar. */
    protected abstract val screenTitle: CharSequence

    /** False on the home screen (no back arrow). */
    protected open val showBack: Boolean = true

    /** Layout holding [R.id.toolbar_layout] and [R.id.fragment_container]. */
    @get:LayoutRes
    protected open val layoutRes: Int get() = R.layout.activity_toolbar

    protected abstract fun createFragment(): Fragment

    /** Non-null: open that screen instead and close this one without drawing it. */
    protected open fun redirect(): Intent? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        redirect()?.let {
            startActivity(it)
            finish()
            return
        }
        setContentView(layoutRes)
        padForSystemBars(findViewById(android.R.id.content))
        toolbarLayout = findViewById(R.id.toolbar_layout)
        toolbarLayout.setTitle(screenTitle)
        toolbarLayout.showNavigationButtonAsBack = showBack
        if (showBack) toolbarLayout.setNavigationButtonOnClickListener { onBackPressedDispatcher.onBackPressed() }
        if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.fragment_container, createFragment())
                .commit()
        }
    }

    fun setExpandedSubtitle(text: CharSequence) {
        toolbarLayout.expandedSubtitle = text
    }

    private fun padForSystemBars(root: View) {
        root.setOnApplyWindowInsetsListener { v, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            WindowInsets.CONSUMED
        }
    }
}
