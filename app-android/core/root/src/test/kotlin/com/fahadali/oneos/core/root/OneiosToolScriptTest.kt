package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosTool
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files

/**
 * `oneios_root.sh tool` and `untool` against a fake root folder (`ONEIOS_TEST_ROOT`), with the serve stand-in
 * (src/test/resources/oneios/serve-standin.sh) staged as the runtime's bin/oneios-tool: what runs is only the
 * file root hashed at staging; `tool work` is refused in a session and `tool read` is not, and passes
 * --read-only; the app's [OneiosToolSession] runs a flow through the launcher; `untool` ends a tool that does not
 * end by itself, and what it started.
 */
class OneiosToolScriptTest {
    private val rootScript = File(Shipped.fullAssets, OneiosRoot.ASSET)
    private val roots = mutableListOf<File>()
    private val sessions = mutableListOf<OneiosToolSession>()

    @After
    fun cleanUp() {
        sessions.forEach { runCatching { it.close() } }
        roots.forEach { it.deleteRecursively() }
    }

    private inner class Fake {
        val root: File = Files.createTempDirectory("oneios-tool-fakeroot").toFile().also { roots += it }
        val stage = File(root, "data/local/tmp/oneios")
        val run = File(root, "standin").apply { mkdirs() }
        private val uid = exec("id", "-u")
        private val gid = exec("id", "-g")
        val layout = OneiosRoot.Layout(stage.path, "/bin/sh", File(root, "proc").path, uid, "$uid:$gid")
        private val script = rootScript.readBytes()
        val standin: ByteArray = OneiosToolScriptTest::class.java.getResourceAsStream("/oneios/serve-standin.sh")!!.readBytes()

        init {
            File(root, "data/local/tmp").mkdirs()
            for (d in listOf("proc/1", "proc/self", "proc/sys/kernel/random")) File(root, d).mkdirs()
            val mounts = "1 0 8:1 / / rw - ext4 /dev/root rw\n"
            File(root, "proc/1/mountinfo").writeText(mounts)
            File(root, "proc/self/mountinfo").writeText(mounts)
            File(root, "proc/sys/kernel/random/boot_id").writeText("boot-1\n")
        }

        private fun exec(vararg cmd: String): String =
            ProcessBuilder(*cmd).redirectErrorStream(true).start().let { p -> p.inputStream.readBytes().toString(Charsets.UTF_8).trim().also { p.waitFor() } }

        fun env(): Map<String, String> = HashMap<String, String>().also {
            it["ONEIOS_TEST_ROOT"] = root.path
            it["STANDIN_DIR"] = run.path
            HostTools.into(it)
        }

        fun command(verb: OneiosRoot.Verb, args: List<String> = emptyList()) =
            OneiosRoot.launcher(verb, args, Hashes.sha256(script), script.size.toLong(), layout)

        inner class Out(val exit: Int, val text: String) {
            val reply = RootReply().also { r -> text.lines().forEach { r.accept(it) } }
        }

        fun verb(verb: OneiosRoot.Verb, args: List<String> = emptyList(), data: ByteArray? = null): Out {
            val pb = ProcessBuilder("/bin/sh", "-c", command(verb, args)).redirectErrorStream(true)
            pb.environment().putAll(env())
            val p = pb.start()
            val input = if (verb.stdin == OneiosRoot.Stdin.SCRIPT) script else data
            val w = Thread { runCatching { p.outputStream.use { o -> input?.let { o.write(it) } } } }.also { it.start() }
            val text = p.inputStream.readBytes().toString(Charsets.UTF_8)
            w.join()
            return Out(p.waitFor(), text)
        }

        fun ok(o: Out) = assertTrue(o.text, o.exit == 0 && o.reply.ok != null)

        fun receive(path: String, bytes: ByteArray, mode: String) =
            ok(verb(OneiosRoot.Verb.RECEIVE, listOf("runtime", path, bytes.size.toString(), Hashes.sha256(bytes), mode), bytes))

        fun runtime(withTool: Boolean = true) {
            ok(verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
            receive("runtime.json", "{}".toByteArray(), "0644")
            receive("bin/xnuhost", ByteArray(64) { 7 }, "0755")
            if (withTool) receive("bin/oneios-tool", standin, "0755")
            ok(verb(OneiosRoot.Verb.FINISH, listOf("runtime", if (withTool) "3" else "2", "0.1.10", "1", "bin/xnuhost", "1", "0")))
        }

        fun openSession() {
            File(stage, "control").mkdirs()
            File(stage, "control/boot").writeText("boot-1\n")
            File(stage, "control/state").writeText("running\n")
        }

        fun session(mode: String, backstop: (() -> Unit)? = null, closeWaitMs: Long = 10_000) = OneiosToolSession(
            command(OneiosRoot.Verb.TOOL, listOf(mode)), launch = listOf("/bin/sh", "-c"), environment = env(),
            backstop = backstop, closeWaitMs = closeWaitMs,
        ).also { sessions += it }
    }

    @Test
    fun aFlowRunsTheStagedToolThroughTheLauncher() {
        val f = Fake()
        f.runtime()
        val s = f.session("work")
        val st = s.start()
        assertTrue("start: $st ${s.errors}", st is OneiosToolSession.Start.Ready)
        assertEquals("0.0.0-standin", (st as OneiosToolSession.Start.Ready).hello.tool)
        assertTrue(s.call("ping") is OneiosTool.Event.Ok)
        assertTrue(s.call("wait") is OneiosTool.Event.Ok)
        // Its temporary folder is the stage's, root's own.
        assertTrue(File(f.stage, "tool").isDirectory)
        s.close()
        assertEquals("the tool ended: eof", s.ended)
    }

    @Test
    fun workIsRefusedInASessionAndReadIsNot() {
        val f = Fake()
        f.runtime()
        f.openSession()
        val work = f.session("work").start()
        assertEquals(OneiosToolSession.Start.Refused("an iOS session is running: return to One UI first"), work)
        val s = f.session("read")
        val st = s.start()
        assertTrue("start: $st", st is OneiosToolSession.Start.Ready)
        assertTrue(s.call("ping") is OneiosTool.Event.Ok)
        s.close()
    }

    @Test
    fun onlyTheFileThatWasStagedRuns() {
        val f = Fake()
        assertEquals(OneiosToolSession.Start.Refused("OneiOS's root script is not in the stage, or it changed: set up again"), f.session("work").start())
        f.runtime(withTool = false)
        assertEquals(OneiosToolSession.Start.Refused("this runtime has no bin/oneios-tool: get a newer runtime"), f.session("work").start())
        f.runtime()
        val bin = File(f.stage, "runtime/bin/oneios-tool")
        bin.appendText("\n# changed after staging\n")
        assertEquals(OneiosToolSession.Start.Refused("bin/oneios-tool is not the file that was staged: stage the runtime again"), f.session("work").start())
        val wrong = f.verb(OneiosRoot.Verb.TOOL, listOf("work"))
        assertEquals(2, wrong.exit)
        assertTrue(runCatching { f.command(OneiosRoot.Verb.TOOL, listOf("write")) }.isFailure)
        assertTrue(runCatching { f.command(OneiosRoot.Verb.UNTOOL, listOf("x")) }.isFailure)
    }

    @Test
    fun untoolEndsAToolThatDoesNotEndAndWhatItStarted() {
        // untool finds the tool's processes in /proc, as on the phone (no /proc on a Mac).
        assumeTrue(File("/proc/self/stat").exists())
        val f = Fake()
        f.runtime()
        var said = ""
        val s = OneiosToolSession(
            f.command(OneiosRoot.Verb.TOOL, listOf("work")), launch = listOf("/bin/sh", "-c"),
            environment = f.env() + mapOf("STANDIN_HANG" to "1", "STANDIN_TICKS" to "600"),
            backstop = { said = f.verb(OneiosRoot.Verb.UNTOOL).text }, closeWaitMs = 500,
        ).also { sessions += it }
        assertTrue(s.start() is OneiosToolSession.Start.Ready)
        val started = java.util.concurrent.CountDownLatch(1)
        Thread { s.call("wait") { if (it is OneiosTool.Event.Progress) started.countDown() } }.start()
        assertTrue(started.await(20, java.util.concurrent.TimeUnit.SECONDS))
        val child = File(f.run, "child.1").readText().trim()
        assertTrue(File("/proc/$child").exists())
        val tool = File(f.stage, "runtime/bin/oneios-tool").path
        fun left() = File("/proc").listFiles()!!.filter { it.name.all(Char::isDigit) }.filter { p ->
            runCatching { File(p, "cmdline").readBytes().toString(Charsets.UTF_8).replace('\u0000', ' ') }.getOrDefault("").contains("$tool serve")
        }
        assertTrue(left().isNotEmpty())
        s.close()
        assertTrue(said, said.contains("@@OK untool"))
        val end = System.currentTimeMillis() + 5000
        while ((left().isNotEmpty() || File("/proc/$child").exists()) && System.currentTimeMillis() < end) Thread.sleep(20)
        assertEquals(emptyList<File>(), left())
        assertFalse("the tool's child is still there", File("/proc/$child").exists() && !File("/proc/$child/stat").readText().contains(") Z "))
        assertEquals("@@OK untool nothing", f.verb(OneiosRoot.Verb.UNTOOL).text.trim())
    }
}
