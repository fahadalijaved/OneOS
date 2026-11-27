package com.fahadali.oneos.ui

import android.content.Intent
import android.content.res.ColorStateList
import android.os.Bundle
import android.os.SystemClock
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.widget.NestedScrollView
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.R
import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.model.OneiosUpdates
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.core.root.OneiosSteps
import com.fahadali.oneos.session.AppUpdater
import com.fahadali.oneos.session.OneiosAuto
import com.fahadali.oneos.session.OneiosConfJob
import com.fahadali.oneos.session.OneiosJob
import com.fahadali.oneos.session.OneiosLogsJob
import com.fahadali.oneos.session.OneiosToolJob
import com.fahadali.oneos.session.UpdateCheck
import dev.oneuiproject.oneui.layout.ToolbarLayout

/**
 * iOS 27's page (docs/oneios.md, "UI (2026-11-25)"): One UI's large title that collapses on scroll, with one line
 * under it (ready, the steps to do, the running step and its percentage); **On this phone**, the one place that shows
 * the phone's iOS state (the runtime, the iOS image, the kernel, iOS's data, the last session, and what stops the
 * switch with its fix); **Steps**, the one checklist ([OneiosSteps]: Get the runtime, Make iOS image, Update the
 * kernel, Activate, Switch, Return, Logs), where a running step shows its phase, a real bar, its amount and Cancel,
 * and a failed one its reason and Show log; one primary button at the bottom (the next step); everything else in the
 * app bar's overflow menu. Every action is the same job as before the redesign ([OneiosJob], [OneiosToolJob]): the
 * root verbs, their order and the switch's confirm (with the way back to One UI) are unchanged.
 */
class OneiosActivity : EdgeToEdgeActivity() {
    private lateinit var picker: OneiosPicker
    private lateinit var toolbar: ToolbarLayout
    private lateinit var primaryColors: ColorStateList
    private var unsubscribe: (() -> Unit)? = null
    private var started = false

    /** The checklist's rows by step, rebound in place for a byte count (rebuilt only when the page's shape changes). */
    private val rows = HashMap<OneiosSteps.Id, View>()
    private var shape: Any? = null
    private var busyRow: dev.oneuiproject.oneui.widget.CardItemView? = null
    private val ticker = android.os.Handler(android.os.Looper.getMainLooper())
    private val tick = object : Runnable {
        override fun run() {
            if (isDestroyed) return
            val s = OneiosJob.state
            val checkBusy = s.job == OneiosFlow.Job.CHECK || s.waitingFor != null
            val toolBusy = OneiosToolJob.state.busy
            if (!checkBusy && !toolBusy) return
            if (checkBusy) busyRow?.summary = busyLine(s)
            if (toolBusy) {
                val steps = OneiosSteps.of(OneiosStepRow.input(this@OneiosActivity))
                for (step in steps.steps) if (step.state == OneiosSteps.State.RUNNING) rows[step.id]?.let { bindStep(it, step) }
            }
            ticker.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        OneiosToolActivity.askNotifications(this, savedInstanceState)
        picker = OneiosPicker(this, savedInstanceState)
        setContentView(R.layout.activity_oneios_screen)
        toolbar = findViewById(R.id.oneios_toolbar)
        OneiosScreens.setUp(this, toolbar, getString(R.string.oneios_short))
        applyEdgeToEdgeInsets(toolbar)
        primaryColors = findViewById<Button>(R.id.oneios_primary).textColors
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        picker.save(outState)
    }

    override fun onStart() {
        super.onStart()
        started = true
        shape = null
        val a = OneiosJob.observe { render() }
        val b = OneiosToolJob.observe { render() }
        val c = OneiosConfJob.observeBy({ it.writing }) { render() }
        val d = UpdateCheck.observe { render() }
        val e = AppUpdater.observe { render() }
        val f = OneiosLogsJob.observe { render() }
        unsubscribe = { a(); b(); c(); d(); e(); f() }
    }

    override fun onResume() {
        super.onResume()
        // Not again when root answered moments ago (back from the picker, a flow, the logs): OneiosJob.refreshIfStale.
        if (!OneiosJob.state.busy) OneiosJob.refreshIfStale(this)
        UpdateCheck.run(this)
    }

    override fun onStop() {
        started = false
        ticker.removeCallbacks(tick)
        unsubscribe?.invoke()
        unsubscribe = null
        super.onStop()
    }

    private fun busyLine(s: OneiosJob.State): String = listOfNotNull(
        if (s.job == null && s.waitingFor != null) getString(R.string.oneios_waiting_line, s.waitingFor) else s.message,
        s.since.takeIf { it > 0 }?.let { getString(R.string.oneios_seconds, ((SystemClock.elapsedRealtime() - it) / 1000).toInt()) },
    ).joinToString(" · ")

    private fun render() {
        if (isDestroyed) return
        val logsState = OneiosLogsJob.state
        logsState.shared?.let { shared ->
            OneiosLogsJob.taken()
            OneiosLogsActivity.share(this, shared)
        }
        logsState.shareProblem?.let {
            OneiosLogsJob.taken()
            Toast.makeText(this, getString(R.string.oneios_logs_share_failed, it), Toast.LENGTH_LONG).show()
        }
        val s = OneiosJob.state
        val t = OneiosToolJob.state
        val input = OneiosStepRow.input(this)
        val steps = OneiosSteps.of(input)
        val st = s.status
        val kernelState = steps.step(OneiosSteps.Id.KERNEL).state
        val kernelDue = if (st?.image != null && st.runtime != null && (kernelState == OneiosSteps.State.TODO || kernelState == OneiosSteps.State.FAILED)) {
            input.expectedKernel ?: OneiosUpdates.KERNEL_NEXT
        } else null
        val avail = OneiosUpdates.of(st?.runtime?.version, UpdateCheck.latestRuntime(this), kernelDue, BuildConfig.VERSION_CODE, UpdateCheck.app)
        // A long copy or a tool flow keeps the screen on, as Setting up does.
        if (s.copying || t.busy) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        toolbar.setTitle(OneiosSystem.shortName(st?.image?.version))
        toolbar.expandedSubtitle = subtitle(s, steps)

        // The page's shape: everything but the numbers of a running step. Only a change of it rebuilds the rows, so a
        // byte count never rebuilds a row under the finger.
        val newShape = listOf(
            steps.steps.map { listOf(it.state, it.line, it.reason, it.cancel, it.log, it.progress == null) }, steps.next,
            st, s.job, s.waitingFor != null, s.offered, s.failure, s.last, s.flow.problem, t.busy, t.builtKc,
            OneiosConfJob.state.writing, OneiosJob.kernelCheckLine(this),
            avail, AppUpdater.state.phase, logsState.exporting,
        )
        if (newShape != shape) {
            shape = newShape
            build(s, steps, avail)
            invalidateOptionsMenu()
        } else {
            for (step in steps.steps) rows[step.id]?.let { bindStep(it, step) }
        }
        bindPrimary(s, t, steps)
        // Updates by themselves (OneiosAuto): after this frame, only while the page is in front (Android lets only a
        // visible app start the foreground service a download or a tool flow needs).
        if (started) window.decorView.post { if (started && !isDestroyed) OneiosAuto.tick(this) }
    }

    private fun subtitle(s: OneiosJob.State, steps: OneiosSteps.View): String = steps.running?.let { r ->
        r.progress?.percent?.let { getString(R.string.oneios_page_sub_running, title(r.id, s.status?.image?.version), it) } ?: title(r.id, s.status?.image?.version)
    } ?: when {
        s.status?.sessionOpen == true -> getString(R.string.oneios_page_sub_open)
        s.flow.ready -> getString(R.string.oneios_page_sub_ready)
        steps.todo == 1 -> getString(R.string.oneios_page_sub_todo_one)
        steps.todo > 1 -> getString(R.string.oneios_page_sub_todo, steps.todo)
        else -> ""
    }

    private fun build(s: OneiosJob.State, steps: OneiosSteps.View, avail: OneiosUpdates.Available) {
        val column = findViewById<LinearLayout>(R.id.oneios_column)
        column.removeAllViews()
        rows.clear()
        busyRow = null
        ticker.removeCallbacks(tick)
        val st = s.status
        val flow = s.flow
        val idle = !s.busy
        val toolBusy = OneiosToolJob.state.busy

        // On this phone: the one place for the phone's iOS state, and what stops the switch with its fix.
        val state = PrebootCards.section(column, getString(R.string.oneios_page_state))
        if (s.job == OneiosFlow.Job.CHECK || (s.job == null && s.waitingFor != null)) {
            busyRow = PrebootCards.row(state, getString(if (s.job == null) R.string.oneios_waiting_title else R.string.oneios_running_check), busyLine(s))
                as dev.oneuiproject.oneui.widget.CardItemView
            ticker.postDelayed(tick, 1000)
            if (s.job == OneiosFlow.Job.CHECK) PrebootCards.row(state, getString(R.string.oneios_stop), getString(R.string.oneios_check_stop_line)) { OneiosJob.cancel() }
        } else if (toolBusy) {
            ticker.postDelayed(tick, 1000)
        }
        if (avail.any && idle && !toolBusy && st?.sessionOpen != true && !AppUpdater.state.busy) {
            val summary = avail.parts.joinToString(" · ") + "\n" + getString(R.string.oneios_update_available_tap)
            PrebootCards.row(state, getString(R.string.oneios_update_available_title), summary, chevron = true) {
                when {
                    avail.runtime != null -> OneiosActions.download(this, null)
                    avail.kernel != null -> action(OneiosSteps.Id.KERNEL, steps.step(OneiosSteps.Id.KERNEL).state)?.invoke()
                    else -> FixActions.confirmAppUpdate(this)
                }
            }
        }
        val problem = flow.problem
        when {
            s.offered == false -> PrebootCards.row(state, getString(R.string.oneios_not_this_phone_title), getString(R.string.oneios_not_this_phone))
            problem != null && s.job == null && !problem.isNextStep ->
                PrebootCards.row(state, problem.title, problem.line, chevron = problem.fix != OneiosFix.NONE, enabled = idle) {
                    OneiosActions.run(this, OneiosFlow.Next.of(problem.fix), picker)
                }
            flow.ready && s.job == null -> PrebootCards.row(state, getString(R.string.oneios_ready), getString(R.string.oneios_ready_line))
        }
        // This phone: only when it is not the one OneiOS is tested on (the Galaxy A56), or root refused it.
        val phone = flow.row(OneiosFlow.Step.PHONE)
        if (phone.mark == OneiosFlow.Mark.FAILED || phone.line?.contains("untested") == true) PrebootCards.row(state, getString(R.string.oneios_page_phone), phone.line)
        PrebootCards.row(state, getString(R.string.oneios_page_runtime), flow.runtimeLine ?: getString(R.string.oneios_page_none))
        PrebootCards.row(state, getString(R.string.oneios_page_image), flow.imageLine ?: getString(R.string.oneios_page_none))
        if (st?.runtime != null && st.image != null) {
            val image = st.imageKernel?.buildId ?: getString(R.string.oneios_kernel_kc_unknown)
            val runtime = st.runtimeKernel?.buildId ?: getString(R.string.oneios_kernel_kc_none)
            val line = listOfNotNull(
                getString(R.string.oneios_page_kernel_line, image, runtime),
                getString(R.string.oneios_page_kernel_fallback).takeIf { st.imageKernel?.hasFallback == true },
                OneiosJob.kernelCheckLine(this),
            ).joinToString("\n")
            PrebootCards.row(state, getString(R.string.oneios_page_kernel), line)
        }
        if (st?.image != null) PrebootCards.row(state, getString(R.string.oneios_page_data), flow.dataLine ?: getString(R.string.environment_unknown))
        // Last session: how it came back; it opens the session logs (no step of their own).
        OneiosFlow.lastReturn(st)?.let { PrebootCards.row(state, getString(R.string.oneios_page_last), it.title + "\n" + it.line, chevron = true) { startActivity(OneiosLogsActivity.intent(this)) } }
        // One-tap Share logs right on the main iOS page (bundles session logs, switch/return logs, iOS last-boot log and versions).
        val exporting = OneiosLogsJob.state.exporting
        if (exporting != null) {
            PrebootCards.row(state, exporting)
            PrebootCards.row(state, getString(R.string.oneios_logs_stop_share)) { OneiosLogsJob.stopShare() }
        } else if (st?.staged == true) {
            PrebootCards.row(state, getString(R.string.oneios_logs_share_bug), getString(R.string.oneios_logs_share_bug_line), chevron = true) {
                OneiosLogsJob.shareBugReport(this, OneiosLogsActivity.header(this), OneiosLogsActivity.versions(this))
            }
        }

        // Steps: the one checklist.
        val card = PrebootCards.section(column, getString(R.string.oneios_page_steps))
        for (step in steps.steps) rows[step.id] = OneiosStepRow.add(card, step, title(step.id, st?.image?.version), tap(step, idle), cancel(step), log(step))
    }

    private fun bindStep(v: View, step: OneiosSteps.Step) =
        OneiosStepRow.bind(v, step, title(step.id, OneiosJob.state.status?.image?.version), tap(step, !OneiosJob.state.busy), cancel(step), log(step))

    /** A step's name on the page and on the button: the docs' words. */
    private fun title(id: OneiosSteps.Id, @Suppress("UNUSED_PARAMETER") version: String?): String = id.title

    /** Switch to the staged system ("Switch to iOS 27", "Switch to iOS 16.5" on the Galaxy A56): the primary button. */
    private fun switchLabel(version: String?): String =
        if (version == null || OneiosSystem.isIos27(version)) getString(R.string.oneios_switch) else "Switch to ${OneiosSystem.shortName(version)}"

    /** What pressing a step does; null when it cannot be pressed now. */
    private fun tap(step: OneiosSteps.Step, idle: Boolean): (() -> Unit)? {
        val toolBusy = OneiosToolJob.state.busy
        if (step.state == OneiosSteps.State.RUNNING) {
            return if (step.cancel == OneiosSteps.Cancel.TOOL || (toolBusy && step.id == OneiosSteps.Id.IMAGE)) { { startActivity(OneiosToolActivity.intent(this)) } } else null
        }
        if (!idle || toolBusy || step.state == OneiosSteps.State.WAITING) return null
        return action(step.id, step.state)
    }

    private fun action(id: OneiosSteps.Id, state: OneiosSteps.State): (() -> Unit)? {
        val st = OneiosJob.state.status
        return when (id) {
            OneiosSteps.Id.RUNTIME -> { { OneiosActions.askRuntime(this, picker) } }
            OneiosSteps.Id.IMAGE ->
                if (state == OneiosSteps.State.DONE) { { again(id, R.string.oneios_step_again_image) { OneiosActions.askImage(this, picker) } } }
                else { { OneiosActions.askImage(this, picker) } }
            OneiosSteps.Id.KERNEL -> {
                // A kernel that is built (and not yet in, or refused by root) is put in again: no second build. The built
                // kernel stays until root's finish kernel put it in (OneiosToolJob.kernelActivated).
                val built = OneiosToolJob.state.builtKc?.takeIf { it.matches(Regex("^[0-9a-f]{64}$")) }
                when {
                    st?.image == null -> null
                    built != null -> if (OneiosJob.canStart()) { { OneiosJob.activateKernel(this, built) } } else null
                    !OneiosToolJob.canStart() -> null
                    state == OneiosSteps.State.DONE -> { { again(id, R.string.oneios_step_again_kernel) { OneiosToolActivity.start(this, OneiosToolJob.Flow.KERNEL) } } }
                    else -> { { OneiosToolActivity.start(this, OneiosToolJob.Flow.KERNEL) } }
                }
            }
        }
    }

    /** A step that is done, asked first before it runs again. */
    private fun again(id: OneiosSteps.Id, line: Int, go: () -> Unit) {
        AlertDialog.Builder(this).setTitle(getString(R.string.oneios_step_again_title, id.title)).setMessage(line)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(id.title) { _, _ -> go() }.show()
    }

    private fun cancel(step: OneiosSteps.Step): (() -> Unit)? = when (step.cancel) {
        null -> null
        OneiosSteps.Cancel.JOB -> { { confirmCancel(step.id, R.string.oneios_step_cancel_copy) { OneiosJob.cancel() } } }
        OneiosSteps.Cancel.TOOL -> { { confirmCancel(step.id, R.string.oneios_step_cancel_tool) { OneiosToolJob.cancel() } } }
    }

    private fun confirmCancel(id: OneiosSteps.Id, line: Int, go: () -> Unit) {
        AlertDialog.Builder(this).setTitle(getString(R.string.oneios_step_cancel_title, id.title)).setMessage(line)
            .setNegativeButton(R.string.oneios_step_keep_going, null)
            .setPositiveButton(R.string.oneios_step_cancel) { _, _ -> go() }.show()
    }

    private fun log(step: OneiosSteps.Step): (() -> Unit)? = when (step.log) {
        null -> null
        OneiosSteps.Log.TOOL -> { { startActivity(OneiosToolActivity.intent(this)) } }
        OneiosSteps.Log.SESSION -> { { startActivity(OneiosLogsActivity.intent(this)) } }
        OneiosSteps.Log.ROOT -> { { rootAnswer() } }
    }

    /** Show log of a root job: root's (or the app's) whole words, which the step's one line puts plainly. */
    private fun rootAnswer() {
        val s = OneiosJob.state
        val text = listOfNotNull(s.failure, s.flow.problem?.detail?.takeIf { it.isNotBlank() }, s.status?.notReady).distinct().joinToString("\n\n")
            .ifBlank { getString(R.string.environment_unknown) }
        OneiosScreens.textDialog(this, getString(R.string.oneios_page_root_answer), text)
    }

    /** The one primary button: the next step's action, Show details while a tool flow runs, or the flow's fix. */
    private fun bindPrimary(s: OneiosJob.State, t: OneiosToolJob.State, steps: OneiosSteps.View) {
        val b = findViewById<Button>(R.id.oneios_primary)
        val spinner = findViewById<View>(R.id.oneios_primary_spinner)
        val next = steps.next
        val flowNext = s.flow.next
        var spin = false
        when {
            t.busy -> set(b, getString(R.string.oneios_page_show_details)) { startActivity(OneiosToolActivity.intent(this)) }
            s.busy -> {
                spin = true
                set(b, s.job?.let { OneiosActions.runningTitle(this, it) } ?: getString(R.string.oneios_page_working), enabled = false)
            }
            next != null -> {
                // The runtime takes the flow's own fix when it names one (Download again, Choose the runtime file).
                val fix = next == OneiosSteps.Id.RUNTIME && flowNext in setOf(OneiosFlow.Next.DOWNLOAD_RUNTIME, OneiosFlow.Next.IMPORT_RUNTIME)
                val act = if (fix) { { OneiosActions.run(this, flowNext, picker) } }
                    else action(next, steps.step(next).state.let { if (it == OneiosSteps.State.FAILED) OneiosSteps.State.TODO else it })
                // Off while the step cannot run now, never a button that does nothing.
                set(b, title(next, s.status?.image?.version), enabled = act != null) { act?.invoke() }
            }
            flowNext == OneiosFlow.Next.NOT_THIS_PHONE -> set(b, getString(R.string.catalog_not_available), enabled = false)
            // The switch is a button, no step (the owner, 2026-11-25): root's last check passed. It asks first and shows
            // the way back before One UI closes (OneiosSwitchConfirm), as before.
            flowNext == OneiosFlow.Next.SWITCH -> set(b, switchLabel(s.status?.image?.version)) { OneiosSwitchConfirm.show(this) }
            else -> {
                val go = if (OneiosActions.label(this, flowNext) == null) OneiosFlow.Next.CHECK_AGAIN else flowNext
                set(b, OneiosActions.label(this, go).orEmpty()) { OneiosActions.run(this, go, picker) }
            }
        }
        spinner.visibility = if (spin) View.VISIBLE else View.GONE
        b.setTextColor(if (spin) ColorStateList.valueOf(android.graphics.Color.TRANSPARENT) else primaryColors)
    }

    private fun set(b: Button, text: CharSequence, enabled: Boolean = true, onClick: (() -> Unit)? = null) {
        b.text = text
        b.contentDescription = text
        b.isEnabled = enabled && onClick != null
        b.setOnClickListener { onClick?.invoke() }
    }

    // --- The overflow menu: everything that is not the next step --------------------------------------------------

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        val s = OneiosJob.state
        val st = s.status
        val idle = !s.busy && !OneiosToolJob.state.busy
        fun item(id: Int, title: Int, enabled: Boolean = true) = menu.add(Menu.NONE, id, Menu.NONE, title).apply {
            setShowAsAction(MenuItem.SHOW_AS_ACTION_NEVER)
            isEnabled = enabled
        }
        if (st?.image != null) item(M_SWITCHES, R.string.oneios_switches)
        item(M_CHECK, R.string.oneios_menu_check_again, enabled = idle)
        if (st?.runtime != null) item(M_SUMS, R.string.oneios_tool_sums, enabled = idle)
        item(M_CHECKS, R.string.oneios_checks)
        item(M_LOGS, R.string.oneios_logs)
        if (st?.image != null && st.runtime != null) item(M_KERNEL_CHECK, R.string.oneios_kernel_check, enabled = idle)
        if (st?.imageKernel?.hasFallback == true) item(M_KERNEL_RESTORE, R.string.oneios_kernel_restore, enabled = idle)
        item(M_RUNTIME_OTHER, R.string.oneios_runtime_other, enabled = idle)
        item(M_IMAGE_FILE, R.string.oneios_image_file, enabled = idle)
        if (st?.image != null && st.runtime != null) item(M_KERNELCACHE, R.string.oneios_kernel_kernelcache, enabled = idle)
        if (st?.staged == true) item(M_REMOVE, R.string.oneios_remove, enabled = idle && !st.sessionOpen)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            M_SWITCHES -> startActivity(OneiosSwitchesActivity.intent(this))
            M_CHECK -> OneiosJob.refresh(this)
            M_SUMS -> OneiosToolActivity.start(this, OneiosToolJob.Flow.SUMS)
            M_CHECKS -> startActivity(OneiosChecksActivity.intent(this))
            M_LOGS -> startActivity(OneiosLogsActivity.intent(this))
            M_KERNEL_CHECK -> OneiosJob.checkKernel(this)
            M_KERNEL_RESTORE -> OneiosActions.confirmRestoreKernel(this)
            M_RUNTIME_OTHER -> OneiosActions.askRuntimeOther(this, picker)
            M_IMAGE_FILE -> picker.pick(OneiosKind.IMAGE)
            M_KERNELCACHE -> picker.pickKernelcache()
            M_REMOVE -> OneiosActions.confirmRemove(this)
            else -> return super.onOptionsItemSelected(item)
        }
        return true
    }

    companion object {
        private const val M_SWITCHES = 1
        private const val M_CHECK = 2
        private const val M_SUMS = 3
        private const val M_CHECKS = 4
        private const val M_LOGS = 5
        private const val M_KERNEL_CHECK = 6
        private const val M_KERNEL_RESTORE = 7
        private const val M_RUNTIME_OTHER = 8
        private const val M_IMAGE_FILE = 9
        private const val M_KERNELCACHE = 10
        private const val M_REMOVE = 11

        fun intent(ctx: android.content.Context): Intent = Intent(ctx, OneiosActivity::class.java)
    }
}

/** What the iOS screens of the redesign share: the app bar, a text dialog. */
internal object OneiosScreens {
    fun setUp(a: EdgeToEdgeActivity, toolbar: ToolbarLayout, title: CharSequence) {
        toolbar.setTitle(title)
        toolbar.showNavigationButtonAsBack = true
        toolbar.setNavigationButtonOnClickListener { a.onBackPressedDispatcher.onBackPressed() }
        a.findViewById<NestedScrollView>(R.id.oneios_scroll)?.apply {
            seslSetFadingEdgeEnabled(true)
            seslSetFadingEdgeColor(a.getColor(R.color.preboot_page))
        }
    }

    /** A dialog with [text] selectable in monospace (root's or the tool's own words). */
    fun textDialog(a: android.app.Activity, title: CharSequence, text: CharSequence) {
        val view = android.widget.TextView(a).apply {
            setTextIsSelectable(true)
            typeface = android.graphics.Typeface.MONOSPACE
            textSize = 13f
            val p = PrebootCards.dp(this, 20)
            setPadding(p, p / 2, p, 0)
            setText(text)
        }
        val scroll = android.widget.ScrollView(a).apply { addView(view) }
        AlertDialog.Builder(a).setTitle(title).setView(scroll).setPositiveButton(android.R.string.ok, null).show()
    }
}
