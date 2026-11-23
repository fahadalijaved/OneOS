package com.fahadali.oneos.session

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.os.SystemClock
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.OneiosImageChoice
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosManifests
import com.fahadali.oneos.core.model.OneiosMessage
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.OneiosKernelUpdate
import com.fahadali.oneos.core.root.OneiosMakeImage
import com.fahadali.oneos.core.root.OneiosRoot
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.core.root.OneiosToolPause
import com.fahadali.oneos.core.root.OneiosToolSession
import com.fahadali.oneos.core.root.RootReply
import com.fahadali.oneos.core.root.RootShell

/**
 * The flows OneiOS's Rust tools run on the phone (docs/oneios.md, "oneios-tool in the app"): one
 * `oneios-tool serve` of the staged runtime per flow ([OneiosToolSession], root's `tool work|read`), its requests
 * sent in a fixed order, every line shown as it comes ([OneiosToolFlow]). The tool does the work, the checks and
 * the step decisions, on all cores at nice 10 with its own heat stop; this job only starts it on its own thread,
 * sends the requests, passes on what it says, and ends it: when the flow ends, on Stop (the tool's cancel; the
 * session is ended if the tool does not answer within [CANCEL_WAIT_MS]), and when [OneiosService] stops. A tool
 * that does not end by itself is ended by root's `untool`. A flow stops at the first request that does not end
 * with `ok`, and shows that request's reason ([Flow.showAll]: every request's answer is shown).
 *
 * Pause and Resume: the user's buttons and Android's default network ([OneiosToolPause]) send the tool `pause` and
 * `resume` for the running request; how a download waits, retries and keeps its parts is the tool's. A flow that was
 * running when the app was ended is remembered ([interrupted]); started again, its requests carry `resume` where the
 * tool takes it, so the tool goes on from what it kept.
 *
 * While a flow runs [OneiosService] keeps the app alive (and the CPU awake), as for an import.
 */
object OneiosToolJob : BackgroundJob<OneiosToolJob.State>(State(), "oneos-oneios-tool") {
    private const val S = OneiosSystem.STAGE
    private const val PREFS = "oneios-tool"
    private const val KEY_RUNNING = "running"

    /** One request of a flow: the tool's command and its keys (the tool's README). */
    data class Request(val cmd: String, val keys: Map<String, Any?> = emptyMap())

    /** What the app asks the tool for; [mode] is root's `tool` argument (read: allowed during a session). */
    enum class Flow(val mode: String, val requests: List<Request>, val showAll: Boolean = false) {
        /**
         * Make iOS image, with no PC ([OneiosMakeImage]; docs/oneios.md, "Make iOS image"): root's `status` (and the
         * latest OneiOS runtime first when the staged one carries no kernel or its tool has no `make-image`), the
         * pairing files into `kb/` (root's `kbinput` ×12), root's `begin image`, then the tool's one `make-image`
         * (fetch from Apple, decrypt, the volumes, the root tweaks, the seed, the kernelcache, the prelink with its
         * audit, the manifest, verify, the lists) into `image.new`, and root's `finish image` with its result's four
         * fields. No `fetch` before it (make-image fetches, after its one room check) and no `tweaks` after it
         * (make-image runs them). [requests] is the tool's part; the run itself is [OneiosMakeImage]'s.
         */
        MAKE_IMAGE("work", listOf(OneiosTool.makeImageRequest(S).let { (cmd, keys) -> Request(cmd, keys) })),

        /** Every file of the staged runtime and image set hashed again against the lists root wrote at staging. */
        SUMS("read", listOf(
            Request(OneiosTool.Cmd.SUMS, mapOf("dir" to "$S/runtime", "list" to "$S/runtime.sha256", "strict" to true)),
            Request(OneiosTool.Cmd.SUMS, mapOf("dir" to "$S/image", "list" to "$S/image.sha256", "strict" to true)),
        )),

        /** `phone cpu` on the phone: cores, domains, clocks and their caps, cpusets, xnuhost in a session. */
        CPU("read", listOf(Request(OneiosTool.Cmd.CPU))),

        /** `phone log` on the phone: the stage's logs, then the last session's xnuhost log. */
        LOG("read", listOf(Request(OneiosTool.Cmd.LOG_LIST), Request(OneiosTool.Cmd.LOG, mapOf("file" to "xnuhost", "tail" to 4000)))),

        /** iOS's own log (the unified log in iOS's Data store): the boots it holds. */
        IOSLOG_BOOTS("read", listOf(Request(OneiosTool.Cmd.IOSLOG_BOOTS, mapOf("source" to "$S/data/data.img")))),

        /** iOS's own log of its last boot, as text lines. */
        IOSLOG_SHOW("read", listOf(Request(OneiosTool.Cmd.IOSLOG_SHOW, mapOf("source" to "$S/data/data.img", "boot" to "last", "format" to "text")))),

        /**
         * Update the kernel, with no PC ([OneiosKernelUpdate]; docs/oneios.md, "Kernel updates"): root's `kbinput`
         * of the app's pairing files, then, unless `kb/kernelcache.macho` is already the pinned one, the tool's
         * `fetch` of the profile's kernelcache member from Apple and its `im4p`, the pin, root's `kbcache`; then
         * the tool's `prelink` into `make-kernel/out` (the audit and the stub check gate what lands there). The
         * kernel is activated by [OneiosJob.activateKernel], never by this flow: the screen shows the build's
         * result first. [requests] is the run with no kernelcache on the phone yet. Not run on the phone yet.
         */
        KERNEL("work", kernelRequests("kernel/xnu.macho", S)),
    }

    data class State(
        /** The flow that runs now; null when idle. */
        val flow: Flow? = null,
        /** The flow that ran last (or runs now). */
        val last: Flow? = null,
        /** The request that runs now (1-based) of the flow's [Flow.requests]. */
        val request: Int = 0,
        val view: OneiosToolFlow = OneiosToolFlow(),
        /** The tool's version and threads (its hello). */
        val toolVersion: String? = null,
        /** The tool takes `pause` and `resume` (its hello's `cmds`). */
        val canPause: Boolean = false,
        /** The user's Pause holds the running request. */
        val pausedByUser: Boolean = false,
        /** Android has no default network now (the tool says its own in [OneiosToolFlow.netWaiting]). */
        val noNetwork: Boolean = false,
        val starting: Boolean = false,
        val stopping: Boolean = false,
        /** Why the flow could not start or root's own step refused (its words). */
        val problem: String? = null,
        /** Each finished request's last line for the screen: its `text`. */
        val results: List<String> = emptyList(),
        /** Each request that did not end with `ok`: "cmd: code: the tool's text". */
        val refusals: List<String> = emptyList(),
        /** The last request's result object (the `ok`'s fields): the kernel build's `sha256`, `bytes`. */
        val lastResult: Map<String, Any?> = emptyMap(),
        /** Update the kernel: what runs now (the tool's request, or root's step of it); null for other flows. */
        val kernelPhase: OneiosKernelUpdate.Phase? = null,
        /** Update the kernel or Make iOS image: why it stopped, in plain words ([OneiosPlain.kernelUpdate], [OneiosPlain.makeImage]); null while it runs or when it ended well. */
        val plain: OneiosMessage? = null,
        /** Update the kernel: the SHA-256 of the kernel.kc it built (in `make-kernel/out`, for root's `finish kernel`). */
        val builtKc: String? = null,
        /** Make iOS image: what runs now (root's step, the runtime's download, the tool's make-image); null for other flows. */
        val makePhase: OneiosMakeImage.Phase? = null,
    ) {
        val busy: Boolean get() = flow != null
    }

    @Volatile private var session: OneiosToolSession? = null

    @Volatile private var requestId: String? = null

    @Volatile private var stop = false

    @Volatile private var pause: OneiosToolPause? = null

    fun canStart(): Boolean = !state.busy && OneiosJob.canStart() && !OneiosChecksJob.state.busy

    /** The flow that was running when the app was last ended (by Android, a crash, a swipe); null when none. */
    fun interrupted(ctx: Context): Flow? = if (state.busy) null else
        ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_RUNNING, null)
            ?.let { name -> Flow.entries.firstOrNull { it.name == name } }

    /** Forget an interrupted flow without starting it again. */
    fun forget(ctx: Context) = remember(ctx.applicationContext, null)

    private fun remember(app: Context, flow: Flow?) {
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().apply {
            if (flow == null) remove(KEY_RUNNING) else putString(KEY_RUNNING, flow.name)
        }.commit()
    }

    fun run(ctx: Context, flow: Flow) {
        if (!canStart()) return
        val app = ctx.applicationContext
        stop = false
        requestId = null
        remember(app, flow)
        update(State(flow = flow, last = flow, starting = true))
        // From the screen the user tapped: Android lets only a visible app start the service.
        OneiosService.start(app)
        executor.execute { work(app, flow) }
    }

    private fun work(app: Context, flow: Flow) {
        var watch: (() -> Unit)? = null
        // False only when the tool went away in the middle of a request: then the flow stays remembered for a Resume.
        var answered = true
        try {
            // This build's root script in the stage first (status installs it, as the checks do).
            val (statusProblem, statusLines) = rootReply(app, OneiosRoot.Verb.STATUS, emptyList(), 180_000)
            statusProblem?.let { return problem(it) }
            // Update the kernel: what it needs before the tool starts (an image set of the pinned build, a runtime with a kernel).
            val status = OneiosStatus.parse(statusLines)
            val kernel = if (flow == Flow.KERNEL) kernelUpdate(app, status) ?: return else null
            // Make iOS image: its own order, its tool sessions its own ([OneiosMakeImage]).
            if (flow == Flow.MAKE_IMAGE) {
                answered = runMake(app, status)
                return
            }
            val s = OneiosToolSession(
                OneiosRoot.launcher(OneiosRoot.Verb.TOOL, listOf(flow.mode), BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES),
                backstop = { root(app, OneiosRoot.Verb.UNTOOL, emptyList(), 60_000) },
            )
            session = s
            try {
                if (stop) return problem("stopped")
                when (val st = s.start()) {
                    is OneiosToolSession.Start.Refused -> return problem(st.reason)
                    is OneiosToolSession.Start.Failed -> return problem(st.reason)
                    is OneiosToolSession.Start.Ready -> {
                        // Update the kernel prelinks with this app's pairing files: a tool of an older format cannot read them.
                        if (kernel != null && st.hello.kb < OneiosKb.FORMAT) {
                            return problem("the staged runtime's oneios-tool reads pairing files of format ${st.hello.kb}; this app's are format ${OneiosKb.FORMAT}: get the latest OneiOS runtime, then update the kernel")
                        }
                        update(state.copy(
                            starting = false, canPause = st.hello.cmds.containsAll(listOf(OneiosTool.Cmd.PAUSE, OneiosTool.Cmd.RESUME)),
                            toolVersion = listOfNotNull(st.hello.tool, st.hello.jobs?.let { "$it threads" }).joinToString(" · "),
                        ))
                    }
                }
                if (state.canPause) watch = watchNetwork(app)
                if (kernel != null) {
                    answered = runKernel(app, s, kernel, status)
                    return
                }
                for ((i, r) in flow.requests.withIndex()) {
                    if (stop) break
                    val view = one(s, i + 1, r)
                    if (view.end != OneiosToolFlow.End.OK) {
                        // The tool's own words for what it would not or could not do, with its code.
                        update(state.copy(refusals = state.refusals + listOfNotNull(r.cmd, view.code, view.text).joinToString(": ")))
                        if (view.end == OneiosToolFlow.End.LOST) { answered = false; return }
                        if (!flow.showAll || view.end == OneiosToolFlow.End.CANCELLED) return
                        continue
                    }
                    update(state.copy(results = state.results + (view.text ?: r.cmd), lastResult = view.result.orEmpty()))
                }
            } finally {
                watch?.invoke()
                pause = null
                s.close()
                session = null
                requestId = null
            }
        } finally {
            if (answered) remember(app, null)
            update(state.copy(flow = null, starting = false, stopping = false, pausedByUser = false))
        }
    }

    /** One request, its lines folded into the screen's view: steps and the end at once, progress four times a second. */
    private fun one(s: OneiosToolSession, n: Int, r: Request): OneiosToolFlow {
        var view = OneiosToolFlow()
        var shown = 0L
        update(state.copy(request = n, view = view))
        val end = s.call(r.cmd, r.keys, onId = { id ->
            requestId = id
            pause = OneiosToolPause { hold -> if (hold) s.pause(id) else s.resume(id) }.also { p ->
                if (state.pausedByUser) p.userPause()
                if (state.noNetwork) p.networkLost()
            }
            if (stop) s.cancel(id)
        }) { e ->
            view = view.with(e)
            val now = SystemClock.elapsedRealtime()
            if (e !is OneiosTool.Event.Progress || now - shown >= 250) {
                shown = now
                update(state.copy(view = view))
            }
        }
        if (end == null) view = view.lost(s.ended ?: "the tool ended")
        update(state.copy(view = view))
        return view
    }

    /**
     * Android's default network for the flow's length: lost, the running request is paused; back, it is resumed
     * unless the user paused it ([OneiosToolPause]). Returns the call that stops watching.
     */
    private fun watchNetwork(app: Context): () -> Unit {
        val cm = app.getSystemService(ConnectivityManager::class.java) ?: return {}
        val cb = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                update(state.copy(noNetwork = false))
                pause?.networkBack()
            }

            override fun onLost(network: Network) {
                // The default network is gone; when another takes over, onAvailable comes again.
                update(state.copy(noNetwork = true))
                pause?.networkLost()
            }
        }
        if (cm.activeNetwork == null) update(state.copy(noNetwork = true))
        try {
            cm.registerDefaultNetworkCallback(cb)
        } catch (_: RuntimeException) {
            return {}
        }
        return { runCatching { cm.unregisterNetworkCallback(cb) }; Unit }
    }

    /** Update the kernel for the staged pair, or null (and the reason on the screen) when it cannot start. */
    private fun kernelUpdate(app: Context, st: OneiosStatus): OneiosKernelUpdate? {
        val kb = try {
            OneiosJob.kbInputs(app)
        } catch (e: Exception) {
            problem(e.message ?: "the app's kernel-build inputs cannot be read: reinstall OneOS")
            return null
        }
        OneiosManifests.updateProblem(st.image?.build, kb, st.runtimeKernel != null)?.let { problem(it); return null }
        val assets = try {
            OneiosJob.kbAssets(app)
        } catch (e: java.io.IOException) {
            problem("the app's kb/ files cannot be read (${e.message}): reinstall OneOS")
            return null
        }
        return OneiosKernelUpdate(S, kb, OneiosJob.stagedKernelPath(app) ?: "kernel/xnu.macho", assets)
    }

    /**
     * Update the kernel on the open tool session ([OneiosKernelUpdate] decides the steps): each tool request shown
     * as any flow's, root's steps on their own `su`. Returns false when the tool went away in a request (the flow
     * stays remembered, and its next run goes on from the download's parts).
     */
    private fun runKernel(app: Context, s: OneiosToolSession, kernel: OneiosKernelUpdate, st: OneiosStatus): Boolean {
        var n = 0
        val io = object : OneiosKernelUpdate.Io {
            override fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow {
                n += 1
                val view = one(s, n, Request(cmd, keys))
                if (view.end == OneiosToolFlow.End.OK) update(state.copy(results = state.results + (view.text ?: cmd)))
                return view
            }

            override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? =
                rootReply(app, verb, args, 10 * 60_000L, data).first

            override fun phase(phase: OneiosKernelUpdate.Phase) = update(state.copy(kernelPhase = phase))

            override fun done(line: String) = update(state.copy(results = state.results + line))

            override val stopped: Boolean get() = stop
        }
        return when (val o = kernel.run(io, st.kb.kernelcacheSha256)) {
            is OneiosKernelUpdate.Outcome.Built -> {
                update(state.copy(builtKc = o.sha256, lastResult = mapOf("sha256" to o.sha256, "bytes" to o.bytes), kernelPhase = null))
                true
            }
            is OneiosKernelUpdate.Outcome.Stopped -> {
                update(state.copy(
                    refusals = state.refusals + listOfNotNull(o.step, o.code, o.text).joinToString(": "),
                    plain = OneiosPlain.kernelUpdate(o.step, o.end, o.code, o.text, o.cleaned),
                    lastResult = emptyMap(), kernelPhase = null,
                ))
                o.end != OneiosToolFlow.End.LOST
            }
        }
    }

    /**
     * Make iOS image ([OneiosMakeImage] decides the order): root's steps on their own `su`, the latest runtime by
     * [OneiosJob.stageLatestForMakeImage] (no tool session is open then), each tool request shown as any flow's.
     * [first] is the status [work] read (it installed this build's root script). Returns false when the tool went
     * away in a request (the flow stays remembered; its next run goes on from the fetched parts).
     */
    private fun runMake(app: Context, first: OneiosStatus): Boolean {
        val kb = try {
            OneiosJob.kbInputs(app)
        } catch (e: Exception) {
            problem(e.message ?: "the app's kernel-build inputs cannot be read: reinstall OneOS")
            return true
        }
        val assets = try {
            OneiosJob.kbAssets(app)
        } catch (e: java.io.IOException) {
            problem("the app's kb/ files cannot be read (${e.message}): reinstall OneOS")
            return true
        }
        var cached: OneiosStatus? = first
        var watch: (() -> Unit)? = null
        var n = 0
        fun close() {
            watch?.invoke()
            watch = null
            pause = null
            session?.close()
            session = null
            requestId = null
        }
        val io = object : OneiosMakeImage.Io {
            override fun status(): Result<OneiosStatus> {
                cached?.let { cached = null; return Result.success(it) }
                val (why, lines) = rootReply(app, OneiosRoot.Verb.STATUS, emptyList(), 180_000)
                return if (why != null) Result.failure(java.io.IOException(why)) else Result.success(OneiosStatus.parse(lines))
            }

            override fun latestRuntime(unless: String?): OneiosMakeImage.Runtime = OneiosJob.stageLatestForMakeImage(app, unless)

            override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? =
                rootReply(app, verb, args, 10 * 60_000L, data).first

            override fun openTool(): Result<List<String>> {
                val s = OneiosToolSession(
                    OneiosRoot.launcher(OneiosRoot.Verb.TOOL, listOf(Flow.MAKE_IMAGE.mode), BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES),
                    backstop = { root(app, OneiosRoot.Verb.UNTOOL, emptyList(), 60_000) },
                )
                session = s
                if (stop) return Result.failure(java.io.IOException("stopped"))
                return when (val st = s.start()) {
                    is OneiosToolSession.Start.Refused -> Result.failure(java.io.IOException(st.reason))
                    is OneiosToolSession.Start.Failed -> Result.failure(java.io.IOException(st.reason))
                    is OneiosToolSession.Start.Ready -> {
                        update(state.copy(
                            canPause = st.hello.cmds.containsAll(listOf(OneiosTool.Cmd.PAUSE, OneiosTool.Cmd.RESUME)),
                            toolVersion = listOfNotNull(st.hello.tool, st.hello.jobs?.let { "$it threads" }).joinToString(" · "),
                        ))
                        if (state.canPause && watch == null) watch = watchNetwork(app)
                        // A tool that cannot read this app's pairing files (an older kb format) cannot make the image
                        // either: it counts as one without make-image, so the newest runtime is staged once.
                        Result.success(if (st.hello.kb < OneiosKb.FORMAT) st.hello.cmds - OneiosTool.Cmd.MAKE_IMAGE else st.hello.cmds)
                    }
                }
            }

            override fun closeTool() = close()

            override fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow {
                val s = session ?: return OneiosToolFlow(cmd = cmd).lost("the tool is not running")
                n += 1
                val view = one(s, n, Request(cmd, keys))
                if (view.end == OneiosToolFlow.End.OK) update(state.copy(results = state.results + (view.text ?: cmd), lastResult = view.result.orEmpty()))
                return view
            }

            override fun phase(phase: OneiosMakeImage.Phase) = update(state.copy(makePhase = phase, starting = false))

            override fun done(line: String) = update(state.copy(results = state.results + line))

            override val stopped: Boolean get() = stop
        }
        try {
            // The image this phone makes: iOS 16.5 on the Galaxy A56 (untested there), iOS 27 on every other phone.
            val image = OneiosImageChoice.of(OneiosJob.phoneProfile(app))
            return when (val o = OneiosMakeImage(S, kb, assets, image).run(io)) {
                is OneiosMakeImage.Outcome.Staged -> {
                    update(state.copy(
                        results = state.results + "iOS ${o.version} (${o.build}) is staged: ${o.files} files${o.bytes?.let { ", ${Units.bytes(it)}" }.orEmpty()}.",
                        makePhase = null,
                    ))
                    close()
                    // The iOS screens: the new image set, and what is next (the switch).
                    rootReply(app, OneiosRoot.Verb.STATUS, emptyList(), 180_000).let { (why, lines) -> if (why == null) OneiosJob.statusRead(app, OneiosStatus.parse(lines)) }
                    true
                }
                is OneiosMakeImage.Outcome.Stopped -> {
                    update(state.copy(
                        refusals = state.refusals + listOfNotNull(o.step, o.code, o.text).joinToString(": "),
                        plain = OneiosPlain.makeImage(o.step, o.end, o.code, o.text, o.need, o.free),
                        makePhase = null,
                    ))
                    o.end != OneiosToolFlow.End.LOST
                }
            }
        } finally {
            close()
        }
    }

    private fun problem(why: String) {
        update(state.copy(problem = why, starting = false))
    }

    /** Activate was tapped for the kernel the update built: the button goes (root's `finish kernel` uses `make-kernel/out` up). */
    fun kernelActivating() {
        if (!state.busy) update(state.copy(builtKc = null))
    }

    /** Pause on the screen: the tool holds the running request where it is. */
    fun pauseByUser() {
        if (!state.busy || !state.canPause) return
        update(state.copy(pausedByUser = true))
        pause?.userPause()
    }

    /** Resume on the screen (a lost network may still hold it: the tool then waits for it). */
    fun resumeByUser() {
        if (!state.busy) return
        update(state.copy(pausedByUser = false))
        pause?.userResume()
    }

    /**
     * Stop: the tool's cancel for the request; the session itself when the tool does not answer in time. During
     * Make iOS image's runtime download (no tool runs then) the download's own Stop.
     */
    fun cancel() {
        if (!state.busy) return
        stop = true
        update(state.copy(stopping = true))
        if (state.makePhase == OneiosMakeImage.Phase.RUNTIME) OneiosJob.cancel()
        val s = session ?: return
        requestId?.let { s.cancel(it) }
        Thread({
            Thread.sleep(CANCEL_WAIT_MS)
            if (session === s) s.close()
        }, "oneios-tool-cancel").apply { isDaemon = true }.start()
    }

    /** [OneiosService] stopped (Android's time limit, the app going away): the flow ends with it. */
    fun serviceStopped() {
        val s = session ?: return
        stop = true
        Thread({ s.close() }, "oneios-tool-close").apply { isDaemon = true }.start()
    }

    /** One root verb of oneios_root.sh; null when it worked, else why not. */
    private fun root(app: Context, verb: OneiosRoot.Verb, args: List<String>, limitMs: Long): String? = rootReply(app, verb, args, limitMs).first

    /** [root], and the verb's `@@RESULT` lines (`status`'s). [data]: the verb's stdin (`kbinput`). */
    private fun rootReply(app: Context, verb: OneiosRoot.Verb, args: List<String>, limitMs: Long, data: ByteArray? = null): Pair<String?, List<String>> = try {
        val command = OneiosRoot.launcher(verb, args, BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES)
        val input = when (verb.stdin) {
            OneiosRoot.Stdin.SCRIPT -> OneiosJob.rootScript(app).let { script -> RootShell.Feed { it.write(script) } }
            OneiosRoot.Stdin.DATA -> requireNotNull(data) { "${verb.word} needs its data" }.let { bytes -> RootShell.Feed { it.write(bytes) } }
            OneiosRoot.Stdin.NONE -> null
        }
        val reply = RootReply()
        val end = RootShell(command).run(input, { reply.accept(it) }, { limitMs }, limitMs)
        val why = if (end.exitCode == 0 && reply.ok != null && end.error == null) null
        else end.error ?: reply.problem(end.exitCode) ?: "no answer from root"
        why to reply.results.toList()
    } catch (e: Exception) {
        (e.message ?: e.javaClass.simpleName) to emptyList()
    }

    private const val CANCEL_WAIT_MS = 15_000L
}

/**
 * Update the kernel's tool requests with no kernelcache on the phone yet (`fetch`, `im4p`, `prelink` for [xnuPath],
 * the staged runtime's kernel), for [OneiosToolJob.Flow.KERNEL]'s list. The run itself is [OneiosKernelUpdate]'s.
 */
private fun kernelRequests(xnuPath: String, stage: String): List<OneiosToolJob.Request> =
    OneiosKernelUpdate.toolRequests(stage, xnuPath, cached = false)
        .map { (cmd, keys) -> OneiosToolJob.Request(cmd, keys) }
