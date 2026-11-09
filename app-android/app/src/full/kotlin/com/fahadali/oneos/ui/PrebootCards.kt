package com.fahadali.oneos.ui

import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import com.fahadali.oneos.R
import dev.oneuiproject.oneui.widget.CardItemView

/** Figma's grouped pre-boot cards, built from the existing SESL components. */
internal object PrebootCards {
    // Use the Settings category holder with SESL's internal adapter API.
    @android.annotation.SuppressLint("RestrictedApi")
    fun section(parent: LinearLayout, title: String? = null, gap: Boolean = parent.childCount > 0): LinearLayout {
        val ctx = parent.context
        if (title != null) {
            // Bind the actual SESL9 PreferenceCategory through its native adapter,
            // exactly as Settings does, including theme, padding and accessibility.
            val theme = android.util.TypedValue()
            ctx.theme.resolveAttribute(androidx.preference.R.attr.preferenceTheme, theme, true)
            val themed = androidx.appcompat.view.ContextThemeWrapper(ctx,
                theme.resourceId.takeIf { it != 0 } ?: androidx.preference.R.style.PreferenceThemeOverlay)
            val screen = androidx.preference.PreferenceManager(themed).createPreferenceScreen(themed)
            screen.addPreference(androidx.preference.PreferenceCategory(themed).apply { this.title = title })
            val adapter = androidx.preference.PreferenceGroupAdapter(screen)
            val holder = adapter.onCreateViewHolder(parent, adapter.getItemViewType(0))
            adapter.onBindViewHolder(holder, 0)
            parent.addView(holder.itemView, LinearLayout.LayoutParams(-1, -2))
        }
        return Cards.section(parent, null, rows = true, gapAbove = false).apply {
            setBackgroundColor(ctx.getColor(R.color.preboot_card))
            if (title == null && gap) (layoutParams as ViewGroup.MarginLayoutParams).topMargin = dp(this, 20)
        }
    }
    fun row(card: LinearLayout, title: CharSequence, summary: CharSequence? = null, chevron: Boolean = false,
        enabled: Boolean = true, onClick: ((View) -> Unit)? = null): View =
        Cards.row(card, 0, title, summary, onClick).also { view ->
            val item = view as CardItemView
            item.minimumHeight = dp(view, if (summary.isNullOrBlank()) 52 else 73)
            item.getTitleView().textSize = 18f
            item.getSummaryView().apply { textSize = 14f; setTextColor(context.getColor(R.color.preboot_secondary)) }
            view.isEnabled = enabled
            if (chevron) Cards.setRowEnd(view, dev.oneuiproject.oneui.R.drawable.ic_oui_keyboard_arrow_right)
        }
    fun dp(view: View, value: Int): Int = (value * view.resources.displayMetrics.density + .5f).toInt()
}
