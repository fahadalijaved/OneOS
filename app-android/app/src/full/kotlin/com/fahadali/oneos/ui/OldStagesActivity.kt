package com.fahadali.oneos.ui

import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.OldStage
import com.fahadali.oneos.session.OldStagesJob
import com.fahadali.oneos.session.StageCheck
import dev.oneuiproject.oneui.R as OuiIcons

/**
 * Free up space (Advanced, and the fix "Free up space"): how full the phone
 * is, the size of the system set up now, and the old copies setup kept
 * (oneos.old-<time>; lineage_stage.old-<time> up to 0.3.6) with what deleting
 * them frees. Delete is one copy at a time, after a confirmation; root
 * deletes only such a folder, and only when nothing is mounted, bridged or
 * running in it. A copy of a known system can also be used again (0.4.10,
 * root `restore`): the system set up now becomes an old copy in its place.
 * The folder names and root's reasons are under Details.
 */
class OldStagesActivity : ToolbarActivity() {
    override val screenTitle: CharSequence get() = getString(R.string.space_title)

    override fun createFragment(): Fragment = OldStagesFragment()
}

class OldStagesFragment : CardsFragment() {
    private val subs = mutableListOf<() -> Unit>()

    override fun onStart() {
        super.onStart()
        subs += OldStagesJob.observe { redraw() }
        subs += StageCheck.observe { redraw() }
        if (!OldStagesJob.state.busy) OldStagesJob.refresh(requireContext())
    }

    override fun onStop() {
        subs.forEach { it() }
        subs.clear()
        super.onStop()
    }

    override fun build(column: LinearLayout) {
        val ctx = column.context
        val st = OldStagesJob.state
        val stages = st.stages
        val oldBytes = stages?.sumOf { it.kib }?.times(1024)

        // Storage: the bar, the system set up now, the old copies.
        val storage = Cards.section(column, getString(R.string.space_card_storage))
        CardRows.storage()?.let { (free, total) ->
            val used = ((total - free) * 100 / total).toInt()
            CardRows.storageBar(
                storage, used,
                getString(R.string.space_free_line, Units.bytes(free), Units.bytes(total)),
                getString(R.string.space_bar_desc, used),
            )
        }
        val tiles = mutableListOf<Pair<CharSequence, CharSequence>>()
        val now = StageCheck.state.result?.status?.takeIf { it.ours }
        val nowRaw = now?.rawSize
        if (now != null && nowRaw != null) {
            val system = Images.systemName(now.marker?.imageId?.let { Images.byId(it) })
            tiles += Units.bytes(nowRaw) to getString(R.string.space_system_label, system)
        }
        tiles += when {
            stages == null -> getString(R.string.space_value_unknown) to getString(R.string.space_old_label)
            stages.isEmpty() -> getString(R.string.space_value_none) to getString(R.string.space_old_label)
            else -> Units.bytes(oldBytes ?: 0) to resources.getQuantityString(R.plurals.advanced_space_copies, stages.size, stages.size)
        }
        CardRows.stats(storage, tiles)
        if (!stages.isNullOrEmpty() && oldBytes != null) {
            CardRows.text(storage, getString(R.string.space_frees, Units.bytes(oldBytes)), R.style.OneOS_Text_Caption)
        }

        // Old copies: one row each; a tap asks before it deletes.
        val list = Cards.section(column, getString(R.string.space_card_old), rows = true)
        CardRows.text(list, getString(R.string.space_old_line), R.style.OneOS_Text_Caption, inList = true)
        // 0.4.11: all of them at once, with one confirmation (the copies in use are left).
        val deletable = stages.orEmpty().filter { !it.busy }
        val batch = st.batch
        if (batch != null) {
            CardRows.tint(Cards.row(list, OuiIcons.drawable.ic_oui_delete_outline, getString(R.string.space_deleting_n, batch.first, batch.second), null), Level.INFO)
        } else if (deletable.size > 1 && !st.busy) {
            Cards.row(
                list, OuiIcons.drawable.ic_oui_delete_outline, getString(R.string.space_delete_all),
                getString(R.string.space_delete_all_summary, Units.bytes(deletable.sumOf { it.kib } * 1024)),
            ) { confirmDeleteAll(deletable) }
        }
        when {
            st.phase == OldStagesJob.Phase.LISTING ->
                CardRows.tint(Cards.row(list, OuiIcons.drawable.ic_oui_refresh, getString(R.string.space_listing), null), Level.INFO)
            stages == null -> CardRows.status(list, Level.WARN, getString(R.string.space_not_read), getString(R.string.space_not_read_line))
            stages.isEmpty() -> CardRows.status(list, Level.OK, getString(R.string.space_none), getString(R.string.space_none_summary))
            else -> for (s in stages) {
                val deleting = st.deleting == s.name
                val restoring = st.restoring == s.name
                // In use for a delete (a session since the restart) can still be used again: root decides.
                val usable = !s.busy || restorable(s)
                val row = CardRows.row(
                    list,
                    if (s.busy) OuiIcons.drawable.ic_oui_lock else OuiIcons.drawable.ic_oui_delete_outline,
                    when {
                        deleting -> getString(R.string.space_deleting)
                        restoring -> getString(R.string.space_restoring)
                        else -> copyTitle(s)
                    },
                    describe(s),
                    enabled = usable && (!st.busy || deleting || restoring),
                ) { if (!st.busy && usable) choose(s) }
                if (s.busy) CardRows.tint(row, Level.WARN)
                if (deleting || restoring) CardRows.tint(row, Level.INFO)
            }
        }
        // The last delete: what it freed, or that it did not happen; or that reading the copies
        // again failed (the list above is the one read before). Root's reason is under Details.
        if (!st.busy && st.stages != null && st.message != null) {
            val freed = st.freedKib
            when {
                st.phase == OldStagesJob.Phase.DONE && st.restored ->
                    CardRows.status(list, Level.OK, getString(R.string.space_restored), null)
                st.phase == OldStagesJob.Phase.FAILED && st.restoreFailed ->
                    CardRows.status(list, Level.WARN, getString(R.string.space_not_restored), getString(R.string.space_not_restored_line))
                st.phase == OldStagesJob.Phase.DONE && freed != null && st.deletedNames != null ->
                    CardRows.status(
                        list, Level.OK,
                        resources.getQuantityString(R.plurals.space_deleted_n, st.deletedNames.size, st.deletedNames.size, Units.bytes(freed * 1024)),
                        null,
                    )
                st.phase == OldStagesJob.Phase.DONE && freed != null ->
                    CardRows.status(list, Level.OK, getString(R.string.space_deleted, Units.bytes(freed * 1024)), null)
                st.phase == OldStagesJob.Phase.FAILED && st.deleteFailed ->
                    CardRows.status(list, Level.WARN, getString(R.string.space_not_deleted), getString(R.string.space_not_deleted_line))
                st.phase == OldStagesJob.Phase.FAILED ->
                    CardRows.status(list, Level.WARN, getString(R.string.space_not_read), getString(R.string.space_not_read_line))
            }
        }
        if (!st.busy) {
            Cards.row(list, OuiIcons.drawable.ic_oui_refresh, getString(R.string.space_check_again), null) { OldStagesJob.refresh(ctx) }
        }

        // Details: what root checks, the folder names, what root said.
        val more = Cards.section(column, title = null, rows = true)
        details(more, getString(R.string.space_details_summary)) { card ->
            CardRows.text(card, getString(R.string.space_details_rules), R.style.OneOS_Text_Caption, inList = true)
            stages?.forEach { s -> Cards.row(card, 0, s.name, getString(R.string.space_details_folder, OldStagesJob.gib(s.kib), s.imageId ?: "-")) }
            st.message?.let { Cards.row(card, 0, getString(R.string.setup_details_result), it) }
        }
    }

    /** "Old copy of {system}", or the copy a stopped delete left. */
    private fun copyTitle(s: OldStage): String {
        val name = s.imageId?.let { Images.byId(it) }?.name
        return when {
            s.isTrash -> getString(R.string.space_old_trash)
            name != null -> getString(R.string.space_old_of, name)
            else -> getString(R.string.space_old_unknown)
        }
    }

    /** "10.3 GB · kept since Oct 23, 2026 · with its apps and data". */
    private fun describe(s: OldStage): String {
        val parts = mutableListOf(Units.bytes(s.kib * 1024))
        since(s)?.let { parts += it }
        if (s.hasData) parts += getString(R.string.space_old_has_data)
        if (s.busy) parts += getString(R.string.space_old_in_use)
        return parts.joinToString(" · ")
    }

    /** "kept since Oct 23, 2026" ("left on" for an unfinished delete), when the folder name says. */
    private fun since(s: OldStage): String? = s.setAsideEpoch?.let { e ->
        getString(if (s.isTrash) R.string.space_old_stopped_since else R.string.space_old_kept_since, CardRows.date(requireContext(), e * 1000))
    }

    /** A copy of a system this build knows, set aside by setup (not a stopped delete). */
    private fun restorable(s: OldStage): Boolean = !s.isTrash && s.name.startsWith("oneos.old-") && s.imageId?.let { Images.byId(it) } != null

    /** Use again or delete; a copy that cannot be used again goes straight to the delete confirmation. */
    private fun choose(s: OldStage) {
        if (!restorable(s)) {
            if (!s.busy) confirmDelete(s)
            return
        }
        val items = mutableListOf(getString(R.string.space_choose_use) to { confirmRestore(s) })
        if (!s.busy) items += getString(R.string.space_choose_delete) to { confirmDelete(s) }
        AlertDialog.Builder(requireContext())
            .setTitle(getString(R.string.space_choose_title, copyTitle(s)))
            .setItems(items.map { it.first }.toTypedArray()) { _, i -> items[i].second() }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun confirmRestore(s: OldStage) {
        val name = s.imageId?.let { Images.byId(it) }?.name ?: return
        val sizeAndDate = listOfNotNull(Units.bytes(s.kib * 1024), since(s)).joinToString(", ")
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.space_restore_title)
            .setMessage(getString(R.string.space_restore_message, name, sizeAndDate))
            .setPositiveButton(R.string.space_restore_run) { _, _ -> OldStagesJob.restore(requireContext(), s) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun confirmDeleteAll(copies: List<OldStage>) {
        val what = resources.getQuantityString(R.plurals.space_delete_all_count, copies.size, copies.size)
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.space_delete_all_title)
            .setMessage(getString(R.string.space_delete_all_message, what, Units.bytes(copies.sumOf { it.kib } * 1024)))
            .setPositiveButton(R.string.space_delete_run) { _, _ -> activity?.let { SystemManage.deleteAllCopies(it) } }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun confirmDelete(s: OldStage) {
        val name = s.imageId?.let { Images.byId(it) }?.name
        val what = if (name != null && !s.isTrash) getString(R.string.space_delete_what_of, name) else getString(R.string.space_delete_what)
        // The size and the date tell two copies of the same system apart.
        val sizeAndDate = listOfNotNull(Units.bytes(s.kib * 1024), since(s)).joinToString(", ")
        AlertDialog.Builder(requireContext())
            .setTitle(R.string.space_delete_title)
            .setMessage(getString(R.string.space_delete_message, what, sizeAndDate))
            .setPositiveButton(R.string.space_delete_run) { _, _ -> activity?.let { SystemManage.deleteCopy(it, s, "$what ($sizeAndDate)") } }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }
}
