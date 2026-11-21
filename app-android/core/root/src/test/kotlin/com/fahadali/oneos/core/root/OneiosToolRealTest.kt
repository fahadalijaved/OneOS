package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files

/**
 * [OneiosToolSession] against the real `oneios-tool serve` (OneiOS's tools/oneios-tool, a build for this machine),
 * only when `ONEIOS_TOOL_SERVE` names one: `ONEIOS_TOOL_SERVE=/path/to/oneios-tool ./gradlew --no-daemon
 * :core:root:testDebugUnitTest --tests '*OneiosToolRealTest*'`. The same requests as the stand-in's tests, on the
 * tool's own `ping`, `wait` (its test command), a cancel, an unknown command, and the end of input: what the tool
 * says must be what the app reads, and no process may be left.
 */
class OneiosToolRealTest {
    private val tool = System.getenv("ONEIOS_TOOL_SERVE")?.let(::File)
    private val dirs = mutableListOf<File>()
    private val sessions = mutableListOf<OneiosToolSession>()

    @After
    fun cleanUp() {
        sessions.forEach { runCatching { it.close() } }
        dirs.forEach { it.deleteRecursively() }
    }

    private fun session(): OneiosToolSession {
        assumeTrue("ONEIOS_TOOL_SERVE names no oneios-tool", tool?.canExecute() == true)
        val stage = Files.createTempDirectory("oneios-tool-real").toFile().also { dirs += it }
        return OneiosToolSession("exec '${tool!!.path}' serve --stage '${stage.path}' --idle 60", launch = listOf("sh", "-c")).also { sessions += it }
    }

    @Test
    fun theRealToolSpeaksWhatTheAppReads() {
        val s = session()
        val st = s.start()
        assertTrue("start: $st ${s.errors}", st is OneiosToolSession.Start.Ready)
        val hello = (st as OneiosToolSession.Start.Ready).hello
        assertEquals(1, hello.protocol)
        assertTrue(hello.cmds.containsAll(listOf("ping", "wait", "cancel", "sums", "cpu", "log", "log-list", "ioslog-boots", "ioslog-show")))
        assertTrue(s.call("ping") is OneiosTool.Event.Ok)

        var flow = OneiosToolFlow()
        val ok = s.call("wait", mapOf("seconds" to 1)) { flow = flow.with(it) }
        assertTrue("wait: $ok", ok is OneiosTool.Event.Ok)
        assertEquals(listOf("wait"), flow.steps.map { it.id })
        assertEquals(OneiosTool.StepState.DONE, flow.steps.single().state)
        assertEquals(1000L, flow.total)

        val no = s.call("no-such-command") as OneiosTool.Event.Refused
        assertEquals("unknown", no.code)
        // make-image: unknown to a tool from before it (OneiOS 42cf43b; the v0.1.12 runtime's), and since then a
        // request without its keys is `usage`, which names the missing key; either way nothing runs.
        val make = s.call(OneiosTool.Cmd.MAKE_IMAGE) as OneiosTool.Event.Refused
        assertEquals(if (OneiosTool.Cmd.MAKE_IMAGE in hello.cmds) "usage" else "unknown", make.code)

        val id = java.util.concurrent.atomic.AtomicReference("")
        var last: OneiosTool.Event? = null
        val t = Thread { last = s.call("wait", mapOf("seconds" to 30), onId = { id.set(it) }) { e -> if (e is OneiosTool.Event.Progress && (e.done ?: 0) >= 250) s.cancel(id.get()) } }
        t.start()
        t.join(20_000)
        assertEquals("request", (last as OneiosTool.Event.Cancelled).by)

        val p = s.processForTests!!
        s.close()
        assertEquals("the tool ended: eof", s.ended)
        assertTrue(!p.isAlive)
    }
}
