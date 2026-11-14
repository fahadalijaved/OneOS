package com.fahadali.oneos.ui

import android.app.Activity
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.LayoutInflater
import android.view.View
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.root.OldStage
import com.fahadali.oneos.session.OldStagesJob
import com.fahadali.oneos.session.RemoveJob

/**
 * Start fresh, Remove and Delete saved copy of one system (0.5.09): the confirmations and the
 * jobs behind them, shared by the system card's menu and the system's own screen.
 *
 * While a run goes, a dialog shows what root is doing and for how long (owner, 11-14: "deleting
 * should show some kinda progress ... people think app just isnt working"), then how it ended,
 * with OK. If that dialog's screen goes away first, the screen showing next reports the result
 * once ([showResult] / [takeResult]); while the dialog is up, they leave it to the dialog.
 */
internal object SystemManage {
    private enum class Waiting { NONE, REMOVE, DELETE, DELETE_ALL }

    private var waiting = Waiting.NONE
    private var removeKind: RemoveJob.Kind? = null
    private var savedName: String? = null
    private var dialogUp = false

    /** Whether a destructive item can run now (no other job uses root). */
    fun canRun(): Boolean = RemoveJob.canStart()

    /** [onDone] runs after the user closed the result (e.g. leave a screen whose system is gone). */
    fun confirmStartFresh(a: Activity, image: ImageRef, onDone: (Result) -> Unit = {}) {
        if (!guard(a)) return
        AlertDialog.Builder(a)
            .setTitle(a.getString(R.string.manage_start_fresh_title, image.name))
            .setMessage(a.getString(R.string.manage_start_fresh_message, image.name))
            .setPositiveButton(R.string.manage_start_fresh_run) { _, _ -> run(a, RemoveJob.Kind.DATA, image, onDone) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    fun confirmRemove(a: Activity, image: ImageRef, onDone: (Result) -> Unit = {}) {
        if (!guard(a)) return
        AlertDialog.Builder(a)
            .setTitle(a.getString(R.string.manage_remove_title, image.name))
            .setMessage(a.getString(R.string.manage_remove_message, image.name))
            .setPositiveButton(R.string.remove_confirm_run) { _, _ -> run(a, RemoveJob.Kind.SYSTEM, image, onDone) }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** The same job as Free up space's single delete, for the copy [savedCopy] holds of [image]. */
    fun confirmDeleteSaved(a: Activity, image: ImageRef, savedCopy: String, onDone: (Result) -> Unit = {}) {
        if (!guard(a)) return
        AlertDialog.Builder(a)
            .setTitle(R.string.space_delete_title)
            .setMessage(a.getString(R.string.manage_delete_saved_message, image.name))
            .setPositiveButton(R.string.space_delete_run) { _, _ ->
                if (!canRun()) { busy(a); return@setPositiveButton }
                waiting = Waiting.DELETE
                savedName = "Saved ${image.name}"
                OldStagesJob.delete(a, OldStage(savedCopy, 0, image.id, hasData = true, busy = false))
                progress(a, a.getString(R.string.manage_progress_deleting_saved, image.name), onDone)
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    /** Free up space's single delete, after its own confirmation: the same progress dialog. */
    fun deleteCopy(a: Activity, stage: OldStage, label: String) {
        if (!canRun()) { busy(a); return }
        waiting = Waiting.DELETE
        savedName = label
        OldStagesJob.delete(a, stage)
        progress(a, a.getString(R.string.manage_progress_deleting_copy, label)) {}
    }

    /** Free up space's Delete all, after its own confirmation. */
    fun deleteAllCopies(a: Activity) {
        if (!canRun()) { busy(a); return }
        waiting = Waiting.DELETE_ALL
        OldStagesJob.deleteAll(a)
        progress(a, a.getString(R.string.manage_progress_deleting_all)) {}
    }

    /** Advanced > Remove OneOS data, after its own confirmation. */
    fun removeAll(a: Activity) {
        if (!canRun()) { busy(a); return }
        waiting = Waiting.REMOVE
        removeKind = RemoveJob.Kind.ALL
        RemoveJob.start(a, RemoveJob.Kind.ALL)
        progress(a, a.getString(R.string.remove_running).trimEnd('…')) {}
    }

    private fun run(a: Activity, kind: RemoveJob.Kind, image: ImageRef, onDone: (Result) -> Unit) {
        if (!canRun()) { busy(a); return }
        waiting = Waiting.REMOVE
        removeKind = kind
        RemoveJob.start(a, kind, image.name)
        val title = when (kind) {
            RemoveJob.Kind.DATA -> a.getString(R.string.manage_progress_erasing, image.name)
            else -> a.getString(R.string.manage_progress_removing, image.name)
        }
        progress(a, title, onDone)
    }

    private fun guard(a: Activity): Boolean {
        if (canRun()) return true
        busy(a)
        return false
    }

    private fun busy(a: Activity) = Toast.makeText(a, R.string.manage_busy, Toast.LENGTH_LONG).show()

    /** The step root is on and when the run started, for the job [waiting] is on. */
    private var allSince = 0L
    private fun running(): Pair<String?, Long> = when (waiting) {
        Waiting.DELETE -> OldStagesJob.state.let { it.step to it.startedAt }
        Waiting.DELETE_ALL -> OldStagesJob.state.let { s ->
            if (allSince == 0L) allSince = SystemClock.elapsedRealtime()
            s.batch?.let { (i, n) -> "Deleting copy $i of $n…" } to allSince
        }
        else -> RemoveJob.state.let { it.step to it.startedAt }
    }

    private fun elapsed(since: Long): String {
        val s = ((SystemClock.elapsedRealtime() - since) / 1000).coerceAtLeast(0)
        return String.format(java.util.Locale.ROOT, "%d:%02d", s / 60, s % 60)
    }

    private fun progress(a: Activity, title: String, onDone: (Result) -> Unit) {
        val view = LayoutInflater.from(a).inflate(R.layout.manage_progress, null)
        val spinner = view.findViewById<View>(R.id.manage_progress_spinner)
        val step = view.findViewById<TextView>(R.id.manage_progress_step)
        val time = view.findViewById<TextView>(R.id.manage_progress_time)
        val handler = Handler(Looper.getMainLooper())
        val since = SystemClock.elapsedRealtime()
        val dialog = AlertDialog.Builder(a)
            .setTitle(title)
            .setView(view)
            .setCancelable(false)
            // One button (a hidden second one left SESL's divider line beside it, 11-14): Hide while it runs
            // (never trapped behind a dialog if root takes long; the screen showing when it ends reports how
            // it went), OK once it ended.
            .setPositiveButton(R.string.manage_progress_hide, null)
            .create()
        val tick = object : Runnable {
            override fun run() {
                val r = take()
                // The dialog's own start: a job's state can be replaced when it ends (Free up space lists the
                // copies again with a fresh state, startedAt 0: "Took 3580:56", the time since the phone started, 11-14).
                val now = running().first
                if (r == null) {
                    step.text = now ?: a.getString(R.string.manage_progress_starting)
                    time.text = a.getString(R.string.manage_progress_time, elapsed(since))
                    handler.postDelayed(this, 500)
                    return
                }
                spinner.visibility = View.GONE
                dialog.setTitle(if (r.failed) a.getString(R.string.environment_manage_failed) else a.getString(R.string.manage_progress_done))
                step.text = r.message
                time.text = a.getString(R.string.manage_progress_took, elapsed(since))
                dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.apply {
                    setText(android.R.string.ok)
                    setOnClickListener { dialog.dismiss(); onDone(r) }
                }
            }
        }
        dialog.setOnShowListener { handler.post(tick) }
        dialog.setOnDismissListener {
            handler.removeCallbacks(tick)
            dialogUp = false
        }
        dialogUp = true
        dialog.show()
    }

    /** The outcome of the run this app started, once it ended (one call gets it); null while it runs or when none is waiting. */
    class Result(val message: String, val failed: Boolean, val systemRemoved: Boolean)

    /** For screens: null while the progress dialog is up (it shows the result itself). */
    fun takeResult(): Result? = if (dialogUp) null else take()

    private fun take(): Result? {
        when (waiting) {
            Waiting.NONE -> return null
            Waiting.REMOVE -> {
                val s = RemoveJob.state
                if (s.busy || s.phase == RemoveJob.Phase.IDLE) return null
                waiting = Waiting.NONE
                val failed = s.phase == RemoveJob.Phase.FAILED
                return Result(s.message.orEmpty(), failed, !failed && removeKind == RemoveJob.Kind.SYSTEM)
            }
            Waiting.DELETE_ALL -> {
                val s = OldStagesJob.state
                if (s.busy || (s.phase != OldStagesJob.Phase.DONE && s.phase != OldStagesJob.Phase.FAILED)) return null
                waiting = Waiting.NONE
                allSince = 0L
                return Result(s.message.orEmpty(), s.phase == OldStagesJob.Phase.FAILED, false)
            }
            Waiting.DELETE -> {
                val s = OldStagesJob.state
                if (s.busy || (s.phase != OldStagesJob.Phase.DONE && s.phase != OldStagesJob.Phase.FAILED)) return null
                waiting = Waiting.NONE
                // The job's own line names the copy's folder (oneos.old-<time>); the card knows the system.
                val freed = s.freedKib?.let { OldStagesJob.gib(it) }
                val line = if (s.deleteFailed || freed == null) s.message.orEmpty() else "${savedName?.replaceFirstChar { it.uppercase() }} deleted: $freed freed."
                return Result(line, s.deleteFailed, false)
            }
        }
    }

    /** Toasts [takeResult]; returns it. */
    fun showResult(a: Activity): Result? = takeResult()?.also {
        if (it.message.isNotEmpty()) Toast.makeText(a.applicationContext, it.message, Toast.LENGTH_LONG).show()
    }
}
