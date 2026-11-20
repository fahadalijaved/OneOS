package com.fahadali.oneos.session

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.os.SystemClock
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import com.fahadali.oneos.core.root.OneiosRoot
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
         * docs/TODO.md "Make iOS image": the IPSW's members from Apple's server by range requests (`fetch` with the
         * runtime's own profile; `resume`: a paused, stopped or interrupted fetch goes on from its parts), then the
         * tool's `make-image` (the released xnu.macho, the volumes, the tweaks, prelink, the audit and the stub check)
         * into `image.new`, which root's `begin image` made and root's `finish image` puts in place with today's checks.
         */
        MAKE_IMAGE(
            "work",
            listOf(
                Request(OneiosTool.Cmd.FETCH, mapOf("profile" to "$S/runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml", "indir" to "$S/make/inputs", "resume" to true)),
                Request(OneiosTool.Cmd.MAKE_IMAGE, mapOf("indir" to "$S/make/inputs", "out" to "$S/image.new", "sums_list" to "$S/image.new.sha256", "ids_list" to "$S/image.new.ids", "work" to "$S/make")),
                // Until the tool has make-image: its `tweaks` answers why the image set cannot be made on the phone
                // yet (`not-ported`), and the screen shows that answer beside make-image's. Drop it when make-image comes.
                Request(OneiosTool.Cmd.TWEAKS),
            ),
            showAll = true,
        ),

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
         * The phone-built kernel: `prelink build` from the staged runtime's xnu, the staged kernelcache and the
         * staged kb/ inputs into `make-kernel/out` (the audit and the stub check gate what lands there). The kernel
         * is activated by [OneiosJob.activateKernel], never by this flow: the screen shows the build's report first.
         * Not run on the phone yet (docs/oneios.md, "Kernel updates").
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
            root(app, OneiosRoot.Verb.STATUS, emptyList(), 180_000)?.let { return problem(it) }
            if (flow == Flow.MAKE_IMAGE) root(app, OneiosRoot.Verb.BEGIN, listOf("image"), 120_000)?.let { return problem(it) }
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
                    is OneiosToolSession.Start.Ready -> update(state.copy(
                        starting = false, canPause = st.hello.cmds.containsAll(listOf(OneiosTool.Cmd.PAUSE, OneiosTool.Cmd.RESUME)),
                        toolVersion = listOfNotNull(st.hello.tool, st.hello.jobs?.let { "$it threads" }).joinToString(" · "),
                    ))
                }
                if (state.canPause) watch = watchNetwork(app)
                val requests = if (flow == Flow.KERNEL) {
                    kernelRequests(OneiosJob.stagedKernelPath(app) ?: "kernel/xnu.macho", S)
                } else {
                    flow.requests
                }
                for ((i, r) in requests.withIndex()) {
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
                    if (r.cmd == OneiosTool.Cmd.MAKE_IMAGE) finishImage(app, view.result.orEmpty())
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

    /** Make iOS image's last step: root's `finish image` with what the tool's result says the set is (today's checks). */
    private fun finishImage(app: Context, result: Map<String, Any?>) {
        val args = listOf("files", "format", "version", "build").map { k -> result[k]?.toString() ?: return problem("the tool's result has no '$k' for root's finish") }
        val p = runCatching { OneiosRoot.problems(OneiosRoot.Verb.FINISH, listOf("image") + args) }.getOrDefault(listOf("bad"))
        if (p.isNotEmpty()) return problem("the tool's result cannot go to root's finish: ${p.joinToString("; ")}")
        root(app, OneiosRoot.Verb.FINISH, listOf("image") + args, 10 * 60_000L)?.let { return problem(it) }
        update(state.copy(results = state.results + "iOS ${args[2]} (${args[3]}) is staged: ${args[0]} files"))
    }

    private fun problem(why: String) {
        update(state.copy(problem = why, starting = false))
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

    /** Stop: the tool's cancel for the request; the session itself when the tool does not answer in time. */
    fun cancel() {
        if (!state.busy) return
        stop = true
        update(state.copy(stopping = true))
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
    private fun root(app: Context, verb: OneiosRoot.Verb, args: List<String>, limitMs: Long): String? = try {
        val command = OneiosRoot.launcher(verb, args, BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES)
        val input = if (verb.stdin == OneiosRoot.Stdin.SCRIPT) {
            val script = OneiosJob.rootScript(app)
            RootShell.Feed { it.write(script) }
        } else null
        val reply = RootReply()
        val end = RootShell(command).run(input, { reply.accept(it) }, { limitMs }, limitMs)
        if (end.exitCode == 0 && reply.ok != null && end.error == null) null
        else end.error ?: reply.problem(end.exitCode) ?: "no answer from root"
    } catch (e: Exception) {
        e.message ?: e.javaClass.simpleName
    }

    private const val CANCEL_WAIT_MS = 15_000L
}

/**
 * The `prelink` request for [xnuPath] (the staged runtime's kernel, as its runtime.json names it).
 * Keys are [OneiosTool.prelinkRequest]'s; this only wraps them for a flow.
 */
private fun kernelRequests(xnuPath: String, stage: String): List<OneiosToolJob.Request> =
    listOf(OneiosTool.prelinkRequest(xnuPath, stage).let { (cmd, keys) -> OneiosToolJob.Request(cmd, keys) })
