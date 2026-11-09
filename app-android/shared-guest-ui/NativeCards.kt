package com.fahadali.oneos.shared

import android.widget.LinearLayout
import dev.oneuiproject.oneui.widget.CardItemView
import dev.oneuiproject.oneui.widget.RoundedLinearLayout

object NativeCards {
    // Render the same SESL PreferenceCategory holder used by Settings.
    @android.annotation.SuppressLint("RestrictedApi")
    fun section(parent: LinearLayout, title: String?, color: Int): LinearLayout {
        val ctx = parent.context
        if (title != null) {
            val value = android.util.TypedValue()
            ctx.theme.resolveAttribute(androidx.preference.R.attr.preferenceTheme, value, true)
            val themed = androidx.appcompat.view.ContextThemeWrapper(ctx, value.resourceId.takeIf { it != 0 } ?: androidx.preference.R.style.PreferenceThemeOverlay)
            val screen = androidx.preference.PreferenceManager(themed).createPreferenceScreen(themed)
            screen.addPreference(androidx.preference.PreferenceCategory(themed).apply { this.title = title })
            val adapter = androidx.preference.PreferenceGroupAdapter(screen)
            val holder = adapter.onCreateViewHolder(parent, adapter.getItemViewType(0))
            adapter.onBindViewHolder(holder, 0)
            parent.addView(holder.itemView)
        }
        return RoundedLinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL; setBackgroundColor(color)
            roundedCorners = androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_ALL
            val value = android.util.TypedValue()
            ctx.theme.resolveAttribute(androidx.appcompat.R.attr.roundedCornerColor, value, true)
            roundedCornersColor = value.data; fillHorizontalPadding = false
            parent.addView(this, LinearLayout.LayoutParams(-1, -2))
        }
    }
    fun row(card: LinearLayout, title: String, summary: String? = null, click: (() -> Unit)? = null): CardItemView = CardItemView(card.context).apply {
        this.title = title; this.summary = summary
        showTopDivider = card.childCount > 0
        if (click != null) {
            getEndImageView().apply { setImageResource(dev.oneuiproject.oneui.R.drawable.ic_oui_keyboard_arrow_right); visibility = android.view.View.VISIBLE }
            setOnClickListener { click() }
        } else { isClickable = false; isFocusable = false }
        card.addView(this, LinearLayout.LayoutParams(-1, -2))
    }
}
