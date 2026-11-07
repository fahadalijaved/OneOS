package com.fahadali.oneos.shared

import android.text.SpannableString
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.widget.PopupMenu
import dev.oneuiproject.oneui.widget.RoundedLinearLayout
import dev.oneuiproject.oneui.widget.SwitchItemView

/** Shared SESL card: compact information, independent switch and long-press actions. */
object ModuleCards {
    fun add(parent: LinearLayout, name: String, description: String?, checked: Boolean,
        enabled: Boolean, color: Int, version: String = "", author: String = "", status: String? = null,
        toggleEnabled: Boolean = true, options: List<Pair<String, () -> Unit>> = emptyList(),
        onToggle: (Boolean) -> Unit): View {
        val ctx=parent.context
        fun dp(n:Int)=(n*ctx.resources.displayMetrics.density+.5f).toInt()
        val card=RoundedLinearLayout(ctx).apply {
            orientation=LinearLayout.VERTICAL;setBackgroundColor(color)
            roundedCorners=androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_ALL
            val value=android.util.TypedValue()
            ctx.theme.resolveAttribute(androidx.appcompat.R.attr.roundedCornerColor,value,true)
            roundedCornersColor=value.data;fillHorizontalPadding=false
        }
        parent.addView(card,LinearLayout.LayoutParams(-1,-2).apply { if(parent.childCount>0)topMargin=dp(12) })
        val summary=listOfNotNull(description?.takeIf { it.isNotBlank() },version.takeIf { it.isNotBlank() }?.let { "Version: $it" },
            author.takeIf { it.isNotBlank() }?.let { "Author: $it" },status?.takeIf { it.isNotBlank() }).joinToString("\n")
        val row=SwitchItemView(ctx).apply {
            title=name;summaryOn=summary;summaryOff=summary
            showTopDivider=false;showBottomDivider=false
            separateSwitch=true;isChecked=checked;isEnabled=enabled
            setSwitchEnabled(enabled && toggleEnabled)
            findViewById<View>(dev.oneuiproject.oneui.design.R.id.vertical_divider).visibility=View.GONE
            findViewById<TextView>(dev.oneuiproject.oneui.design.R.id.switch_card_title).textSize=18f
            findViewById<TextView>(dev.oneuiproject.oneui.design.R.id.switch_card_summary)?.apply {
                textSize=14f;maxLines=Int.MAX_VALUE;ellipsize=null
                setLineSpacing(dp(2).toFloat(),1f)
            }
            val content=findViewById<View>(dev.oneuiproject.oneui.design.R.id.content_frame)
            // Consume ordinary row clicks. Only the switch changes the disable flag.
            content.setOnClickListener { }
            if(options.isNotEmpty()) content.setOnLongClickListener { anchor ->
                if(!enabled) return@setOnLongClickListener false
                PopupMenu(ctx,anchor,Gravity.END).apply {
                    options.forEachIndexed { index,option ->
                        val label=if(option.first.startsWith("Uninstall")) {
                            val value=android.util.TypedValue()
                            ctx.theme.resolveAttribute(android.R.attr.colorError,value,true)
                            SpannableString(option.first).apply { setSpan(ForegroundColorSpan(value.data),0,length,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE) }
                        } else option.first
                        menu.add(0,index,index,label)
                    }
                    setOnMenuItemClickListener { item -> options[item.itemId].second();true }
                    show()
                }
                true
            }
            onCheckedChangedListener={ _,value -> onToggle(value) }
        }
        card.addView(row,LinearLayout.LayoutParams(-1,-2))
        return row
    }
}
