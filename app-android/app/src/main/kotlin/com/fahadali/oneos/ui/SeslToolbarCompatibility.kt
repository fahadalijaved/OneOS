package com.fahadali.oneos.ui

import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import androidx.appcompat.widget.Toolbar
import androidx.coordinatorlayout.widget.CoordinatorLayout
import androidx.core.view.children
import androidx.core.widget.NestedScrollView
import androidx.recyclerview.widget.RecyclerView
import androidx.slidingpanelayout.widget.SlidingPaneLayout
import java.util.WeakHashMap
import com.google.android.material.appbar.AppBarLayout
import com.google.android.material.appbar.CollapsingToolbarLayout
import com.google.android.material.oneui.floatingactioncontainer.FloatingToolbarLayout

/** Bridges the OneUI8 design wrapper to SESL9's sibling floating toolbar contract. */
internal object SeslToolbarCompatibility {
    fun applyDrawerBottomInset(root: View, bottom: Int) {
        val group = root as? ViewGroup ?: return
        val slidingDrawer = descendants(group).filterIsInstance<SlidingPaneLayout>().firstOrNull()
        if (slidingDrawer != null) {
            // SESL owns both the tablet rail's bounds and its rounded surface.
            // A margin on drawer_panel alone is ignored by this container.
            slidingDrawer.seslSetDrawerMarginBottom(bottom)
        } else {
            group.findViewById<View>(dev.oneuiproject.oneui.design.R.id.drawer_panel)?.let { panel ->
                val params = panel.layoutParams as? ViewGroup.MarginLayoutParams
                if (params != null && params.bottomMargin != bottom) {
                    params.bottomMargin = bottom
                    panel.layoutParams = params
                }
            }
        }
    }

    fun applyTopInset(root: View, top: Int): Boolean {
        val group = root as? ViewGroup ?: return false
        val appBar = descendants(group).filterIsInstance<AppBarLayout>().firstOrNull() ?: return false
        // Keep controls below the status bar while the scrolling coordinator
        // occupies the full window, including the region behind the status bar.
        appBar.setPadding(appBar.paddingLeft, top, appBar.paddingRight, appBar.paddingBottom)
        val drawerTop = top + group.resources.getDimensionPixelSize(androidx.appcompat.R.dimen.sesl_action_bar_top_padding)
        val slidingDrawer = descendants(group).filterIsInstance<SlidingPaneLayout>().firstOrNull()
        if (slidingDrawer != null) {
            // Tablet rail geometry and its rounded surface are owned by the
            // native sliding container; child layout margins are ignored there.
            slidingDrawer.seslSetDrawerMarginTop(drawerTop)
        } else {
            group.findViewById<View>(dev.oneuiproject.oneui.design.R.id.drawer_panel)?.let { panel ->
                val params = panel.layoutParams as? ViewGroup.MarginLayoutParams
                if (params != null && params.topMargin != drawerTop) {
                    params.topMargin = drawerTop
                    panel.layoutParams = params
                }
            }
        }
        group.clipToPadding = false
        return true
    }

    fun install(root: ViewGroup) {
        // The older wrapper adds a bottom corner mask over its scrolling page.
        // Keep all host pages open to the transparent navigation edge.
        descendants(root).filter { it.id == dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners }
            .forEach { it.visibility = View.GONE }
        val fadingViews = WeakHashMap<View, Boolean>()
        fun enableNativeFadingEdges() {
            for (view in descendants(root)) {
                if (view.id == dev.oneuiproject.oneui.design.R.id.tbl_bottom_corners) {
                    if (view.visibility != View.GONE) view.visibility = View.GONE
                    continue
                }
                if (fadingViews.containsKey(view)) continue
                when (view) {
                    is NestedScrollView -> view.seslSetFadingEdgeEnabled(true)
                    is RecyclerView -> {
                        // The catalogue is a horizontal, edge-to-edge pager. Native
                        // vertical overflow fades belong only to scrolling pages.
                        val horizontal = (view.layoutManager as? androidx.recyclerview.widget.LinearLayoutManager)
                            ?.orientation == RecyclerView.HORIZONTAL
                        view.seslSetFadingEdgeEnabled(!horizontal)
                    }
                    else -> continue
                }
                fadingViews[view] = true
                // Fragment lists can already have received their first insets
                // before the native helper installs its own inset listener.
                androidx.core.view.ViewCompat.requestApplyInsets(view)
            }
        }
        enableNativeFadingEdges()
        // Preference fragments and lazy queue content attach their lists later.
        root.viewTreeObserver.addOnGlobalLayoutListener { enableNativeFadingEdges() }
        val appBars = descendants(root).filterIsInstance<AppBarLayout>().toList()
        for (appBar in appBars) {
            val coordinator = appBar.parent as? CoordinatorLayout ?: continue
            val collapsing = appBar.children.filterIsInstance<CollapsingToolbarLayout>()
                .firstOrNull() ?: continue
            if (coordinator.children.any { it is FloatingToolbarLayout }) continue
            val toolbar = collapsing.children.filterIsInstance<Toolbar>().firstOrNull() ?: continue
            val toolbarHeight = toolbar.layoutParams.height
            val collapsedToolbarHeight = maxOf(appBar.seslGetCollapsedHeight(), toolbarHeight.toFloat())
            val bottomAligned = (toolbar.layoutParams as? FrameLayout.LayoutParams)
                ?.gravity?.and(Gravity.VERTICAL_GRAVITY_MASK) == Gravity.BOTTOM
            val floating = FloatingToolbarLayout(root.context).apply {
                enableScrollTransition(false, true)
                id = View.generateViewId()
                elevation = maxOf(appBar.elevation, 4 * resources.displayMetrics.density)
                enableToolbarItemBackgroundTransition(true)
            }
            coordinator.addView(floating, CoordinatorLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT,
            ).apply {
                anchorId = appBar.id
                anchorGravity = (if (bottomAligned) Gravity.BOTTOM else Gravity.TOP) or Gravity.CENTER_HORIZONTAL
                // In an anchored CoordinatorLayout, TOP places the child's bottom
                // at the anchor; BOTTOM places its top there.
                gravity = (if (bottomAligned) Gravity.TOP else Gravity.BOTTOM) or Gravity.CENTER_HORIZONTAL
            })
            // Keep the same Toolbar and menu presenters: navigation, badges and actions
            // continue to be owned by the existing activity / OneUI design wrapper.
            fun moveToolbars() {
                collapsing.children.filterIsInstance<Toolbar>().toList().forEach { bar ->
                    val height = bar.layoutParams.height
                    bar.menu.findItem(dev.oneuiproject.oneui.design.R.id.menu_item_am_cancel)?.apply {
                        icon = null
                        setShowAsAction(android.view.MenuItem.SHOW_AS_ACTION_ALWAYS or android.view.MenuItem.SHOW_AS_ACTION_WITH_TEXT)
                        bar.background = null
                    }
                    if (bar.id == dev.oneuiproject.oneui.design.R.id.toolbarlayout_action_mode_toolbar) {
                        bar.viewTreeObserver.addOnPreDrawListener {
                            val cancel = bar.menu.findItem(dev.oneuiproject.oneui.design.R.id.menu_item_am_cancel)
                            descendants(bar).filterIsInstance<TextView>().filter { it.text == cancel?.title }.forEach { label ->
                                if (label.maxLines != 1) label.setSingleLine(true)
                                val width = kotlin.math.ceil(label.paint.measureText(label.text.toString())).toInt() +
                                    label.compoundPaddingLeft + label.compoundPaddingRight
                                if (label.layoutParams.width != width) {
                                    label.layoutParams = label.layoutParams.apply { this.width = width }
                                }
                            }
                            true
                        }
                    }
                    collapsing.removeView(bar)
                    if (height > 0) bar.minimumHeight = maxOf(bar.minimumHeight, height)
                    floating.addView(bar, FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT,
                    ))
                }
                if (toolbarHeight > 0) collapsing.minimumHeight = toolbarHeight
                val params = floating.layoutParams as CoordinatorLayout.LayoutParams
                // Controls retain the app bar's system inset when floating.
                if (params.topMargin != appBar.paddingTop) {
                    params.topMargin = appBar.paddingTop
                    floating.layoutParams = params
                }
                // A top-inset app bar must retain that inset at the
                // collapsed stop too. Otherwise content reaches the toolbar while
                // SESL still considers it collapsed, before its floating phase.
                val collapsedHeight = collapsedToolbarHeight + appBar.paddingTop
                // Fixed-height pages need room for the inset as well. Leaving
                // their old height makes SESL treat them as already hidden on entry.
                if (!appBar.isEnabled && appBar.layoutParams.height != collapsedHeight.toInt()) {
                    appBar.seslSetCustomHeight(collapsedHeight.toInt())
                }
                if (appBar.seslGetCollapsedHeight() != collapsedHeight) {
                    appBar.seslSetCollapsedHeight(collapsedHeight)
                    appBar.requestLayout()
                }
            }
            moveToolbars()
            var boundScroll: View? = null
            var selectionWasVisible = false
            floating.viewTreeObserver.addOnPreDrawListener {
                // The SESL8 wrapper never connects the new floating container to
                // its scrolling page. SESL9 uses this link to clamp the native top
                // fade while the app bar moves offscreen, even before list scrollY changes.
                val scroll = descendants(coordinator).firstOrNull {
                    it.isShown && (it is NestedScrollView || it is RecyclerView)
                }
                if (scroll != null && scroll !== boundScroll) {
                    boundScroll = scroll
                    when (scroll) {
                        is NestedScrollView -> floating.setNestedScrollView(scroll)
                        is RecyclerView -> floating.setRecyclerView(scroll)
                    }
                }
                val selectionVisible = floating.children.filterIsInstance<Toolbar>().any {
                    it.id == dev.oneuiproject.oneui.design.R.id.toolbarlayout_action_mode_toolbar && it.visibility == View.VISIBLE
                }
                if (selectionVisible != selectionWasVisible) {
                    selectionWasVisible = selectionVisible
                    // The SESL8 wrapper leaves its normal toolbar visible beneath
                    // action mode. Native floating layout measures the visible bar.
                    toolbar.visibility = if (selectionVisible) View.INVISIBLE else View.VISIBLE
                    floating.requestLayout()
                    floating.showFloatingItemBackground(selectionVisible, false)
                }
                true
            }
            // Search and selection toolbars are inflated lazily by the older wrapper.
            // Leave their stubs in place, then move each real toolbar after inflation.
            collapsing.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ -> moveToolbars() }
        }
    }

    private fun descendants(root: ViewGroup): Sequence<View> = sequence {
        for (child in root.children) {
            yield(child)
            if (child is ViewGroup) yieldAll(descendants(child))
        }
    }
}
