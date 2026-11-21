package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Make iOS image's order and its rules ([OneiosMakeImage]; docs/oneios.md, "Make iOS image"), against a stand-in of
 * root, the release download and the tool that records what was asked: a fresh phone gets the runtime first, a
 * runtime with a kernel does not; the pairing files, `begin image`, the one `make-image` with the app's keys and
 * root's `finish image` with its result's four fields, in that order; no `fetch` and no `tweaks`; a tool without
 * `make-image` gets the newest runtime once; every refusal and a Stop end the flow where they come, and nothing after
 * them is asked. OneiosScriptTest runs the same flow against the real tool when one is given.
 */
class OneiosMakeImageTest {
    private val stage = "/data/local/tmp/oneios"
    private val names = OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }
    private val assets = names.associateWith { "kb-$it".toByteArray() }
    private val kb = OneiosKb("24A446", "iPhone18,2", "3".repeat(64), assets.mapValues { Hashes.sha256(it.value) })
    private val inputs = names.sorted().map { "kbinput $it" }

    private val none = OneiosStatus(staged = false)
    private val oldRuntime = OneiosStatus(staged = true, runtime = OneiosStatus.Runtime("0.1.11", "1", "bin/xnuhost", "1"))
    private val withKernel = OneiosStatus(
        staged = true, runtime = OneiosStatus.Runtime("0.1.12", "1", "bin/xnuhost", "1"), runtimeKernel = OneiosStatus.Kernel("xnu-12377-v54-326e2144aaaa", "12377"),
    )
    private val newer = withKernel.copy(runtime = withKernel.runtime!!.copy(version = "0.1.13"))
    private val withMake = listOf("ping", "fetch", "prelink", OneiosTool.Cmd.MAKE_IMAGE, "pause", "resume")
    private val withoutMake = withMake - OneiosTool.Cmd.MAKE_IMAGE

    private val made = OneiosToolFlow(
        end = OneiosToolFlow.End.OK, text = "iOS 27.0.1 (24A446): 21 files, 13.2 GB, checked",
        result = mapOf(
            "files" to 21L, "format" to 1L, "version" to "27.0.1", "build" to "24A446", "out" to "$stage/image.new",
            "bytes" to 13_200_000_000L, "manifest_sha256" to "a".repeat(64), "seed_sha256" to "b".repeat(64), "kernel_sha256" to "c".repeat(64),
        ),
    )

    private class Fake(
        statuses: List<OneiosStatus>,
        val runtimes: List<OneiosMakeImage.Runtime> = emptyList(),
        val tools: List<List<String>> = emptyList(),
        val makeImage: OneiosToolFlow? = null,
        val roots: Map<OneiosRoot.Verb, String?> = emptyMap(),
        val stopAfter: String? = null,
    ) : OneiosMakeImage.Io {
        private val statuses = ArrayDeque(statuses)
        private val runtimeAnswers = ArrayDeque(runtimes)
        private val toolAnswers = ArrayDeque(tools)
        val asked = mutableListOf<String>()
        val keys = mutableListOf<Map<String, Any?>>()
        val phases = mutableListOf<OneiosMakeImage.Phase>()
        val lines = mutableListOf<String>()
        var stop = false

        private fun ask(what: String) {
            asked += what
            if (what == stopAfter) stop = true
        }

        override fun status(): Result<OneiosStatus> {
            ask("status")
            return statuses.removeFirstOrNull()?.let { Result.success(it) } ?: Result.failure(IllegalStateException("root did not answer"))
        }

        override fun latestRuntime(unless: String?): OneiosMakeImage.Runtime {
            ask("runtime ${unless ?: "-"}")
            return runtimeAnswers.removeFirstOrNull() ?: error("no runtime answer")
        }

        override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? {
            ask(if (verb == OneiosRoot.Verb.KBINPUT) "kbinput ${args[0]}" else (listOf(verb.word) + args).joinToString(" "))
            if (verb == OneiosRoot.Verb.KBINPUT) {
                assertEquals(args[1], data!!.size.toString())
                assertEquals(args[2], Hashes.sha256(data))
            }
            return roots[verb]
        }

        override fun openTool(): Result<List<String>> {
            ask("tool")
            return toolAnswers.removeFirstOrNull()?.let { Result.success(it) } ?: Result.failure(IllegalStateException("this runtime has no bin/oneios-tool: get a newer runtime"))
        }

        override fun closeTool() = ask("close")

        override fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow {
            ask(cmd)
            this.keys += keys
            return when (cmd) {
                OneiosTool.Cmd.MAKE_IMAGE -> makeImage ?: error("no answer for $cmd")
                else -> error("the flow sends only make-image, not $cmd")
            }
        }

        override fun phase(phase: OneiosMakeImage.Phase) {
            phases += phase
        }

        override fun done(line: String) {
            lines += line
        }

        override val stopped: Boolean get() = stop
    }

    private fun flow() = OneiosMakeImage(stage, kb, assets)

    private val finish = "finish image 21 1 27.0.1 24A446"
    private val tail = inputs + listOf("begin image", "tool", "make-image", finish)

    @Test
    fun aFreshPhoneGetsTheRuntimeThenMakesAndStagesTheImage() {
        val io = Fake(listOf(none, withKernel), runtimes = listOf(OneiosMakeImage.Runtime.Staged("0.1.12")), tools = listOf(withMake), makeImage = made)
        val o = flow().run(io)
        assertEquals(OneiosMakeImage.Outcome.Staged(21, 1, "27.0.1", "24A446", 13_200_000_000L, "a".repeat(64)), o)
        assertEquals(listOf("status", "runtime -", "status") + tail, io.asked)
        // The tool gets exactly the app's request (interface.md section 9): no fetch before it, no tweaks after it.
        assertEquals(listOf(OneiosTool.makeImageRequest(stage).second), io.keys)
        assertFalse(io.asked.any { it == OneiosTool.Cmd.FETCH || it == OneiosTool.Cmd.TWEAKS })
        assertEquals(
            listOf(OneiosMakeImage.Phase.STATUS, OneiosMakeImage.Phase.RUNTIME, OneiosMakeImage.Phase.INPUTS, OneiosMakeImage.Phase.BEGIN,
                OneiosMakeImage.Phase.TOOL, OneiosMakeImage.Phase.BUILD, OneiosMakeImage.Phase.FINISH),
            io.phases,
        )
        assertTrue(io.lines.toString(), io.lines.any { "0.1.12 is staged" in it } && io.lines.any { "pairing files" in it })
    }

    @Test
    fun aRuntimeWithAKernelIsNotDownloadedAgain() {
        val io = Fake(listOf(withKernel), tools = listOf(withMake), makeImage = made)
        assertTrue(flow().run(io) is OneiosMakeImage.Outcome.Staged)
        assertEquals(listOf("status") + tail, io.asked)
        assertFalse(OneiosMakeImage.Phase.RUNTIME in io.phases)
    }

    @Test
    fun aRuntimeWithoutAKernelIsReplacedOrTheFlowSaysWhy() {
        // An older runtime: the newest one comes first (it is asked to skip the staged version).
        val io = Fake(listOf(oldRuntime, withKernel), runtimes = listOf(OneiosMakeImage.Runtime.Staged("0.1.12")), tools = listOf(withMake), makeImage = made)
        assertTrue(flow().run(io) is OneiosMakeImage.Outcome.Staged)
        assertEquals(listOf("status", "runtime 0.1.11", "status") + tail, io.asked)
        // The newest release is the staged one, without a kernel: nothing else is asked.
        val same = Fake(listOf(oldRuntime), runtimes = listOf(OneiosMakeImage.Runtime.Same("0.1.11")))
        val o = flow().run(same) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_RUNTIME to OneiosMakeImage.CODE_NO_KERNEL, o.step to o.code)
        assertEquals(listOf("status", "runtime 0.1.11"), same.asked)
        assertEquals("The runtime has no kernel yet", OneiosPlain.makeImage(o.step, o.end, o.code, o.text).title)
        // A placeholder runtime cannot make one either.
        val placeholder = withKernel.copy(runtime = withKernel.runtime!!.copy(placeholder = true))
        assertFalse(OneiosMakeImage.canBuild(placeholder))
        // The download failing: said, nothing else asked.
        val failed = Fake(listOf(none), runtimes = listOf(OneiosMakeImage.Runtime.Failed("No connection to GitHub (timeout).")))
        val f = flow().run(failed) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_RUNTIME to OneiosToolFlow.End.FAILED, f.step to f.end)
        assertEquals(listOf("status", "runtime -"), failed.asked)
        // A staged runtime that still has no kernel after the download.
        val still = Fake(listOf(none, oldRuntime), runtimes = listOf(OneiosMakeImage.Runtime.Staged("0.1.11")))
        assertEquals(OneiosMakeImage.CODE_NO_KERNEL, (flow().run(still) as OneiosMakeImage.Outcome.Stopped).code)
    }

    @Test
    fun aToolWithoutMakeImageGetsTheNewestRuntimeOnce() {
        // v0.1.12's tool (before make-image): the newest runtime, then the tool again.
        val io = Fake(listOf(withKernel, newer), runtimes = listOf(OneiosMakeImage.Runtime.Staged("0.1.13")), tools = listOf(withoutMake, withMake), makeImage = made)
        assertTrue(flow().run(io) is OneiosMakeImage.Outcome.Staged)
        assertEquals(listOf("status") + inputs + listOf("begin image", "tool", "close", "runtime 0.1.12", "status", "tool", "make-image", finish), io.asked)
        // The newest is the staged one: said in plain words, the tool never asked for make-image.
        val same = Fake(listOf(withKernel), runtimes = listOf(OneiosMakeImage.Runtime.Same("0.1.12")), tools = listOf(withoutMake))
        val o = flow().run(same) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.CODE_NO_MAKE_IMAGE, o.code)
        assertFalse(OneiosTool.Cmd.MAKE_IMAGE in same.asked)
        assertEquals("This runtime can't make the image yet", OneiosPlain.makeImage(o.step, o.end, o.code, o.text).title)
        // A runtime this run just staged whose tool has no make-image: not downloaded a second time.
        val fresh = Fake(listOf(none, withKernel), runtimes = listOf(OneiosMakeImage.Runtime.Staged("0.1.12")), tools = listOf(withoutMake))
        assertEquals(OneiosMakeImage.CODE_NO_MAKE_IMAGE, (flow().run(fresh) as OneiosMakeImage.Outcome.Stopped).code)
        assertEquals(1, fresh.asked.count { it.startsWith("runtime") })
        // No tool at all (a runtime without bin/oneios-tool): root's words.
        val noTool = Fake(listOf(withKernel), tools = emptyList())
        val t = flow().run(noTool) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_TOOL, t.step)
        assertTrue(t.text!!, "get a newer runtime" in t.text!!)
    }

    @Test
    fun theToolsRefusalsEndTheFlowAndRootsFinishIsNotAsked() {
        for ((code, words) in listOf(
            "space" to "Not enough free space in /data/local/tmp/oneios: 37.1 GB needed, 12.0 GB free",
            "not-ported" to "step decrypt: the AEA decryption is not in this tool yet (043-69487-662.dmg.aea must be decrypted)",
            "auth" to "043-69487-662.dmg.aea does not authenticate",
            "mismatch" to "os.img: plain_sha256 ab was expected: nothing was kept",
            "not-found" to "the kernel's inputs are missing: /data/local/tmp/oneios/kb/stubs.json",
            "audit" to "2 binds failed",
            "heat" to "the case is at 46.0 C",
        )) {
            val view = OneiosToolFlow(end = OneiosToolFlow.End.REFUSED, code = code, text = words, spaceNeed = 39_000_000_000L, spaceFree = 12_000_000_000L)
            val io = Fake(listOf(withKernel), tools = listOf(withMake), makeImage = view)
            val o = flow().run(io) as OneiosMakeImage.Outcome.Stopped
            assertEquals(OneiosTool.Cmd.MAKE_IMAGE to code, o.step to o.code)
            assertEquals(words, o.text)
            assertEquals(39_000_000_000L to 12_000_000_000L, o.need to o.free)
            assertEquals(OneiosTool.Cmd.MAKE_IMAGE, io.asked.last())
        }
        for (end in listOf(OneiosToolFlow.End.FAILED, OneiosToolFlow.End.CANCELLED, OneiosToolFlow.End.LOST)) {
            val io = Fake(listOf(withKernel), tools = listOf(withMake), makeImage = OneiosToolFlow(end = end, code = "network", text = "no byte for 120 s"))
            val o = flow().run(io) as OneiosMakeImage.Outcome.Stopped
            assertEquals(end, o.end)
            assertFalse(io.asked.any { it.startsWith("finish") })
        }
        // An ok without root's four fields: never sent to finish.
        val bad = Fake(listOf(withKernel), tools = listOf(withMake), makeImage = made.copy(result = made.result!! - "build"))
        val o = flow().run(bad) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_FINISH to "internal", o.step to o.code)
        assertFalse(bad.asked.any { it.startsWith("finish") })
        // Root refusing the finish (a session opened meanwhile): its words.
        val late = Fake(listOf(withKernel), tools = listOf(withMake), makeImage = made, roots = mapOf(OneiosRoot.Verb.FINISH to "an iOS session is running: return to One UI first"))
        val r = flow().run(late) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_FINISH, r.step)
        assertEquals("An iOS session is still open", OneiosPlain.makeImage(r.step, r.end, r.code, r.text).title)
    }

    @Test
    fun rootsRefusalsBeforeTheToolEndTheFlowThere() {
        val session = Fake(listOf(withKernel.copy(sessionOpen = true)))
        val s = flow().run(session) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_STATUS to "session", s.step to s.code)
        assertEquals(listOf("status"), session.asked)
        // No answer from root at all.
        val silent = Fake(emptyList())
        assertEquals(OneiosMakeImage.STEP_STATUS, (flow().run(silent) as OneiosMakeImage.Outcome.Stopped).step)
        // A pairing file root does not take: nothing after it.
        val kbinput = Fake(listOf(withKernel), roots = mapOf(OneiosRoot.Verb.KBINPUT to "kb/lead.json is a link"))
        assertEquals(OneiosMakeImage.STEP_KBINPUT, (flow().run(kbinput) as OneiosMakeImage.Outcome.Stopped).step)
        assertEquals(listOf("status", inputs.first()), kbinput.asked)
        // The app's own files not the pinned ones: root is not asked for them.
        val damaged = Fake(listOf(withKernel))
        val d = OneiosMakeImage(stage, kb, assets + (names.first() to "not it".toByteArray())).run(damaged) as OneiosMakeImage.Outcome.Stopped
        assertEquals(OneiosMakeImage.STEP_KBINPUT to "mismatch", d.step to d.code)
        assertEquals(listOf("status"), damaged.asked)
        assertEquals("This copy of OneOS is damaged", OneiosPlain.makeImage(d.step, d.end, d.code, d.text).title)
        // begin refused: the tool is not started.
        val begin = Fake(listOf(withKernel), roots = mapOf(OneiosRoot.Verb.BEGIN to "could not make /data/local/tmp/oneios/image.new"))
        assertEquals(OneiosMakeImage.STEP_BEGIN, (flow().run(begin) as OneiosMakeImage.Outcome.Stopped).step)
        assertEquals("begin image", begin.asked.last())
    }

    @Test
    fun aStopEndsTheFlowBeforeItsNextStep() {
        // After each step that ends well, a Stop: the next step is not started.
        for ((after, next) in listOf("status" to OneiosMakeImage.STEP_KBINPUT, inputs.last() to OneiosMakeImage.STEP_BEGIN, "begin image" to OneiosMakeImage.STEP_TOOL, "tool" to OneiosTool.Cmd.MAKE_IMAGE)) {
            val io = Fake(listOf(withKernel), tools = listOf(withMake), makeImage = made, stopAfter = after)
            val o = flow().run(io) as OneiosMakeImage.Outcome.Stopped
            assertEquals(after, OneiosToolFlow.End.CANCELLED, o.end)
            // Nothing after the step the Stop came in; the stop names the step that did not start.
            assertEquals(after, io.asked.last())
            assertEquals(after, next, o.step)
            assertEquals("Stopped", OneiosPlain.makeImage(o.step, o.end, o.code, o.text).title)
        }
        // Stopped during the runtime download: the download's own failure is a Stop.
        val io = Fake(listOf(none), runtimes = listOf(OneiosMakeImage.Runtime.Failed("stopped")), stopAfter = "runtime -")
        assertEquals(OneiosToolFlow.End.CANCELLED, (flow().run(io) as OneiosMakeImage.Outcome.Stopped).end)
    }
}
