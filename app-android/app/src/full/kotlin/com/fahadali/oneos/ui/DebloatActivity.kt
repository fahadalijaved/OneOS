package com.fahadali.oneos.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Debloat
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.session.Debloater
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * Debloat (0.5.32, on each system's page under Apps, next to Bring apps). The overview: what the system's next
 * start leaves out (apps, space, how many take a feature with them), Review and Restore all, and the two lists
 * to choose from, each on its own page ([DebloatListActivity]): Safe to remove (green) and Remove with care
 * (orange). The ticks are kept per system ([Debloater]) and take effect at the system's next start: root gets
 * the list right before it, and guest_prepare.sh leaves those apps out. No root here, so it works whichever
 * system is set up now.
 */
class DebloatActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.debloat_title)

    override fun createFragment(): Fragment = DebloatFragment().apply {
        arguments = Bundle().apply { putString(EXTRA_IMAGE, intent.getStringExtra(EXTRA_IMAGE)) }
    }

    companion object {
        const val EXTRA_IMAGE = "image"

        fun intent(ctx: Context, image: ImageRef): Intent =
            Intent(ctx, DebloatActivity::class.java).putExtra(EXTRA_IMAGE, image.id)
    }
}

/** The lists the overview opens. */
enum class DebloatPage { SAFE, CAUTION, SELECTED }

/** One list of [DebloatPage]: the apps in groups (the maker's, Google's, partners' ...), each folded until opened. */
class DebloatListActivity : ToolbarActivity() {
    private val page: DebloatPage
        get() = runCatching { DebloatPage.valueOf(intent.getStringExtra(EXTRA_PAGE).orEmpty()) }.getOrDefault(DebloatPage.SAFE)

    override val screenTitle: CharSequence
        get() = getString(
            when (page) {
                DebloatPage.SAFE -> R.string.debloat_safe_title
                DebloatPage.CAUTION -> R.string.debloat_caution_title
                DebloatPage.SELECTED -> R.string.debloat_selected_title
            },
        )

    override fun createFragment(): Fragment = DebloatListFragment().apply {
        arguments = Bundle().apply {
            putString(DebloatActivity.EXTRA_IMAGE, intent.getStringExtra(DebloatActivity.EXTRA_IMAGE))
            putString(EXTRA_PAGE, page.name)
        }
    }

    companion object {
        const val EXTRA_PAGE = "page"

        fun intent(ctx: Context, imageId: String, page: DebloatPage): Intent =
            Intent(ctx, DebloatListActivity::class.java)
                .putExtra(DebloatActivity.EXTRA_IMAGE, imageId)
                .putExtra(EXTRA_PAGE, page.name)
    }
}

class DebloatFragment : CardsFragment() {
    private val imageId: String get() = requireArguments().getString(DebloatActivity.EXTRA_IMAGE).orEmpty()

    private var built = false

    override fun onResume() {
        super.onResume()
        // Back from a list: its ticks show here.
        if (built) redraw()
    }

    override fun build(column: LinearLayout) {
        built = true
        val ctx = column.context
        val system = Images.systemName(Images.byId(imageId))
        val apps = Debloater.apps(ctx, imageId)
        val hidden = Debloater.hidden(ctx, imageId)

        if (apps.isEmpty()) {
            CardRows.status(Cards.section(column, title = null, rows = true), Level.INFO, getString(R.string.debloat_no_list, system), null)
            about(column, system)
            return
        }

        // What the next start leaves out.
        val ticked = apps.filter { it.pkg in hidden }
        val cautionTicked = ticked.count { it.rating == Debloat.Rating.CAUTION }
        val summary = Cards.section(
            column, getString(R.string.debloat_next_start, system),
            trailing = if (ticked.isEmpty()) getString(R.string.debloat_trailing_none) else getString(R.string.debloat_trailing_set),
            trailingLevel = if (ticked.isEmpty()) Level.INFO else Level.OK,
        )
        CardRows.stats(
            summary,
            listOf(
                ticked.size.toString() to getString(R.string.debloat_stat_apps),
                Debloat.size(ticked.sumOf { it.kib }) to getString(R.string.debloat_stat_space),
                cautionTicked.toString() to getString(R.string.debloat_stat_caution),
            ),
        )
        CardRows.text(
            summary,
            getString(if (ticked.isEmpty()) R.string.debloat_summary_empty else R.string.debloat_summary_note, system),
            R.style.OneOS_Text_Caption,
        )
        if (ticked.isNotEmpty()) {
            val actions = Cards.section(column, title = null, rows = true)
            CardRows.row(
                actions, OuiIcons.drawable.ic_oui_selected, getString(R.string.debloat_review),
                resources.getQuantityString(R.plurals.debloat_review_summary, ticked.size, ticked.size),
            ) { open(DebloatPage.SELECTED) }.also { Cards.setRowEnd(it, OuiIcons.drawable.ic_oui_keyboard_arrow_right) }
            CardRows.row(actions, OuiIcons.drawable.ic_oui_undo, getString(R.string.debloat_restore), getString(R.string.debloat_restore_summary)) {
                AlertDialog.Builder(ctx)
                    .setTitle(R.string.debloat_restore)
                    .setMessage(getString(R.string.debloat_restore_confirm, system))
                    .setPositiveButton(R.string.debloat_restore_run) { _, _ -> Debloater.setHidden(ctx, imageId, emptySet()); redraw() }
                    .setNegativeButton(android.R.string.cancel, null)
                    .show()
            }
        }

        // The two lists, each on its own page.
        val choose = Cards.section(column, getString(R.string.debloat_card_choose), rows = true)
        val safe = apps.filter { it.rating == Debloat.Rating.SAFE }
        val caution = apps.filter { it.rating == Debloat.Rating.CAUTION }
        if (safe.isNotEmpty()) {
            CardRows.status(
                choose, Level.OK, getString(R.string.debloat_safe_title),
                listSummary(safe, hidden, R.string.debloat_safe_line),
            ) { open(DebloatPage.SAFE) }.also { Cards.setRowEnd(it, OuiIcons.drawable.ic_oui_keyboard_arrow_right) }
        }
        if (caution.isNotEmpty()) {
            CardRows.status(
                choose, Level.WARN, getString(R.string.debloat_caution_title),
                listSummary(caution, hidden, R.string.debloat_caution_line),
            ) { open(DebloatPage.CAUTION) }.also { Cards.setRowEnd(it, OuiIcons.drawable.ic_oui_keyboard_arrow_right) }
        }
        // 0.5.32 (owner: the old debloated ColorOS build ran smoother): every app MysticGSI's own debloat removes
        // from this system's builds, ticked or unticked at once; the lists above show each with what goes.
        val mystic = apps.filter { it.mystic }
        if (mystic.isNotEmpty()) {
            val n = mystic.count { it.pkg in hidden }
            CardRows.tick(
                choose, getString(R.string.debloat_mystic),
                resources.getQuantityString(R.plurals.debloat_mystic_summary, mystic.size, mystic.size,
                    mystic.count { it.rating == Debloat.Rating.CAUTION }, Debloat.size(mystic.sumOf { it.kib })),
                checked = n == mystic.size,
            ) { on ->
                val pkgs = mystic.map { it.pkg }.toSet()
                Debloater.setHidden(ctx, imageId, if (on) hidden + pkgs else hidden - pkgs)
                redraw()
            }
        }

        about(column, system)
    }

    /** "Nothing you use goes · 112 apps, 1.2 GB · 8 ticked". */
    private fun listSummary(list: List<Debloat.App>, hidden: Set<String>, line: Int): String {
        val n = list.count { it.pkg in hidden }
        val count = resources.getQuantityString(R.plurals.debloat_select_safe_n, list.size, list.size, Debloat.size(list.sumOf { it.kib }))
        val ticked = if (n > 0) resources.getQuantityString(R.plurals.debloat_ticked_n, n, n) else getString(R.string.debloat_none_ticked)
        return getString(line) + "\n" + count + " · " + ticked
    }

    private fun about(column: LinearLayout, system: String) {
        val about = Cards.section(column, getString(R.string.debloat_card_about))
        CardRows.text(about, getString(R.string.debloat_about_body, system))
        CardRows.text(about, getString(R.string.debloat_about_data, system), R.style.OneOS_Text_Caption)
    }

    private fun open(page: DebloatPage) = startActivity(DebloatListActivity.intent(requireContext(), imageId, page))
}

class DebloatListFragment : CardsFragment() {
    private val imageId: String get() = requireArguments().getString(DebloatActivity.EXTRA_IMAGE).orEmpty()
    private val page: DebloatPage
        get() = runCatching { DebloatPage.valueOf(requireArguments().getString(DebloatListActivity.EXTRA_PAGE).orEmpty()) }
            .getOrDefault(DebloatPage.SAFE)

    /** Groups opened (kept across recreation). */
    private val opened = HashSet<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        savedInstanceState?.getStringArrayList(KEY_OPENED)?.let { opened.addAll(it) }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putStringArrayList(KEY_OPENED, ArrayList(opened))
    }

    override fun build(column: LinearLayout) {
        val ctx = column.context
        val system = Images.systemName(Images.byId(imageId))
        val all = Debloater.apps(ctx, imageId)
        val hidden = Debloater.hidden(ctx, imageId)
        val apps = when (page) {
            DebloatPage.SAFE -> all.filter { it.rating == Debloat.Rating.SAFE }
            DebloatPage.CAUTION -> all.filter { it.rating == Debloat.Rating.CAUTION }
            DebloatPage.SELECTED -> all.filter { it.pkg in hidden }
        }
        val ticked = apps.filter { it.pkg in hidden }

        // What this list is.
        val banner = Cards.section(column, title = null, rows = true)
        when (page) {
            DebloatPage.SAFE -> {
                CardRows.status(banner, Level.OK, getString(R.string.debloat_safe_banner), getString(R.string.debloat_safe_banner_body, system))
                if (apps.isNotEmpty()) {
                    CardRows.tick(
                        banner, getString(R.string.debloat_select_safe),
                        resources.getQuantityString(R.plurals.debloat_select_safe_n, apps.size, apps.size, Debloat.size(apps.sumOf { it.kib })),
                        checked = ticked.size == apps.size,
                    ) { on -> set(hidden, apps, on) }
                }
            }
            DebloatPage.CAUTION ->
                CardRows.status(banner, Level.WARN, getString(R.string.debloat_caution_banner), getString(R.string.debloat_caution_banner_body))
            DebloatPage.SELECTED ->
                if (apps.isEmpty()) {
                    CardRows.status(banner, Level.OK, getString(R.string.debloat_none), getString(R.string.debloat_selected_empty, system))
                } else {
                    CardRows.status(
                        banner, Level.INFO,
                        resources.getQuantityString(R.plurals.debloat_status_n, apps.size, apps.size, Debloat.size(apps.sumOf { it.kib })),
                        getString(R.string.debloat_selected_body, system),
                    )
                }
        }

        // The apps, by who made them; a group folds until opened (Your selection shows every app).
        val groups = apps.groupBy { Debloat.group(it.pkg) }.toSortedMap()
        for ((group, list) in groups) {
            val n = list.count { it.pkg in hidden }
            val card = Cards.section(
                column, groupTitle(group, system),
                trailing = if (page == DebloatPage.SELECTED) list.size.toString() else getString(R.string.debloat_group_count, n, list.size),
                trailingLevel = when {
                    n == 0 || page == DebloatPage.SELECTED -> Level.INFO
                    page == DebloatPage.CAUTION -> Level.WARN
                    else -> Level.OK
                },
                rows = true,
            )
            val open = page == DebloatPage.SELECTED || groups.size == 1 || group.name in opened
            if (page != DebloatPage.SELECTED && groups.size > 1) {
                val row = Cards.row(
                    card, 0,
                    if (open) getString(R.string.debloat_group_hide) else resources.getQuantityString(R.plurals.debloat_group_show, list.size, list.size),
                    Debloat.size(list.sumOf { it.kib }),
                ) { if (!opened.remove(group.name)) opened.add(group.name); redraw() }
                CardRows.expandable(row, open)
            }
            if (page == DebloatPage.SAFE && list.size > 1) {
                CardRows.tick(card, getString(R.string.debloat_group_tick_all), null, checked = n == list.size) { on -> set(hidden, list, on) }
            }
            if (open) for (a in list) appRow(card, a, a.pkg in hidden)
        }
    }

    private fun groupTitle(group: Debloat.Group, system: String): String = when (group) {
        Debloat.Group.PARTNER -> getString(R.string.debloat_group_partner)
        Debloat.Group.MAKER -> getString(R.string.debloat_group_maker, system)
        Debloat.Group.GOOGLE -> getString(R.string.debloat_group_google)
        Debloat.Group.ANDROID -> getString(R.string.debloat_group_android)
        Debloat.Group.CHIP -> getString(R.string.debloat_group_chip)
    }

    private fun set(hidden: Set<String>, apps: List<Debloat.App>, on: Boolean) {
        val pkgs = apps.map { it.pkg }.toSet()
        Debloater.setHidden(requireContext(), imageId, if (on) hidden + pkgs else hidden - pkgs)
        redraw()
    }

    private fun appRow(card: LinearLayout, a: Debloat.App, checked: Boolean) {
        val ctx = card.context
        val caution = a.rating == Debloat.Rating.CAUTION
        val summary = if (caution) getString(R.string.debloat_row_caution, a.reason, Debloat.size(a.kib))
        else getString(R.string.debloat_row_summary, a.reason, Debloat.size(a.kib))
        val row = CardRows.tick(card, a.label, summary, checked) { on ->
            if (on && caution) {
                // A feature goes: say which, once more, before it is ticked.
                AlertDialog.Builder(ctx)
                    .setTitle(getString(R.string.debloat_caution_confirm_title, a.label))
                    .setMessage(getString(R.string.debloat_caution_confirm, a.reason))
                    .setPositiveButton(R.string.debloat_caution_confirm_run) { _, _ -> Debloater.toggle(ctx, imageId, a.pkg, true); redraw() }
                    .setNegativeButton(android.R.string.cancel, null)
                    .setOnDismissListener { redraw() }
                    .show()
            } else {
                Debloater.toggle(ctx, imageId, a.pkg, on)
                redraw()
            }
        }
        if (caution && page == DebloatPage.SELECTED) CardRows.titleColor(row, R.color.oneos_warn_text)
    }

    private companion object {
        const val KEY_OPENED = "opened"
    }
}
