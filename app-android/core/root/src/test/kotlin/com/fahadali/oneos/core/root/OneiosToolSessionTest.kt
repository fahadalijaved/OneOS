package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger

/**
 * [OneiosToolSession] against a stand-in `oneios-tool serve` (src/test/resources/oneios/serve-standin.sh, POSIX
 * sh): progress lines, results, refusals, a cancel, the end of input, the tool's idle end, a tool that does not end
 * by itself. After every flow no process the session started is left: neither the shell that stands for `su`, nor
 * the tool, nor what the tool started.
 */
class OneiosToolSessionTest {
    private val dirs = mutableListOf<File>()
    private val sessions = mutableListOf<OneiosToolSession>()

    @After
    fun cleanUp() {
        sessions.forEach { runCatching { it.close() } }
        dirs.forEach { it.deleteRecursively() }
    }

    private fun standin(): File {
        val d = Files.createTempDirectory("oneios-tool-standin").toFile().also { dirs += it }
        val f = File(d, "serve-standin.sh")
        f.writeBytes(OneiosToolSessionTest::class.java.getResourceAsStream("/oneios/serve-standin.sh")!!.readBytes())
        return f
    }

    private fun session(env: Map<String, String> = emptyMap(), backstop: (() -> Unit)? = null, closeWaitMs: Long = 10_000, silenceMs: Long = 120_000): Pair<OneiosToolSession, File> {
        val s = standin()
        val dir = File(s.parentFile, "run").apply { mkdirs() }
        val session = OneiosToolSession(
            "exec sh '${s.path}' serve --stage '${dir.path}'",
            launch = listOf("sh", "-c"),
            environment = mapOf("STANDIN_DIR" to dir.path) + env,
            backstop = backstop,
            closeWaitMs = closeWaitMs,
            silenceMs = silenceMs,
        )
        sessions += session
        return session to dir
    }

    /** The process the session started and every process below it, now (java.lang.ProcessHandle by reflection:
     * the tests compile against Android's java.lang.Process, which has neither). */
    private fun tree(s: OneiosToolSession): List<Any> {
        val p = s.processForTests ?: return emptyList()
        val handle = Process::class.java.getMethod("toHandle").invoke(p)
        val below = (Process::class.java.getMethod("descendants").invoke(p) as java.util.stream.Stream<*>).toList().filterNotNull()
        return listOf(handle) + below
    }

    private fun alive(handles: List<Any>): List<Any> {
        val isAlive = Class.forName("java.lang.ProcessHandle").getMethod("isAlive")
        return handles.filter { isAlive.invoke(it) == true }
    }

    private fun awaitGone(handles: List<Any>, ms: Long = 5000) {
        val end = System.currentTimeMillis() + ms
        while (alive(handles).isNotEmpty() && System.currentTimeMillis() < end) Thread.sleep(20)
        assertEquals("processes left after the flow", emptyList<Any>(), alive(handles))
    }

    private fun ready(s: OneiosToolSession): OneiosTool.Event.Hello {
        val st = s.start()
        assertTrue("start: $st", st is OneiosToolSession.Start.Ready)
        return (st as OneiosToolSession.Start.Ready).hello
    }

    @Test
    fun aRequestGivesItsStepsProgressAndResultThenTheEndOfInputEndsEverything() {
        val (s, _) = session(env = mapOf("STANDIN_TICKS" to "5"))
        val hello = ready(s)
        assertEquals(1, hello.protocol)
        assertEquals("0.0.0-standin", hello.tool)
        var flow = OneiosToolFlow()
        val seen = mutableListOf<OneiosTool.Event>()
        val last = s.call("wait") { e -> synchronized(seen) { seen += e }; flow = flow.with(e) }
        assertTrue("last: $last", last is OneiosTool.Event.Ok)
        assertEquals(5L, (last as OneiosTool.Event.Ok).raw["ticks"])
        assertEquals(5, seen.count { it is OneiosTool.Event.Progress })
        assertEquals(listOf("wait", "place"), flow.steps.map { it.id })
        assertEquals(OneiosToolFlow.End.OK, flow.end)
        assertEquals(1000L, flow.spaceNeed)
        // A second request on the same process.
        assertTrue(s.call("standin-lines") { flow = flow.with(it) } is OneiosTool.Event.Ok)
        assertEquals(listOf("line 1", "line 2", "line 3"), flow.lines)
        val procs = tree(s)
        s.close()
        awaitGone(procs)
        assertEquals("the tool ended: eof", s.ended)
    }

    @Test
    fun refusalsAndFailuresComeWithTheToolsReason() {
        val (s, _) = session()
        ready(s)
        val no = s.call("standin-refuse") as OneiosTool.Event.Refused
        assertEquals("not enough free space in /data: 12.0 GB needed, 3.1 GB free", no.text)
        assertEquals("space", no.code)
        val bad = s.call("standin-fail") as OneiosTool.Event.Failed
        assertEquals("io", bad.code)
        val procs = tree(s)
        s.close()
        awaitGone(procs)
    }

    @Test
    fun aCancelEndsTheRequestAndWhatItStartedAndTheSessionGoesOn() {
        val (s, dir) = session(env = mapOf("STANDIN_TICKS" to "600"))
        ready(s)
        val id = java.util.concurrent.atomic.AtomicReference("")
        var last: OneiosTool.Event? = null
        val t = Thread { last = s.call("wait", onId = { id.set(it) }) { e -> if (e is OneiosTool.Event.Progress && e.done == 3L) s.cancel(id.get()) } }
        t.start()
        t.join(30_000)
        assertFalse("the call did not end", t.isAlive)
        assertTrue("last: $last", last is OneiosTool.Event.Cancelled)
        assertFalse("the child of the cancelled request is still there", File(dir, "child.${id.get()}").exists())
        assertTrue(s.alive)
        assertTrue(s.call("standin-lines") is OneiosTool.Event.Ok)
        val procs = tree(s)
        s.close()
        awaitGone(procs)
    }

    @Test
    fun closingDuringAWorkEndsTheWorkAndItsChild() {
        val (s, _) = session(env = mapOf("STANDIN_TICKS" to "600"))
        ready(s)
        var last: OneiosTool.Event? = OneiosTool.Event.Other(null, emptyMap())
        val started = java.util.concurrent.CountDownLatch(1)
        val t = Thread { last = s.call("wait") { if (it is OneiosTool.Event.Progress) started.countDown() } }
        t.start()
        assertTrue(started.await(20, java.util.concurrent.TimeUnit.SECONDS))
        val procs = tree(s)
        assertTrue("the work runs in processes of its own: $procs", procs.size >= 3)
        s.close()
        t.join(10_000)
        // The end of input cancels the running request: its own last line says so (by eof).
        assertEquals("eof", (last as OneiosTool.Event.Cancelled).by)
        awaitGone(procs)
    }

    @Test
    fun aToolThatDoesNotEndByItselfIsEndedAndTheBackstopRuns() {
        val backstops = AtomicInteger()
        lateinit var procs: List<Any>
        val (s, _) = session(env = mapOf("STANDIN_HANG" to "1", "STANDIN_TICKS" to "600"), closeWaitMs = 500, backstop = {
            backstops.incrementAndGet()
            // On the phone this is `untool` as root; here the stand-in's own processes, as untool finds them.
            val destroy = Class.forName("java.lang.ProcessHandle").getMethod("destroyForcibly")
            procs.forEach { destroy.invoke(it) }
        })
        ready(s)
        val started = java.util.concurrent.CountDownLatch(1)
        Thread { s.call("wait") { if (it is OneiosTool.Event.Progress) started.countDown() } }.start()
        assertTrue(started.await(20, java.util.concurrent.TimeUnit.SECONDS))
        procs = tree(s)
        s.close()
        assertEquals(1, backstops.get())
        awaitGone(procs)
    }

    @Test
    fun theToolsIdleEndEndsTheSession() {
        val (s, _) = session(env = mapOf("STANDIN_IDLE" to "1"))
        ready(s)
        val procs = tree(s)
        val end = System.currentTimeMillis() + 10_000
        while (s.ended == null && System.currentTimeMillis() < end) Thread.sleep(20)
        assertEquals("the tool ended: idle", s.ended)
        assertNull("no request after the end", s.send("ping") {})
        s.close()
        awaitGone(procs)
    }

    @Test
    fun aSilentToolIsGivenUpButSilenceWithoutARequestIsFine() {
        val (s, _) = session(silenceMs = 600)
        ready(s)
        val procs = tree(s)
        // No request is open: no limit.
        Thread.sleep(1200)
        assertNull(s.ended)
        assertTrue(s.call("standin-lines") is OneiosTool.Event.Ok)
        // `quiet` is never answered: the watchdog ends the request and the session.
        assertNull(s.call("standin-quiet"))
        assertTrue("ended: ${s.ended}", s.ended!!.startsWith("the tool sent nothing for"))
        s.close()
        awaitGone(procs)
    }

    @Test
    fun aHeatPauseIsNotSilence() {
        val (s, _) = session(silenceMs = 600)
        ready(s)
        var flow = OneiosToolFlow()
        val pauses = mutableListOf<String?>()
        val last = s.call("standin-heat") { e -> flow = flow.with(e); pauses += flow.paused }
        assertTrue("last: $last ended: ${s.ended}", last is OneiosTool.Event.Ok)
        assertEquals(listOf("the case is at 44 C: the work waits", null, null), pauses)
        val procs = tree(s)
        s.close()
        awaitGone(procs)
    }

    @Test
    fun aRefusalOfTheRootScriptBeforeTheToolStartsIsTheStartsAnswer() {
        val d = Files.createTempDirectory("oneios-tool-refuse").toFile().also { dirs += it }
        val s = OneiosToolSession(
            "echo '@@REFUSED this runtime has no bin/oneios-tool: get a newer runtime'; exit 2",
            launch = listOf("sh", "-c"), helloMs = 10_000,
        ).also { sessions += it }
        val st = s.start()
        assertEquals(OneiosToolSession.Start.Refused("this runtime has no bin/oneios-tool: get a newer runtime"), st)
        assertTrue(d.exists())
    }

    @Test
    fun aToolOfAnotherProtocolIsRefused() {
        val (s, _) = session(env = mapOf("STANDIN_PROTOCOL" to "2"))
        val st = s.start()
        assertTrue("start: $st", st is OneiosToolSession.Start.Refused && st.reason.contains("protocol 2"))
        assertFalse(s.alive)
    }
}
