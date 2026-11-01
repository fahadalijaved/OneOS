package com.fahadali.oneos.ui

import android.content.Context
import android.content.res.ColorStateList
import android.os.Bundle
import android.os.Environment
import android.os.StatFs
import android.text.format.DateFormat
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.CheckBox
import android.widget.CompoundButton
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.annotation.DrawableRes
import androidx.annotation.StyleRes
import androidx.appcompat.widget.AppCompatCheckBox
import androidx.appcompat.widget.SeslProgressBar
import androidx.appcompat.widget.SwitchCompat
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.Level
import java.util.Date
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * A screen behind Advanced in the redesign's card look (docs/app/redesign-2.md):
 * One UI cards in one scrolling column (oneos_cards_screen) under the
 * screen's collapsing bar. [build] adds every card; [redraw] empties the
 * column and builds it again (from the jobs' states, as the old preference
 * screens did). [details] is the shared "Details" row that opens the
 * technical rows below it; the OneOS team's entry opens a screen with it open.
 */
abstract class CardsFragment : Fragment() {
    /** Details (the technical rows) are open; kept across recreation. */
    protected var detailsOpen = false

    /** Details start open (the screen was opened from For the OneOS team). */
    protected open val detailsOpenAtStart: Boolean get() = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        detailsOpen = savedInstanceState?.getBoolean(KEY_DETAILS) ?: detailsOpenAtStart
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View =
        inflater.inflate(R.layout.oneos_cards_screen, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        redraw()
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putBoolean(KEY_DETAILS, detailsOpen)
    }

    /** Adds the screen's cards to [column] (empty). */
    protected abstract fun build(column: LinearLayout)

    fun redraw() {
        if (!isAdded) return
        val column = view?.findViewById<LinearLayout>(R.id.oneos_cards_column) ?: return
        column.removeAllViews()
        build(column)
    }

    /** The "Details" row in [card] (a list card); when open, [fill] adds the technical rows below it. */
    protected fun details(card: LinearLayout, summary: CharSequence?, fill: (LinearLayout) -> Unit) {
        val row = Cards.row(card, OuiIcons.drawable.ic_oui_info_outline, getString(R.string.advanced_details), summary) {
            detailsOpen = !detailsOpen
            redraw()
        }
        CardRows.expandable(row, detailsOpen)
        if (detailsOpen) fill(card)
    }

    private companion object {
        const val KEY_DETAILS = "details_open"
    }
}

/** Rows and pieces the card screens share, on top of [Cards]. */
internal object CardRows {
    private const val DISABLED_ALPHA = 0.4f

    /** A paragraph in [card]. In a list card ([inList]) it gets the rows' side padding. */
    fun text(card: LinearLayout, text: CharSequence, @StyleRes style: Int = R.style.OneOS_Text_Body, inList: Boolean = false): TextView {
        val t = TextView(card.context)
        t.setTextAppearance(style)
        t.text = text
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        if (inList) {
            val h = card.resources.getDimension(R.dimen.oneos_row_padding_horizontal).toInt()
            t.setPaddingRelative(h, dp(card.context, 6), h, dp(card.context, 10))
        } else if (card.childCount > 1) {
            // Child 0 is the card's header; something is above this text already.
            lp.topMargin = dp(card.context, 8)
        }
        card.addView(t, lp)
        return t
    }

    /** A row with a line icon; off when not [enabled] (dimmed, no tap). */
    fun row(
        card: LinearLayout,
        @DrawableRes icon: Int,
        title: CharSequence,
        summary: CharSequence?,
        enabled: Boolean = true,
        onClick: ((View) -> Unit)? = null,
    ): View {
        val row = Cards.row(card, icon, title, summary, if (enabled) onClick else null)
        if (!enabled) row.alpha = DISABLED_ALPHA
        return row
    }

    /** A row whose icon is [level]'s filled badge (the badge keeps its own colours). */
    fun status(card: LinearLayout, level: Level, title: CharSequence, summary: CharSequence?, onClick: ((View) -> Unit)? = null): View {
        val row = Cards.row(card, Cards.badge(level), title, summary, onClick)
        (row as dev.oneuiproject.oneui.widget.CardItemView).getIconImageView().imageTintList = null
        return row
    }

    /** A gate's finding as it is (title and technical detail), for the OneOS team's screens. */
    fun finding(card: LinearLayout, f: Finding): View = status(card, f.level, f.title, f.detail.ifEmpty { null })

    /** Tints [row]'s icon by [level] (a check that runs, a copy in use). */
    fun tint(row: View, level: Level): View {
        (row as dev.oneuiproject.oneui.widget.CardItemView).getIconImageView().imageTintList = ColorStateList.valueOf(Cards.levelColor(row.context, level))
        return row
    }

    /** Colours [row]'s title (the main action). */
    fun titleColor(row: View, color: Int): View {
        (row as dev.oneuiproject.oneui.widget.CardItemView).getTitleView().setTextColor(row.context.getColor(color))
        return row
    }

    /** The chevron and TalkBack's state of a row that opens and closes what is below it. */
    fun expandable(row: View, open: Boolean) {
        row.stateDescription = row.context.getString(if (open) R.string.setup_expanded else R.string.setup_collapsed)
        Cards.setRowEnd(row, if (open) OuiIcons.drawable.ic_oui_keyboard_arrow_up else OuiIcons.drawable.ic_oui_keyboard_arrow_down)
    }

    /** A box to tick; the whole row is the tap target. [onChange] gets the new state. */
    fun tick(card: LinearLayout, title: CharSequence, summary: CharSequence?, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit): View =
        compound(card, AppCompatCheckBox(card.context), CheckBox::class.java.name, title, summary, checked, enabled, onChange)

    /** An on/off row (the One UI switch); the whole row is the tap target. Not saved: the screen keeps it. */
    fun toggle(card: LinearLayout, title: CharSequence, summary: CharSequence?, on: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit): View {
        val previous = card.getChildAt(card.childCount - 1)
        return dev.oneuiproject.oneui.widget.SwitchItemView(card.context).apply {
            this.title = title
            summaryOn = summary
            summaryOff = summary
            separateSwitch = false
            isChecked = on
            isEnabled = enabled
            showTopDivider = previous is dev.oneuiproject.oneui.widget.CardItemView ||
                previous is dev.oneuiproject.oneui.widget.SwitchItemView
            onCheckedChangedListener = { _, checked -> onChange(checked) }
            card.addView(this, LinearLayout.LayoutParams(-1, -2))
        }
    }

    private fun compound(
        card: LinearLayout,
        box: CompoundButton,
        role: String,
        title: CharSequence,
        summary: CharSequence?,
        checked: Boolean,
        enabled: Boolean,
        onChange: (Boolean) -> Unit,
    ): View {
        val row = Cards.row(card, 0, title, summary, null) as LinearLayout
        box.isChecked = checked
        box.isEnabled = enabled
        box.isClickable = false
        box.isFocusable = false
        box.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        val end = (row as dev.oneuiproject.oneui.widget.CardItemView).getEndImageView()
        val content = end.parent as ViewGroup
        box.id = end.id
        val endParams = end.layoutParams
        content.removeView(end)
        content.addView(box, endParams)

        // TalkBack reads the row as the box: its title, summary and state.
        row.accessibilityDelegate = object : View.AccessibilityDelegate() {
            override fun onInitializeAccessibilityNodeInfo(host: View, info: AccessibilityNodeInfo) {
                super.onInitializeAccessibilityNodeInfo(host, info)
                info.className = role
                info.isCheckable = true
                @Suppress("DEPRECATION") info.setChecked(box.isChecked)
            }
        }
        if (enabled) {
            row.setOnClickListener {
                box.isChecked = !box.isChecked
                onChange(box.isChecked)
            }
            row.isFocusable = true
        } else {
            row.alpha = DISABLED_ALPHA
        }
        return row
    }

    /** Value-and-label tiles (home_stat_tile) side by side in [card]: equal widths, 8dp apart. */
    fun stats(card: LinearLayout, tiles: List<Pair<CharSequence, CharSequence>>): LinearLayout {
        val ctx = card.context
        val line = LinearLayout(ctx)
        line.orientation = LinearLayout.HORIZONTAL
        line.isBaselineAligned = false
        val gap = card.resources.getDimension(R.dimen.oneos_tile_gap).toInt()
        val inflater = LayoutInflater.from(ctx)
        for ((i, t) in tiles.withIndex()) {
            val v = inflater.inflate(R.layout.home_stat_tile, line, false)
            v.findViewById<TextView>(R.id.home_stat_value).text = t.first
            v.findViewById<TextView>(R.id.home_stat_label).text = t.second
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f)
            if (i > 0) lp.marginStart = gap
            line.addView(v, lp)
        }
        val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        if (card.childCount > 1) lp.topMargin = dp(ctx, 12)
        card.addView(line, lp)
        return line
    }

    /** The One UI bar of how full the phone is ([usedPercent]) with [line] under it (oneos_storage_bar). */
    fun storageBar(card: LinearLayout, usedPercent: Int, line: CharSequence, description: CharSequence) {
        val ctx = card.context
        val v = LayoutInflater.from(ctx).inflate(R.layout.oneos_storage_bar, card, false)
        v.findViewById<SeslProgressBar>(R.id.oneos_storage_bar).apply {
            setMax(100)
            setProgress(usedPercent.coerceIn(0, 100))
            setProgressTintList(ColorStateList.valueOf(ctx.getColor(R.color.oneos_primary_text)))
            contentDescription = description
        }
        v.findViewById<TextView>(R.id.oneos_storage_line).text = line
        card.addView(v)
    }

    /** Free and total bytes of /data (no root, the same as the phone check), or null. */
    fun storage(): Pair<Long, Long>? = runCatching {
        val fs = StatFs(Environment.getDataDirectory().path)
        fs.availableBytes to fs.totalBytes
    }.getOrNull()?.takeIf { it.second > 0 }

    /** "Oct 24, 2026". */
    fun date(ctx: Context, wallMs: Long): String = DateFormat.getMediumDateFormat(ctx).format(Date(wallMs))

    /** "Oct 24, 2026 14:02". */
    fun dateTime(ctx: Context, wallMs: Long): String = date(ctx, wallMs) + " " + DateFormat.getTimeFormat(ctx).format(Date(wallMs))

    private fun dp(ctx: Context, v: Int): Int = (v * ctx.resources.displayMetrics.density).toInt()
}
