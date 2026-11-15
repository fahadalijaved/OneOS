package com.fahadali.oneos.session

import android.content.Context
import android.os.SystemClock
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import com.fahadali.oneos.core.root.OneiosRoot
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
 * with `ok`, and shows that request's reason.
 *
 * While a flow runs [OneiosService] keeps the app alive (and the CPU awake), as for an import.
 */
object OneiosToolJob : BackgroundJob<OneiosToolJob.State>(State(), "oneos-oneios-tool") {
    private const val S = OneiosSystem.STAGE

    /** One request of a flow: the tool's command and its keys (the tool's README). */
    data class Request(val cmd: String, val keys: Map<String, Any?> = emptyMap())

    /** What the app asks the tool for; [mode] is root's `tool` argument (read: allowed during a session). */
    enum class Flow(val mode: String, val requests: List<Request>) {
        /**
         * docs/TODO.md "Make iOS image": the tool's `make-image` (the released xnu.macho, Apple's IPSW members by
         * range requests, the volumes, the tweaks, prelink, the audit and the stub check) into `image.new`, which
         * root's `begin image` made and root's `finish image` puts in place with today's checks.
         */
        MAKE_IMAGE("work", listOf(Request(OneiosTool.Cmd.MAKE_IMAGE, mapOf("out" to "$S/image.new", "sums_list" to "$S/image.new.sha256", "ids_list" to "$S/image.new.ids", "work" to "$S/make")))),

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
        val starting: Boolean = false,
        val stopping: Boolean = false,
        /** Why the flow could not start or root's own step refused (its words). */
        val problem: String? = null,
        /** Each finished request's last line for the screen: its `text`. */
        val results: List<String> = emptyList(),
    ) {
        val busy: Boolean get() = flow != null
    }

    @Volatile private var session: OneiosToolSession? = null

    @Volatile private var requestId: String? = null

    @Volatile private var stop = false

    fun canStart(): Boolean = !state.busy && OneiosJob.canStart() && !OneiosChecksJob.state.busy

    fun run(ctx: Context, flow: Flow) {
        if (!canStart()) return
        val app = ctx.applicationContext
        stop = false
        requestId = null
        update(State(flow = flow, last = flow, starting = true))
        // From the screen the user tapped: Android lets only a visible app start the service.
        OneiosService.start(app)
        executor.execute { work(app, flow) }
    }

    private fun work(app: Context, flow: Flow) {
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
                    is OneiosToolSession.Start.Ready -> update(state.copy(starting = false, toolVersion = listOfNotNull(st.hello.tool, st.hello.jobs?.let { "$it threads" }).joinToString(" · ")))
                }
                for ((i, r) in flow.requests.withIndex()) {
                    if (stop) break
                    val view = one(s, i + 1, r)
                    if (view.end != OneiosToolFlow.End.OK) return
                    update(state.copy(results = state.results + (view.text ?: r.cmd)))
                    if (flow == Flow.MAKE_IMAGE) finishImage(app, view.result.orEmpty())
                }
            } finally {
                s.close()
                session = null
                requestId = null
            }
        } finally {
            update(state.copy(flow = null, starting = false, stopping = false))
        }
    }

    /** One request, its lines folded into the screen's view: steps and the end at once, progress four times a second. */
    private fun one(s: OneiosToolSession, n: Int, r: Request): OneiosToolFlow {
        var view = OneiosToolFlow()
        var shown = 0L
        update(state.copy(request = n, view = view))
        val end = s.call(r.cmd, r.keys, onId = { id -> requestId = id; if (stop) s.cancel(id) }) { e ->
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
