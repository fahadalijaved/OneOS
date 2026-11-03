package com.fahadali.oneos.ui

import android.content.Context
import android.content.res.ColorStateList
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.annotation.ColorInt
import androidx.annotation.DrawableRes
import androidx.annotation.LayoutRes
import dev.oneuiproject.oneui.widget.CardItemView
import dev.oneuiproject.oneui.widget.RoundedLinearLayout
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Level

/**
 * The redesign's shared pieces (docs/app/redesign-2.md): One UI cards, check
 * tiles and rows from res/layout/oneos_*.xml, coloured by [Level].
 *
 * ```
 * val checks = Cards.section(column, "Your phone is ready", "4 of 4 checks", Level.OK)
 * Cards.tileGrid(checks, listOf(Cards.Tile(R.drawable.ic_oneos_check_root, "Root", value)))
 * val more = Cards.section(column, title = null, rows = true)
 * Cards.row(more, R.drawable.ic_oneos_row_advanced, "Advanced", summary) { openAdvanced() }
 * ```
 */
internal object Cards {

    /** One check tile. [icon] is a line icon such as R.drawable.ic_oneos_check_root; it is tinted by [level]. */
    data class Tile(
        @DrawableRes val icon: Int,
        val title: CharSequence,
        val value: CharSequence,
        val level: Level = Level.OK,
    )

    /** Text and icon colour for [level] on a card or a tile (4.5:1 or more in both modes). */
    @ColorInt
    fun levelColor(ctx: Context, level: Level): Int = ctx.getColor(
        when (level) {
            Level.OK -> R.color.oneos_ok_text
            Level.WARN -> R.color.oneos_warn_text
            Level.BLOCK -> R.color.oneos_block_text
            Level.INFO -> R.color.oneos_text_secondary
        },
    )

    /** A check tile's background for [level]: the plain tile, or a light orange / red tint. */
    @ColorInt
    fun tileColor(ctx: Context, level: Level): Int = ctx.getColor(
        when (level) {
            Level.WARN -> R.color.oneos_tile_bg_warn
            Level.BLOCK -> R.color.oneos_tile_bg_block
            Level.OK, Level.INFO -> R.color.oneos_tile_bg
        },
    )

    /** The filled status badge for [level] (24dp): tick, "!", cross or "i". */
    @DrawableRes
    fun badge(level: Level): Int = when (level) {
        Level.OK -> R.drawable.oneos_badge_ok
        Level.WARN -> R.drawable.oneos_badge_warn
        Level.BLOCK -> R.drawable.oneos_badge_block
        Level.INFO -> R.drawable.oneos_badge_info
    }

    /** The worst of [levels] (BLOCK, then WARN, then OK, then INFO); OK when empty. */
    fun worst(levels: Iterable<Level>): Level = levels.maxByOrNull { rank(it) } ?: Level.OK

    private fun rank(level: Level): Int = when (level) {
        Level.INFO -> 0
        Level.OK -> 1
        Level.WARN -> 2
        Level.BLOCK -> 3
    }

    // Cards ==================================================================

    /**
     * Adds a card (oneos_card_section) to [parent] and returns it; add its
     * content with addView, below the header. A null [title] and [trailing]
     * hide the header. [rows] = true makes it a list card for [row] items
     * (rows reach the card's edges). [gapAbove] puts the 12dp card gap above it.
     */
    fun section(
        parent: ViewGroup,
        title: CharSequence?,
        trailing: CharSequence? = null,
        trailingLevel: Level = Level.OK,
        rows: Boolean = false,
        gapAbove: Boolean = parent.childCount > 0,
    ): LinearLayout {
        val card = inflate(parent, R.layout.oneos_card_section) as LinearLayout
        round(card)
        val res = card.resources
        if (rows) {
            // CardItemView owns the SESL row's vertical and horizontal spacing.
            card.setPaddingRelative(0, 0, 0, 0)
            val h = res.getDimensionPixelSize(R.dimen.oneos_row_padding_horizontal)
            val header = card.findViewById<View>(R.id.oneos_section_header)
            header.setPaddingRelative(h, res.getDimensionPixelSize(R.dimen.oneos_tile_padding), h, 0)
            (header.layoutParams as? ViewGroup.MarginLayoutParams)?.bottomMargin = 0
        }
        if (gapAbove) {
            (card.layoutParams as? ViewGroup.MarginLayoutParams)?.topMargin = res.getDimensionPixelSize(R.dimen.oneos_card_gap)
        }
        bindSection(card, title, trailing, trailingLevel)
        parent.addView(card)
        return card
    }

    /** Sets a [section] card's header: title, and the trailing status in [trailingLevel]'s colour. */
    fun bindSection(card: View, title: CharSequence?, trailing: CharSequence?, trailingLevel: Level = Level.OK) {
        val header = card.findViewById<View>(R.id.oneos_section_header)
        val titleView = card.findViewById<TextView>(R.id.oneos_section_title)
        val trailingView = card.findViewById<TextView>(R.id.oneos_section_trailing)
        header.visibility = if (title.isNullOrEmpty() && trailing.isNullOrEmpty()) View.GONE else View.VISIBLE
        titleView.text = title
        trailingView.text = trailing
        trailingView.visibility = if (trailing.isNullOrEmpty()) View.GONE else View.VISIBLE
        trailingView.setTextColor(levelColor(card.context, trailingLevel))
    }

    // Check tiles ============================================================

    /** Adds a grid of check tiles to [parent] ([columns] per line, 8dp gaps, equal heights per line) and returns it. */
    fun tileGrid(parent: ViewGroup, tiles: List<Tile>, columns: Int = 2): LinearLayout {
        val grid = LinearLayout(parent.context)
        grid.orientation = LinearLayout.VERTICAL
        parent.addView(grid, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        setTiles(grid, tiles, columns)
        return grid
    }

    /** Replaces the tiles of a grid made by [tileGrid]. */
    fun setTiles(grid: LinearLayout, tiles: List<Tile>, columns: Int = 2) {
        require(columns >= 1) { "columns must be 1 or more" }
        grid.removeAllViews()
        val gap = grid.resources.getDimensionPixelSize(R.dimen.oneos_tile_gap)
        tiles.chunked(columns).forEachIndexed { i, line ->
            val row = LinearLayout(grid.context)
            row.orientation = LinearLayout.HORIZONTAL
            val rowLp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            if (i > 0) rowLp.topMargin = gap
            grid.addView(row, rowLp)
            for (c in 0 until columns) {
                val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f)
                if (c > 0) lp.marginStart = gap
                val tile = line.getOrNull(c)
                if (tile == null) {
                    row.addView(View(grid.context), lp)
                } else {
                    val v = inflate(row, R.layout.oneos_check_tile)
                    bindCheckTile(v, tile)
                    row.addView(v, lp)
                }
            }
        }
    }

    /** Inflates one check tile (not attached; for a custom arrangement). */
    fun checkTile(parent: ViewGroup, tile: Tile): View {
        val v = inflate(parent, R.layout.oneos_check_tile)
        bindCheckTile(v, tile)
        return v
    }

    /** Sets a check tile's icon, name and value, and tints the icon and the tile by its level. */
    fun bindCheckTile(view: View, tile: Tile) {
        val ctx = view.context
        val icon = view.findViewById<ImageView>(R.id.oneos_tile_icon)
        if (tile.icon == 0) {
            icon.visibility = View.GONE
        } else {
            icon.visibility = View.VISIBLE
            icon.setImageResource(tile.icon)
            icon.imageTintList = ColorStateList.valueOf(levelColor(ctx, tile.level))
        }
        view.findViewById<TextView>(R.id.oneos_tile_title).text = tile.title
        view.findViewById<TextView>(R.id.oneos_tile_value).text = tile.value
        view.backgroundTintList = ColorStateList.valueOf(tileColor(ctx, tile.level))
    }

    // Rows ===================================================================

    /**
     * Adds a row (oneos_row) to [parent], normally a list card from
     * section(rows = true), and returns it. [icon] 0 hides the icon; a null
     * [onClick] makes the row plain, not tappable.
     */
    fun row(
        parent: ViewGroup,
        @DrawableRes icon: Int,
        title: CharSequence,
        summary: CharSequence? = null,
        onClick: ((View) -> Unit)? = null,
    ): View {
        val v = CardItemView(parent.context)
        bindRow(v, icon, title, summary, onClick)
        val previous = parent.getChildAt(parent.childCount - 1)
        v.showTopDivider = previous is CardItemView || previous is dev.oneuiproject.oneui.widget.SwitchItemView
        parent.addView(v, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        return v
    }

    /** Sets a row's icon, title, summary (hidden when empty) and click action. */
    fun bindRow(
        row: View,
        @DrawableRes icon: Int,
        title: CharSequence,
        summary: CharSequence?,
        onClick: ((View) -> Unit)?,
    ) {
        val item = row as CardItemView
        item.title = title
        item.summary = summary
        item.icon = if (icon == 0) null else androidx.appcompat.content.res.AppCompatResources.getDrawable(row.context, icon)

        if (onClick == null) {
            row.setOnClickListener(null)
            row.isClickable = false
            row.isFocusable = false
        } else {
            row.setOnClickListener { onClick(it) }
            row.isClickable = true
            row.isFocusable = true
        }
    }

    /** Shows [drawable] (for example [badge]) at the row's end; 0 hides it. */
    fun setRowEnd(row: View, @DrawableRes drawable: Int) {
        val end = (row as CardItemView).getEndImageView()
        if (drawable == 0) {
            end.visibility = View.GONE
            end.setImageDrawable(null)
        } else {
            end.setImageResource(drawable)
            end.visibility = View.VISIBLE
        }
    }

    /** Stock oneui-design corner renderer, matching SESL preference cards. */
    fun round(card: LinearLayout) {
        (card as? RoundedLinearLayout)?.apply {
            roundedCorners = androidx.appcompat.util.SeslRoundedCorner.ROUNDED_CORNER_ALL
            val color = android.util.TypedValue()
            context.theme.resolveAttribute(androidx.appcompat.R.attr.roundedCornerColor, color, true)
            roundedCornersColor = color.data
            fillHorizontalPadding = false
        }
    }

    private fun inflate(parent: ViewGroup, @LayoutRes layout: Int): View =
        LayoutInflater.from(parent.context).inflate(layout, parent, false)
}
