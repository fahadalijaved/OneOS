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
        enforceEdgeToEdgeWindow()
    }

    override fun onPostResume() {
        super.onPostResume()
        enforceEdgeToEdgeWindow()
    }

    @Suppress("DEPRECATION")
    private fun enforceEdgeToEdgeWindow() {
        androidx.core.view.WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor = android.graphics.Color.TRANSPARENT
        window.navigationBarColor = android.graphics.Color.TRANSPARENT
        window.isNavigationBarContrastEnforced = false
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
        val footer = root.findViewById<ViewGroup>(dev.oneuiproject.oneui.design.R.id.tbl_footer_parent)
        val footerBottom = footer?.paddingBottom ?: 0
        fun updateFooter(navigation: Int) {
            footer?.let {
                val hasControls = (0 until it.childCount).any { index -> it.getChildAt(index).visibility != View.GONE }
                val bottom = footerBottom + if (hasControls) navigation else 0
                if (it.paddingBottom != bottom) it.setPadding(it.paddingLeft, it.paddingTop, it.paddingRight, bottom)
            }
        }
        if (footer != null) root.viewTreeObserver.addOnGlobalLayoutListener {
            val insets = root.rootWindowInsets ?: return@addOnGlobalLayoutListener
            val navigation = insets.getInsets(android.view.WindowInsets.Type.navigationBars() or android.view.WindowInsets.Type.displayCutout()).bottom
            val keyboard = insets.getInsets(android.view.WindowInsets.Type.ime()).bottom
            updateFooter((navigation - keyboard).coerceAtLeast(0))
        }
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
            // Every scrolling page occupies the full window. Navigation clearance
            // belongs to the list's trailing padding or an individual fixed control.
            val bottomPadding = ime.bottom
            view.setPadding(safe.left, topPadding, safe.right, bottomPadding)
            updateFooter((safe.bottom - ime.bottom).coerceAtLeast(0))
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

    /** Give ordinary list pages scroll clearance without shortening their viewport. */
    protected fun applyScrollingNavigationInsets(root: ViewGroup) {
        data class Padding(val left: Int, val top: Int, val right: Int, val bottom: Int)
        val bases = java.util.WeakHashMap<View, Padding>()
        fun descendants(group: ViewGroup): Sequence<View> = sequence {
            for (index in 0 until group.childCount) {
                val child = group.getChildAt(index)
                yield(child)
                if (child is ViewGroup) yieldAll(descendants(child))
            }
        }
        root.viewTreeObserver.addOnGlobalLayoutListener {
            val insets = root.rootWindowInsets ?: return@addOnGlobalLayoutListener
            val safe = insets.getInsets(android.view.WindowInsets.Type.navigationBars() or android.view.WindowInsets.Type.displayCutout())
            val ime = insets.getInsets(android.view.WindowInsets.Type.ime())
            val navigation = (safe.bottom - ime.bottom).coerceAtLeast(0)
            for (view in descendants(root)) {
                val list = view is androidx.core.widget.NestedScrollView || view is android.widget.ScrollView ||
                    (view is androidx.recyclerview.widget.RecyclerView &&
                        (view.layoutManager as? androidx.recyclerview.widget.LinearLayoutManager)?.orientation == androidx.recyclerview.widget.RecyclerView.VERTICAL)
                if (!list) continue
                val base = bases.getOrPut(view) { Padding(view.paddingLeft, view.paddingTop, view.paddingRight, view.paddingBottom) }
                (view as ViewGroup).clipToPadding = false
                val bottom = base.bottom + navigation
                if (view.paddingBottom != bottom) view.setPadding(base.left, base.top, base.right, bottom)
            }
        }
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
