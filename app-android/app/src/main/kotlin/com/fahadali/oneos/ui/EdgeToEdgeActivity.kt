package com.fahadali.oneos.ui

import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import dev.oneuiproject.oneui.utils.applyEdgeToEdge

/** Twidget's SESL9 window and floating-toolbar integration. */
abstract class EdgeToEdgeActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applyEdgeToEdge()
    }

    override fun onContentChanged() {
        super.onContentChanged()
        findViewById<ViewGroup>(android.R.id.content)?.let(SeslToolbarCompatibility::install)
    }

    /**
     * Keeps content clear of system navigation and the keyboard. Callers with
     * floating controls can use [onNavigationBarInset] to handle the navigation
     * edge themselves while keeping their scrolling viewport full height.
     */
    protected fun applyEdgeToEdgeInsets(
        root: View,
        onNavigationBarInset: ((Int) -> Unit)? = null,
    ) {
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val safe = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout()
            )
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            val imeVisible = insets.isVisible(WindowInsetsCompat.Type.ime()) && ime.bottom > 0
            val topPadding = if (SeslToolbarCompatibility.applyTopInset(view, safe.top)) 0 else safe.top
            // Screens with floating controls handle their navigation inset in the callback.
            // Other screens keep their entire content viewport above system navigation.
            val bottomPadding = if (onNavigationBarInset == null) maxOf(ime.bottom, safe.bottom) else ime.bottom
            view.setPadding(safe.left, topPadding, safe.right, bottomPadding)
            // The drawer surface stops above system navigation even when the
            // page scrolls behind it. Root padding may already cover part or all
            // of this space (including the keyboard), so avoid counting it twice.
            SeslToolbarCompatibility.applyDrawerBottomInset(
                view,
                (maxOf(safe.bottom, ime.bottom) - bottomPadding).coerceAtLeast(0),
            )
            // IME insets already include the navigation region on Samsung and
            // several other OEM keyboards. Do not add it to floating chrome twice.
            onNavigationBarInset?.invoke(if (imeVisible) 0 else safe.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(root)
    }

    /** Preference lists own navigation padding so their viewport reaches the window edge. */
    protected fun applyPreferenceScreenInsets(root: View) {
        applyEdgeToEdgeInsets(root, onNavigationBarInset = {})
    }

    /** Keeps bottom-floating chrome above gesture and button navigation bars. */
    protected fun View.updateBottomMarginForNavigationBar(
        baseMargin: Int,
        navigationBarInset: Int,
    ) {
        val params = layoutParams as? ViewGroup.MarginLayoutParams ?: return
        val targetMargin = baseMargin + navigationBarInset
        if (params.bottomMargin == targetMargin) return
        params.bottomMargin = targetMargin
        layoutParams = params
    }
}
