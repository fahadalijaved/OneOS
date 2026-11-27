package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosMessage
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow

/**
 * The one checklist of iOS 27's page (docs/oneios.md, "UI (2026-11-25)"): Get the runtime, Make iOS image, Update the
 * kernel (Activate is its last part; the switch, Back to One UI and the logs are no steps). Each step is done, to do, running or failed (to do is [State.WAITING] while
 * an earlier step it needs is not done), says what it does in one sentence, and while it runs how far it is: the
 * phase in words, a bar ([Progress.fraction]; null: a moving bar) and the amount. Read from what is known already:
 * root's status and the flow ([OneiosFlow]), the job of the app that runs or ran ([Job]) and oneios-tool's flow
 * ([Tool]). Nothing here asks root anything or changes what a step runs.
 */
object OneiosSteps {
    /** The steps, by the docs' names; [about] is the one sentence a step shows while it is not done. */
    enum class Id(val title: String, val about: String) {
        RUNTIME("Get the runtime", "Downloads OneiOS's runtime: xnuhost and its tools. A newer release is staged by itself."),
        IMAGE("Make iOS image", "This phone downloads iOS from Apple and builds the iOS image set itself."),
        KERNEL("Update the kernel", "Builds kernel.kc from this runtime's XNU and puts it in the image; it runs by itself when one is due."),
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
        val todo: Int get() = steps.count { it.state == State.TODO || it.state == State.FAILED }
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
        /** Extra detail during starting or a root phase (e.g. "Pairing file 3 of 9: reviewed.json"). */
        val detail: String? = null,
        /** Fractional progress during a non-tool phase (e.g. pairing files), or null. */
        val detailFraction: Float? = null,
        /** Elapsed seconds of the running flow (null when idle or not shown). */
        val elapsedSeconds: Int? = null,
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

        // Update the kernel: the image's kernel.kc against the runtime's kernel build; it builds (oneios-tool), then
        // puts the build in (root's finish kernel). Both run by themselves when a newer kernel is there ([auto]).
        val imageKernel = st?.imageKernel?.buildId?.takeIf { it.isNotBlank() && it != "unknown" }
        val current = imageKernel != null && imageKernel == i.expectedKernel
        val built = tool.builtKc != null && tool.running == null
        val kernel = when {
            tool.running == ToolFlow.KERNEL -> Step(Id.KERNEL, State.RUNNING, null, toolStepProgress(tool), cancel = Cancel.TOOL)
            job.running == OneiosFlow.Job.FINISH_KERNEL || job.running == OneiosFlow.Job.RESTORE_KERNEL ->
                Step(Id.KERNEL, State.RUNNING, null, jobProgress(job))
            !runtimeDone || !imageDone -> Step(Id.KERNEL, State.WAITING, after(if (!runtimeDone) Id.RUNTIME else Id.IMAGE))
            // Root refused to put the build in: its reason; the build is kept, so a tap tries again without building.
            ran(OneiosFlow.Job.FINISH_KERNEL, OneiosFlow.Job.RESTORE_KERNEL) ->
                plain(null).let { Step(Id.KERNEL, State.FAILED, it.title, reason = it.line, log = Log.ROOT) }
            built -> Step(Id.KERNEL, State.TODO, "Built; putting it in the image set")
            toolFailed(ToolFlow.KERNEL) -> Step(Id.KERNEL, State.FAILED, tool.failure!!.title, reason = tool.failure.line, log = Log.TOOL)
            current -> Step(Id.KERNEL, State.DONE, "kernel.kc is this runtime's ($imageKernel)")
            st?.runtimeKernel == null -> Step(Id.KERNEL, State.WAITING, "This runtime carries no kernel: get a newer one")
            imageKernel == null -> Step(Id.KERNEL, State.TODO, "kernel.kc was staged before kernel tracking: build it from this runtime")
            else -> Step(Id.KERNEL, State.TODO, "kernel.kc is $imageKernel; this runtime's is ${i.expectedKernel ?: "another"}")
        }

        // Back to One UI, the session logs and the switch are no steps (the owner, 2026-11-25): the page's primary
        // button is Switch to iOS 27 when root's last check passed, Back to One UI with a session open (OneiosFlow's
        // next), and the logs are the overflow's and the Last session row's.
        val steps = listOf(runtime, image, kernel)
        return View(steps, next(i, steps))
    }

    /** The primary button's step; null while something runs, or when the flow's own next is it (Switch, Back, a fix). */
    private fun next(i: Input, steps: List<Step>): Id? {
        if (steps.any { it.state == State.RUNNING } || i.job.running != null || i.tool.running != null) return null
        return when {
            i.status?.sessionOpen == true -> null
            i.status == null || i.flow.mark(OneiosFlow.Step.PHONE) == OneiosFlow.Mark.FAILED -> null
            // Not staged, or not usable; a failed later run with a usable package staged does not hold the switch back.
            i.status.runtime == null || i.status.runtime.placeholder || i.flow.runtime == OneiosFlow.Check.FAILED -> Id.RUNTIME
            i.status.image == null || i.flow.image == OneiosFlow.Check.FAILED -> Id.IMAGE
            else -> null
        }
    }

    // --- Updates by themselves --------------------------------------------------------------------------------

    /** What the page starts by itself, so nobody has to know that a runtime or a kernel update is there. */
    enum class Auto { NONE, CHECK_RUNTIME, UPDATE_RUNTIME, UPDATE_KERNEL, ACTIVATE }

    data class AutoInput(
        val steps: Input,
        /** Nothing else of the app runs (OneiosJob and OneiosToolJob could start one now). */
        val idle: Boolean,
        /** The newest release's runtime version, when the last look found one; null: not looked or not answered. */
        val latest: String?,
        /** The last look for the newest release is old enough ([CHECK_EVERY_MS]). */
        val checkDue: Boolean,
        /** What was started by itself in this run of the app ([autoKey]): each is tried once, a failure is the user's. */
        val tried: Set<String>,
    )

    const val CHECK_EVERY_MS = 6L * 60 * 60 * 1000

    /** The key of an automatic start, so the same one never runs twice by itself (a failure stays on its step). */
    fun autoKey(a: Auto, i: Input, latest: String?): String = when (a) {
        Auto.UPDATE_RUNTIME -> "runtime $latest"
        Auto.UPDATE_KERNEL -> "kernel ${i.expectedKernel} ${i.status?.imageKernel?.buildId}"
        Auto.ACTIVATE -> "activate ${i.tool.builtKc}"
        else -> a.name
    }

    /**
     * The next automatic start, in this order: put in a kernel that was built; stage a newer release's runtime; build
     * the kernel when the image's is not the staged runtime's; look for a newer release (every 6 h). Never while
     * anything runs, an iOS session is open, root has not answered or refused this phone, nothing is staged yet (the
     * first runtime and the image are the user's choices), or this one was tried already in this run.
     */
    fun auto(a: AutoInput): Auto {
        val i = a.steps
        val st = i.status ?: return Auto.NONE
        if (!a.idle || st.sessionOpen || i.flow.mark(OneiosFlow.Step.PHONE) == OneiosFlow.Mark.FAILED) return Auto.NONE
        val runtime = st.runtime ?: return Auto.NONE
        fun fresh(x: Auto) = autoKey(x, i, a.latest) !in a.tried
        val imageKernel = st.imageKernel?.buildId?.takeIf { it.isNotBlank() && it != "unknown" }
        return when {
            i.tool.builtKc != null && st.image != null && fresh(Auto.ACTIVATE) -> Auto.ACTIVATE
            a.latest != null && a.latest != runtime.version &&
                com.fahadali.oneos.core.model.OneiosManifests.versionAtLeast(a.latest, runtime.version) && fresh(Auto.UPDATE_RUNTIME) -> Auto.UPDATE_RUNTIME
            st.image != null && i.flow.image != OneiosFlow.Check.FAILED && st.runtimeKernel != null && i.expectedKernel != null &&
                imageKernel != i.expectedKernel && i.tool.builtKc == null && fresh(Auto.UPDATE_KERNEL) -> Auto.UPDATE_KERNEL
            a.checkDue -> Auto.CHECK_RUNTIME
            else -> Auto.NONE
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

    /** "42 s", or "1 min 15 s" for elapsed progress counters. */
    fun elapsedWords(seconds: Int): String = if (seconds < 60) "$seconds s" else "${seconds / 60} min ${seconds % 60} s"

    /**
     * oneios-tool's progress, from its own events ([OneiosToolFlow]: `start`'s plan, `step`, `progress`): the bar is the
     * running step's `percent`, else its `done` of `total`, else the share of the plan's steps done; the phase is the
     * flow's own words or "Step k of N · <the step's text>"; the amount the tool's numbers (bytes, files, rate, time
     * left), or the latest tool output line while a step without byte counts (like prelink) runs, plus elapsed time.
     * A wait (a pause, no network, heat) is said in the amount.
     */
    fun toolProgress(
        view: OneiosToolFlow,
        phase: String? = null,
        held: String? = null,
        starting: Boolean = false,
        stopping: Boolean = false,
        detail: String? = null,
        detailFraction: Float? = null,
        elapsedSeconds: Int? = null,
    ): Progress {
        val steps = view.steps
        val at = steps.indexOfFirst { it.state == OneiosTool.StepState.RUNNING }
        val running = steps.getOrNull(at)
        val stepWords = running?.let { r -> "Step ${at + 1} of ${steps.size} · ${r.text ?: r.id}" }
        val own = view.percent?.let { (it / 100.0).toFloat() }
            ?: view.done?.let { d -> view.total?.takeIf { it > 0 }?.let { (d.toFloat() / it) } }
        val share = if (steps.isNotEmpty() && at >= 0) at.toFloat() / steps.size else null
        val fraction = (own ?: share ?: detailFraction)?.coerceIn(0f, 1f)
        val cleanDetail = detail?.takeIf { it.isNotBlank() }
        val words = when {
            stopping -> "Stopping…"
            starting -> cleanDetail ?: "Starting oneios-tool…"
            else -> listOfNotNull(phase, stepWords, if (stepWords == null) cleanDetail else null).distinct().joinToString(" · ").ifEmpty { "Working…" }
        }
        val lastLine = if (view.progressLine == null && !starting && !stopping) {
            view.lines.lastOrNull { it.isNotBlank() }?.trim()?.take(120)
        } else null
        val elapsed = elapsedSeconds?.takeIf { it >= 0 }?.let(::elapsedWords)
        val amount = listOfNotNull(held, view.progressLine ?: lastLine, elapsed).joinToString(" · ").ifEmpty { null }
        return Progress(fraction, words, amount)
    }

    private fun toolStepProgress(t: Tool): Progress =
        toolProgress(t.view, t.phase, t.held, t.starting, t.stopping, t.detail, t.detailFraction, t.elapsedSeconds)
}
