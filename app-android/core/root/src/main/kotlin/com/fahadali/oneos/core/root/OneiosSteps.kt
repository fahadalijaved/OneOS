package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosMessage
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow

/**
 * The one checklist of iOS 27's page (docs/oneios.md, "UI (2026-11-25)"): Get the runtime, Make iOS image, Update the
 * kernel, Activate, Switch, Return, Logs. Each step is done, to do, running or failed (to do is [State.WAITING] while
 * an earlier step it needs is not done), says what it does in one sentence, and while it runs how far it is: the
 * phase in words, a bar ([Progress.fraction]; null: a moving bar) and the amount. Read from what is known already:
 * root's status and the flow ([OneiosFlow]), the job of the app that runs or ran ([Job]) and oneios-tool's flow
 * ([Tool]). Nothing here asks root anything or changes what a step runs.
 */
object OneiosSteps {
    /** The steps, by the docs' names; [about] is the one sentence a step shows while it is not done. */
    enum class Id(val title: String, val about: String) {
        RUNTIME("Get the runtime", "Downloads OneiOS's runtime: xnuhost, the program that runs iOS, with its tools and kernel."),
        IMAGE("Make iOS image", "This phone downloads iOS from Apple and builds the iOS image set itself."),
        KERNEL("Update the kernel", "Builds the image's kernel.kc again from this runtime's XNU and Apple's kernelcache."),
        ACTIVATE("Activate", "Puts the kernel this phone built in the image set; the one before is kept to restore."),
        SWITCH("Switch", "One UI closes and iOS starts. Volume Up + Volume Down for 3 seconds brings One UI back."),
        RETURN("Return", "Back to One UI from the open iOS session, as Volume Up + Volume Down does."),
        LOGS("Logs", "What xnuhost, the switch and the return wrote, with a summary."),
    }

    enum class State { WAITING, TODO, RUNNING, DONE, FAILED }

    /** What Cancel stops: one of the app's root jobs (a download, an import) or oneios-tool's flow. */
    enum class Cancel { JOB, TOOL }

    /** Where Show log goes: the tool flow's details, root's whole answer, or the session logs. */
    enum class Log { TOOL, ROOT, SESSION }

    data class Progress(
        /** 0..1; null: no numbers yet (a moving bar). */
        val fraction: Float?,
        /** What runs now, in words ("Step 5 of 28 · Decrypting the OS image", "Downloading"). */
        val phase: String,
        /** "3.2 GB of 11.4 GB (28%) · 40 MB/s · about 5 min left"; null without numbers. */
        val amount: String?,
    ) {
        val percent: Int? get() = fraction?.let { (it * 100).toInt().coerceIn(0, 100) }
    }

    data class Step(
        val id: Id,
        val state: State,
        /** Under the title: what it did (done), what comes first (waiting), its sentence (to do), its failure's title. */
        val line: String?,
        val progress: Progress? = null,
        /** A failed step's reason, in one line. */
        val reason: String? = null,
        val cancel: Cancel? = null,
        val log: Log? = null,
    )

    data class View(val steps: List<Step>, val next: Id?) {
        fun step(id: Id): Step = steps.first { it.id == id }
        val running: Step? get() = steps.firstOrNull { it.state == State.RUNNING }
        val todo: Int get() = steps.count { it.id != Id.LOGS && (it.state == State.TODO || it.state == State.FAILED) }
    }

    /** The app's root job ([OneiosFlow.Job]) as it runs or ran: its words, its bytes, its failure. */
    data class Job(
        val running: OneiosFlow.Job? = null,
        val message: String? = null,
        val done: Long = 0,
        val total: Long = 0,
        val file: String? = null,
        val progressLine: String? = null,
        val last: OneiosFlow.Job? = null,
        val failure: String? = null,
    )

    enum class ToolFlow { MAKE_IMAGE, KERNEL, OTHER }

    /** oneios-tool's flow (the app's OneiosToolJob) as it runs or ran. */
    data class Tool(
        val running: ToolFlow? = null,
        val last: ToolFlow? = null,
        val view: OneiosToolFlow = OneiosToolFlow(),
        /** The flow's own phase in words (Make iOS image's, Update the kernel's); null: the tool's step says it. */
        val phase: String? = null,
        val starting: Boolean = false,
        val stopping: Boolean = false,
        /** Why it waits (paused, no network, too warm), in words; null when it does not. */
        val held: String? = null,
        /** Why it stopped, in plain words; null when it ended well or runs. */
        val failure: OneiosMessage? = null,
        /** Update the kernel built a kernel.kc that waits for Activate. */
        val builtKc: String? = null,
    )

    data class Input(
        val flow: OneiosFlow.View,
        val status: OneiosStatus?,
        val job: Job = Job(),
        val tool: Tool = Tool(),
        /** The kernel build id the image's kernel.kc has when it is the staged runtime's; null: not known. */
        val expectedKernel: String? = null,
    )

    fun of(i: Input): View {
        val st = i.status
        val job = i.job
        val tool = i.tool
        fun ran(vararg jobs: OneiosFlow.Job) = job.running == null && job.last in jobs && !job.failure.isNullOrBlank()
        fun plain(kind: OneiosKind?): OneiosMessage = OneiosPlain.refused(job.failure.orEmpty(), kind)
        fun toolFailed(f: ToolFlow) = tool.running == null && tool.last == f && tool.failure != null

        // Get the runtime.
        val runtime = when {
            job.running == OneiosFlow.Job.DOWNLOAD_RUNTIME || job.running == OneiosFlow.Job.IMPORT_RUNTIME ->
                Step(Id.RUNTIME, State.RUNNING, null, jobProgress(job), cancel = Cancel.JOB)
            ran(OneiosFlow.Job.DOWNLOAD_RUNTIME, OneiosFlow.Job.IMPORT_RUNTIME) ->
                plain(OneiosKind.RUNTIME).let { Step(Id.RUNTIME, State.FAILED, it.title, reason = it.line, log = Log.ROOT) }
            st?.runtime?.placeholder == true ->
                Step(Id.RUNTIME, State.FAILED, i.flow.runtimeLine, reason = "This runtime has no xnuhost yet: get a newer one.")
            i.flow.runtime == OneiosFlow.Check.FAILED ->
                Step(Id.RUNTIME, State.FAILED, i.flow.runtimeLine, reason = i.flow.problem?.line, log = Log.ROOT)
            st?.runtime != null -> Step(Id.RUNTIME, State.DONE, i.flow.runtimeLine)
            else -> Step(Id.RUNTIME, State.TODO, Id.RUNTIME.about)
        }
        // Staged and usable, even when a later run of the step failed (that failure shows; the steps after it do not wait).
        val runtimeDone = st?.runtime != null && st.runtime.placeholder != true && i.flow.runtime != OneiosFlow.Check.FAILED

        // Make iOS image (or an image set the user has: its import).
        val image = when {
            tool.running == ToolFlow.MAKE_IMAGE -> Step(Id.IMAGE, State.RUNNING, null, toolStepProgress(tool), cancel = Cancel.TOOL)
            job.running == OneiosFlow.Job.IMPORT_IMAGE -> Step(Id.IMAGE, State.RUNNING, null, jobProgress(job), cancel = Cancel.JOB)
            toolFailed(ToolFlow.MAKE_IMAGE) ->
                Step(Id.IMAGE, State.FAILED, tool.failure!!.title, reason = tool.failure.line, log = Log.TOOL)
            ran(OneiosFlow.Job.IMPORT_IMAGE) -> plain(OneiosKind.IMAGE).let { Step(Id.IMAGE, State.FAILED, it.title, reason = it.line, log = Log.ROOT) }
            i.flow.image == OneiosFlow.Check.FAILED -> Step(Id.IMAGE, State.FAILED, i.flow.imageLine, reason = i.flow.problem?.line, log = Log.ROOT)
            st?.image != null -> Step(Id.IMAGE, State.DONE, i.flow.imageLine)
            !runtimeDone -> Step(Id.IMAGE, State.WAITING, after(Id.RUNTIME))
            else -> Step(Id.IMAGE, State.TODO, Id.IMAGE.about)
        }
        val imageDone = st?.image != null && i.flow.image != OneiosFlow.Check.FAILED

        // The kernel: the image's kernel.kc against the runtime's kernel build.
        val imageKernel = st?.imageKernel?.buildId?.takeIf { it.isNotBlank() && it != "unknown" }
        val current = imageKernel != null && imageKernel == i.expectedKernel
        val built = tool.builtKc != null && tool.running == null
        val kernel = when {
            tool.running == ToolFlow.KERNEL -> Step(Id.KERNEL, State.RUNNING, null, toolStepProgress(tool), cancel = Cancel.TOOL)
            !runtimeDone || !imageDone -> Step(Id.KERNEL, State.WAITING, after(if (!runtimeDone) Id.RUNTIME else Id.IMAGE))
            built -> Step(Id.KERNEL, State.DONE, "Built; Activate puts it in the image set")
            toolFailed(ToolFlow.KERNEL) -> Step(Id.KERNEL, State.FAILED, tool.failure!!.title, reason = tool.failure.line, log = Log.TOOL)
            current -> Step(Id.KERNEL, State.DONE, "kernel.kc is this runtime's ($imageKernel)")
            st?.runtimeKernel == null -> Step(Id.KERNEL, State.WAITING, "This runtime carries no kernel: get a newer one")
            imageKernel == null -> Step(Id.KERNEL, State.TODO, "kernel.kc was staged before kernel tracking: build it from this runtime")
            else -> Step(Id.KERNEL, State.TODO, "kernel.kc is $imageKernel; this runtime's is ${i.expectedKernel ?: "another"}")
        }

        val activate = when {
            job.running == OneiosFlow.Job.FINISH_KERNEL || job.running == OneiosFlow.Job.RESTORE_KERNEL ->
                Step(Id.ACTIVATE, State.RUNNING, null, jobProgress(job))
            ran(OneiosFlow.Job.FINISH_KERNEL, OneiosFlow.Job.RESTORE_KERNEL) ->
                plain(null).let { Step(Id.ACTIVATE, State.FAILED, it.title, reason = it.line, log = Log.ROOT) }
            built -> Step(Id.ACTIVATE, State.TODO, Id.ACTIVATE.about)
            kernel.state == State.DONE && current -> Step(Id.ACTIVATE, State.DONE, "The image boots this runtime's kernel")
            else -> Step(Id.ACTIVATE, State.WAITING, after(Id.KERNEL))
        }

        // Switch: root's last check of every file and the phone, then the switch.
        val ready = i.flow.ready
        val readyMark = i.flow.mark(OneiosFlow.Step.READY)
        val switch = when {
            job.running == OneiosFlow.Job.SWITCH -> Step(Id.SWITCH, State.RUNNING, null, jobProgress(job))
            st?.sessionOpen == true -> Step(Id.SWITCH, State.DONE, "An iOS session is open")
            ran(OneiosFlow.Job.SWITCH) -> plain(null).let { Step(Id.SWITCH, State.FAILED, it.title, reason = it.line, log = Log.ROOT) }
            !runtimeDone || !imageDone -> Step(Id.SWITCH, State.WAITING, after(if (!runtimeDone) Id.RUNTIME else Id.IMAGE))
            ready -> Step(Id.SWITCH, State.TODO, Id.SWITCH.about)
            job.running == OneiosFlow.Job.CHECK -> Step(Id.SWITCH, State.WAITING, "Root checks the staged files and the phone…")
            readyMark == OneiosFlow.Mark.FAILED -> i.flow.problem.let { p ->
                Step(Id.SWITCH, State.FAILED, p?.title ?: "Not ready to switch", reason = p?.line, log = Log.ROOT)
            }
            else -> Step(Id.SWITCH, State.WAITING, "Not checked yet: Check again")
        }

        val last = OneiosFlow.lastReturn(st)
        val back = when {
            job.running == OneiosFlow.Job.RETURN -> Step(Id.RETURN, State.RUNNING, null, jobProgress(job))
            ran(OneiosFlow.Job.RETURN) -> plain(null).let { Step(Id.RETURN, State.FAILED, it.title, reason = it.line, log = Log.SESSION) }
            st?.sessionOpen == true -> Step(Id.RETURN, State.TODO, Id.RETURN.about)
            last != null -> Step(Id.RETURN, if (last.level == com.fahadali.oneos.core.model.Level.WARN) State.FAILED else State.DONE, last.title,
                reason = if (last.level == com.fahadali.oneos.core.model.Level.WARN) last.line else null,
                log = if (last.level == com.fahadali.oneos.core.model.Level.WARN) Log.SESSION else null)
            else -> Step(Id.RETURN, State.WAITING, after(Id.SWITCH))
        }

        val sessionRan = st?.sessionOpen == true || last != null || OneiosFlow.dataNew(st) == false
        val logs = Step(Id.LOGS, if (sessionRan) State.TODO else State.WAITING, if (sessionRan) Id.LOGS.about else after(Id.SWITCH))

        val steps = listOf(runtime, image, kernel, activate, switch, back, logs)
        return View(steps, next(i, steps, current))
    }

    /** The primary button's step; null while something runs, or when the flow's own fix is the next thing (Check again). */
    private fun next(i: Input, steps: List<Step>, kernelCurrent: Boolean): Id? {
        if (steps.any { it.state == State.RUNNING } || i.job.running != null || i.tool.running != null) return null
        fun s(id: Id) = steps.first { it.id == id }
        return when {
            i.status?.sessionOpen == true -> Id.RETURN
            i.status == null || i.flow.mark(OneiosFlow.Step.PHONE) == OneiosFlow.Mark.FAILED -> null
            // Not staged, or not usable; a failed later run with a usable package staged does not hold the switch back.
            i.status.runtime == null || i.status.runtime.placeholder || i.flow.runtime == OneiosFlow.Check.FAILED -> Id.RUNTIME
            i.status.image == null || i.flow.image == OneiosFlow.Check.FAILED -> Id.IMAGE
            s(Id.ACTIVATE).state == State.TODO -> Id.ACTIVATE
            // A kernel known to be another runtime's: the update comes before the switch (unknown ones do not block).
            s(Id.KERNEL).state == State.TODO && !kernelCurrent && i.status.imageKernel?.buildId.let { it != null && it != "unknown" } &&
                i.expectedKernel != null -> Id.KERNEL
            s(Id.SWITCH).state == State.TODO -> Id.SWITCH
            else -> null
        }
    }

    private fun after(id: Id): String = "After ${id.title}"

    /** A root job's progress: its bytes when it copies, else its words with a moving bar. */
    fun jobProgress(job: Job): Progress {
        val fraction = if (job.total > 0) (job.done.toFloat() / job.total).coerceIn(0f, 1f) else null
        val phase = listOfNotNull(job.message, job.file).firstOrNull()?.takeIf { it.isNotBlank() } ?: "Working…"
        val amount = job.progressLine ?: job.file?.takeIf { it != phase }
        return Progress(fraction, phase, amount)
    }

    /**
     * oneios-tool's progress, from its own events ([OneiosToolFlow]: `start`'s plan, `step`, `progress`): the bar is the
     * running step's `percent`, else its `done` of `total`, else the share of the plan's steps done; the phase is the
     * flow's own words or "Step k of N · <the step's text>"; the amount the tool's numbers (bytes, files, rate, time
     * left). A wait (a pause, no network, heat) is said in the phase.
     */
    fun toolProgress(view: OneiosToolFlow, phase: String? = null, held: String? = null, starting: Boolean = false, stopping: Boolean = false): Progress {
        val steps = view.steps
        val at = steps.indexOfFirst { it.state == OneiosTool.StepState.RUNNING }
        val running = steps.getOrNull(at)
        val stepWords = running?.let { r -> "Step ${at + 1} of ${steps.size} · ${r.text ?: r.id}" }
        val own = view.percent?.let { (it / 100.0).toFloat() }
            ?: view.done?.let { d -> view.total?.takeIf { it > 0 }?.let { (d.toFloat() / it) } }
        val share = if (steps.isNotEmpty() && at >= 0) at.toFloat() / steps.size else null
        val fraction = (own ?: share)?.coerceIn(0f, 1f)
        val words = when {
            stopping -> "Stopping…"
            starting -> "Starting oneios-tool…"
            else -> listOfNotNull(phase, stepWords).distinct().joinToString(" · ").ifEmpty { "Working…" }
        }
        val amount = listOfNotNull(held, view.progressLine).joinToString(" · ").ifEmpty { null }
        return Progress(fraction, words, amount)
    }

    private fun toolStepProgress(t: Tool): Progress = toolProgress(t.view, t.phase, t.held, t.starting, t.stopping)
}
