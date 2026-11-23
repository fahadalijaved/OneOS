package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosCheckOutcome
import com.fahadali.oneos.core.model.OneiosChecks
import com.fahadali.oneos.core.model.OneiosEndKind
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosLogs
import com.fahadali.oneos.core.model.OneiosToolFlow
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.nio.file.Paths
import java.util.concurrent.TimeUnit

/**
 * The OneiOS root script, its launcher and the session script's stage checks,
 * run under the machine's shells against a fake root folder
 * (`ONEIOS_TEST_ROOT`): nothing is started there, and the scripts refuse the
 * test root as uid 0.
 *
 * The way back to One UI (the key readers, the watcher, `oneios_return.sh`)
 * runs there against a fake phone ([Fake.phone]): stand-ins for Android's
 * tools (`src/test/resources/oneios/phone-tools.sh`), processes as folders,
 * and a clock that runs faster. No real process is signalled or stopped.
 */
class OneiosScriptTest {
    private val rootScript = File(Shipped.fullAssets, OneiosRoot.ASSET)
    private val switchScript = File(Shipped.switcherAssets, "oneios_switch.sh")
    private val returnScript = File(Shipped.switcherAssets, "oneios_return.sh")

    /** OneOS's boot screen, which the iOS switch shows too: staged in the iOS stage's bin/. */
    private val bootScreenFiles = OneiosRoot.BOOT_SCREEN_FILES.map { File(Shipped.switcherAssets, it) }

    private val shells: List<String> =
        // busybox is not a shell by its own name ("busybox sh"): the others are run as <shell> -c.
        (listOf("/bin/sh") + TestShell.available().filterNot { it.appletsFirst }.map { it.path }).filter { File(it).canExecute() }.distinct()

    private val roots = mutableListOf<File>()
    private val started = mutableListOf<Process>()

    @After
    fun cleanUp() {
        // Whatever a fake getevent or a hanging stand-in still waits for ends, then every script a test left running.
        roots.forEach { r -> runCatching { File(r, "events/stop").createNewFile(); File(r, "behave/unhang").createNewFile() } }
        started.forEach { p ->
            // Process.descendants() by name: the tests compile against Android's java.lang.Process, which has none.
            runCatching {
                val handle = Class.forName("java.lang.ProcessHandle").getMethod("destroyForcibly")
                (Process::class.java.getMethod("descendants").invoke(p) as java.util.stream.Stream<*>).forEach { handle.invoke(it) }
            }
            p.destroyForcibly()
        }
        roots.forEach { it.deleteRecursively() }
    }

    private fun await(what: String, ms: Long = 30_000, cond: () -> Boolean) {
        val end = System.currentTimeMillis() + ms
        while (!cond()) {
            assertTrue("timed out waiting for: $what", System.currentTimeMillis() < end)
            Thread.sleep(20)
        }
    }

    private inner class Fake(val sh: String) {
        val root: File = Files.createTempDirectory("oneios-fakeroot").toFile().also { roots += it }
        val stage = File(root, "data/local/tmp/oneios")
        private val uid = run("id", "-u")
        private val gid = run("id", "-g")
        val layout = OneiosRoot.Layout(stage.path, sh, File(root, "proc").path, uid, "$uid:$gid")
        private val script = rootScript.readBytes()

        init {
            File(root, "data/local/tmp").mkdirs()
            for (d in listOf("proc/1", "proc/self", "proc/sys/kernel/random")) File(root, d).mkdirs()
            val mounts = "1 0 8:1 / / rw - ext4 /dev/root rw\n"
            File(root, "proc/1/mountinfo").writeText(mounts)
            File(root, "proc/self/mountinfo").writeText(mounts)
            File(root, "proc/sys/kernel/random/boot_id").writeText("boot-1\n")
        }

        private fun run(vararg cmd: String): String =
            ProcessBuilder(*cmd).redirectErrorStream(true).start().let { p -> p.inputStream.readBytes().toString(Charsets.UTF_8).trim().also { p.waitFor() } }

        inner class Out(val exit: Int, val text: String) {
            val reply = RootReply().also { r -> text.lines().forEach { r.accept(it) } }
            val status: OneiosStatus get() = OneiosStatus.parse(reply.results)
        }

        fun verb(verb: OneiosRoot.Verb, args: List<String> = emptyList(), data: ByteArray? = null, env: Map<String, String> = emptyMap()): Out {
            val cmd = OneiosRoot.launcher(verb, args, Hashes.sha256(script), script.size.toLong(), layout)
            val pb = ProcessBuilder(sh, "-c", cmd).redirectErrorStream(true)
            pb.environment()["ONEIOS_TEST_ROOT"] = root.path
            HostTools.into(pb.environment())
            pb.environment().putAll(env)
            val p = pb.start()
            val input = when (verb.stdin) {
                OneiosRoot.Stdin.SCRIPT -> script
                OneiosRoot.Stdin.DATA -> data!!
                OneiosRoot.Stdin.NONE -> null
            }
            val writer = Thread {
                runCatching { p.outputStream.use { o -> input?.let { o.write(it) } } }
            }.also { it.start() }
            val text = p.inputStream.readBytes().toString(Charsets.UTF_8)
            writer.join()
            return Out(p.waitFor(), text)
        }

        fun receive(kind: String, path: String, bytes: ByteArray, mode: String = "0644", sha: String = Hashes.sha256(bytes)) =
            verb(OneiosRoot.Verb.RECEIVE, listOf(kind, path, bytes.size.toString(), sha, mode), bytes)

        fun scripts() {
            for (f in listOf(switchScript, returnScript) + bootScreenFiles) {
                val b = f.readBytes()
                assertOk(verb(OneiosRoot.Verb.SCRIPT, listOf(f.name, b.size.toString(), Hashes.sha256(b)), b))
            }
        }

        fun runtime(withXnuhost: Boolean = true, abi: Int = 1, formats: String = "1", placeholder: Boolean = false): Out {
            assertOk(verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
            assertOk(receive("runtime", "runtime.json", "{}".toByteArray()))
            assertOk(receive("runtime", "bin/stub", ByteArray(100) { 1 }, "0755"))
            if (withXnuhost) assertOk(receive("runtime", "bin/xnuhost", ELF, "0755"))
            return verb(OneiosRoot.Verb.FINISH, listOf("runtime", if (withXnuhost) "3" else "2", "0.1.0", abi.toString(), "bin/xnuhost", formats, if (placeholder) "1" else "0", "none", "none", "none"))
        }

        fun image(format: Int = 1): Out {
            assertOk(verb(OneiosRoot.Verb.BEGIN, listOf("image")))
            assertOk(receive("image", "manifest.json", "{}".toByteArray()))
            assertOk(receive("image", "os.img", ByteArray(5000) { it.toByte() }))
            assertOk(receive("image", "overlay/kernel.kc", "kc".toByteArray()))
            return verb(OneiosRoot.Verb.FINISH, listOf("image", "3", format.toString(), "27.0.1", "24A446"))
        }

        // --- A fake phone in an iOS session, for the way back ---------------------------

        /** What xnuhost and the switch share (ready, return.request, the log). */
        val session = File(stage, "session")

        /** The way back's own folder: the state, the baseline, the pids, the keys. */
        val control = File(stage, "control")
        val busybox = File(root, "data/adb/ksu/bin/busybox")

        fun file(path: String) = File(root, path)
        fun lines(path: String): List<String> = file(path).takeIf { it.isFile }?.readLines().orEmpty()

        /** What was asked of init, in order ("ctl.restart netd", "sys.powerctl reboot,..."). */
        val setprops: List<String> get() = lines("log/setprop")
        val kills: List<String> get() = lines("log/kill")
        val returnLog: String get() = File(stage, "return.log").takeIf { it.isFile }?.readText().orEmpty()
        val state: String get() = File(control, "state").takeIf { it.isFile }?.readText()?.trim().orEmpty()
        val outcome: String get() = File(stage, "return.outcome").takeIf { it.isFile }?.readText()?.trim().orEmpty()
        val rebooted: String? get() = setprops.firstOrNull { it.startsWith("sys.powerctl ") }?.substringAfter(' ')

        fun behave(flag: String) = file("behave/$flag").createNewFile()

        /** A process as a folder in the fake /proc: its mount namespace, name and command line. */
        fun proc(pid: Int, name: String, ns: String = INIT_NS, cmdline: String = name): File {
            val d = file("proc/$pid").apply { File(this, "ns").mkdirs() }
            Files.deleteIfExists(File(d, "ns/mnt").toPath())
            Files.createSymbolicLink(File(d, "ns/mnt").toPath(), Paths.get(ns))
            File(d, "comm").writeText("$name\n")
            File(d, "cmdline").writeText(cmdline.replace(' ', '\u0000') + "\u0000")
            return d
        }

        private fun daemon(name: String, pid: Int, service: String? = null, initName: String = name) {
            proc(pid, name)
            file("pids/$name").writeText("$pid\n")
            file("props").appendText("init.svc.$initName=running\n")
            service?.let { file("services/${it.replace('/', '_')}").createNewFile() }
        }

        /**
         * Makes this root a phone in an iOS session as `oneios_switch.sh` leaves it: One UI's daemons running and its
         * framework stopped, xnuhost (pid [XNUHOST]) in its own mount namespace and cgroup, the baseline of the switch.
         * [scale]: how much faster the scripts' clock runs (their `sleep`).
         */
        fun phone(scale: Int = 100, stopped: Boolean = true, state: String = "running") {
            assertOk(verb(OneiosRoot.Verb.BEGIN, listOf("image")))
            scripts()
            val sleep = listOf("/usr/bin/sleep", "/bin/sleep").first { File(it).canExecute() }
            val tools = OneiosScriptTest::class.java.getResourceAsStream("/oneios/phone-tools.sh")!!.readBytes().toString(Charsets.UTF_8).replace("@SLEEP@", sleep)
            val names = listOf("getprop", "setprop", "pidof", "service", "getenforce", "am", "vdc", "sync", "renice", "lshal", "sleep", "now", "kill", "getevent", "dmesg", "logcat")
            for (f in names.map { file("bin/$it") } + listOf(busybox, File(busybox.parentFile, "resetprop"))) {
                f.parentFile.mkdirs()
                f.writeText(tools)
                assertTrue(f.setExecutable(true))
            }
            for (d in listOf("log", "pids", "services", "behave", "events", "keystate", "sys/power", "sys/fs/cgroup/oneios_session", "vendor/etc/vintf")) file(d).mkdirs()
            file("sys/fs/cgroup/oneios_session/cgroup.kill").writeText("")
            file("sleep_scale").writeText("$scale\n")
            file("nextpid").writeText("9000\n")
            file("selinux").writeText("Enforcing\n")
            file("vendor/etc/vintf/manifest.xml").writeText("<hal><name>android.hardware.graphics.composer3</name></hal>\n")
            file("props").writeText("ro.product.model=SM-S928B\npersist.sys.timezone=Asia/Kolkata\ninit.svc.zygote=stopped\ninit.svc.zygote_secondary=stopped\n")
            // One UI, without its framework.
            proc(1, "init")
            daemon("vold", 300, "vold")
            daemon("keystore2", 301)
            daemon("servicemanager", 302)
            daemon("hwservicemanager", 303)
            daemon("logd", 304)
            daemon("lmkd", 305)
            daemon("installd", 306, "installd")
            daemon("surfaceflinger", 310, "SurfaceFlinger")
            daemon("composer", 311, "android.hardware.graphics.composer3.IComposer/default", initName = COMPOSER)
            file("props").appendText("init.svc_debug_pid.$COMPOSER=311\n")
            daemon("audioserver", 312, "media.audio_policy")
            file("services/media.audio_flinger").createNewFile()
            daemon("netd", 313)
            daemon("cameraserver", 314)
            // The session.
            for (d in listOf("base", "keys")) File(control, d).mkdirs()
            File(session, "tmp").mkdirs()
            File(control, "boot").writeText("boot-1\n")
            File(control, "state").writeText("$state\n")
            File(session, "xnuhost.log").writeText("guest: launchd\n")
            if (state == "running") {
                File(control, "xnuhost.pid").writeText("$XNUHOST\n")
                File(control, "mntns").writeText("$GUEST_NS\n")
                guest(XNUHOST, "xnuhost")
            }
            if (stopped) File(control, "stopped").writeText("1\n")
            // A switch that never stopped One UI: its framework still runs.
            if (!stopped) file("props").appendText("init.svc.zygote=running\n")
            val base = File(control, "base")
            File(base, "boot_id").writeText("boot-1\n")
            File(base, "selinux").writeText("Enforcing\n")
            File(base, "props").writeText(
                (lines("props") + listOf("init.svc.zygote=running", "init.svc.zygote_secondary=running"))
                    .associate { it.substringBefore('=') to it.substringAfter('=') }.entries.joinToString("") { "[${it.key}]: [${it.value}]\n" },
            )
            File(base, "pids").writeText("vold 300\nkeystore2 301\nsurfaceflinger 310\nservicemanager 302\n")
            File(base, "mounts").writeText("/\n")
        }

        /** A process of the session: in xnuhost's mount namespace and cgroup. */
        fun guest(pid: Int, name: String, ns: String = GUEST_NS, cgroup: Boolean = true): File {
            val d = proc(pid, name, ns)
            File(d, "mountinfo").writeText("1 0 8:1 / / rw - ext4 /dev/root rw\n40 1 254:50 /local/tmp/oneios /data rw - f2fs /dev/block/dm-50 rw\n")
            if (cgroup) file("sys/fs/cgroup/oneios_session/cgroup.procs").appendText("$pid\n")
            return d
        }

        private fun builder(script: String, args: List<String>, env: Map<String, String>): ProcessBuilder {
            val pb = ProcessBuilder(listOf(sh, File(stage, script).path) + args).redirectErrorStream(true)
            pb.environment()["ONEIOS_TEST_ROOT"] = root.path
            HostTools.into(pb.environment())
            pb.environment()["ONEIOS_TEST_SH"] = sh
            pb.environment()["BB"] = busybox.path
            pb.environment().putAll(env)
            return pb
        }

        /** Runs a staged session script to its end. */
        fun run(script: String, vararg args: String, env: Map<String, String> = emptyMap()): Ran {
            val p = builder(script, args.toList(), env).start().also { started += it }
            p.outputStream.close()
            val text = p.inputStream.readBytes().toString(Charsets.UTF_8)
            assertTrue("$script ${args.toList()} did not end:\n$text", p.waitFor(120, TimeUnit.SECONDS))
            return Ran(p.exitValue(), text)
        }

        /** Starts a staged session script (a watcher, a key reader) and leaves it running; its output goes to [log]. */
        fun start(script: String, vararg args: String, env: Map<String, String> = emptyMap(), log: String = "log/${args.first().trimStart('-')}"): Process {
            val pb = builder(script, args.toList(), env).redirectInput(ProcessBuilder.Redirect.from(File("/dev/null")))
            pb.redirectOutput(ProcessBuilder.Redirect.appendTo(file(log)))
            return pb.start().also { started += it }
        }

        fun returns(who: String = "manual", env: Map<String, String> = emptyMap()) = run("oneios_return.sh", who, env = env)

        /** One UI came back in place: its display, its services and its framework, in that order, and no reboot. */
        fun assertInPlace(why: String = "") {
            val log = setprops
            val text = "$why\n${log.joinToString("\n")}\n$returnLog"
            assertEquals(text, "returned", state)
            assertTrue(text, outcome.startsWith("inplace "))
            assertEquals(text, null, rebooted)
            val order = listOf(
                "ctl.restart $COMPOSER", "service.bootanim.exit 0", "ctl.start bootanim", "ctl.stop audioserver", "ctl.start audioserver",
                "ctl.restart cameraserver", "ctl.restart wificond", "ctl.restart netd",
            )
            val at = order.map { log.indexOf(it) }
            assertTrue("$at $text", at.all { it >= 0 } && at == at.sorted())
            // A surfaceflinger and a composer that are not the session's old ones, and One UI's framework.
            assertFalse(text, lines("pids/surfaceflinger") == listOf("310"))
            assertFalse(text, lines("pids/composer") == listOf("311"))
            assertTrue(text, file("pids/system_server").isFile && file("services/SurfaceFlinger").isFile)
            assertTrue(text, returnLog.contains("One UI restored in place (Enforcing)."))
            // Nothing of the session: no process, no guard mark, no lock, both wakelocks released.
            assertFalse(text, file("proc/$XNUHOST").exists())
            assertFalse(text, File(control, "return.guard").exists() || File(control, "returning.lock").exists())
            assertEquals(text, "oneios_return", lines("sys/power/wake_unlock").lastOrNull())
        }

        /** A process of the session ends by itself. */
        fun ends(pid: Int) {
            file("proc/$pid").deleteRecursively()
            val cg = file("sys/fs/cgroup/oneios_session/cgroup.procs")
            cg.writeText(cg.readLines().filterNot { it == "$pid" }.joinToString("") { "$it\n" })
        }

        /** The return gave up on in place: the reboot was asked, and (unless it failed after that) One UI's framework was never started. */
        fun assertFailsafe(part: String, frameworkStarted: Boolean = false) {
            val text = "${setprops.joinToString("\n")}\n$returnLog"
            assertEquals(text, frameworkStarted, setprops.any { it == "ctl.restart netd" || it == "ctl.start zygote" })
            assertEquals(text, "reboot,oneios-inplace-failsafe", rebooted)
            assertTrue("'$outcome' lacks '$part'", outcome.startsWith("failsafe ") && outcome.contains(part))
            assertTrue(text, returnLog.contains("FAILSAFE: ") && returnLog.contains(part))
            assertEquals(text, "returning", state)
            // The last resorts after init's reboot: the kernel's, then sysrq.
            assertTrue(text, lines("log/busybox").contains("reboot -f"))
            assertEquals(text, listOf("b"), lines("proc/sysrq-trigger"))
        }
    }

    private class Ran(val exit: Int, val text: String)

    private fun assertOk(o: Fake.Out) = assertTrue(o.text, o.exit == 0 && o.reply.ok != null)

    private fun assertRefused(o: Fake.Out, part: String) {
        assertEquals(o.text, 2, o.exit)
        assertTrue("'${o.reply.refused}' lacks '$part'", o.reply.refused.orEmpty().contains(part))
    }

    private fun each(body: (Fake) -> Unit) {
        assumeTrue("no shell to run the scripts under", shells.isNotEmpty())
        for (sh in shells) body(Fake(sh))
    }

    @Test
    fun statusOnAPhoneWithoutAStageMakesNone() = each { f ->
        val o = f.verb(OneiosRoot.Verb.STATUS)
        assertOk(o)
        assertFalse(o.status.staged)
        assertFalse(f.stage.exists())
        assertOk(f.verb(OneiosRoot.Verb.REMOVE))
        assertFalse(f.stage.exists())
    }

    @Test
    fun onlyBeginStatusAndRemoveInstallTheScript() = each { f ->
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "1")), "not in the stage")
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("image", "3", "1", "27.0.1", "24A446")), "not in the stage")
        assertFalse(f.stage.exists())
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertTrue(File(f.stage, "bin/oneios_root.sh").isFile)
        assertEquals(Hashes.sha256(rootScript.readBytes()), Hashes.sha256(File(f.stage, "bin/oneios_root.sh").readBytes()))
    }

    /** Until a runtime with xnuhost is staged, the switch refuses with one line that says so. */
    @Test
    fun withoutARuntimeTheSwitchRefusesWithTheReason() = each { f ->
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")))
        f.scripts()
        assertOk(f.image())
        val s = f.verb(OneiosRoot.Verb.STATUS).status
        assertTrue(s.staged)
        assertEquals(null, s.runtime)
        assertEquals("27.0.1", s.image?.version)
        assertEquals("24A446", s.image?.build)
        assertEquals(5004L, s.image?.bytes)
        assertFalse(s.ready)
        assertTrue(s.notReady, s.notReady!!.contains("no OneiOS runtime is staged") && s.notReady!!.contains("xnuhost"))
        assertFalse(s.notReady!!.contains("\n"))
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "1")), "no OneiOS runtime is staged")
    }

    @Test
    fun aRuntimeWithoutXnuhostCannotBeStaged() = each { f ->
        assertRefused(f.runtime(withXnuhost = false), "the runtime has no bin/xnuhost")
        assertFalse(File(f.stage, "runtime").exists())
        assertFalse(File(f.stage, "runtime.conf").exists())
    }

    @Test
    fun aStagedPairPassesTheStageChecksAndNothingStarts() = each { f ->
        assertOk(f.runtime())
        f.scripts()
        var s = f.verb(OneiosRoot.Verb.STATUS).status
        assertEquals(OneiosStatus.Runtime("0.1.0", "1", "bin/xnuhost", "1", placeholder = false), s.runtime)
        assertTrue(s.notReady, s.notReady!!.contains("no iOS image set is staged"))
        assertOk(f.image())
        s = f.verb(OneiosRoot.Verb.STATUS).status
        assertTrue(s.notReady.orEmpty(), s.ready)
        assertFalse(s.sessionOpen)
        // The test root never starts a session.
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "1")), "nothing was started")
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "0")), "experimental tick")
        // The Android takeover's word goes the same way (the session mode is the preflight's: --mode-check below).
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "1", "takeover")), "nothing was started")
        // Back to One UI with no open session does nothing.
        val back = f.verb(OneiosRoot.Verb.RETURN)
        assertOk(back)
        assertEquals("return nothing", back.reply.ok)
        // An open session of this boot: the test root starts nothing, and staging is refused.
        File(f.stage, "control").mkdirs()
        File(f.stage, "control/boot").writeText("boot-1\n")
        File(f.stage, "control/state").writeText("running\n")
        assertTrue(f.verb(OneiosRoot.Verb.STATUS).status.sessionOpen)
        assertRefused(f.verb(OneiosRoot.Verb.RETURN), "a session is open")
        assertRefused(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")), "an iOS session is running")
        assertRefused(f.verb(OneiosRoot.Verb.REMOVE), "an iOS session is running")
        File(f.stage, "control").deleteRecursively()
        // What root recorded: every file with its hash, the manifest included.
        assertEquals(
            setOf("runtime.json", "bin/stub", "bin/xnuhost"),
            File(f.stage, "runtime.sha256").readLines().map { it.substringAfter("  ") }.toSet(),
        )
        assertOk(f.verb(OneiosRoot.Verb.REMOVE))
        assertFalse(f.stage.exists())
    }

    @Test
    fun aChangedFileOrAMismatchedPairIsRefused() = each { f ->
        assertOk(f.runtime())
        f.scripts()
        assertOk(f.image())
        assertTrue(f.verb(OneiosRoot.Verb.STATUS).status.ready)
        fun why() = f.verb(OneiosRoot.Verb.STATUS).status.also { assertFalse(it.ready) }.notReady!!

        // xnuhost changed after staging (same size). Status is quick (the files' ids, nothing hashed): with the
        // staged id kept, it does not see the change, and the switch's own preflight, which hashes, refuses it.
        val x = File(f.stage, "runtime/bin/xnuhost")
        val staged = x.lastModified()
        x.writeBytes(ELF.copyOf().also { it[40] = 9 })
        assertTrue(x.setLastModified(staged))
        assertTrue(f.verb(OneiosRoot.Verb.STATUS).status.ready)
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "1")), "runtime/bin/xnuhost does not match its SHA-256")
        // With its time changed too, status sees it by its id.
        assertTrue(x.setLastModified(staged + 5_000))
        assertTrue(why(), why().contains("runtime/bin/xnuhost changed since it was staged"))
        // Not an arm64 program.
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertOk(f.receive("runtime", "runtime.json", "{}".toByteArray()))
        assertOk(f.receive("runtime", "bin/xnuhost", "#!/bin/sh\n".toByteArray() + ByteArray(60), "0755"))
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("runtime", "2", "0.1.1", "1", "bin/xnuhost", "1", "0", "none", "none", "none")))
        assertTrue(why(), why().contains("not an arm64 program"))
        // OneiOS's stand-in for an xnuhost that is not built yet: staged, shown, and never started.
        assertOk(f.runtime(placeholder = true))
        assertTrue(f.verb(OneiosRoot.Verb.STATUS).status.runtime!!.placeholder)
        assertTrue(why(), why().contains("placeholder instead of xnuhost"))
        assertRefused(f.verb(OneiosRoot.Verb.SWITCH, listOf("100", "1")), "placeholder instead of xnuhost")
        // Another session ABI, another image format.
        assertOk(f.runtime(abi = 2))
        assertTrue(why(), why().contains("session ABI 2"))
        assertOk(f.runtime(formats = "2,3"))
        assertTrue(why(), why().contains("image set is format 1"))
        assertOk(f.runtime())
        assertTrue(f.verb(OneiosRoot.Verb.STATUS).status.ready)
        // An image file replaced since it was staged, and a file nobody listed.
        val os = File(f.stage, "image/os.img")
        val copy = File(f.stage, "image/os.copy").also { it.writeBytes(os.readBytes()) }
        assertTrue(why(), why().contains("holds files its list does not name"))
        os.delete()
        assertTrue(copy.renameTo(os))
        assertTrue(why(), why().contains("image/os.img changed since it was staged"))
    }

    @Test
    fun receiveChecksSizeHashAndPath() = each { f ->
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")))
        assertRefused(f.receive("image", "os.img", ByteArray(10), sha = "0".repeat(64)), "did not arrive intact")
        assertFalse(File(f.stage, "image.new/os.img").exists())
        assertFalse(File(f.stage, "image.new/os.img.part").exists())
        val short = f.verb(OneiosRoot.Verb.RECEIVE, listOf("image", "os.img", "20", Hashes.sha256(ByteArray(10)), "0644"), ByteArray(10))
        assertRefused(short, "10 of 20 bytes")
        assertOk(f.receive("image", "os.img", ByteArray(10)))
        assertRefused(f.receive("image", "os.img", ByteArray(10)), "already received")
        // A finish that does not match what was received.
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("image", "3", "1", "27.0.1", "24A446")), "1 of 3 files")
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("image", "2", "1", "27.0.1", "24A446")), "1 of 2 files")
        assertOk(f.receive("image", "a/b/c.bin", ByteArray(3)))
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("image", "2", "1", "27.0.1", "24A446")), "manifest.json was not received")
        // Nothing is staged without a begin.
        assertRefused(f.receive("runtime", "bin/xnuhost", ELF, "0755"), "begin first")
    }

    /**
     * Kernel updates (docs/oneios.md, "Kernel updates"): `kbinput` stages the
     * prelink inputs, `finish kernel` activates the phone-built collection
     * atomically (hashes, lists, manifest, configs, receipt), and the old set
     * stays as the fallback (`restore kernel`). A swapped binary with stale
     * hashes or configs is impossible: root rewrites every one of them before
     * the set counts as staged, and any half-state fails the preflight.
     */
    @Test
    fun kernelUpdatesSwapHashesConfigsAndKeepAFallback() = each { f ->
        val bid = "xnu-12377.121.6-ios-27.0.1-24A446-abcdef012345"
        val xnu = ByteArray(100) { it.toByte() }
        val xnuSha = Hashes.sha256(xnu)
        // A runtime that carries a kernel.
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertOk(f.receive("runtime", "runtime.json", "{}".toByteArray()))
        assertOk(f.receive("runtime", "kernel/xnu.macho", xnu, "0644"))
        assertOk(f.receive("runtime", "bin/xnuhost", ELF, "0755"))
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("runtime", "3", "0.1.0", "1", "bin/xnuhost", "1", "0", bid, xnuSha, "xnu-12377.121.6")))
        assertEquals(bid, f.verb(OneiosRoot.Verb.STATUS).status.runtimeKernel!!.buildId)
        // An image set with a kernel collection.
        val kc1 = ByteArray(5000) { (it % 251).toByte() }
        val kc1Sha = Hashes.sha256(kc1)
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")))
        assertOk(f.receive("image", "manifest.json", manifestWithKc(kc1.size, kc1Sha)))
        assertOk(f.receive("image", "kernel.kc", kc1, "0644"))
        assertOk(f.receive("image", "kernel.kc.hashes", "hashes-1".toByteArray(), "0644"))
        assertOk(f.receive("image", "os.img", ByteArray(100)))
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("image", "4", "1", "27.0.1", "24A446")))
        // No fallback kept yet: restoring refuses and changes nothing.
        assertRefused(f.verb(OneiosRoot.Verb.RESTORE, listOf("kernel")), "no previous kernel set")
        assertEquals("$kc1Sha  kernel.kc", shaLine(File(f.stage, "image.sha256"), "kernel.kc"))
        // The prelink inputs, then the user's kernelcache.
        kbInputs(f)
        assertTrue(runCatching { f.verb(OneiosRoot.Verb.KBINPUT, listOf("xnu.macho", "10", "a".repeat(64)), ByteArray(10)) }.isFailure)
        val kcIn = ByteArray(300) { (it * 3).toByte() }
        val kcInSha = Hashes.sha256(kcIn)
        assertOk(f.verb(OneiosRoot.Verb.KBINPUT, listOf("kernelcache.macho", kcIn.size.toString(), kcInSha), kcIn))
        assertEquals(10, f.verb(OneiosRoot.Verb.STATUS).status.kb.inputs)  // 9 pairing files and the kernelcache
        // A phone-built kernel from this xnu and this kernelcache.
        val kc2 = ByteArray(6000) { (it % 251).toByte() }
        val kc2Sha = Hashes.sha256(kc2)
        makeKernelOut(f, kc2, xnuSha, kcInSha)
        // A refused activation changes nothing and leaves no stray files behind.
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("kernel", "0".repeat(64), bid)), "the built kernel.kc is not ${"0".repeat(64)}")
        assertEquals(kc1Sha, Hashes.sha256(File(f.stage, "image/kernel.kc").readBytes()))
        assertEquals("$kc1Sha  kernel.kc", shaLine(File(f.stage, "image.sha256"), "kernel.kc"))
        assertFalse(File(f.stage, "image").list()!!.any { it.endsWith(".new") || it.endsWith(".new2") || it.endsWith(".new3") })
        // A collection paired from another xnu is not activated either.
        val kc3 = ByteArray(6000) { (it % 241).toByte() }
        makeKernelOut(f, kc3, "0".repeat(64), kcInSha)
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("kernel", Hashes.sha256(kc3), bid)), "not from this runtime's xnu")
        makeKernelOut(f, kc2, xnuSha, kcInSha)
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("kernel", kc2Sha, bid)))
        // The swap: the files, every hash and list, the configs, and the receipt.
        assertEquals(kc2Sha, Hashes.sha256(File(f.stage, "image/kernel.kc").readBytes()))
        assertEquals("$kc2Sha  kernel.kc", shaLine(File(f.stage, "image.sha256"), "kernel.kc"))
        assertEquals("${Hashes.sha256(File(f.stage, "image/manifest.json").readBytes())}  manifest.json", shaLine(File(f.stage, "image.sha256"), "manifest.json"))
        assertTrue(File(f.stage, "image/manifest.json").readText().contains("\"sha256\": \"$kc2Sha\""))
        assertEquals(bid, File(f.stage, "image.conf").readLines().first { it.startsWith("kernel_build_id=") }.substringAfter('='))
        assertEquals(kc2Sha, File(f.stage, "image.conf").readLines().first { it.startsWith("kernel_kc_sha256=") }.substringAfter('='))
        val st = f.verb(OneiosRoot.Verb.STATUS).status
        assertEquals(bid, st.imageKernel!!.buildId)
        assertEquals(kc2Sha, st.imageKernel.kcSha256)
        assertTrue(st.imageKernel.hasFallback)
        val receipt = File(f.stage, "logs").list()!!.single { it.startsWith("update-") && it.endsWith(".log") }
        assertTrue(File(f.stage, "logs/$receipt").readText().contains("from: kernel.kc $kc1Sha"))
        // The fallback restores everything, with its own receipt.
        assertOk(f.verb(OneiosRoot.Verb.RESTORE, listOf("kernel")))
        assertEquals(kc1Sha, Hashes.sha256(File(f.stage, "image/kernel.kc").readBytes()))
        assertEquals("$kc1Sha  kernel.kc", shaLine(File(f.stage, "image.sha256"), "kernel.kc"))
        assertTrue(File(f.stage, "image/manifest.json").readText().contains("\"sha256\": \"$kc1Sha\""))
        assertEquals(2, File(f.stage, "logs").list()!!.count { it.startsWith("update-") })
        val st2 = f.verb(OneiosRoot.Verb.STATUS).status
        assertEquals("unknown", st2.imageKernel!!.buildId)
        assertEquals(kc1Sha, st2.imageKernel.kcSha256)
        // Refused during a session: nothing changes.
        f.control.mkdirs()
        File(f.control, "boot").writeText("boot-1\n")
        File(f.control, "state").writeText("running\n")
        assertRefused(f.verb(OneiosRoot.Verb.FINISH, listOf("kernel", kc2Sha, bid)), "session is running")
        assertRefused(f.verb(OneiosRoot.Verb.RESTORE, listOf("kernel")), "session is running")
        assertRefused(f.verb(OneiosRoot.Verb.KBINPUT, listOf("profile.toml", "3", Hashes.sha256("a".toByteArray())), "a".toByteArray()), "session is running")
        assertEquals(kc1Sha, Hashes.sha256(File(f.stage, "image/kernel.kc").readBytes()))
    }

    /**
     * Update the kernel's two root verbs (docs/oneios.md, "Kernel updates"): `kbcache` keeps the kernelcache the
     * tool fetched from Apple and decoded only when root's own hash of it is the pin, removes the downloaded IM4P,
     * and `status` then reports it (the cache a later update builds from without a download); `kbclean` removes
     * the update's work folder and never `kb/`. Both refuse during a session.
     */
    @Test
    fun theKernelUpdateKeepsOnlyThePinnedKernelcacheAndCleansItsWork() = each { f ->
        assertOk(f.runtime())
        val work = File(f.stage, "make-kernel")
        val kc = ByteArray(4096) { (it % 253).toByte() }
        val sha = Hashes.sha256(kc)
        fun plain(file: File, mode: String) = Files.setPosixFilePermissions(file.toPath(), java.nio.file.attribute.PosixFilePermissions.fromString(mode))
        fun fetched(bytes: ByteArray) {
            // As the tool leaves them: the IM4P and the fetch's record in inputs/, the decode beside them.
            File(work, "inputs").mkdirs()
            plain(work, "rwxr-xr-x"); plain(File(work, "inputs"), "rwxr-xr-x")
            File(work, "inputs/kernelcache.release.v54").writeBytes(ByteArray(64) { 9 })
            File(work, "inputs/inputs.json").writeText("{}")
            File(work, "kernelcache.macho").writeBytes(bytes)
            plain(File(work, "kernelcache.macho"), "rw-r--r--")
        }
        val kbcache = OneiosRoot.Verb.KBCACHE
        assertRefused(f.verb(kbcache, listOf("4096", sha)), "no kernelcache was fetched")
        // Not the pinned one, by its hash or its size: refused, deleted, nothing in kb/.
        fetched(kc)
        assertRefused(f.verb(kbcache, listOf("4096", "0".repeat(64))), "not the one the profile pins")
        assertFalse(File(work, "kernelcache.macho").exists())
        assertFalse(File(f.stage, "kb/kernelcache.macho").exists())
        fetched(kc)
        assertRefused(f.verb(kbcache, listOf("4095", sha)), "not the one the profile pins")
        assertFalse(File(work, "kernelcache.macho").exists())
        assertEquals(null, f.verb(OneiosRoot.Verb.STATUS).status.kb.kernelcacheSha256)
        // The pinned one: into kb/ and recorded, the IM4P gone; status reports it.
        fetched(kc)
        assertOk(f.verb(kbcache, listOf("4096", sha)))
        assertEquals(sha, Hashes.sha256(File(f.stage, "kb/kernelcache.macho").readBytes()))
        assertEquals(sha, File(f.stage, "kb/kernelcache.sha256").readText().trim())
        assertFalse(File(work, "inputs").exists())
        assertFalse(File(work, "kernelcache.macho").exists())
        assertEquals(sha, f.verb(OneiosRoot.Verb.STATUS).status.kb.kernelcacheSha256)
        // kbclean: a download's parts and a build that was not activated go; kb/ stays.
        File(work, "inputs").mkdirs()
        File(work, "inputs/kernelcache.release.v54.part").writeBytes(ByteArray(10))
        File(work, "out").mkdirs()
        assertOk(f.verb(OneiosRoot.Verb.KBCLEAN))
        assertFalse(work.exists())
        assertEquals(sha, Hashes.sha256(File(f.stage, "kb/kernelcache.macho").readBytes()))
        assertTrue(f.verb(OneiosRoot.Verb.KBCLEAN).reply.ok!!.contains("nothing"))
        // The runtime's list is untouched by either: the switch's check_list of runtime/ still passes.
        assertOk(f.verb(OneiosRoot.Verb.STATUS))
        // During a session: both refused, nothing changes.
        f.control.mkdirs()
        File(f.control, "boot").writeText("boot-1\n")
        File(f.control, "state").writeText("running\n")
        fetched(kc)
        assertRefused(f.verb(kbcache, listOf("4096", sha)), "session is running")
        assertRefused(f.verb(OneiosRoot.Verb.KBCLEAN), "session is running")
        assertTrue(File(work, "kernelcache.macho").isFile)
    }

    /**
     * Update the kernel end to end against the real `oneios-tool serve` and this root script, with the network:
     * only when `ONEIOS_TOOL_SERVE` names a tool for this machine and `ONEIOS_PROFILE` OneiOS's
     * `profiles/ios-27.0.1-iPhone18,2.toml` (it downloads Apple's 23 MB kernelcache member from Apple):
     * `ONEIOS_TOOL_SERVE=.../oneios-tool ONEIOS_PROFILE=.../ios-27.0.1-iPhone18,2.toml ./gradlew :core:root:testDebugUnitTest
     * --tests '*OneiosScriptTest.theKernelUpdateFetchesFromApple*'`. The runtime here has no kernel, so the build
     * itself is refused (`not-found`); what is checked is everything before it: the exact requests, the decoded
     * SHA-256 against the app's kb.json pin, kb/ holding it, the IM4P gone, and a second run not downloading again.
     */
    @Test
    fun theKernelUpdateFetchesFromAppleDecodesAndCachesOnThePhone() {
        val tool = System.getenv("ONEIOS_TOOL_SERVE")?.let(::File)
        val profile = System.getenv("ONEIOS_PROFILE")?.let(::File)
        assumeTrue("ONEIOS_TOOL_SERVE and ONEIOS_PROFILE name no tool and profile", tool?.canExecute() == true && profile?.isFile == true)
        val f = Fake("/bin/sh")
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertOk(f.receive("runtime", "runtime.json", "{}".toByteArray()))
        assertOk(f.receive("runtime", "bin/xnuhost", ELF, "0755"))
        assertOk(f.receive("runtime", "lib/profiles/ios-27.0.1-iPhone18-2.toml", profile!!.readBytes()))
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("runtime", "3", "0.1.0", "1", "bin/xnuhost", "1", "0", "none", "none", "none")))
        val kb = com.fahadali.oneos.core.model.OneiosKb.parse(File(Shipped.fullAssets, "kb/kb.json").readText()).getOrThrow()
        val assets = OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }.associateWith { File(Shipped.fullAssets, "kb/$it").readBytes() }
        File(f.stage, "tool").mkdirs()
        fun once(): Pair<OneiosKernelUpdate.Outcome, List<String>> {
            val s = OneiosToolSession(
                "exec '${tool!!.path}' serve --stage '${f.stage.path}' --idle 120", launch = listOf("sh", "-c"),
                environment = mapOf("TMPDIR" to File(f.stage, "tool").path),
            )
            try {
                assertTrue(s.start() is OneiosToolSession.Start.Ready)
                val asked = mutableListOf<String>()
                val io = object : OneiosKernelUpdate.Io {
                    override fun tool(cmd: String, keys: Map<String, Any?>): com.fahadali.oneos.core.model.OneiosToolFlow {
                        asked += cmd
                        var v = com.fahadali.oneos.core.model.OneiosToolFlow()
                        val end = s.call(cmd, keys) { v = v.with(it) }
                        return if (end == null) v.lost(s.ended ?: "the tool ended") else v
                    }

                    override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? {
                        asked += verb.word
                        val o = f.verb(verb, args, data)
                        return if (o.exit == 0 && o.reply.ok != null) null else o.reply.refused ?: o.reply.failed ?: o.text
                    }

                    override fun phase(phase: OneiosKernelUpdate.Phase) {}
                    override fun done(line: String) {}
                    override val stopped = false
                }
                val cached = f.verb(OneiosRoot.Verb.STATUS).status.kb.kernelcacheSha256
                return OneiosKernelUpdate(f.stage.path, kb, "kernel/xnu.macho", assets).run(io, cached) to asked.filter { it != "kbinput" }
            } finally {
                s.close()
            }
        }
        val (first, asked) = once()
        assertEquals(listOf("fetch", "im4p", "kbcache", "prelink", "kbclean"), asked)
        first as OneiosKernelUpdate.Outcome.Stopped
        assertEquals("prelink" to "not-found", first.step to first.code)
        assertEquals(kb.kernelcacheSha256, Hashes.sha256(File(f.stage, "kb/kernelcache.macho").readBytes()))
        assertEquals(78_135_296L, File(f.stage, "kb/kernelcache.macho").length())
        assertFalse(File(f.stage, "make-kernel").exists())
        // Again: the cached kernelcache is used, nothing is downloaded.
        val (_, again) = once()
        assertEquals(listOf("prelink", "kbclean"), again)
    }

    /**
     * Make iOS image end to end against the real `oneios-tool serve` and this root script, with no network: only when
     * `ONEIOS_TOOL_SERVE` names a tool for this machine that has `make-image` (OneiOS 42cf43b or newer):
     * `ONEIOS_TOOL_SERVE=.../oneios-tool ./gradlew :core:root:testDebugUnitTest --tests '*OneiosScriptTest.makeIOSImage*'`.
     * The runtime is staged by root's own verbs with a kernel and one stand-in profile in `lib/profiles/`, whose IPSW
     * (nothing of Apple's: OneiOS's tests/serve.rs `stand_in_ipsw`) `oneios-tool rangeserve` serves on 127.0.0.1; the
     * pairing files are this APK's own `assets/kb/`. [OneiosMakeImage] sends the app's exact requests:
     * 1. with the room short (the tool's `ONEIOS_SERVE_TEST_FREE`): `make-image` is refused `space` at `check`, with
     *    one `space` event, before anything is fetched or written;
     * 2. with room: the tool takes the app's keys and its defaults (the profile, the runtime's kernel, kb/), fetches
     *    every member from the profile's URL, and stops at `place` (the stand-in OS image is no APFS volume), so
     *    root's `finish` is not asked; it leaves `image.new` and both lists empty and no `make/build`, and keeps the
     *    fetched members in `make/inputs` for the next run.
     * What it does not reach (no stand-in can): the decryption, the volumes, the tweaks, the prelink, `finish image`.
     */
    @Test
    fun makeIOSImageRunsTheAppsRequestsAgainstTheRealTool() {
        val tool = System.getenv("ONEIOS_TOOL_SERVE")?.let(::File)
        assumeTrue("ONEIOS_TOOL_SERVE names no oneios-tool", tool?.canExecute() == true)
        val f = Fake("/bin/sh")
        val web = File(f.root, "web").apply { mkdirs() }
        val port = java.net.ServerSocket(0).use { it.localPort }
        val (profile, sizes) = standInIpsw(web, "http://127.0.0.1:$port/stand-in.ipsw", osLen = 9000)
        val toolPath = tool!!.path
        started += ProcessBuilder(toolPath, "rangeserve", web.path, port.toString()).redirectErrorStream(true).redirectOutput(File(f.root, "rangeserve.log")).start()
        await("rangeserve on $port") { runCatching { java.net.Socket("127.0.0.1", port).close() }.isSuccess }
        // A runtime with a kernel, staged as the app stages one (root's begin, receive, finish with the kernel's facts).
        val xnu = ByteArray(4096) { (it * 7).toByte() }
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertOk(f.receive("runtime", "runtime.json", """{"format": 1, "kernel": {"path": "kernel/xnu.macho"}}""".toByteArray()))
        assertOk(f.receive("runtime", "bin/xnuhost", ELF, "0755"))
        assertOk(f.receive("runtime", "kernel/xnu.macho", xnu))
        assertOk(f.receive("runtime", "lib/profiles/test.toml", profile.toByteArray()))
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("runtime", "4", "0.1.13", "1", "bin/xnuhost", "1", "0", "xnu-12377-test-aaaaaaaaaaaa", Hashes.sha256(xnu), "12377")))
        val kb = com.fahadali.oneos.core.model.OneiosKb.parse(File(Shipped.fullAssets, "kb/kb.json").readText()).getOrThrow()
        val assets = OneiosKbInput.NAMES.associateWith { File(Shipped.fullAssets, "kb/$it").readBytes() }
        File(f.stage, "tool").mkdirs()

        class Run(val env: Map<String, String>) : OneiosMakeImage.Io {
            val asked = mutableListOf<String>()
            var view = com.fahadali.oneos.core.model.OneiosToolFlow()
            val events = mutableListOf<com.fahadali.oneos.core.model.OneiosTool.Event>()
            private var s: OneiosToolSession? = null

            override fun status(): Result<OneiosStatus> = Result.success(f.verb(OneiosRoot.Verb.STATUS).also { asked += "status" }.status)
            override fun latestRuntime(unless: String?): OneiosMakeImage.Runtime = error("the staged runtime carries a kernel: no download")
            override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? {
                asked += if (verb == OneiosRoot.Verb.KBINPUT) "kbinput" else verb.word
                val o = f.verb(verb, args, data)
                return if (o.exit == 0 && o.reply.ok != null) null else o.reply.refused ?: o.reply.failed ?: o.text
            }
            override fun openTool(): Result<List<String>> {
                asked += "tool"
                val t = OneiosToolSession(
                    "exec '$toolPath' serve --stage '${f.stage.path}' --idle 120 --thermal off", launch = listOf("sh", "-c"),
                    environment = mapOf("TMPDIR" to File(f.stage, "tool").path) + env,
                )
                s = t
                return when (val st = t.start()) {
                    is OneiosToolSession.Start.Ready -> Result.success(st.hello.cmds)
                    else -> Result.failure(IllegalStateException(st.toString()))
                }
            }
            override fun closeTool() {
                s?.close()
                s = null
            }
            override fun tool(cmd: String, keys: Map<String, Any?>): com.fahadali.oneos.core.model.OneiosToolFlow {
                asked += cmd
                val t = s!!
                view = com.fahadali.oneos.core.model.OneiosToolFlow()
                val end = t.call(cmd, keys) { e -> events += e; view = view.with(e) }
                return if (end == null) view.lost(t.ended ?: "the tool ended") else view
            }
            override fun phase(phase: OneiosMakeImage.Phase) {}
            override fun done(line: String) {}
            override val stopped = false
        }
        fun once(env: Map<String, String>): Pair<OneiosMakeImage.Outcome, Run> {
            val io = Run(env)
            try {
                return OneiosMakeImage(f.stage.path, kb, assets).run(io) to io
            } finally {
                io.closeTool()
            }
        }
        fun nothingLeft(what: String) {
            assertEquals(what, emptyList<String>(), File(f.stage, "image.new").list()!!.toList())
            assertEquals(what, 0L, File(f.stage, "image.new.sha256").length())
            assertEquals(what, 0L, File(f.stage, "image.new.ids").length())
            assertFalse(what, File(f.stage, "make/build").exists())
        }
        // A tool from before make-image (the v0.1.12 runtime's): nothing to test against.
        val probe = OneiosToolSession(
            "exec '$toolPath' serve --stage '${f.stage.path}' --idle 10 --thermal off", launch = listOf("sh", "-c"),
            environment = mapOf("TMPDIR" to File(f.stage, "tool").path),
        )
        val cmds = try {
            (probe.start() as? OneiosToolSession.Start.Ready)?.hello?.cmds.orEmpty()
        } finally {
            probe.close()
        }
        assumeTrue("this oneios-tool has no make-image (OneiOS 42cf43b or newer has)", com.fahadali.oneos.core.model.OneiosTool.Cmd.MAKE_IMAGE in cmds)

        // 1. The room short: refused at check, nothing fetched or written; root's finish not asked.
        val (short, a) = once(mapOf("ONEIOS_SERVE_TEST_FREE" to "1000"))
        short as OneiosMakeImage.Outcome.Stopped
        assertEquals("make-image" to "space", short.step to short.code)
        assertEquals(listOf("status") + List(12) { "kbinput" } + listOf("begin", "tool", "make-image"), a.asked)
        assertEquals(1, a.events.count { it is com.fahadali.oneos.core.model.OneiosTool.Event.Space })
        assertEquals(1000L, short.free)
        assertTrue("${short.need}", (short.need ?: 0) > 1000)
        assertEquals("Not enough space", com.fahadali.oneos.core.model.OneiosPlain.makeImage(short.step, short.end, short.code, short.text, short.need, short.free).title)
        assertFalse(File(f.stage, "make/inputs").exists())
        nothingLeft("space")
        // The pairing files are in kb/, each the APK's.
        for (name in OneiosKbInput.NAMES) assertTrue(name, File(f.stage, "kb/$name").readBytes().contentEquals(assets.getValue(name)))

        // 2. With room: the app's request is taken whole, every member fetched from the profile's URL, the stop at
        // place (the stand-in OS image is no APFS volume), everything written removed but the fetched members.
        val (failed, b) = once(emptyMap())
        failed as OneiosMakeImage.Outcome.Stopped
        assertEquals("make-image" to OneiosToolFlow.End.FAILED, failed.step to failed.end)
        assertTrue(failed.text!!, "is not a raw APFS image" in failed.text!!)
        assertFalse(b.asked.any { it == "finish" || it == "fetch" || it == "tweaks" })
        val start = b.events.filterIsInstance<com.fahadali.oneos.core.model.OneiosTool.Event.Start>().single()
        assertEquals(com.fahadali.oneos.core.model.OneiosTool.Cmd.MAKE_IMAGE, start.cmd)
        assertEquals(listOf("check", "directory", "download", "decrypt", "place"), start.steps.map { it.first }.take(5))
        assertTrue(start.steps.map { it.first }.containsAll(listOf("tweaks", "seed", "kernelcache", "kernel-audit", "kernel-stubs-check", "manifest", "verify", "lists")))
        assertEquals(listOf("check", "directory", "download", "decrypt", "place"), b.events.filterIsInstance<com.fahadali.oneos.core.model.OneiosTool.Event.Step>().map { it.step })
        assertEquals(1, b.events.count { it is com.fahadali.oneos.core.model.OneiosTool.Event.Space })
        nothingLeft("failure")
        for ((name, size) in sizes) assertEquals(name, size, File(f.stage, "make/inputs/$name").length())
        assertTrue(File(f.stage, "make/inputs/inputs.json").isFile)
        assertEquals("The image couldn't be made", com.fahadali.oneos.core.model.OneiosPlain.makeImage(failed.step, failed.end, failed.code, failed.text).title)
        // The staged runtime and kb/ are as they were; no image set was staged.
        assertEquals(null, f.verb(OneiosRoot.Verb.STATUS).status.image)
    }

    /**
     * A stand-in IPSW in [web] (`stand-in.ipsw`) and its profile, as OneiOS's tests/serve.rs `stand_in_ipsw` makes
     * them (no AEA): generated members, a BuildManifest with the build identity the profile asks for, every member's
     * size and CRC-32 pinned, the profile's URL [url]. Returns the profile's text and each file `fetch` writes (by
     * its name in INDIR) with its size.
     */
    private fun standInIpsw(web: File, url: String, osLen: Int): Pair<String, Map<String, Long>> {
        fun noise(n: Int, seed: Int) = ByteArray(n) { i -> ((i * 1103515245L + seed * 12345L) ushr 7).toByte() }
        val members = listOf(
            Triple("os", "001-00001-001.dmg", noise(osLen, 31)),
            Triple("systemos", "001-00002-001.dmg", noise(70_000, 32)),
            Triple("app", "001-00003-001.dmg", noise(32_768, 33)),
            Triple("trust-static", "Firmware/001-00001-001.dmg.trustcache", noise(100, 34)),
            Triple("trust-system", "Firmware/001-00002-001.dmg.trustcache", noise(100, 35)),
            Triple("trust-app", "Firmware/001-00003-001.dmg.trustcache", noise(100, 36)),
            Triple("roothash-os", "Firmware/001-00001-001.dmg.root_hash", noise(100, 37)),
            Triple("roothash-system", "Firmware/001-00002-001.dmg.root_hash", noise(100, 38)),
            Triple("roothash-app", "Firmware/001-00003-001.dmg.root_hash", noise(100, 39)),
            Triple("kernelcache", "kernelcache.release.t1", noise(4000, 40)),
            Triple("devicetree", "Firmware/all_flash/DeviceTree.t1ap.im4p", noise(200, 41)),
        )
        val components = listOf(
            "os" to "OS", "systemos" to "Cryptex1,SystemOS", "app" to "Cryptex1,AppOS", "trust-static" to "StaticTrustCache",
            "trust-system" to "Cryptex1,SystemTrustCache", "trust-app" to "Cryptex1,AppTrustCache", "roothash-os" to "SystemVolume",
            "roothash-system" to "Cryptex1,SystemVolume", "roothash-app" to "Cryptex1,AppVolume", "kernelcache" to "KernelCache", "devicetree" to "DeviceTree",
        )
        val manifest = components.joinToString("") { (role, name) ->
            "<key>$name</key><dict><key>Info</key><dict><key>Path</key><string>${members.first { it.first == role }.second}</string></dict></dict>"
        }
        val plist = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><plist version=\"1.0\"><dict><key>ProductVersion</key><string>0.0.1</string>" +
            "<key>ProductBuildVersion</key><string>0T1</string><key>SupportedProductTypes</key><array><string>iTest1,1</string></array>" +
            "<key>BuildIdentities</key><array><dict><key>ApChipID</key><string>0x1234</string><key>ApBoardID</key><string>0x02</string>" +
            "<key>Info</key><dict><key>DeviceClass</key><string>t1ap</string><key>RestoreBehavior</key><string>Erase</string></dict>" +
            "<key>Manifest</key><dict>$manifest</dict></dict></array></dict></plist>"
        val all = members + listOf(Triple("buildmanifest", "BuildManifest.plist", plist.toByteArray()), Triple("restore", "Restore.plist", "<plist/>".toByteArray()))
        fun crc(b: ByteArray) = java.util.zip.CRC32().apply { update(b) }.value
        // A stored ZIP, as tests/serve.rs `zip_of` writes it.
        val out = java.io.ByteArrayOutputStream()
        val dir = java.io.ByteArrayOutputStream()
        fun le(o: java.io.ByteArrayOutputStream, v: Long, width: Int) = repeat(width) { o.write(((v ushr (8 * it)) and 0xff).toInt()) }
        for ((_, path, data) in all) {
            val fields = java.io.ByteArrayOutputStream()
            for ((v, w) in listOf(20L to 2, 0L to 2, 0L to 2, 0L to 2, 0x21L to 2, crc(data) to 4, data.size.toLong() to 4, data.size.toLong() to 4, path.length.toLong() to 2, 0L to 2)) le(fields, v, w)
            val offset = out.size().toLong()
            out.write("PK\u0003\u0004".toByteArray(Charsets.ISO_8859_1)); out.write(fields.toByteArray()); out.write(path.toByteArray()); out.write(data)
            dir.write("PK\u0001\u0002\u0014\u0000".toByteArray(Charsets.ISO_8859_1)); dir.write(fields.toByteArray()); dir.write(ByteArray(10)); le(dir, offset, 4); dir.write(path.toByteArray())
        }
        val start = out.size().toLong()
        out.write(dir.toByteArray())
        out.write("PK\u0005\u0006\u0000\u0000\u0000\u0000".toByteArray(Charsets.ISO_8859_1))
        le(out, all.size.toLong(), 2); le(out, all.size.toLong(), 2); le(out, dir.size().toLong(), 4); le(out, start, 4); le(out, 0, 2)
        File(web, "stand-in.ipsw").writeBytes(out.toByteArray())
        val pins = all.joinToString("") { (role, path, data) -> "[[member]]\nrole = \"$role\"\npath = \"$path\"\nsize = ${data.size}\ncrc32 = \"%08x\"\n".format(crc(data)) }
        val profile = "schema = 1\n[os]\nname = \"ios-0.0.1-0T1-iTest1,1\"\nversion = \"0.0.1\"\nbuild = \"0T1\"\ndevice = \"iTest1,1\"\nboard = \"t1ap\"\n" +
            "chip_id = 0x1234\nboard_id = 0x02\narch = \"arm64e\"\n[ipsw]\nurl = \"$url\"\nsize = 12345\nsha256 = \"${"00".repeat(32)}\"\nneed_gib = 0\n$pins" +
            "[image]\nformat = 1\nid = \"ios-0.0.1-0T1-iTest1-1\"\nstage = \"/data/local/tmp/oneios/image\"\narchive = \"OneiOS_test.tar.zst\"\nchunk = 4096\n" +
            "seed = \"data.seed\"\nkernel = \"kernel.kc\"\n[image.files]\nos = \"os.img\"\nsystemos = \"systemos.img\"\napp = \"app.img\"\n" +
            "trust-static = \"trust/static.trustcache\"\ntrust-system = \"trust/system.trustcache\"\ntrust-app = \"trust/app.trustcache\"\n" +
            "roothash-os = \"trust/os.root_hash\"\nroothash-system = \"trust/system.root_hash\"\nroothash-app = \"trust/app.root_hash\"\n" +
            "[data]\nvolume_uuid = \"11111111-2222-3333-4444-555555555555\"\nepoch = 1700000000\n"
        return profile to mapOf("001-00001-001.dmg" to osLen.toLong(), "001-00002-001.dmg" to 70_000L, "001-00003-001.dmg" to 32_768L)
    }

    private fun manifestWithKc(size: Int, sha: String) = """
        { "format": 1, "name": "oneios-image", "os": "iOS", "version": "27.0.1", "build": "24A446",
          "device": "iPhone18,2",
          "files": [
            { "path": "kernel.kc", "size": $size, "sha256": "$sha", "role": "kernel", "format": "kernel-collection", "read_only": true, "hashes": "kernel.kc.hashes" },
            { "path": "kernel.kc.hashes", "size": 8, "sha256": "${Hashes.sha256("hashes-1".toByteArray())}", "role": "hashes", "format": "oneios-hash-list-1" },
            { "path": "os.img", "size": 100, "sha256": "${Hashes.sha256(ByteArray(100))}" }
          ] }
    """.trimIndent().toByteArray()

    private fun shaLine(list: File, path: String) =
        list.readLines().single { it.endsWith("  $path") }

    private fun kbInputs(f: Fake) {
        for (name in OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }) {
            val bytes = "kb-$name".toByteArray()
            assertOk(f.verb(OneiosRoot.Verb.KBINPUT, listOf(name, bytes.size.toString(), Hashes.sha256(bytes)), bytes))
        }
    }

    private fun makeKernelOut(f: Fake, kc: ByteArray, xnuSha: String, kcInSha: String) {
        val out = File(f.stage, "make-kernel/out").apply { mkdirs() }
        File(out, "kernel.kc").writeBytes(kc)
        File(out, "kernel.kc.hashes").writeBytes("hashes".toByteArray())
        File(out, "kernel.kc.build.json").writeText("""{"inputs": {"kernel": {"sha256": "$xnuSha"}, "kernelcache": {"sha256": "$kcInSha"}}}""")
        File(out, "kernel.kc.prelink.json").writeText("{}")
        File(out, "kernel.kc.binds.json").writeText("{}")
    }

    /**
     * `take` copies with dd in 1 MiB blocks where dd counts in bytes, and with
     * head -c where it does not. Three kinds of dd, as stand-ins in front of the
     * machine's: GNU's and busybox's (count_bytes with fullblock), toybox's
     * (count_bytes; it refuses fullblock) and one that knows neither. Each
     * takes a file of several pipe buffers whole, and refuses a short one and
     * a wrong SHA-256.
     */
    @Test
    fun receiveCopiesWithWhicheverDdCountsInBytes() = each { f ->
        val real = listOf("/usr/bin/dd", "/bin/dd").first { File(it).canExecute() }
        val bin = File(f.root, "fakebin").apply { mkdirs() }
        val used = File(f.root, "dd.used")
        fun dd(body: String) = File(bin, "dd").apply {
            writeText("#!/bin/sh\n$body\n")
            setExecutable(true)
        }
        val data = ByteArray(700_001) { (it * 31 + it / 4099).toByte() }
        val kinds = mapOf(
            "toybox" to """case "$*" in *fullblock*) echo "dd: bad iflag" >&2; exit 1 ;; esac
                           echo toybox >> $used
                           exec $real "$@" iflag=count_bytes,fullblock""",
            "none" to """case "$*" in *iflag*) echo "dd: bad arg" >&2; exit 1 ;; esac; exec $real "$@" """,
            "gnu" to """echo gnu >> $used; exec $real "$@" """,
        )
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")))
        for ((kind, body) in kinds) {
            dd(body)
            used.delete()
            val env = HostTools.env(bin.path)
            val name = "$kind.img"
            val args = { size: Int, sha: String -> listOf("image", name, size.toString(), sha, "0644") }
            assertRefused(f.verb(OneiosRoot.Verb.RECEIVE, args(data.size, "0".repeat(64)), data, env), "did not arrive intact")
            assertRefused(f.verb(OneiosRoot.Verb.RECEIVE, args(data.size + 5, Hashes.sha256(data)), data, env), "${data.size} of ${data.size + 5} bytes")
            assertFalse(File(f.stage, "image.new/$name").exists())
            assertFalse(File(f.stage, "image.new/$name.part").exists())
            assertOk(f.verb(OneiosRoot.Verb.RECEIVE, args(data.size, Hashes.sha256(data)), data, env))
            assertTrue(kind, File(f.stage, "image.new/$name").readBytes().contentEquals(data))
            // More than was announced: only the announced bytes are taken, and they are not the file.
            val more = f.verb(OneiosRoot.Verb.RECEIVE, listOf("image", "$kind.more", "10", Hashes.sha256(data.copyOf(10)), "0644"), data, env)
            assertOk(more)
            assertEquals(10L, File(f.stage, "image.new/$kind.more").length())
            // The copy itself went through dd, except where dd cannot count bytes.
            assertEquals(kind, if (kind == "none") false else true, used.exists() && used.readText().trim().lines().all { it == kind })
        }
    }

    @Test
    fun theLauncherCarriesOnlyPlainArguments() {
        fun bad(verb: OneiosRoot.Verb, vararg args: String) =
            assertTrue("$verb ${args.toList()}", OneiosRoot.problems(verb, args.toList()).isNotEmpty())
        fun good(verb: OneiosRoot.Verb, vararg args: String) =
            assertEquals("$verb ${args.toList()}", emptyList<String>(), OneiosRoot.problems(verb, args.toList()))
        val h = "a".repeat(64)
        good(OneiosRoot.Verb.STATUS)
        good(OneiosRoot.Verb.BEGIN, "image")
        good(OneiosRoot.Verb.RECEIVE, "image", "overlay/kernel.kc", "12", h, "0644")
        good(OneiosRoot.Verb.FINISH, "runtime", "3", "0.1.0", "1", "bin/xnuhost", "1,2", "0", "none", "none", "none")
        good(OneiosRoot.Verb.FINISH, "runtime", "3", "0.1.0", "1", "bin/xnuhost", "1,2", "0", "xnu-1-2-3", h, "xnu-1")
        bad(OneiosRoot.Verb.FINISH, "runtime", "3", "0.1.0", "1", "bin/xnuhost", "1,2", "0")
        bad(OneiosRoot.Verb.FINISH, "runtime", "3", "0.1.0", "1", "bin/xnuhost", "1,2", "0", "none", "none", "yes")
        bad(OneiosRoot.Verb.FINISH, "runtime", "3", "0.1.0", "1", "bin/xnuhost", "1,2", "0", "xnu-1", h, "none")
        good(OneiosRoot.Verb.FINISH, "kernel", h, "xnu-1-2-3")
        bad(OneiosRoot.Verb.FINISH, "kernel", h)
        bad(OneiosRoot.Verb.FINISH, "kernel", "zz", "xnu-1")
        good(OneiosRoot.Verb.KBINPUT, "kernelcache.macho", "12", h)
        good(OneiosRoot.Verb.KBINPUT, "match/fixtures/fileset-24A446-symbols.json", "12", h)
        bad(OneiosRoot.Verb.KBINPUT, "xnu.macho", "12", h)
        bad(OneiosRoot.Verb.KBINPUT, "../kernelcache.macho", "12", h)
        good(OneiosRoot.Verb.RESTORE, "kernel")
        bad(OneiosRoot.Verb.RESTORE, "runtime")
        bad(OneiosRoot.Verb.RESTORE)
        good(OneiosRoot.Verb.KBCACHE, "78135296", h)
        bad(OneiosRoot.Verb.KBCACHE, "78135296")
        bad(OneiosRoot.Verb.KBCACHE, "-1", h)
        bad(OneiosRoot.Verb.KBCACHE, "1", "zz")
        good(OneiosRoot.Verb.KBCLEAN)
        bad(OneiosRoot.Verb.KBCLEAN, "make-kernel")
        good(OneiosRoot.Verb.FINISH, "image", "3", "1", "27.0.1", "24A446")
        good(OneiosRoot.Verb.SWITCH, "100", "1")
        good(OneiosRoot.Verb.SWITCH, "100", "1", "takeover")
        good(OneiosRoot.Verb.SWITCH, "100", "1", "hosted")
        bad(OneiosRoot.Verb.BEGIN, "system")
        bad(OneiosRoot.Verb.BEGIN, "image", "x")
        bad(OneiosRoot.Verb.RECEIVE, "image", "../os.img", "12", h, "0644")
        bad(OneiosRoot.Verb.RECEIVE, "image", "/os.img", "12", h, "0644")
        bad(OneiosRoot.Verb.RECEIVE, "image", "os.img;reboot", "12", h, "0644")
        bad(OneiosRoot.Verb.RECEIVE, "image", "os.img", "12", h, "4755")
        bad(OneiosRoot.Verb.RECEIVE, "image", "os.img", "1 2", h, "0644")
        bad(OneiosRoot.Verb.RECEIVE, "image", "os.img", "12", "\$(id)", "0644")
        bad(OneiosRoot.Verb.SCRIPT, "oneos_switch.sh", "12", h)
        bad(OneiosRoot.Verb.FINISH, "runtime", "3", "0.1.0", "1", "bin/xnuhost", "1;2", "0")
        bad(OneiosRoot.Verb.FINISH, "image", "3", "1", "27.0.1", "24A446 x")
        bad(OneiosRoot.Verb.SWITCH, "100", "yes")
        bad(OneiosRoot.Verb.SWITCH, "100", "1", "fast")
        bad(OneiosRoot.Verb.SWITCH, "100", "1", "takeover", "x")
        bad(OneiosRoot.Verb.REMOVE, "all")
        assertTrue(runCatching { OneiosRoot.launcher(OneiosRoot.Verb.BEGIN, listOf("image; reboot"), h, 10) }.isFailure)
        val text = OneiosRoot.launcher(OneiosRoot.Verb.RECEIVE, listOf("image", "os.img", "12", h, "0644"), h, 10)
        assertTrue(text.contains("set -- receive image os.img 12 $h 0644\n"))
        assertTrue(text.contains("S=/data/local/tmp/oneios\n"))
        assertFalse(Regex("@[A-Z]+@").containsMatchIn(text))
    }

    @Test
    fun statusLinesParse() {
        val s = OneiosStatus.parse(
            listOf(
                "stage present", "runtime 0.1.0 1 bin/xnuhost 1,2", "image 1 27.0.1 24A446 12345", "session open running",
                "outcome failsafe 1700000000 processes still in the session's namespace: 12", "ready 0 an iOS session of this boot is still open (running)",
            ),
        )
        assertTrue(s.staged)
        assertEquals("1,2", s.runtime?.imageFormats)
        assertEquals(12345L, s.image?.bytes)
        assertTrue(s.sessionOpen)
        assertEquals("failsafe", s.lastReturn)
        assertEquals("processes still in the session's namespace: 12", s.lastReturnDetail)
        assertEquals("an iOS session of this boot is still open (running)", s.notReady)
        val none = OneiosStatus.parse(listOf("stage present", "runtime none", "image none", "session none never", "outcome none", "ready 1"))
        assertEquals(null, none.runtime)
        assertEquals(null, none.image)
        assertTrue(none.ready)
        assertEquals(null, none.notReady)
    }

    // --- The session scripts' guards, on their text --------------------------------

    private fun code(f: File): List<String> = f.readLines().filterNot { it.trimStart().startsWith("#") }

    /** An iOS session never changes SELinux, a persist property, or anything of One UI's lock screen and keys. */
    @Test
    fun theSessionScriptsKeepOneUisGuards() {
        for (f in listOf(switchScript, returnScript, rootScript)) {
            val text = code(f).joinToString("\n")
            for (never in listOf(
                "setenforce", "setprop persist", "locksettings", "gatekeeper", "weaver", "/data/system/", "/data/misc/",
                "/data/user/", "/data/app/", " pm ", "cmd lock_settings", "vdc cryptfs", "keystore_cli",
            )) {
                assertFalse("${f.name} has '$never'", text.contains(never))
            }
        }
        // The clock caps are One UI's to set and the session's to lift; the kernel's thermal zones, trips and cooling
        // devices are never written (OneiOS docs/hardware.md 7d).
        for (f in listOf(switchScript, returnScript)) assertFalse(f.name, code(f).joinToString("\n").let { it.contains("/sys/class/thermal") || it.contains("cooling_device") })
        val sw = code(switchScript).joinToString("\n")
        // xnuhost's namespace has the stage over /data, and the session refuses to go on if One UI's data shows.
        assertTrue(sw.contains("mount --bind \"\$STAGE\" /data"))
        assertTrue(sw.contains("One UI's /data is still visible in the session's namespace"))
        assertTrue(sw.contains("remount,bind,ro"))
        // Its own stage, never the Android guests'.
        assertTrue(sw.contains("STAGE=\"\$T/data/local/tmp/oneios\""))
        assertEquals(OneiosRoot.STAGE, "/data/local/tmp/oneios")
        assertFalse(OneiosRoot.STAGE == RootScript.STAGE)
        // The S24 Ultra only, checked by the script itself.
        assertTrue(sw.contains("SM-S928*") && sw.contains("e3q") && sw.contains("SM8650"))
    }

    /** The owner (2026-11-16): another phone may try it, told what to expect — a warning, not a refusal. */
    @Test
    fun theSwitchWarnsOtherPhonesInsteadOfRefusingThem() {
        val sw = code(switchScript).joinToString("\n")
        assertTrue(sw.contains("WARNING: OneiOS is mainly tested and working on the Galaxy S24 Ultra 5G"))
        assertFalse(sw.contains("refuse \"iOS runs on the Galaxy S24 Ultra"))
    }

    /**
     * The switch's own phone check, run as written in the script on stand-in properties: every S24 Ultra model number
     * (the owner's SM-S928B, US U and U1, Canada's W with the US vendor model and bootloader, Korea's N, China's 0) is
     * the phone it is mainly tested on, with no warning; the same model on another codename or chip, and another phone, are warned.
     */
    @Test
    fun theSwitchTakesEveryS24UltraModelAsTheTestedPhone() {
        val lines = switchScript.readLines()
        val from = lines.indexOfFirst { it.startsWith("P_MODEL=\$(getprop ro.product.model)") }
        val to = (from until lines.size).first { lines[it] == "fi" }
        assertTrue(from > 0 && to > from)
        val check = lines.subList(from, to + 1).joinToString("\n")
        val dir = Files.createTempDirectory("oneios-s24u").toFile().also { roots += it }
        val getprop = File(dir, "getprop")
        getprop.writeText("#!/bin/sh\ncase \"\$1\" in\n  ro.product.model) echo \"\$FAKE_MODEL\" ;;\n  ro.product.device) echo \"\$FAKE_DEVICE\" ;;\n" +
            "  ro.soc.model) echo \"\$FAKE_SOC\" ;;\n  ro.product.vendor.model) echo SM-S928U ;;\n  ro.bootloader) echo S928USQU6EZIF ;;\nesac\n")
        assertTrue(getprop.setExecutable(true))
        fun output(sh: String, model: String, device: String, soc: String): String {
            val pb = ProcessBuilder(sh, "-c", "$check\necho \"S24U=\$S24U\"").redirectErrorStream(true)
            pb.environment()["PATH"] = "${dir.path}:${pb.environment()["PATH"]}"
            pb.environment().putAll(mapOf("FAKE_MODEL" to model, "FAKE_DEVICE" to device, "FAKE_SOC" to soc))
            val p = pb.start()
            val out = p.inputStream.readBytes().toString(Charsets.UTF_8)
            assertTrue(p.waitFor(30, TimeUnit.SECONDS))
            assertEquals(out, 0, p.exitValue())
            return out
        }
        fun warned(sh: String, model: String, device: String = "e3q", soc: String = "SM8650"): Boolean =
            output(sh, model, device, soc).let { it.contains("WARNING: OneiOS is mainly tested") && it.contains("S24U=1") }
        val s26 = "WARNING: Galaxy S26 Ultra (SM8850): iOS ran there only in another fork's root-only test"
        for (sh in shells) {
            for (m in listOf("SM-S928B", "SM-S928U", "SM-S928U1", "SM-S928W", "SM-S928N", "SM-S9280")) assertFalse("$sh $m", warned(sh, m))
            assertTrue(sh, warned(sh, "SM-S928W", device = "e3s", soc = "s5e9945"))
            assertTrue(sh, warned(sh, "SM-S928W", soc = "SM8750"))
            assertTrue(sh, warned(sh, "SM-S938W", device = "pa3q", soc = "SM8750"))
            // The S26 Ultra: warned, not refused, with what another fork measured on it (docs/oneios.md, "Scope").
            assertTrue(sh, warned(sh, "SM-S948B", device = "m3q", soc = "SM8850"))
            assertTrue(sh, output(sh, "SM-S948B", "m3q", "SM8850").contains(s26))
            assertTrue(sh, output(sh, "Galaxy S26 Ultra", "m3q", "SM8850").contains(s26))
            assertFalse(sh, output(sh, "SM-S938B", "pa3q", "SM8750").contains(s26))
            assertFalse(sh, output(sh, "SM-S928B", "e3q", "SM8650").contains(s26))
            // The S24 Ultra: no line at all, as before.
            assertEquals(sh, "S24U=0\n", output(sh, "SM-S928B", "e3q", "SM8650"))
            // The Galaxy A56 (SM-A566, a56x, s5e8855): its own path's lines (iOS 16.5, untested on an A56), not the
            // S24-only warning. The same model on another chip or codename is warned as any other phone.
            for (m in listOf("SM-A566B", "SM-A566E")) {
                val a56 = output(sh, m, "a56x", "s5e8855")
                assertTrue(a56, a56.contains("Galaxy A56 path: this phone is $m (a56x, s5e8855): iOS 16.5 (20F66)"))
                assertTrue(a56, a56.contains("WARNING: this path has not run on a Galaxy A56 yet (untested)"))
                assertFalse(a56, a56.contains("WARNING: OneiOS is mainly tested"))
                assertFalse(a56, a56.contains(s26))
            }
            assertTrue(sh, warned(sh, "SM-A566B", device = "a56x", soc = "s5e8865"))
            assertTrue(sh, warned(sh, "SM-A566B", device = "a57x", soc = "s5e8855"))
            assertFalse(sh, output(sh, "SM-A576B", "a57x", "s5e8865").contains("Galaxy A56 path"))
            assertFalse(sh, output(sh, "SM-S928B", "e3q", "SM8650").contains("A56"))
        }
    }

    /**
     * On the Galaxy A56 a staged image that is not iOS 16.5 (20F66) is warned, never refused (the owner's 2026-11-16
     * rule): iOS 27 has no GPU path there. The check runs as written in the script, after the stage checks (which
     * read I_BUILD); on the S24 Ultra (A56=0) it prints nothing, whatever the image.
     */
    @Test
    fun theA56WarnsAnImageThatIsNotIos165() {
        val lines = switchScript.readLines()
        val stage = lines.indexOf("stage_checks")
        assertTrue(lines[stage - 1].startsWith("# The stage first"))
        val from = lines.indexOfFirst { it == "if [ \"\$A56\" = 1 ] && [ \"\$I_BUILD\" != 20F66 ]; then" }
        val to = (from until lines.size).first { lines[it] == "fi" }
        assertTrue("$stage $from", stage > 0 && from > stage && to > from)
        // Nothing but echo lines inside: a warning, no refuse, no exit.
        val body = lines.subList(from + 1, to)
        assertTrue(body.toString(), body.all { it.trimStart().startsWith("echo \"WARNING: ") })
        val check = lines.subList(from, to + 1).joinToString("\n")
        fun output(sh: String, a56: String, build: String): String {
            val pb = ProcessBuilder(sh, "-c", "$check\necho done").redirectErrorStream(true)
            pb.environment().putAll(mapOf("A56" to a56, "I_BUILD" to build, "I_VERSION" to if (build == "20F66") "16.5" else "27.0.1"))
            val p = pb.start()
            val out = p.inputStream.readBytes().toString(Charsets.UTF_8)
            assertTrue(p.waitFor(30, TimeUnit.SECONDS))
            assertEquals(out, 0, p.exitValue())
            return out
        }
        for (sh in shells) {
            val warned = output(sh, "1", "24A446")
            assertTrue(warned, warned.contains("WARNING: the staged image is iOS 27.0.1 (24A446), not iOS 16.5 (20F66): iOS 27 has no GPU"))
            assertTrue(warned, warned.endsWith("done\n"))
            assertEquals(sh, "done\n", output(sh, "1", "20F66"))
            assertEquals(sh, "done\n", output(sh, "0", "24A446"))
            assertEquals(sh, "done\n", output(sh, "0", "20F66"))
        }
    }

    /**
     * The A56 path passes no xnuhost argument of its own (OneiOS's host table and the image's xnuhost.conf carry it):
     * xnuhost's two command lines are the S24 Ultra's, and nothing after the preflight's checks reads A56.
     */
    @Test
    fun theA56PathLeavesXnuhostsCommandLineAsItWas() {
        val sw = switchScript.readText()
        // xnuhost's command line (since fork bd4bbf2 built with set -- and run as the inner shell's waited-for child)
        val inner = sw.substring(sw.indexOf("set -- \"/data/runtime/\$R_XNUHOST\""), sw.indexOf("exit \"\$rc\""))
        assertTrue(inner.contains(
            "set -- \"/data/runtime/\$R_XNUHOST\" --session-abi \$ABI --mode takeover \\\n" +
                "            --runtime /data/runtime --image /data/image --data /data/data --session /data/session\n",
        ))
        assertTrue(inner.contains(
            "        [ \"\$(cat /data/control/base/mode 2>/dev/null)\" = takeover ] && set -- \"\$@\" --set session-mode=takeover\n",
        ))
        assertEquals(1, Regex("""exec "\${'$'}@"""").findAll(inner).count())
        assertFalse(inner.contains("A56") || inner.contains("a56"))
        // A56 is read only by the device lines and the image warning, both in the preflight.
        val code = code(switchScript)
        val uses = code.withIndex().filter { "\$A56" in it.value }.map { it.index }
        val session = code.indexOfFirst { it.contains("echo \"=== [1/5]") }
        assertEquals(2, uses.size)
        assertTrue(uses.toString(), uses.all { it < session })
        // No A56-only xnuhost argument of the other fork (OneiOS docs/a56-oneos-fork.md section 1).
        for (never in listOf("--display shm", "--gpu 2d", "--ram 4096M", "ONEIOS_AMDGPU_RENDER_NODE")) {
            assertFalse(never, code.joinToString("\n").contains(never))
        }
    }

    /** Every refusal of the switch comes before its first change: nothing above "THE SESSION" stops or starts anything. */
    @Test
    fun theSwitchRefusesBeforeItChangesAnything() {
        val lines = code(switchScript)
        val preflight = lines.indexOfFirst { it.contains("id -u 2>/dev/null)\" = 0 ] || refuse") }
        val session = lines.indexOfFirst { it.contains("echo \"=== [1/5]") }
        assertTrue(preflight in 1 until session)
        val before = lines.subList(preflight, session).joinToString("\n")
        for (change in listOf("ctl.stop", "ctl.start", "kill ", "wake_lock 2", "mkdir", "rm -", "mount --", "unshare -m", "> \"\$SESSION", "> \"\$CTL")) {
            assertFalse("the preflight has '$change'", before.contains(change))
        }
        val after = lines.subList(session, lines.size).joinToString("\n")
        assertFalse("a refusal after the first change", Regex("""(^|\s)refuse "(?!\${'$'}SESSION is a symlink|\${'$'}CTL is a symlink|could not make)""").containsMatchIn(after))
        // The way back is armed before One UI's zygote stops.
        assertTrue(after.indexOf("--watch") in 0 until after.indexOf("setprop ctl.stop zygote"))
        assertTrue(after.indexOf("--keys") in 0 until after.indexOf("setprop ctl.stop zygote"))
        // The return starts One UI's zygote only after its checks, and reboots when one fails.
        val ret = code(returnScript).joinToString("\n")
        assertTrue(ret.indexOf("Gate A") in 0 until ret.indexOf("setprop ctl.start zygote"))
        assertTrue(ret.contains("failsafe \"processes still in the session's namespace"))
        assertTrue(ret.contains("setprop sys.powerctl \"reboot,\$1\""))
        // A switch that ended before the stop is not a reason to restart One UI's framework or the phone:
        // the stop is marked, and without the mark the return only ends the helpers.
        assertTrue(after.indexOf("\"\$CTL/stopped\"") in 0 until after.indexOf("setprop ctl.stop zygote"))
        val unmarked = ret.indexOf("if [ ! -e \"\$CTL/stopped\" ]")
        assertTrue(unmarked in 0 until ret.indexOf("Gate A"))
        assertTrue(ret.indexOf("exit 0", unmarked) in unmarked until ret.indexOf("Gate A"))
        // A return with no open session does nothing.
        assertTrue(ret.indexOf("nothing to return from") in 0 until ret.indexOf("kill -TERM"))
    }


    // --- The way back to One UI, against a fake phone -------------------------------

    private fun keyEvents(f: Fake, device: String, vararg lines: String) = f.file("events/$device").writeText(lines.joinToString("") { "$it\n" })

    private fun reader(f: Fake, device: String, token: String = TOKEN) = f.start("oneios_switch.sh", "--keys", "/dev/input/$device", token, log = "log/keys-$device")

    /** Volume Up and Volume Down are two devices on the S24 Ultra (gpio-keys and the PMIC's resin key): one reader each. */
    @Test
    fun theKeyReadersAskForTheReturnAfterA3sHoldOfBothKeys() = each { f ->
        // A second of the scripts' clock is 100 ms here: the 3 s hold is 300 ms.
        f.phone(scale = 10, state = "returning")
        File(f.control, "keys/session").writeText("$TOKEN\n")
        keyEvents(f, "event0", "EV_KEY       KEY_VOLUMEUP         DOWN", "EV_SYN       SYN_REPORT           00000000")
        keyEvents(f, "event4", "@ 0.1", "EV_KEY       KEY_VOLUMEDOWN       DOWN", "EV_SYN       SYN_REPORT           00000000")
        val request = File(f.session, "return.request")
        reader(f, "event0")
        reader(f, "event4")
        await("the request of the key readers") { request.isFile && request.length() > 0 }
        assertTrue(request.readText(), request.readText().startsWith("keys: Volume Up + Volume Down held 3 s at "))
        // Each reader listed itself for the return, and neither started the return: the watcher had it (state returning).
        assertEquals(2, File(f.control, "keys/pids").readLines().size)
        Thread.sleep(1200)
        assertEquals("returning", f.state)
        assertFalse(f.returnLog, f.returnLog.contains("keys:"))
    }

    @Test
    fun aShortHoldOrOneKeyAsksForNothing() = each { f ->
        // The 3 s hold is 1.5 s here; both keys are down for 300 ms, then Volume Up alone stays down.
        f.phone(scale = 2, state = "returning")
        File(f.control, "keys/session").writeText("$TOKEN\n")
        keyEvents(f, "event0", "EV_KEY KEY_VOLUMEUP DOWN", "@ 0.3", "EV_KEY KEY_VOLUMEUP UP", "@ 0.3", "EV_KEY KEY_VOLUMEUP DOWN", "EV_KEY KEY_POWER DOWN")
        keyEvents(f, "event4", "EV_KEY KEY_VOLUMEDOWN DOWN", "@ 0.4", "EV_KEY KEY_VOLUMEDOWN UP")
        reader(f, "event0")
        reader(f, "event4")
        await("both readers have read their events") {
            File(f.control, "keys/up").takeIf { it.isFile }?.readText()?.trim() == "DOWN" && File(f.control, "keys/down").takeIf { it.isFile }?.readText()?.trim() == "UP"
        }
        Thread.sleep(2500)
        assertFalse(File(f.session, "return.request").exists())
    }

    /**
     * The S24 Ultra's volume keys are one rocker: pressing both ends chatters (session of 2026-11-12: 6 key events in 3 s,
     * no return). Releases under 0.5 s do not end the hold; the two keys go down at the same moment on two devices.
     */
    @Test
    fun aChatteringHoldOfTheRockerStillReturns() = each { f ->
        // A second of the scripts' clock is 200 ms here: a lift of 0.1 s of it at least every 2 s, on one key or the other,
        // through a 16 s hold, then both released. No 3 s without a release: the rule before 2026-11-12 never returned here.
        // (16 s, not 4: twelve samples of the stand-ins' clock take longer than 3 s of it; 8 s was enough on Linux, not
        // on macOS, where every sample's stand-ins start slower: OneiOS's macOS CI, 2026-11-15.)
        f.phone(scale = 5, state = "returning")
        File(f.control, "keys/session").writeText("$TOKEN\n")
        fun chatter(key: String, first: String, lifts: Int) = listOf("EV_KEY $key DOWN", first, "EV_KEY $key UP") +
            (1..lifts).flatMap { listOf("@ 0.02", "EV_KEY $key DOWN", "@ 0.38", "EV_KEY $key UP") }
        keyEvents(f, "event0", *chatter("KEY_VOLUMEUP", "@ 0.1", 8).toTypedArray())
        keyEvents(f, "event4", *chatter("KEY_VOLUMEDOWN", "@ 0.3", 7).toTypedArray())
        reader(f, "event0")
        reader(f, "event4")
        await("the request despite the chatter") { File(f.session, "return.request").let { it.isFile && it.length() > 0 } }
        assertTrue(File(f.session, "return.request").readText().startsWith("keys: Volume Up + Volume Down held 3 s at "))
    }

    /** A release of a second ends the hold, and the 2 s after it are not 3 s. */
    @Test
    fun aLongReleaseEndsTheHold() = each { f ->
        f.phone(scale = 5, state = "returning")
        File(f.control, "keys/session").writeText("$TOKEN\n")
        keyEvents(f, "event0", "EV_KEY KEY_VOLUMEUP DOWN", "@ 0.2", "EV_KEY KEY_VOLUMEUP UP", "@ 0.2", "EV_KEY KEY_VOLUMEUP DOWN",
            "@ 0.4", "EV_KEY KEY_VOLUMEUP UP")
        keyEvents(f, "event4", "EV_KEY KEY_VOLUMEDOWN DOWN")
        reader(f, "event0")
        reader(f, "event4")
        await("the last release") { File(f.control, "keys/up").takeIf { it.isFile }?.readText()?.trim() == "UP" && File(f.control, "keys/down").isFile }
        Thread.sleep(1500)
        assertFalse(File(f.session, "return.request").exists())
    }

    /** A key device with auto-repeat reports a held key again and again: that is not a release. Bare values count too. */
    @Test
    fun aHeldKeysAutoRepeatDoesNotBreakTheHold() = each { f ->
        f.phone(scale = 10, state = "returning")
        File(f.control, "keys/session").writeText("$TOKEN\n")
        val repeats = (1..12).flatMap { listOf("@ 0.05", "EV_KEY KEY_VOLUMEUP REPEAT", "EV_KEY KEY_VOLUMEDOWN 00000002") }
        keyEvents(f, "event0", *(listOf("EV_KEY KEY_VOLUMEUP DOWN", "EV_KEY KEY_VOLUMEDOWN 00000001") + repeats).toTypedArray())
        reader(f, "event0")
        await("the request despite the repeats") { File(f.session, "return.request").isFile }
    }

    /** A reader of an earlier session (another token) ends on its first event and asks for nothing. */
    @Test
    fun aLaterSessionsTokenEndsAnOldReader() = each { f ->
        f.phone(scale = 10)
        File(f.control, "keys/session").writeText("$TOKEN\n")
        keyEvents(f, "event0", "EV_KEY KEY_VOLUMEUP DOWN", "EV_KEY KEY_VOLUMEDOWN DOWN", "@ 0.2", "EV_KEY KEY_VOLUMEDOWN UP", "EV_KEY KEY_VOLUMEDOWN DOWN")
        val old = reader(f, "event0", token = "an-earlier-session")
        Thread.sleep(1500)
        assertFalse(File(f.control, "keys/up").exists() || File(f.control, "keys/down").exists() || File(f.control, "keys/both").exists())
        assertFalse(File(f.session, "return.request").exists())
        assertEquals("running", f.state)
        // Its loop is gone: only its (stand-in) getevent, blocked on a quiet device, keeps the pipeline open.
        f.file("events/stop").createNewFile()
        assertTrue(old.waitFor(10, TimeUnit.SECONDS))
        // On a phone the reader leads its own process group and ends all of it, getevent included.
        val sw = code(switchScript).joinToString("\n")
        assertTrue(sw.contains("[ \"\$(cat \"\$KS/session\" 2>/dev/null)\" = \"\$tok\" ] || reader_end"))
        assertTrue(sw.contains("[ \"\$OWN_GROUP\" = 1 ] && kill -9 -- \"-\$\$\""))
    }

    /** The keys' state, asked of the devices: what a grab (EVIOCGRAB) by the guest cannot take away. */
    @Test
    fun thePollSeesTheChordWithoutAnyEvent() = each { f ->
        f.phone(scale = 10, state = "returning")
        File(f.control, "keys/session").writeText("$TOKEN\n")
        fun keys(device: String, vararg down: String) = f.file("keystate/$device").writeText(
            "add device 1: /dev/input/$device\n  name:     \"keys\"\n  events:\n    KEY (0001): " +
                listOf("KEY_VOLUMEDOWN", "KEY_VOLUMEUP", "KEY_POWER").joinToString("") { "$it${if (it in down) "*" else " "}       " } + "\n",
        )
        // One key down, however long: nothing.
        keys("event0", "KEY_VOLUMEUP")
        keys("event4")
        f.start("oneios_switch.sh", "--keys-poll", TOKEN, "/dev/input/event0", "/dev/input/event4")
        Thread.sleep(1500)
        assertFalse(File(f.session, "return.request").exists())
        // Both down (each on its own device): seven samples, half a second apart, later; one sample without Volume
        // Down in between (the rocker's chatter) does not start the count again.
        keys("event4", "KEY_VOLUMEDOWN")
        Thread.sleep(150)
        keys("event4")
        Thread.sleep(30)
        keys("event4", "KEY_VOLUMEDOWN")
        await("the request of the poll") { File(f.session, "return.request").let { it.isFile && it.length() > 0 } }
        assertTrue(File(f.session, "return.request").readText().startsWith("keys: Volume Up + Volume Down down for 3 s (polled) at "))
        // No events file was ever read: the poll does not depend on the event stream.
        assertFalse(f.file("events/event0").exists())
    }

    /** No watcher (killed, or stuck): five seconds after their request the key readers start the return themselves. */
    @Test
    fun withoutAWatcherTheKeysStartTheReturnThemselves() = each { f ->
        f.phone(scale = 20)
        File(f.control, "keys/session").writeText("$TOKEN\n")
        keyEvents(f, "event0", "EV_KEY KEY_VOLUMEUP DOWN", "EV_KEY KEY_VOLUMEDOWN DOWN")
        reader(f, "event0")
        await("One UI back from the key reader alone", 60_000) { f.state == "returned" }
        assertTrue(f.returnLog, f.returnLog.contains("keys: the watcher did not start the return within 5 s"))
        assertTrue(f.returnLog, f.returnLog.contains("=== Return to One UI (keys-direct)"))
        // In a session of its own: the return ends the readers' process groups, and it came from one.
        assertTrue(f.lines("log/busybox").any { it.startsWith("setsid ") && it.endsWith("oneios_return.sh keys-direct") })
        f.assertInPlace()
    }

    /** The shmem THP mode the switch wrote (advise, for the 2 MiB host pages) comes back at the return. The node
     *  carries every mode with the active one in brackets ("always within_size [advise] deny force"): the base keeps
     *  the bare mode, and the return compares and restores the bare mode (2026-11-16: the whole line written back was
     *  EINVAL and that rebooted the phone out of Gate A). */
    @Test
    fun shmemEnabledComesBackAtTheReturn() = each { f ->
        f.phone()
        File(f.root, "sys/kernel/mm/transparent_hugepage").mkdirs()
        File(f.root, "sys/kernel/mm/transparent_hugepage/shmem_enabled").writeText("always within_size [advise] deny force\n")
        File(f.control, "base/shmem_enabled").writeText("never\n")
        f.returns()
        f.assertInPlace()
        assertEquals("never\n", f.file("sys/kernel/mm/transparent_hugepage/shmem_enabled").readText())
        assertFalse(File(f.control, "base/shmem_enabled").exists())
    }

    /** The node is already at the mode the switch found (bracketed, in the annotated line): nothing is written. */
    @Test
    fun shmemAlreadyBackIsNotWrittenAgain() = each { f ->
        f.phone()
        File(f.root, "sys/kernel/mm/transparent_hugepage").mkdirs()
        val line = "always within_size advise [never] deny force\n"
        File(f.root, "sys/kernel/mm/transparent_hugepage/shmem_enabled").writeText(line)
        File(f.control, "base/shmem_enabled").writeText("never\n")
        f.returns()
        f.assertInPlace()
        assertEquals(line, f.file("sys/kernel/mm/transparent_hugepage/shmem_enabled").readText())
        assertFalse(File(f.control, "base/shmem_enabled").exists())
    }

    /** A switch that wrote advise and ended before its stop mark (YMGPwcca/OneOS 403d8b4): One UI never stopped, and
     *  the early return writes the mode back too (it used to leave advise until the next boot). */
    @Test
    fun shmemComesBackAtAnEarlyReturn() = each { f ->
        f.phone(stopped = false, state = "starting")
        File(f.root, "sys/kernel/mm/transparent_hugepage").mkdirs()
        File(f.root, "sys/kernel/mm/transparent_hugepage/shmem_enabled").writeText("always within_size [advise] deny force\n")
        File(f.control, "base/shmem_enabled").writeText("never\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("shmem_enabled back: never"))
        assertTrue(r.text, r.text.contains("The switch ended before One UI's framework was stopped: nothing to restore."))
        assertEquals("never\n", f.file("sys/kernel/mm/transparent_hugepage/shmem_enabled").readText())
        assertFalse(File(f.control, "base/shmem_enabled").exists())
        assertEquals(emptyList<String>(), f.setprops)
        assertEquals(null, f.rebooted)
    }

    /** The switch's side: the mode is saved and advise written only under the stop lock, after the last look for a
     *  return and before the stop mark; the baseline (before the way back is armed) writes nothing to the node. */
    @Test
    fun theSwitchWritesShmemOnlyUnderTheStopLock() {
        val sw = code(switchScript).joinToString("\n")
        val arm = sw.indexOf("=== [2/5]")
        val lock = sw.indexOf("until mkdir \"\$CTL/stop.lock\"", arm)
        val inside = sw.indexOf("return_asked && end_for_return \"One UI's framework was stopped\"", lock)
        val save = sw.indexOf("mv -f \"\$B/shmem_enabled.tmp\" \"\$B/shmem_enabled\"", inside)
        val write = sw.indexOf("echo advise 2>/dev/null > \"\$SHMEM_EN\"", save)
        val mark = sw.indexOf("echo \"\$(date +%s)\" > \"\$CTL/stopped\"", write)
        val order = listOf(arm, lock, inside, save, write, mark)
        assertTrue(order.toString(), order.all { it >= 0 } && order == order.sorted())
        assertFalse(sw.substring(0, lock).contains("> \"\$SHMEM_EN\""))
    }

    /** The switch never wrote (no value in the base): the return touches nothing. */
    @Test
    fun shmemLeftAloneWhenTheSwitchNeverWrote() = each { f ->
        f.phone()
        File(f.root, "sys/kernel/mm/transparent_hugepage").mkdirs()
        File(f.root, "sys/kernel/mm/transparent_hugepage/shmem_enabled").writeText("always within_size advise [never] deny force\n")
        f.returns()
        f.assertInPlace()
        assertEquals("always within_size advise [never] deny force\n", f.file("sys/kernel/mm/transparent_hugepage/shmem_enabled").readText())
    }

    private fun watcher(f: Fake, max: Int = 600): Process {
        // The watcher's output is the return log, as on the phone. oneios_return.sh then writes each line once, told
        // by /proc/$$/fd/1; a machine without /proc (a Mac) has the test say it (ONEIOS_TEST_OUT_IS_LOG, read only with
        // a test root). On Linux the script's own check is what is tested.
        val env = mapOf("ONEIOS_RETURN_MAX" to "$max") + (if (File("/proc/self/fd/1").exists()) emptyMap() else mapOf("ONEIOS_TEST_OUT_IS_LOG" to "1"))
        val p = f.start("oneios_switch.sh", "--watch", env = env, log = "data/local/tmp/oneios/return.log")
        await("the watcher's pid") { File(f.control, "watcher.pid").let { it.isFile && it.readText().trim().toIntOrNull() != null } }
        return p
    }

    @Test
    fun theWatcherReturnsWhenXnuhostEnds() = each { f ->
        f.phone()
        val w = watcher(f)
        Thread.sleep(300)
        assertEquals("running", f.state)
        assertEquals(emptyList<String>(), f.setprops)
        f.ends(XNUHOST)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertEquals(f.returnLog, 0, w.exitValue())
        assertTrue(f.returnLog, f.returnLog.contains("watcher: xnuhost $XNUHOST ended: how is not recorded (last log lines: guest: launchd|); returning to One UI"))
        assertTrue(f.returnLog, f.returnLog.contains("=== Return to One UI (watcher)"))
        // xnuhost was gone already: nothing was signalled.
        assertFalse(f.kills.toString(), f.kills.any { it.contains("$XNUHOST") })
        f.assertInPlace()
    }

    @Test
    fun theWatcherReturnsOnARequest() = each { f ->
        f.phone()
        File(f.session, "ready").createNewFile()
        val w = watcher(f)
        File(f.session, "return.request").writeText("the guest asked to return\n")
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertTrue(f.returnLog, f.returnLog.contains("watcher: return asked (the guest asked to return); returning to One UI"))
        // A running xnuhost gets SIGTERM and ends: nothing is killed.
        assertEquals(listOf("-TERM $XNUHOST"), f.kills)
        f.assertInPlace()
    }

    /**
     * What the way back reads is not in the folder xnuhost writes: a guest that empties its session folder, or leaves
     * a state of its own there, and ends, is still returned from.
     */
    @Test
    fun aGuestThatWipesItsSessionFolderIsStillReturnedFrom() = each { f ->
        f.phone()
        val w = watcher(f)
        f.session.listFiles()!!.forEach { it.deleteRecursively() }
        File(f.session, "state").writeText("returned\n")
        File(f.session, "xnuhost.pid").writeText("1\n")
        f.ends(XNUHOST)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertTrue(f.returnLog, f.returnLog.contains("watcher: xnuhost $XNUHOST ended"))
        f.assertInPlace()
        // In xnuhost's namespace that folder, and the scripts, are read-only.
        val inner = code(switchScript).joinToString("\n").let { it.substring(it.indexOf("    --inner)"), it.indexOf("    --stop-loop)")) }
        assertTrue(inner.contains("for d in runtime image control bin oneios_switch.sh oneios_return.sh; do"))
        assertTrue(inner.contains("the way back's control folder is writable in the session's namespace"))
    }

    /** iOS never came up: no `ready` within the deadline is a return; with `ready` the session goes on. */
    @Test
    fun theWatcherReturnsWhenTheGuestNeverReportsReady() = each { f ->
        f.phone()
        val w = watcher(f, max = 30)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertTrue(f.returnLog, f.returnLog.contains("watcher: the guest did not report ready within 30s; returning to One UI"))
        f.assertInPlace()
    }

    @Test
    fun aReadyGuestIsLeftRunningPastTheDeadline() = each { f ->
        f.phone()
        File(f.session, "ready").createNewFile()
        val w = watcher(f, max = 5)
        // Twenty of the scripts' seconds and more.
        Thread.sleep(1500)
        assertTrue(w.isAlive)
        // It keeps the session's wakelock up meanwhile: nothing else holds the phone awake. (Looked at until it is
        // there: the watcher writes the node again each second with `echo > `, and a read between the truncation and
        // the write saw an empty file once, OneiOS run 43720242712 on Linux.)
        await("the session's wakelock", 5_000) { f.lines("sys/power/wake_lock").firstOrNull() == "oneios_session" }
        assertEquals("running", f.state)
        assertEquals(emptyList<String>(), f.setprops)
        assertTrue(f.file("proc/$XNUHOST").isDirectory)
        File(f.session, "return.request").writeText("adb\n")
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        f.assertInPlace()
    }

    /** The switch never got as far as starting xnuhost: the watcher ends the session; One UI was never stopped. */
    @Test
    fun theWatcherEndsASwitchThatNeverStartedXnuhost() = each { f ->
        f.phone(stopped = false, state = "starting")
        val w = watcher(f)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertTrue(f.returnLog, f.returnLog.contains("watcher: the switch did not start xnuhost within 60 s; returning to One UI"))
        assertTrue(f.returnLog, f.returnLog.contains("The switch ended before One UI's framework was stopped: nothing to restore."))
        assertEquals("returned", f.state)
        assertEquals(emptyList<String>(), f.setprops)
    }

    // --- A return asked while the switch runs (2026-11-12 11:04: a return in step 3 found no "stopped" mark yet and
    // tidied up; the switch then stopped the framework, xnuhost did not start, and nothing returned) ---------------

    /** A return before the stop: nothing to restore, and the stop lock stays the return's, so the switch stops nothing. */
    @Test
    fun aReturnBeforeTheStopKeepsTheStopLock() = each { f ->
        f.phone(stopped = false, state = "starting")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("The switch ended before One UI's framework was stopped: nothing to restore."))
        assertTrue(File(f.control, "stop.lock/return").isFile)
        assertEquals(emptyList<String>(), f.setprops)
    }

    /** A return during the stop waits for the switch to finish it (the lock), then restores One UI in place. */
    @Test
    fun aReturnDuringTheStopWaitsForItThenRestoresOneUi() = each { f ->
        // A second of the scripts' clock is 100 ms here: the return waits for the lock 15 s = 1.5 s at most.
        f.phone(scale = 10, stopped = false, state = "starting")
        assertTrue(File(f.control, "stop.lock").mkdir())      // the switch, in the middle of its stop
        val r = f.start("oneios_return.sh", "manual", log = "log/return")
        Thread.sleep(400)
        assertTrue(r.isAlive)
        // The switch finishes: the mark, the framework down, the lock given back.
        File(f.control, "stopped").writeText("1\n")
        f.file("props").appendText("init.svc.zygote=stopped\n")
        assertTrue(File(f.control, "stop.lock").delete())
        assertTrue(r.waitFor(120, TimeUnit.SECONDS))
        assertFalse(f.returnLog, f.returnLog.contains("nothing to restore"))
        f.assertInPlace()
    }

    /** A session left "returned" with One UI's framework down (what the switch before the lock could do) is returned again. */
    @Test
    fun aReturnedStateWithTheFrameworkDownIsReturnedAgain() = each { f ->
        f.phone(state = "returned")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(f.returnLog, f.returnLog.contains("state 'returned', but One UI's framework is down since the switch's stop: returning again"))
        f.assertInPlace()
    }

    /** The switch's side, in its text: each step looks for a return, the stop is inside the lock, a failed start returns. */
    @Test
    fun theSwitchLetsAReturnWinAtEachStep() {
        val sw = code(switchScript).joinToString("\n")
        val arm = sw.indexOf("=== [2/5]")
        val before = sw.indexOf("return_asked && end_for_return \"One UI's framework was stopped\"", arm)
        val lock = sw.indexOf("until mkdir \"\$CTL/stop.lock\"", before)
        val inside = sw.indexOf("return_asked && end_for_return \"One UI's framework was stopped\"", lock)
        val mark = sw.indexOf("echo \"\$(date +%s)\" > \"\$CTL/stopped\"", inside)
        val stop = sw.indexOf("setprop ctl.stop zygote", mark)
        val unlock = sw.indexOf("rmdir \"\$CTL/stop.lock\"", stop)
        val step4 = sw.indexOf("return_asked && end_for_return \"xnuhost was started\"", unlock)
        val start = sw.indexOf("=== [4/5]", step4)
        val failed = sw.indexOf("xnuhost did not start after", start)
        val back = sw.indexOf("\$SH \"\$STAGE/oneios_return.sh\" switch-failed", failed)
        val order = listOf(arm, before, lock, inside, mark, stop, unlock, step4, start, failed, back)
        assertTrue(order.toString(), order.all { it >= 0 } && order == order.sorted())
        // The return keeps the lock and decides only after it has it.
        val rt = code(returnScript).joinToString("\n")
        val taken = rt.indexOf("until mkdir \"\$CTL/stop.lock\"")
        assertTrue(taken in 0 until rt.indexOf("if [ ! -e \"\$CTL/stopped\" ] && ! framework_down; then"))
        assertFalse(rt.contains("rmdir \"\$CTL/stop.lock\"") || rt.contains("rm -rf \"\$CTL/stop.lock\""))
    }

    /**
     * The watchdog nodes of system_server come from one `ls -l` per process, not one readlink per fd: with about 1500
     * fds the readlink loop took 48 s on the phone (2026-11-23 18:19) and the watcher's 60 s ran out before xnuhost.
     * The script's own filter, run on an `ls -l` listing, keeps the watchdog and softdog nodes and nothing else.
     */
    @Test
    fun theSoftdogScanIsOneListingPerProcess() {
        val sw = code(switchScript).joinToString("\n")
        val scan = sw.substring(sw.indexOf("for p in \$(pidof system_server); do"), sw.indexOf("> \"\$CTL/softdog_nodes\""))
        assertTrue(scan, scan.contains("ls -l \"/proc/\$p/fd/\""))
        assertFalse(scan, scan.contains("readlink"))
        val filter = scan.substringAfter("done 2>/dev/null | ").trim()
        val listing = """
            lrwx------ 1 system system 64 2026-11-23 18:20 0 -> /dev/null
            l-wx------ 1 system system 64 2026-11-23 18:20 412 -> /dev/watchdog
            lr-x------ 1 system system 64 2026-11-23 18:20 413 -> socket:[123456]
            l-wx------ 1 system system 64 2026-11-23 18:20 414 -> /dev/softdog0
            l-wx------ 1 system system 64 2026-11-23 18:20 415 -> /dev/watchdog
            lr-x------ 1 system system 64 2026-11-23 18:20 416 -> /system/framework/framework.jar
        """.trimIndent() + "\n"
        val p = ProcessBuilder("sh", "-c", filter).redirectErrorStream(true).start()
        p.outputStream.use { it.write(listing.toByteArray()) }
        val out = p.inputStream.bufferedReader().readText()
        assertEquals(0, p.waitFor())
        assertEquals("/dev/softdog0\n/dev/watchdog\n", out)
    }

    /**
     * xnuhost's `versions:` line (OneiOS docs/booter.md 2.9b) names the app: root's switch verb sets
     * ONEIOS_APP_VERSION_CODE to its versionCode after it clears every ONEIOS_ variable and before it starts the switch,
     * and the switch's inner shell exports it to xnuhost only when it is a number.
     */
    @Test
    fun theAppsVersionCodeReachesXnuhost() {
        val root = code(rootScript).joinToString("\n")
        val sw = root.substring(root.indexOf("do_switch() {"), root.indexOf("do_return() {"))
        val set = sw.indexOf("ONEIOS_APP_VERSION_CODE=\$1; export ONEIOS_APP_VERSION_CODE")
        assertTrue(sw, set > sw.indexOf("do unset \"\$v\"; done") && sw.indexOf("is_dec \"\$1\"") in 0 until set)
        assertTrue(sw, set < sw.indexOf("setsid /system/bin/sh \"\$STAGE/oneios_switch.sh\""))
        val inner = code(switchScript).joinToString("\n").let { it.substring(it.indexOf("    --inner)"), it.indexOf("    --stop-loop)")) }
        val keep = inner.lines().single { it.contains("case \"\${ONEIOS_APP_VERSION_CODE:-}\" in") }.trim()
        assertTrue(inner.indexOf(keep) in 0 until inner.indexOf(LAUNCH))
        for ((given, seen) in listOf("208" to "208", "" to "-", "20 8" to "-", "2a" to "-", "-1" to "-")) {
            val p = ProcessBuilder("sh", "-c", "$keep\nsh -c 'echo \"\${ONEIOS_APP_VERSION_CODE--}\"'").redirectErrorStream(true)
            p.environment()["ONEIOS_APP_VERSION_CODE"] = given
            val run = p.start()
            val out = run.inputStream.bufferedReader().readText()
            assertEquals(0, run.waitFor())
            assertEquals("'$given'", "$seen\n", out)
        }
    }

    /** A return script that cannot run must still end in One UI: the watcher reboots. */
    @Test
    fun theWatcherRebootsWhenTheReturnScriptCannotRun() = each { f ->
        f.phone()
        assertTrue(File(f.stage, "oneios_return.sh").delete())
        val w = watcher(f)
        f.ends(XNUHOST)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertEquals("reboot,oneios-watcher-failsafe", f.rebooted)
        assertTrue(f.outcome, f.outcome.startsWith("failsafe ") && f.outcome.contains("oneios_return.sh ended with"))
        assertTrue(f.lines("log/busybox").contains("reboot -f"))
    }

    @Test
    fun theReturnRestoresTheDisplayAndStartsOneUiInPlace() = each { f ->
        f.phone()
        // One UI's own daemons change persist properties in a session too: named in the log, never written back.
        f.file("props").appendText("persist.sys.locale=xx-secret\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertEquals(listOf("-TERM $XNUHOST"), f.kills)
        assertFalse(r.text, r.text.contains("xx-secret") || f.lines("log/resetprop").any { it.contains("persist.") })
        // Every line once, in the log as on the caller's output.
        assertEquals(f.returnLog, 1, f.returnLog.lines().count { it.contains("One UI restored in place") })
        for (line in listOf(
            "SIGTERM to xnuhost $XNUHOST", "Gate A: no session process, the stage mounted nowhere",
            "persist properties that differ from the switch: persist.sys.locale ",
            "display: composer $COMPOSER restarted (was 311), surfaceflinger 9001 (was 310; 310 at the switch), boot animation started",
            "audioserver, cameraserver, media and wificond restarted", "Gate B: display, audio and One UI's services up", "user 0 unlocked after ",
        )) assertTrue("'$line' is not in:\n${r.text}", r.text.contains(line))
        // The boot counters went back in memory, and nothing else was written to a property.
        assertTrue(f.lines("log/resetprop").contains("-n sys.rescue_boot_count 0"))
        assertFalse(f.setprops.any { it.startsWith("persist.") })
        // The session's cgroup is gone with it.
        assertFalse(f.file("sys/fs/cgroup/oneios_session/cgroup.procs").readText().isNotBlank())
        // A second return finds nothing to do.
        val again = f.returns()
        assertEquals(0, again.exit)
        assertTrue(again.text, again.text.contains("nothing to return from"))
    }

    /** A wedged xnuhost ignores SIGTERM: everything of the session is killed, and the display still comes back. */
    @Test
    fun aKilledSessionStillGetsItsDisplayBack() = each { f ->
        f.phone()
        File(f.file("proc/$XNUHOST"), "ignore_term").createNewFile()
        f.guest(5001, "xnuhost-tasks")
        // A task that left xnuhost's mount namespace for one of its own: still in its cgroup, and the stage is still its /data.
        f.guest(5002, "SpringBoard", ns = "mnt:[78]")
        // And one that left the cgroup too: found by its mount table.
        f.guest(5003, "backboardd", ns = "mnt:[79]", cgroup = false)
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("SIGKILL to what is left of the session: 5000 5001 5002 5003 "))
        assertEquals(listOf("-TERM 5000", "-9 5000", "-9 5001", "-9 5002", "-9 5003"), f.kills)
        assertEquals("1", f.lines("sys/fs/cgroup/oneios_session/cgroup.kill").firstOrNull())
        f.assertInPlace(r.text)
    }

    /**
     * One UI's clock caps (SSRM's, left by system_server): saved while One UI is whole, the hardware's range for the
     * session once system_server is gone, One UI's values back at the return before its zygote, a killed xnuhost's too.
     */
    @Test
    fun oneUisClockCapsAreLiftedForTheSessionAndPutBackAtTheReturn() = each { f ->
        f.phone()
        fun node(path: String, value: String) = f.file(path).also { it.parentFile.mkdirs(); it.writeText("$value\n") }
        fun value(path: String) = f.file(path).readText().trim()
        val cpu = "sys/devices/system/cpu/cpufreq"
        // policy, cpuinfo min, cpuinfo max, One UI's floor (a boost), One UI's cap
        for (p in listOf(listOf("0", "556800", "2265600", "2265600", "1689600"), listOf("7", "672000", "3398400", "672000", "2035200"))) {
            node("$cpu/policy${p[0]}/cpuinfo_min_freq", p[1]); node("$cpu/policy${p[0]}/cpuinfo_max_freq", p[2])
            node("$cpu/policy${p[0]}/scaling_min_freq", p[3]); node("$cpu/policy${p[0]}/scaling_max_freq", p[4])
        }
        // Samsung's cpufreq_limit: SSRM's one cap for every cluster, its own QoS request above scaling_max_freq; -1 is none.
        val lim = "sys/devices/system/cpu/cpufreq_limit"
        node("$lim/cpufreq_max_limit", "2035200")
        node("$lim/cpufreq_min_limit", "-1")
        node("$lim/limit_stat", "user max 2035200")
        node("sys/kernel/gpu/gpu_max_clock", "500")
        node("sys/kernel/gpu/gpu_freq_table", "1000 950 903 500 231 80")
        node("sys/class/kgsl/kgsl-3d0/max_gpuclk", "500000000")
        node("sys/class/kgsl/kgsl-3d0/gpu_available_frequencies", "1000000000 500000000 231000000")
        node("sys/class/kgsl/kgsl-3d0/thermal_pwrlevel", "9")
        // a thermal zone and its trip: never the scripts' to write
        val trip = node("sys/class/thermal/thermal_zone0/trip_point_0_temp", "95000")

        val save = f.run("oneios_switch.sh", "--clocks-save")
        assertEquals(save.text, 0, save.exit)
        assertEquals(
            listOf(
                "/$lim/cpufreq_max_limit 2035200 -1", "/$lim/cpufreq_min_limit -1 -1",
                "/$cpu/policy0/scaling_min_freq 2265600 556800", "/$cpu/policy0/scaling_max_freq 1689600 2265600",
                "/$cpu/policy7/scaling_min_freq 672000 672000", "/$cpu/policy7/scaling_max_freq 2035200 3398400",
                "/sys/kernel/gpu/gpu_max_clock 500 1000", "/sys/class/kgsl/kgsl-3d0/max_gpuclk 500000000 1000000000",
            ),
            File(f.control, "base/clocks").readLines(),
        )
        assertTrue(save.text, save.text.contains("Clocks of One UI: /$lim/cpufreq_max_limit 2035200, ") && save.text.contains("/$cpu/policy0/scaling_min_freq 2265600, ") && save.text.contains("KGSL thermal_pwrlevel 9"))
        val tops = f.run("oneios_switch.sh", "--clocks-tops")
        assertEquals(tops.text, 0, tops.exit)
        assertEquals("556800", value("$cpu/policy0/scaling_min_freq"))
        assertEquals("3398400", value("$cpu/policy7/scaling_max_freq"))
        assertEquals("1000", value("sys/kernel/gpu/gpu_max_clock"))
        assertEquals("1000000000", value("sys/class/kgsl/kgsl-3d0/max_gpuclk"))
        assertEquals("-1", value("$lim/cpufreq_max_limit"))
        assertTrue(tops.text, tops.text.contains("clocks: /sys/kernel/gpu/gpu_max_clock 500 -> 1000 (reads 1000)"))
        assertTrue(tops.text, tops.text.contains("clocks: /$lim/cpufreq_max_limit 2035200 -> -1 (reads -1)"))
        assertTrue(tops.text, tops.text.contains("clocks: cpufreq_limit limit_stat: user max 2035200"))
        // The release comes before the policies' own writes.
        assertTrue(tops.text, tops.text.indexOf("cpufreq_max_limit") in 0 until tops.text.indexOf("scaling_min_freq"))
        assertTrue(File(f.control, "clocks.set").isFile)

        // In the session a vendor HAL writes the GPU cap again; then xnuhost ignores SIGTERM and is killed.
        node("sys/kernel/gpu/gpu_max_clock", "422")
        File(f.file("proc/$XNUHOST"), "ignore_term").createNewFile()
        // A line that is not one of the nodes, or not a number, is never written.
        File(f.control, "base/clocks").appendText("/sys/class/thermal/thermal_zone0/trip_point_0_temp 1 2\n/$cpu/policy0/../policy7/scaling_max_freq 5 6\n/sys/kernel/gpu/gpu_max_clock x 1\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertEquals("2265600", value("$cpu/policy0/scaling_min_freq"))
        assertEquals("1689600", value("$cpu/policy0/scaling_max_freq"))
        assertEquals("672000", value("$cpu/policy7/scaling_min_freq"))
        assertEquals("2035200", value("$cpu/policy7/scaling_max_freq"))
        assertEquals("500", value("sys/kernel/gpu/gpu_max_clock"))
        assertEquals("500000000", value("sys/class/kgsl/kgsl-3d0/max_gpuclk"))
        assertEquals("2035200", value("$lim/cpufreq_max_limit"))
        assertEquals("-1", value("$lim/cpufreq_min_limit"))
        // SSRM's cap goes back last, after the policies.
        assertTrue(r.text, r.text.indexOf("clocks: /$lim/cpufreq_max_limit -1 -> 2035200 (One UI's)") > r.text.indexOf("policy0/scaling_min_freq"))
        assertEquals("95000", trip.readText().trim())
        assertTrue(r.text, r.text.contains("clocks: /sys/kernel/gpu/gpu_max_clock 422 -> 500 (One UI's)"))
        assertTrue(r.text, r.text.contains("clocks: /$cpu/policy7/scaling_max_freq 3398400 -> 2035200 (One UI's)"))
        // Before One UI's zygote and the first gate.
        assertTrue(r.text, r.text.indexOf("clocks: ") in 0 until r.text.indexOf("Gate A"))
        assertFalse(File(f.control, "clocks.set").exists())
    }

    /** Without the switch's mark (it never wrote the session's clocks) the return writes no clock node. */
    @Test
    fun aReturnWithoutTheClockMarkWritesNoClock() = each { f ->
        f.phone()
        val cap = f.file("sys/kernel/gpu/gpu_max_clock").also { it.parentFile.mkdirs(); it.writeText("700\n") }
        File(f.control, "base/clocks").writeText("/sys/kernel/gpu/gpu_max_clock 500 1000\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertEquals("700", cap.readText().trim())
        assertFalse(r.text, r.text.contains("clocks: "))
    }

    // --- The Android takeover (session-mode=takeover; docs/oneios.md, "Android takeover") ---------------------------

    private val cpuNodes = "sys/devices/system/cpu/cpufreq"

    /**
     * A fake phone in a session whose clocks the switch saved and lifted (as [oneUisClockCapsAreLiftedForTheSessionAndPutBackAtTheReturn]):
     * policy0 (556800..2265600, One UI's cap 1689600) and policy7 (672000..3398400, One UI's cap 2035200); the case
     * (lrp) and the cell readable; with [takeover] the switch's mark of the Android takeover.
     */
    private fun capPhone(f: Fake, takeover: Boolean = true) {
        f.phone()
        fun node(path: String, value: String) = f.file(path).also { it.parentFile.mkdirs(); it.writeText("$value\n") }
        for (p in listOf(listOf("0", "556800", "2265600", "556800", "1689600"), listOf("7", "672000", "3398400", "672000", "2035200"))) {
            node("$cpuNodes/policy${p[0]}/cpuinfo_min_freq", p[1]); node("$cpuNodes/policy${p[0]}/cpuinfo_max_freq", p[2])
            node("$cpuNodes/policy${p[0]}/scaling_min_freq", p[3]); node("$cpuNodes/policy${p[0]}/scaling_max_freq", p[4])
        }
        temps(f, 380, 330)
        assertEquals(0, f.run("oneios_switch.sh", "--clocks-save").exit)
        assertEquals(0, f.run("oneios_switch.sh", "--clocks-tops").exit)
        assertEquals("3398400", maxOf(f, 7))
        if (takeover) File(f.control, "base/mode").writeText("takeover\n")
    }

    /** The case (lrp) and the cell, in tenths of a degree C, as Samsung's power_supply nodes give them. */
    private fun temps(f: Fake, case: Int, cell: Int) {
        val bat = f.file("sys/class/power_supply/battery").apply { mkdirs() }
        // Whole or not at all: the cap reads them while the test writes.
        for ((name, v) in listOf("lrp" to case, "temp" to cell)) {
            val tmp = File(bat, ".$name"); tmp.writeText("$v\n"); assertTrue(tmp.renameTo(File(bat, name)))
        }
    }

    private fun maxOf(f: Fake, policy: Int) = f.file("$cpuNodes/policy$policy/scaling_max_freq").readText().trim()
    private fun capLevel(f: Fake) = File(f.control, "cpu-cap.level").takeIf { it.isFile }?.readText()?.trim()
    private fun capLog(f: Fake) = File(f.control, "cpu-cap.log").takeIf { it.isFile }?.readText().orEmpty()

    private fun startCap(f: Fake): Process {
        val p = f.start("oneios_switch.sh", "--cpu-cap", log = "data/local/tmp/oneios/control/cpu-cap.log")
        await("the cap's level") { capLevel(f) != null }
        return p
    }

    private fun awaitLevel(f: Fake, level: Int) = await("cpu-cap level $level\n${capLog(f)}") { capLevel(f) == "$level" && capLog(f).contains("cpu-cap: level $level ") }

    /** Hosted (no mark): the cap does nothing at all, and the return is the one of every session. */
    @Test
    fun theCpuCapDoesNothingInAHostedSession() = each { f ->
        capPhone(f, takeover = false)
        temps(f, 520, 490)
        val r = f.run("oneios_switch.sh", "--cpu-cap")
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("cpu-cap: not an Android takeover session: nothing to do"))
        assertFalse(File(f.control, "cpu-cap.pid").exists() || File(f.control, "cpu-cap.level").exists())
        assertFalse(File(f.session, "return.request").exists())
        assertEquals("3398400", maxOf(f, 7))
        val back = f.returns()
        f.assertInPlace(back.text)
        assertFalse(back.text, back.text.contains("Android takeover"))
        assertEquals("2035200", maxOf(f, 7))
    }

    /**
     * On: the cap leaves the hardware's top while the phone is cool, lowers each policy's scaling_max_freq as the case
     * warms (80 %, then 60 % of its top, never under cpuinfo_min_freq), asks for the return at the case's limit, and the
     * return in place ends it first and writes One UI's values back.
     */
    @Test
    fun theCpuCapFollowsTheCaseAndTheReturnPutsOneUisClocksBack() = each { f ->
        capPhone(f)
        val cap = startCap(f)
        Thread.sleep(200)
        assertEquals("0", capLevel(f))
        assertEquals("3398400", maxOf(f, 7))
        temps(f, 465, 330)
        awaitLevel(f, 1)
        assertEquals("${3398400 / 100 * 80}", maxOf(f, 7))
        assertEquals("${2265600 / 100 * 80}", maxOf(f, 0))
        assertTrue(capLog(f), capLog(f).contains("cpu-cap: level 1 (80 % of each policy's top): case 46.5 C (lrp), cell 33.0 C: policy0=${2265600 / 100 * 80} policy7=${3398400 / 100 * 80}"))
        temps(f, 470, 472)                     // the cell alone takes it further
        awaitLevel(f, 2)
        assertEquals("${3398400 / 100 * 60}", maxOf(f, 7))
        assertFalse(File(f.session, "return.request").exists())
        temps(f, 503, 400)
        awaitLevel(f, 3)
        await("the return request") { File(f.session, "return.request").isFile }
        assertTrue(File(f.session, "return.request").readText().startsWith("thermal: the Android takeover's limit: case 50.3 C (lrp, limit 50.0 C), cell 40.0 C (limit 48.0 C)"))
        assertEquals("${3398400 / 100 * 60}", maxOf(f, 7))
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertTrue(cap.waitFor(30, TimeUnit.SECONDS))
        assertEquals("1689600", maxOf(f, 0))
        assertEquals("2035200", maxOf(f, 7))
        assertTrue(r.text, r.text.contains("Android takeover: its CPU cap ended at level 3"))
        // Ended before One UI's clocks went back.
        assertTrue(r.text, r.text.indexOf("Android takeover: its CPU cap ended") in 0 until r.text.indexOf("clocks: "))
        assertTrue(capLog(f), capLog(f).contains("the cap ends at level 3"))
    }

    /** Down one step at a time: only when both readings are 2 C under the level for 3 readings in a row. */
    @Test
    fun theCpuCapComesBackToTheTopWhenThePhoneCools() = each { f ->
        capPhone(f)
        val cap = startCap(f)
        temps(f, 482, 330)
        awaitLevel(f, 2)
        temps(f, 465, 330)                     // under level 2's 48 C, but not 2 C under: it stays
        Thread.sleep(300)
        assertEquals("2", capLevel(f))
        temps(f, 455, 330)
        awaitLevel(f, 1)
        assertEquals("${3398400 / 100 * 80}", maxOf(f, 7))
        temps(f, 430, 330)
        awaitLevel(f, 0)
        assertEquals("3398400", maxOf(f, 7))
        assertEquals("2265600", maxOf(f, 0))
        // A reading that is not a number keeps the level.
        f.file("sys/class/power_supply/battery/lrp").writeText("busy\n")
        await("the cap's line on the reading") { capLog(f).contains("a reading is not a number (case 'busy', cell '330'): the level stays 0") }
        File(f.control, "cpu-cap.off").createNewFile()
        assertTrue(cap.waitFor(30, TimeUnit.SECONDS))
        assertTrue(capLog(f), capLog(f).contains("control/cpu-cap.off: the cap ends at level 0"))
    }

    /** xnuhost crashed with the cap in force: the watcher's return ends the cap and writes One UI's clocks back. */
    @Test
    fun theCpuCapIsPutBackAfterXnuhostCrashes() = each { f ->
        capPhone(f)
        val cap = startCap(f)
        temps(f, 490, 330)
        awaitLevel(f, 2)
        val w = watcher(f)
        f.ends(XNUHOST)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        f.assertInPlace()
        assertTrue(cap.waitFor(30, TimeUnit.SECONDS))
        assertEquals("1689600", maxOf(f, 0))
        assertEquals("2035200", maxOf(f, 7))
        assertTrue(f.returnLog, f.returnLog.contains("watcher: xnuhost $XNUHOST ended") && f.returnLog.contains("Android takeover: its CPU cap ended at level 2"))
    }

    /** A switch that failed after the stop (xnuhost never ran) with the cap in force: the same restore. */
    @Test
    fun theCpuCapIsPutBackAfterAnEarlyStop() = each { f ->
        capPhone(f)
        val cap = startCap(f)
        temps(f, 490, 330)
        awaitLevel(f, 2)
        f.ends(XNUHOST)
        File(f.control, "state").writeText("failed\n")
        assertTrue(cap.waitFor(30, TimeUnit.SECONDS))
        assertTrue(capLog(f), capLog(f).contains("the session is over (state 'failed'): the cap ends at level 2"))
        val r = f.returns("switch-failed")
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertEquals("1689600", maxOf(f, 0))
        assertEquals("2035200", maxOf(f, 7))
    }

    /**
     * The restart is the way back only where the return in place cannot put One UI back: in the Android takeover, a
     * policy still at the cap that cannot be written back, or a cap that cannot be ended. The same unwritable node with
     * the cap at level 0, or in a hosted session, is logged only, as before.
     */
    @Test
    fun theRestartIsChosenOnlyWhenTheInPlaceReturnCannotWork() = each { f ->
        fun lock(f: Fake) = assertTrue(f.file("$cpuNodes/policy7/scaling_max_freq").setWritable(false))
        // A takeover whose cap holds policy7 at 60 %, and the node cannot be written any more.
        run {
            capPhone(f)
            val cap = startCap(f)
            temps(f, 490, 330)
            awaitLevel(f, 2)
            lock(f)
            val r = f.returns()
            assertTrue(cap.waitFor(30, TimeUnit.SECONDS))
            assertTrue(r.text, r.text.contains("clocks: /$cpuNodes/policy7/scaling_max_freq could not be written back to 2035200 (it reads ${3398400 / 100 * 60}; the Android takeover's CPU cap was at level 2)"))
            f.assertFailsafe("the Android takeover's CPU cap is still in force: /$cpuNodes/policy7/scaling_max_freq could not be written back")
        }
        // The cap at level 0 (nothing of it in force): logged only, in place.
        val g = Fake(f.sh)
        capPhone(g)
        val cap = startCap(g)
        Thread.sleep(200)
        lock(g)
        val r = g.returns()
        assertTrue(cap.waitFor(30, TimeUnit.SECONDS))
        g.assertInPlace(r.text)
        assertTrue(r.text, r.text.contains("policy7/scaling_max_freq could not be written back to 2035200 (logged only)"))
        assertTrue(r.text, r.text.contains("Android takeover: its CPU cap ended at level 0"))
        // Hosted: the line of every session.
        val h = Fake(f.sh)
        capPhone(h, takeover = false)
        lock(h)
        val hr = h.returns()
        h.assertInPlace(hr.text)
        assertTrue(hr.text, hr.text.contains("policy7/scaling_max_freq could not be written back to 2035200 (logged only)"))
        // A cap that does not end: the restart, before One UI's clocks.
        val u = Fake(f.sh)
        capPhone(u)
        u.proc(7100, "sh", cmdline = "/system/bin/sh /data/local/tmp/oneios/oneios_switch.sh --cpu-cap")
        File(u.file("proc/7100"), "unkillable").createNewFile()
        File(u.control, "cpu-cap.pid").writeText("7100\n")
        File(u.control, "cpu-cap.level").writeText("2\n")
        val ur = u.returns()
        assertTrue(ur.text, !ur.text.contains("clocks: /"))
        u.assertFailsafe("the Android takeover's CPU cap (7100) could not be ended")
    }

    /** The session mode's choice and preflight (--mode-check), with a stand-in for xnuhost's --host-info. */
    @Test
    fun theSessionModeIsHostedUnlessAskedAndTakeoverOnlyWhereTheHostTableAllowsIt() = each { f ->
        capPhone(f, takeover = false)
        val xh = f.file("bin/xnuhost-host-info")
        xh.writeText("#!/bin/sh\necho \"\$*\" > \"\$ONEIOS_TEST_ROOT/log/host-info-args\"\ncat \"\$ONEIOS_TEST_ROOT/host-info\" 2>/dev/null\nexit \$(cat \"\$ONEIOS_TEST_ROOT/host-info-rc\" 2>/dev/null || echo 0)\n")
        assertTrue(xh.setExecutable(true))
        val env = mapOf("ONEIOS_TEST_XNUHOST" to xh.path)
        fun check(mode: String? = null): Ran = f.run("oneios_switch.sh", "--mode-check", env = env + (mode?.let { mapOf("ONEIOS_SESSION_MODE" to it) } ?: emptyMap()))
        fun refused(r: Ran, part: String) {
            assertEquals(r.text, 2, r.exit)
            assertTrue(r.text, r.text.contains("PREFLIGHT REFUSED: ") && r.text.contains(part))
        }
        // Nothing asked: hosted, no line, xnuhost not asked.
        var r = check()
        assertEquals(r.text, 0, r.exit)
        assertEquals("MODE OK hosted", r.text.trim())
        assertFalse(f.file("log/host-info-args").exists())
        // The app's toggle on the S24 Ultra's row.
        f.file("host-info").writeText("host-info: device=galaxy-s24-ultra takeover=yes (matched by ro.product.model=SM-S928B)\n")
        r = check("takeover")
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("Session mode: Android takeover (session-mode=takeover, from the app; device=galaxy-s24-ultra takeover=yes (matched by ro.product.model=SM-S928B))"))
        assertTrue(r.text, r.text.trim().endsWith("MODE OK takeover"))
        assertEquals("--host-info", f.lines("log/host-info-args").single().trim())
        // A row that does not allow it, a runtime too old to say, a bad word.
        f.file("host-info").writeText("host-info: device=galaxy-s25-ultra takeover=no (matched by ro.product.model=SM-S938B)\n")
        refused(check("takeover"), "session-mode=takeover (from the app) is not supported on this phone (device=galaxy-s25-ultra takeover=no")
        f.file("host-info").writeText("xnuhost: unknown or incomplete argument --host-info\n")
        f.file("host-info-rc").writeText("2\n")
        refused(check("takeover"), "does not answer --host-info (a runtime from before the Android takeover)")
        f.file("host-info-rc").delete()
        refused(check("fast"), "session-mode 'fast' (from the app) is not hosted or takeover")
        // The image's xnuhost.conf, the last line of the overlay's; its files go to xnuhost as --config.
        f.file("host-info").writeText("host-info: device=galaxy-s26-ultra takeover=yes (matched by ro.product.model=SM-S948B)\n")
        val conf = File(f.stage, "image/overlay/userland/xnuhost.conf").apply { parentFile.mkdirs(); writeText("pen=auto\nsession-mode=hosted\n  session-mode=takeover\r\n") }
        r = check()
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("from the image's xnuhost.conf; device=galaxy-s26-ultra takeover=yes"))
        assertEquals("--host-info --config ${conf.path}", f.lines("log/host-info-args").single().trim())
        assertEquals("MODE OK hosted", check("hosted").text.trim())          // the app's word over the image's
        conf.writeText("session-mode=sometimes\n")
        refused(check(), "session-mode 'sometimes' (from the image's xnuhost.conf) is not hosted or takeover")
        conf.delete()
        // Nothing for its cap to write, or to read.
        f.file("sys/class/power_supply/battery/temp").delete()
        refused(check("takeover"), "the cell's temperature, its CPU cap's input, is not readable")
        f.file(cpuNodes).deleteRecursively()
        refused(check("takeover"), "no CPU policy for its CPU cap")
    }

    /** The default session: the switch's xnuhost command line, its record and its lines are what they were. */
    @Test
    fun theHostedSessionIsTheSessionAsBefore() {
        val sw = code(switchScript).joinToString("\n")
        // xnuhost's command line of session ABI 1, unchanged, and the takeover's only with the switch's mark.
        val plain = "set -- \"/data/runtime/\$R_XNUHOST\" --session-abi \$ABI --mode takeover \\\n            --runtime /data/runtime --image /data/image --data /data/data --session /data/session\n"
        assertTrue(sw.contains(plain))
        val marked = sw.indexOf("[ \"\$(cat /data/control/base/mode 2>/dev/null)\" = takeover ] && set -- \"\$@\" --set session-mode=takeover")
        assertTrue(marked in sw.indexOf(plain) until sw.indexOf(LAUNCH))
        assertTrue(sw.indexOf("--set session-mode=takeover") > marked)
        // Every step of the takeover is behind its mode; base/mode is written only for it.
        assertTrue(sw.contains("if [ \"\$SMODE\" = takeover ]; then\n    echo takeover > \"\$B/mode\""))
        assertTrue(sw.contains("if [ \"\$SMODE\" = takeover ]; then\n    rm -f \"\$CTL/cpu-cap.pid\""))
        assertTrue(sw.contains("[ \"\$SMODE\" = hosted ] || takeover_checks \"\$X\""))
        // The cap writes no thermal node, no scaling_min_freq, nothing under /sys/power, and lowers no OOM score.
        val capMode = sw.substring(sw.indexOf("    --cpu-cap)"), sw.indexOf("    --usb-watch)"))
        for (never in listOf("/sys/class/thermal", "scaling_min_freq", "/sys/power", "oom_score_adj", "out_of_the_way", "renice", "EVIOCGRAB", "getevent")) {
            assertFalse("the cap has '$never'", capMode.contains(never))
        }
        // The return keeps its order: the cap ended, then One UI's clocks, then Gate A.
        val ret = code(returnScript).joinToString("\n")
        assertTrue(ret.indexOf("end_helper \"\$CTL/cpu-cap.pid\" --cpu-cap") in 0 until ret.indexOf("awk '{ l[NR] = \$0 }"))
        assertTrue(ret.indexOf("awk '{ l[NR] = \$0 }") in 0 until ret.indexOf("Gate A"))
    }

    /** One UI's USB gadget, as its framework set it: adb on, the UDC bound, a cable to a computer. */
    private fun usbOfOneUi(f: Fake) {
        f.file("props").appendText(
            "sys.usb.config=mtp,adb\nsys.usb.state=mtp,adb\npersist.sys.usb.config=mtp,adb\nsys.usb.controller=$UDC\n" +
                "sys.usb.configfs=1\nsys.usb.ffs.ready=1\ninit.svc.adbd=running\n",
        )
        for ((path, value) in listOf("config/usb_gadget/g1/UDC" to UDC, "sys/class/udc/$UDC/state" to "configured", "sys/class/power_supply/usb/online" to "1")) {
            f.file(path).apply { parentFile.mkdirs(); writeText("$value\n") }
        }
        // The repairs are off unless the stage asks for them.
        File(f.stage, "usb-repair").createNewFile()
    }

    /**
     * USB and adb during a session (docs/oneios.md): the switch's record of One UI's USB, and the return puts back
     * what differs (here as on a phone whose gadget HAL, not init, binds the UDC: the fake setprop only sets), before
     * One UI's zygote.
     */
    @Test
    fun oneUisUsbIsRecordedAndPutBackBeforeOneUisZygote() = each { f ->
        f.phone()
        usbOfOneUi(f)
        val save = f.run("oneios_switch.sh", "--usb-save")
        assertEquals(save.text, 0, save.exit)
        assertTrue(save.text, save.text.contains("USB of One UI: state mtp,adb, config mtp,adb, UDC $UDC configured; bound '$UDC', adbd running") && save.text.contains("USB debugging on"))
        val rec = File(f.control, "base/usb").readLines()
        for (want in listOf("adb=1", "config=mtp,adb", "controller=$UDC", "udc=$UDC", "adbd=running")) assertTrue("$rec lacks $want", want in rec)
        assertTrue(f.setprops.toString(), f.setprops.isEmpty())
        // In the session adb went from the gadget, adbd stopped and the gadget was unbound.
        f.file("props").appendText("sys.usb.config=adb\ninit.svc.adbd=stopped\n")
        f.file("config/usb_gadget/g1/UDC").writeText("")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        val log = f.setprops
        val netd = log.indexOf("ctl.restart netd")
        assertTrue("$log", log.indexOf("sys.usb.config mtp,adb") in 0 until netd && log.indexOf("ctl.start adbd") in 0 until netd)
        assertEquals(UDC, f.file("config/usb_gadget/g1/UDC").readText().trim())
        assertTrue(r.text, r.text.contains("usb: sys.usb.config adb -> mtp,adb (One UI's)") && r.text.contains("usb: UDC $UDC written back"))
        assertTrue(r.text, r.text.indexOf("usb: before the restore: ") in r.text.indexOf("[4/5]") until r.text.indexOf("One UI's zygote started"))
    }

    /** A return with nothing of USB that differs sets no USB property; one with no record of the switch says so. */
    @Test
    fun aReturnLeavesAnUnchangedUsbGadgetAlone() = each { f ->
        f.phone()
        usbOfOneUi(f)
        assertEquals(0, f.run("oneios_switch.sh", "--usb-save").exit)
        val r = f.returns()
        f.assertInPlace(r.text)
        assertFalse(f.setprops.toString(), f.setprops.any { it.startsWith("sys.usb.") || it == "ctl.start adbd" })
        assertTrue(r.text, r.text.contains("usb: after the restore: state mtp,adb, config mtp,adb, UDC $UDC configured"))
        val g = Fake(f.sh).also { it.phone() }
        val r2 = g.returns()
        g.assertInPlace(r2.text)
        assertTrue(r2.text, r2.text.contains("usb: no record of the switch"))
    }

    /**
     * The session's USB watcher puts One UI's UDC back on a gadget that was unbound and adb back on one that lost it,
     * and ends when the return begins.
     */
    @Test
    fun theUsbWatcherKeepsAdbOnTheGadgetUntilTheReturn() = each { f ->
        f.phone()
        usbOfOneUi(f)
        assertEquals(0, f.run("oneios_switch.sh", "--usb-save").exit)
        val w = f.start("oneios_switch.sh", "--usb-watch", log = "log/usb-watch")
        await("the watcher's first line") { f.lines("log/usb-watch").any { it.contains("usb: state mtp,adb") } }
        f.file("config/usb_gadget/g1/UDC").writeText("")
        await("the UDC written back") { f.file("config/usb_gadget/g1/UDC").readText().trim() == UDC }
        f.file("props").appendText("sys.usb.config=mtp\n")
        await("adb on the gadget again") { "sys.usb.config mtp,adb" in f.setprops }
        File(f.control, "state").writeText("returning\n")
        assertTrue(f.lines("log/usb-watch").toString(), w.waitFor(30, TimeUnit.SECONDS))
        assertTrue(f.lines("log/usb-watch").toString(), f.lines("log/usb-watch").any { it.contains("the session is over: the watcher ends") })
    }

    /** Where the composer's restart does not take surfaceflinger with it, surfaceflinger is restarted by name. */
    @Test
    fun aSurfaceflingerThatOutlivesTheComposerIsRestarted() = each { f ->
        f.phone()
        f.behave("sf_survives_composer")
        val r = f.returns()
        assertTrue(r.text, f.setprops.indexOf("ctl.restart surfaceflinger") > f.setprops.indexOf("ctl.restart $COMPOSER"))
        f.assertInPlace(r.text)
    }

    /** A surfaceflinger that died in the session (a GPU reset) is no reason to reboot: it is started with the composer. */
    @Test
    fun aSurfaceflingerThatDiedInTheSessionIsStartedAgain() = each { f ->
        f.phone()
        // (And a pid in the cgroup's list that is no process is not one of the session's.)
        f.file("sys/fs/cgroup/oneios_session/cgroup.procs").appendText("4999\n")
        f.file("proc/310").deleteRecursively()
        f.file("pids/surfaceflinger").delete()
        f.file("services/SurfaceFlinger").delete()
        val r = f.returns()
        assertTrue(r.text, r.text.contains("surfaceflinger is not running now, was 310 at the switch (it is restarted below)"))
        f.assertInPlace(r.text)
    }

    private fun failsafe(part: String, frameworkStarted: Boolean = false, arrange: (Fake) -> Unit) = each { f ->
        f.phone()
        arrange(f)
        val r = f.returns()
        assertEquals(r.text, 1, r.exit)
        f.assertFailsafe(part, frameworkStarted)
    }

    @Test
    fun aProcessThatEndsLateAfterSigkillIsWaitedForAtGateA() = each { f ->
        // Phone, 2026-11-12 23:15: a killed task outlived the stop's five SIGKILL rounds, Gate A looked once and the
        // failsafe restarted the phone. It ends at the 8th SIGKILL here: within Gate A's wait, so One UI comes back in place.
        // The scripts' clock runs 10 times faster here, not 100: Gate A's 30 s are then 3 s, room for the three more
        // rounds of kill, sleep and the session's listing that the stand-ins need on any machine (at 100 they were
        // 0.3 s, less than one round on macOS: OneiOS's macOS CI, 2026-11-15).
        f.phone(scale = 10)
        File(f.guest(5001, "xnuhost-tasks"), "kills_left").writeText("8\n")
        val r = f.returns()
        assertTrue(r.text, r.text.contains("Gate A: 5001 still there after SIGKILL: xnuhost-tasks"))
        assertTrue(r.text, r.text.contains("Gate A: the killed processes ended after"))
        f.assertInPlace(r.text)
    }

    @Test
    fun aProcessThatCannotBeKilledIsAReboot() = failsafe("processes still in the session's namespace or cgroup: 5001") { f ->
        File(f.guest(5001, "xnuhost-tasks"), "unkillable").createNewFile()
    }

    @Test
    fun aStageMountLeftInAnotherNamespaceIsAReboot() = failsafe("processes still in the session's namespace or cgroup: 6000") { f ->
        // Not in xnuhost's namespace nor its cgroup, but the stage is still its /data, and it does not die.
        File(f.guest(6000, "launchd", ns = "mnt:[90]", cgroup = false), "unkillable").createNewFile()
    }

    @Test
    fun aStageMountInInitsNamespaceIsAReboot() = failsafe("the stage is still mounted") { f ->
        f.file("proc/1/mountinfo").appendText("41 1 254:50 /local/tmp/oneios/image /data/local/tmp/oneios/x rw - f2fs /dev/block/dm-50 rw\n")
    }

    @Test
    fun aMountAddedOnOneUisPartitionsIsAReboot() = failsafe("mounts added on One UI's partitions during the session: /system/etc") { f ->
        f.file("proc/1/mountinfo").appendText("42 1 0:99 / /system/etc rw - tmpfs tmpfs rw\n")
    }

    @Test
    fun aVoldThatIsNotTheSwitchsIsAReboot() = failsafe("One UI's vold is 999 now, was 300 at the switch") { f ->
        f.file("pids/vold").writeText("999\n")
    }

    @Test
    fun aChangedSelinuxModeIsAReboot() = failsafe("SELinux is Permissive, was Enforcing") { f -> f.file("selinux").writeText("Permissive\n") }

    @Test
    fun anotherBootsBaselineIsAReboot() = failsafe("the baseline is another boot's") { f -> File(f.control, "base/boot_id").writeText("boot-0\n") }

    @Test
    fun aZygoteThatStartedByItselfIsAReboot() = failsafe("One UI's zygote or system_server started before the return was ready") { f ->
        f.file("props").appendText("init.svc.zygote=running\n")
    }

    @Test
    fun aComposerThatDoesNotComeBackIsAReboot() = failsafe("the display composer $COMPOSER did not restart") { f -> f.behave("no_start_$COMPOSER") }

    @Test
    fun aComposerThatWasNotRestartedIsAReboot() = failsafe("the display composer $COMPOSER did not restart (pid still '311'") { f -> f.behave("no_restart_$COMPOSER") }

    @Test
    fun aSurfaceflingerThatDoesNotComeBackIsAReboot() = failsafe("One UI's surfaceflinger did not restart") { f -> f.behave("no_start_surfaceflinger") }

    @Test
    fun aSurfaceflingerThatDoesNotRegisterIsAReboot() = failsafe("One UI's surfaceflinger did not register") { f -> f.behave("sf_not_registered") }

    @Test
    fun anAudioserverThatDoesNotRegisterIsAReboot() = failsafe("One UI's audioserver did not register") { f -> f.behave("audio_not_registered") }

    @Test
    fun noSystemServerIsAReboot() = failsafe("One UI's system_server did not start in 60 s", frameworkStarted = true) { f -> f.behave("no_system_server") }

    @Test
    fun aUserThatNeverUnlocksIsAReboot() = failsafe("user 0 not unlocked within 180 s", frameworkStarted = true) { f -> f.behave("locked") }

    /** A step that never comes back (init does not answer): the return's own guard reboots. */
    @Test
    fun aReturnThatHangsIsRebootedByItsGuard() = each { f ->
        f.phone()
        f.behave("hang_ctl.start_audioserver")
        val p = f.start("oneios_return.sh", "manual", env = mapOf("ONEIOS_TEST_GUARD_MAX" to "300"), log = "log/return")
        await("the guard's reboot", 60_000) { f.rebooted == "reboot,oneios-return-guard" }
        assertTrue(p.isAlive)
        assertTrue(f.outcome, f.outcome.startsWith("failsafe ") && f.outcome.contains("the return did not finish within 300s (last step: [3/5] Gate B: One UI's display and services)"))
        assertTrue(f.returnLog, f.returnLog.contains("GUARD: the return did not finish within 300s"))
        assertFalse(f.setprops.any { it == "ctl.restart netd" || it == "ctl.start zygote" })
    }

    /** One return at a time; a lock whose holder is gone does not keep the next return out. */
    @Test
    fun aReturnInProgressIsLeftAloneAndADeadOnesLockIsTaken() = each { f ->
        f.phone()
        File(f.control, "returning.lock").mkdirs()
        File(f.control, "returning.lock/pid").writeText("4242\n")
        f.proc(4242, "sh", cmdline = "/system/bin/sh /data/local/tmp/oneios/oneios_return.sh watcher")
        var r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("another return is already running (pid 4242); leaving it to it"))
        assertEquals(emptyList<String>(), f.setprops)
        assertEquals(emptyList<String>(), f.kills)
        // That return was killed: its pid is gone, or is another program's now.
        f.proc(4242, "sh", cmdline = "/system/bin/sh /vendor/bin/something.sh")
        r = f.returns()
        assertTrue(r.text, r.text.contains("the return that held the lock is gone (pid '4242'): taking over"))
        f.assertInPlace(r.text)
    }

    /**
     * Without a readable state there is nothing to return from, and never a reboot: except for the watcher and the
     * key readers, which exist only in a session, when One UI's framework is down as well.
     */
    @Test
    fun aSessionWhoseStateIsGoneIsARebootOnlyForTheWatcherAndTheKeys() = each { f ->
        f.phone()
        assertTrue(File(f.control, "state").delete())
        var r = f.returns("manual")
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("nothing to return from"))
        assertEquals(emptyList<String>(), f.setprops)
        assertEquals(emptyList<String>(), f.kills)
        r = f.returns("watcher")
        assertEquals(r.text, 1, r.exit)
        assertEquals("reboot,oneios-inplace-failsafe", f.rebooted)
        assertTrue(f.outcome, f.outcome.contains("the session's state cannot be read"))
        assertEquals(emptyList<String>(), f.kills)
    }

    /** ...and with One UI's framework running, not even for them. */
    @Test
    fun aMissingStateWithOneUiRunningIsNothing() = each { f ->
        f.phone()
        assertTrue(File(f.control, "state").delete())
        f.file("props").appendText("init.svc.zygote=running\n")
        val r = f.returns("keys-direct")
        assertEquals(r.text, 0, r.exit)
        assertEquals(emptyList<String>(), f.setprops)
    }

    @Test
    fun theRebootReturnNeedsNoSession() = each { f ->
        f.phone()
        f.session.deleteRecursively()
        f.control.deleteRecursively()
        val r = f.returns("reboot")
        assertEquals(r.text, 1, r.exit)
        assertEquals("reboot,oneios-return", f.rebooted)
        assertTrue(f.outcome, f.outcome.startsWith("reboot "))
        assertEquals(emptyList<String>(), f.kills)
    }

    /** What the way back rests on, on the scripts' text: it is armed first, apart from the guest, and never grabs a key. */
    @Test
    fun theWayBackIsArmedApartFromTheGuest() {
        val lines = code(switchScript)
        val sw = lines.joinToString("\n")
        // Reading the keys never takes them from anyone (no grab; the word is only in comments), by events and by state.
        assertFalse(sw.contains("EVIOCGRAB"))
        assertTrue(sw.contains("getevent -lq \"\$kd\"") && sw.contains("getevent -pl \"\$kd\""))
        assertTrue(sw.contains("*\"KEY_VOLUMEUP*\"*") && sw.contains("*\"KEY_VOLUMEDOWN*\"*"))
        val session = sw.substring(sw.indexOf("echo \"=== [1/5]"))
        val stop = session.indexOf("setprop ctl.stop zygote")
        val xnuhost = session.indexOf("unshare -m")
        // The watcher, the readers and the poll start in sessions of their own before xnuhost's namespace exists.
        for (mode in listOf("--watch", "--keys \"\$kd\"", "--keys-poll")) {
            val at = session.indexOf("\"\$BB\" setsid \$SH \"\$SELF\" $mode")
            assertTrue(mode, at in 0 until stop && at < xnuhost)
        }
        // The wakelock, and the check that all of it runs, come before the stop; a way back that is not armed stops nothing.
        assertTrue(session.indexOf("echo oneios_session > /sys/power/wake_lock") in 0 until stop)
        val notArmed = session.indexOf("if [ -n \"\$armed\" ]; then")
        assertTrue(notArmed in 0 until stop && session.indexOf("exit 4", notArmed) in notArmed until stop)
        for (check in listOf("the watcher is not running", "key readers started", "is not running", "the wakelock oneios_session is not held")) {
            assertTrue(check, session.indexOf(check) in 0 until notArmed)
        }
        // The watcher and the readers leave for the root cgroup and are exempt from the OOM killer; xnuhost gets a
        // cgroup of its own and is what the kernel ends first.
        val out = sw.substring(sw.indexOf("out_of_the_way() {"), sw.indexOf("ask_return() {"))
        assertTrue(out.contains("\"\$T/sys/fs/cgroup/cgroup.procs\"") && out.contains("echo -1000"))
        val watch = sw.substring(sw.indexOf("    --watch)"), sw.indexOf("    session|--check) ;;"))
        assertTrue(watch.contains("out_of_the_way") && watch.contains("awake") && watch.contains("hard_reboot oneios-watcher-failsafe"))
        val inner = sw.substring(sw.indexOf("    --inner)"), sw.indexOf("    --stop-loop)"))
        assertTrue(inner.contains("CG=/sys/fs/cgroup/oneios_session") && inner.contains("echo \$\$ > \"\$CG/cgroup.procs\""))
        assertTrue(inner.contains("echo 500 > /proc/\$\$/oom_score_adj"))
        assertTrue(inner.indexOf("oom_score_adj") in 0 until inner.indexOf(LAUNCH))
        // The return: the guard is armed before the first step, the display comes back before One UI's zygote, and
        // the reboot has its two last resorts.
        val ret = code(returnScript).joinToString("\n")
        assertTrue(ret.indexOf("--guard \"\$GTOK\"") in 0 until ret.indexOf("step \"[1/5]"))
        val display = ret.indexOf("setprop ctl.restart \"\$COMPOSER_SVC\"")
        assertTrue(display in ret.indexOf("Gate A") until ret.indexOf("setprop ctl.restart netd"))
        assertTrue(ret.indexOf("setprop ctl.start bootanim") in display until ret.indexOf("setprop ctl.restart netd"))
        assertTrue(ret.contains("\"\$BB\" reboot -f") && ret.contains("echo b > \"\$P/sysrq-trigger\""))
        // Nothing is unmounted by the return, in any namespace.
        assertFalse(ret.contains("umount"))
    }

    // --- The boot screen: OneOS's, from the stop of One UI's framework until iOS draws ----

    /**
     * The boot screen's status folder as the switch leaves it (`boot_status.sh`'s `oneos_boot_begin ios`), in the way
     * back's control folder. With [processes]: its supervisor, its renderer and the switch's feeder, as fake processes.
     */
    private fun bootScreen(f: Fake, processes: Boolean = false, drawn: Boolean = true): File {
        val d = File(f.control, "bootui").apply { mkdirs() }
        File(d, "generation").writeText("g1\n")
        File(d, "title").writeText("Starting iOS 27\n")
        File(d, "status").writeText("Stopping One UI's framework\n")
        if (drawn) File(d, "ready").writeText("7002 g1\n")
        if (processes) {
            f.proc(7001, "sh", cmdline = "/system/bin/sh ${f.stage}/bin/boot_status.sh supervise g1 ios")
            f.proc(7002, "app_process", cmdline = "app_process /system/bin OneOSBootStatus $d g1 1800")
            f.proc(7003, "sh", cmdline = "/system/bin/sh ${f.stage}/oneios_switch.sh --bootui")
            File(d, "supervisor").writeText("7001\n")
            File(d, "worker").writeText("7002\n")
            File(d, "feeder.pid").writeText("7003\n")
        }
        return d
    }

    private fun shown(d: File, name: String = "status") = File(d, name).takeIf { it.isFile }?.readText()?.trim().orEmpty()

    /** The switch's feeder: reads xnuhost's log and writes the boot screen's status line. */
    private fun feeder(f: Fake, d: File): Process {
        val p = f.start("oneios_switch.sh", "--bootui", log = "log/bootui")
        await("the feeder's pid") { File(d, "feeder.pid").isFile }
        return p
    }

    private fun xnuhostSays(f: Fake, vararg lines: String) = File(f.session, "xnuhost.log").appendText(lines.joinToString("") { "$it\n" })

    private fun assertBootScreenEnded(f: Fake, d: File, text: String) {
        for (pid in 7001..7003) assertFalse("$pid is left\n$text", f.file("proc/$pid").exists())
        assertTrue(text, File(d, "stop").exists() && shown(d, "generation").startsWith("ended."))
        assertTrue(text, f.kills.containsAll(listOf("-9 7001", "-9 7002", "-9 7003")))
        assertTrue(text, f.returnLog.contains("boot screen: ended"))
    }

    /** Root stages the three files in bin/, which xnuhost's namespace has read-only; the verb takes no other name. */
    @Test
    fun theBootScreenFilesAreStagedWhereTheGuestCannotWrite() = each { f ->
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")))
        f.scripts()
        for (a in bootScreenFiles) assertTrue(a.name, File(f.stage, "bin/${a.name}").readBytes().contentEquals(a.readBytes()))
        assertEquals(listOf("boot_status.sh", "OneOSBootStatus.dex", "oneos_boot_icon.png"), OneiosRoot.BOOT_SCREEN_FILES)
        val sum = "a".repeat(64)
        for (n in OneiosRoot.SESSION_FILES) assertEquals(n, emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.SCRIPT, listOf(n, "10", sum)))
        for (n in listOf("guest_start.sh", "bin/boot_status.sh", "oneios_root.sh")) {
            assertTrue(n, OneiosRoot.problems(OneiosRoot.Verb.SCRIPT, listOf(n, "10", sum)).isNotEmpty())
        }
        val inner = code(switchScript).joinToString("\n").let { it.substring(it.indexOf("    --inner)"), it.indexOf("    --stop-loop)")) }
        assertTrue(inner.contains("for d in runtime image control bin oneios_switch.sh oneios_return.sh; do"))
        // A changed file is not taken, and what was staged stays.
        val icon = bootScreenFiles.last().readBytes()
        assertRefused(f.verb(OneiosRoot.Verb.SCRIPT, listOf("oneos_boot_icon.png", icon.size.toString(), sum), icon), "did not arrive intact")
        assertTrue(File(f.stage, "bin/oneos_boot_icon.png").readBytes().contentEquals(icon))
    }

    /** OneOS's own script makes the iOS screen: a plain title, the status line always on, the way back as a hint. */
    @Test
    fun oneOssBootScriptStartsTheIosScreen() = each { f ->
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("image")))
        f.scripts()
        val bin = File(f.stage, "bin")
        val d = File(f.root, "bootui")
        fun sh(script: String, vararg args: String, path: File? = null): Process {
            val pb = ProcessBuilder(listOf(f.sh, "-c", script, "sh") + args).redirectErrorStream(true)
            pb.environment()["ONEOS_BOOT_DIR"] = d.path
            pb.environment()["ONEOS_BOOT_HOME"] = bin.path
            pb.environment()["ONEOS_BOOT_MAX"] = "77"
            HostTools.into(pb.environment(), path?.path)
            pb.redirectOutput(ProcessBuilder.Redirect.appendTo(File(f.root, "boot.out")))
            return pb.redirectInput(ProcessBuilder.Redirect.from(File("/dev/null"))).start().also { started += it }
        }
        // (Its supervisor is started with /system/bin/sh, which this machine has not: only the files are made.)
        assertTrue(sh(". \"\$1\"; oneos_boot_begin ios; oneos_boot_event 'a status line'", File(bin, "boot_status.sh").path).waitFor(30, TimeUnit.SECONDS))
        assertEquals("Starting iOS 27", shown(d, "title"))
        assertEquals("Hold Volume Up + Volume Down for 3 s to go back to One UI", shown(d, "hint"))
        assertEquals("1", shown(d, "verbose"))
        assertEquals("a status line", shown(d))
        assertTrue(File(d, "icon.png").readBytes().contentEquals(bootScreenFiles.last().readBytes()))
        val generation = shown(d, "generation")
        assertTrue(generation.isNotEmpty() && !File(d, "stop").exists())
        // No Apple name or mark on it: the title is text, the picture is OneOS's own icon.
        val script = File(bin, "boot_status.sh").readText()
        val ios = script.substring(script.indexOf("if [ \"\$1\" = ios ]; then"), script.indexOf("elif [ \"\$1\" = enter ]"))
        assertFalse(ios, ios.contains("Apple", ignoreCase = true))
        // The supervisor in its iOS mode: no Android boot events are read, the renderer gets the bound, the pids
        // are left for the return, and the stop flag ends it.
        val tools = File(f.root, "boottools").apply { mkdirs() }
        fun tool(name: String, body: String) = File(tools, name).apply { writeText("#!/bin/sh\n$body\n"); setExecutable(true) }
        tool("app_process", "echo \"\$CLASSPATH \$*\" >> \"\$ONEOS_BOOT_DIR/renderer.args\"\nwhile [ ! -f \"\$ONEOS_BOOT_DIR/stop\" ]; do sleep 0.05; done")
        tool("logcat", "echo logcat >> \"\$ONEOS_BOOT_DIR/called\"")
        tool("getprop", "echo getprop >> \"\$ONEOS_BOOT_DIR/called\"; echo 1")
        tool("pidof", "echo 12345")
        val sup = sh("exec \"\$0\" \"\$1\" supervise \"\$2\" ios".replace("\"\$0\"", f.sh), File(bin, "boot_status.sh").path, generation, path = tools)
        await("the renderer's start") { File(d, "renderer.args").isFile && File(d, "worker").isFile }
        assertEquals("${bin.path}/OneOSBootStatus.dex /system/bin OneOSBootStatus ${d.path} $generation 77", File(d, "renderer.args").readLines().first())
        assertTrue(shown(d, "supervisor").toIntOrNull() != null && shown(d, "worker").toIntOrNull() != null)
        Thread.sleep(700)
        assertTrue(sup.isAlive)
        File(d, "stop").createNewFile()
        assertTrue(sup.waitFor(30, TimeUnit.SECONDS))
        assertFalse("it read Android's boot events", File(d, "called").exists())
        assertEquals(1, File(d, "renderer.args").readLines().size)
    }

    /** The boot screen's bar: (the step, of how many, how far), from `progress`, or null when there is none. */
    private fun bar(d: File): Triple<Int, Int, Double>? =
        shown(d, "progress").split(" ").takeIf { it.size == 3 }?.let { Triple(it[0].toInt(), it[1].toInt(), it[2].toDouble()) }

    /**
     * The status line follows xnuhost's log through the boot screen's twelve steps (a first start here: the stage
     * has no `data/data.img`), with the bar's step, how far it is and the next step's name, then says why iOS
     * stopped. The bar never goes back within a boot.
     */
    @Test
    fun theBootScreenShowsHowFarTheBootGotAndWhyItStopped() = each { f ->
        f.phone(scale = 20)
        val d = bootScreen(f)
        File(f.session, "xnuhost.log").writeText("")
        val p = feeder(f, d)
        await("the first step's bar") { bar(d)?.first == 1 && shown(d, "next") == "Starting xnuhost" }
        assertEquals("Stopping One UI's framework", shown(d))
        assertEquals(12, bar(d)!!.second)
        assertEquals("Starting xnuhost", shown(d, "next"))
        // The lines of a first start on the phone (2026-11-22), each with the step it begins and the next one's name.
        val boot = listOf(
            Triple("oneios inner: cgroup /sys/fs/cgroup/oneios_session", "Starting xnuhost", "Locking iOS's RAM"),
            Triple("[286239.524] xnuhost I xnuhost: session ABI 1, mode takeover, pid 4146179", "Starting xnuhost", "Locking iOS's RAM"),
            Triple("[8280.900] xnuhost I memory: the guest's RAM is held for the session: 5632 MiB, prefaulted on a thread at nice 19 in 16 MiB steps, locked as it goes", "Locking iOS's RAM", "Starting the kernel"),
            Triple("[8284.000] xnuhost I memory: the guest's RAM is held: 5632 MiB prefaulted in 3638 ms, locked (mlock: the host cannot swap it)", "Starting the kernel", "First start: making iOS's Data store (once)"),
            Triple("[286239.909] xnuhost I cpu0: entering the kernel at 0x2003dcc488", "Starting the kernel", "First start: making iOS's Data store (once)"),
            Triple("[286240.068] guest     Darwin Kernel Version 25.5.0: Wed Nov 11 04:04:41 IST 2026; akshay:ios-obj/DEVELOPMENT_ARM64_BCM2837", "Starting the kernel", "First start: making iOS's Data store (once)"),
            Triple("[286727.194] guest     BSD root: disk8s1, major 1, minor 12", "Starting the kernel", "First start: making iOS's Data store (once)"),
            Triple("[286727.411] guest     OneiOS Data: first start: /sbin/newfs_apfs -e -x -v Data /dev/disk9", "First start: making iOS's Data store (once)", "First start: unpacking iOS's data (once)"),
            Triple("[8307.787] guest     OneiOS Data: unpacking the seed (1209 MiB on disk2) into /private/var", "First start: unpacking iOS's data (once)", "Starting launchd"),
            Triple("[286728.026] guest     load_init_program: attempting to load /sbin/launchd", "Starting launchd", "Starting iOS's system services"),
            Triple("[287612.623] guest     com.apple.xpc.launchd|2026-11-10 15:05:22.422484 <Notice>: hello, launchd UUID: CA54230D", "Starting iOS's system services", "Starting SpringBoard"),
            Triple("[288194.264] guest     SpringBoard[124] triggered unnest of range 0x1e9c00000->0x1ebe00000 of DYLD shared region", "Starting SpringBoard", "Starting the display (backboardd)"),
            Triple("[286981.700] guest     oneios-display: framebuffer opened by backboardd[53], type 0: status 0, client IOMobileFramebufferUserClient", "Starting the display (backboardd)", "Waiting for iOS's first picture"),
            Triple("[14380.637] xnuhost I display: the guest's first frame of its own: all black; session/ready waits for one with content (up to 120 s)", "Waiting for iOS's first picture", "iOS is up: handing the screen to it"),
            Triple("[14419.537] xnuhost I guest ready: first frame with content, 38.9 s and 1 frames after the guest's first (black) frame", "iOS is up: handing the screen to it", ""),
        )
        val steps = mapOf("Starting xnuhost" to 2, "Locking iOS's RAM" to 3, "Starting the kernel" to 4, "First start: making iOS's Data store (once)" to 5,
            "First start: unpacking iOS's data (once)" to 6, "Starting launchd" to 7, "Starting iOS's system services" to 8, "Starting SpringBoard" to 9,
            "Starting the display (backboardd)" to 10, "Waiting for iOS's first picture" to 11, "iOS is up: handing the screen to it" to 12)
        var was = bar(d)!!.third
        for ((line, text, next) in boot) {
            // (Among the console's other lines, and after a megabyte of them for one step: nothing is skipped.)
            if (text.startsWith("First start: making")) File(f.session, "xnuhost.log").appendText("[286241.714] guest     pmap_startup() init/release time: 1542521 microsec\n".repeat(20_000))
            xnuhostSays(f, "[286241.714] guest     pmap_startup() init/release time: 1542521 microsec", line)
            await("$text, next $next") { shown(d) == text && bar(d)?.first == steps[text] && shown(d, "next") == next }
            val now = bar(d)!!
            assertEquals(12, now.second)
            assertTrue("$text: ${now.third} after $was", now.third >= was && now.third <= 1.0)
            was = now.third
        }
        assertEquals(1.0, bar(d)!!.third, 0.0)
        // A line of an earlier step does not take the boot back; a restart of the guest in place does, bar and all.
        xnuhostSays(f, "[288195.000] guest     BSD root: disk8s1, major 1, minor 12")
        Thread.sleep(300)
        assertEquals("iOS is up: handing the screen to it", shown(d))
        assertEquals(12, bar(d)!!.first)
        xnuhostSays(f, "[288300.000] xnuhost I the guest asked for a restart: starting again", "[288300.100] xnuhost I xnuhost: session ABI 1, mode takeover, pid 4146179")
        await("the restart") { shown(d) == "Starting xnuhost" && bar(d)?.first == 2 }
        assertTrue(bar(d)!!.third < 0.5)
        // A panic, as the console has it. What is drawn is printable ASCII, whatever the guest wrote.
        xnuhostSays(f, "[287167.735] guest     panic(cpu 1 caller 0xfffffff00ad8d2c4): Console I/O \u001b[31mfrom\u0007 interrupt-disabled context @serial_console.c:175", "[287167.737] guest       frame 0xfffffff00b4aa0cc")
        val panic = "Console I/O  [31mfrom  interrupt-disabled context @serial_console.c:175"
        await("the panic") { shown(d) == "Kernel panic: $panic" && shown(d, "next") == "" }
        val stopped = bar(d)
        xnuhostSays(f, "[287167.934] xnuhost I stopping: the guest halted on cpu1 (reason 2, code 0)", "[287168.353] xnuhost I exit 4")
        f.ends(XNUHOST)
        await("why it ended") { shown(d) == "iOS stopped: kernel panic: $panic" && shown(d, "next") == "Going back to One UI" }
        // The bar stays where the boot stopped.
        assertEquals(stopped, bar(d))
        // It stays up with the reason until a return begins, and then leaves the screen to the return.
        Thread.sleep(300)
        assertTrue(p.isAlive)
        assertFalse(File(d, "stop").exists())
        File(f.control, "state").writeText("returning\n")
        assertTrue(p.waitFor(30, TimeUnit.SECONDS))
        assertFalse(File(d, "stop").exists())
        // It only read and wrote its own folder: nothing was signalled, nothing asked of init, no return asked.
        assertEquals(emptyList<String>(), f.kills)
        assertEquals(emptyList<String>(), f.setprops)
        assertFalse(File(f.session, "return.request").exists())
        assertEquals("Starting iOS 27", shown(d, "title"))
    }

    /**
     * A later boot (the stage has its Data store): "next" after the kernel is launchd, the two first-start steps are
     * passed over (the count goes from 4 to 7), and the bar never goes back.
     */
    @Test
    fun aLaterBootPassesOverTheFirstStartSteps() = each { f ->
        f.phone(scale = 20)
        val d = bootScreen(f)
        File(f.stage, "data").mkdirs()
        File(f.stage, "data/data.img").writeText("a Data store\n")
        File(f.session, "xnuhost.log").writeText("")
        val p = feeder(f, d)
        await("the first step's bar") { bar(d)?.first == 1 }
        var was = bar(d)!!.third
        val boot = listOf(
            Pair("[14330.714] xnuhost I xnuhost: session ABI 1, mode takeover, pid 10317", Triple(2, "Starting xnuhost", "Locking iOS's RAM")),
            Pair("[14335.153] xnuhost I memory: the guest's RAM is held: 5632 MiB prefaulted in 3638 ms, locked (mlock: the host cannot swap it)", Triple(4, "Starting the kernel", "Starting launchd")),
            Pair("[14337.436] guest     OneiOS Data: /dev/disk6s3 on /dev/disk2", Triple(4, "Starting the kernel", "Starting launchd")),
            Pair("[14337.711] guest     load_init_program: attempting to load /sbin/launchd", Triple(7, "Starting launchd", "Starting iOS's system services")),
        )
        for ((line, want) in boot) {
            val (step, status, next) = want
            xnuhostSays(f, line)
            await("step $step") { bar(d)?.first == step && shown(d, "next") == next && shown(d) == status }
            assertTrue("step $step: ${bar(d)} after $was", bar(d)!!.third >= was)
            was = bar(d)!!.third
        }
        assertEquals("Starting launchd", shown(d))
        // The steps a later boot has, each its typical length (a share of the bar): before launchd 24 s of 102 s.
        assertTrue(bar(d).toString(), bar(d)!!.third in 0.2..0.45)
        File(f.control, "state").writeText("returning\n")
        assertTrue(p.waitFor(30, TimeUnit.SECONDS))
    }

    /** The screen goes when the guest's picture is on the display helper's layer, and stays while iOS shows nothing. */
    @Test
    fun theBootScreenIsHandedToTheDisplayHelperAtTheGuestsFirstFrame() = each { f ->
        f.phone(scale = 20)
        val d = bootScreen(f)
        val p = feeder(f, d)
        // xnuhost reports ready, and no display helper runs: nothing shows iOS, so the screen stays.
        xnuhostSays(f, "[1.000] xnuhost I xnuhost: session ABI 1, mode takeover, pid 1", "[288301.000] xnuhost I guest ready: first frame")
        await("ready") { shown(d) == "iOS is up: handing the screen to it" && bar(d) == Triple(12, 12, 1.0) }
        // A helper's log of another session, and a pid that is some other process now: still nothing.
        File(f.control, "display.log").writeText("oneios-display: layer up\noneios-display: first frame posted (1440x3120 buffer, stride 5760, format 1)\n")
        File(f.control, "display.pid").writeText("300\n")
        Thread.sleep(400)
        assertTrue(p.isAlive && !File(d, "stop").exists())
        // The helper, connected and with its layer up, but no frame yet and no ready: the screen stays.
        f.proc(7100, "app_process", cmdline = "app_process /system/bin OneiOSDisplay --session ${f.session} --takeover --wait 60")
        File(f.control, "display.pid").writeText("7100\n")
        File(f.control, "display.log").writeText("oneios-display: guest frame 1440x3120, stride 5760\noneios-display: layer up\n")
        Thread.sleep(400)
        assertTrue(p.isAlive && !File(d, "stop").exists())
        assertFalse(File(d, "native").exists())
        // The helper put the display's projection on the panel's own mode: the renderer is told to draw for it.
        File(f.control, "display.log").appendText("oneios-display: display projection set to the active mode 1440x3120\n")
        await("the size of the panel's mode") { shown(d, "native") == "1" }
        assertTrue(p.isAlive && !File(d, "stop").exists())
        // Its first frame: the picture covers the boot screen, which is stopped under it.
        File(f.control, "display.log").appendText("oneios-display: first frame posted (1440x3120 buffer, stride 5760, format 1)\n")
        assertTrue(p.waitFor(30, TimeUnit.SECONDS))
        assertTrue(File(d, "stop").exists())
        assertTrue(f.lines("log/bootui").any { it.contains("the guest's picture is on the display helper's layer") })
        assertEquals(emptyList<String>(), f.kills)
        assertEquals("running", f.state)
    }

    /** `session/ready` hands over too, once the helper has a layer; a renderer that never drew is given up after 30 s. */
    @Test
    fun readyHandsTheBootScreenOverAndADeadRendererIsGivenUp() = each { f ->
        f.phone(scale = 20)
        val d = bootScreen(f)
        f.proc(7100, "oneios-display", cmdline = "${f.stage}/runtime/bin/oneios-display --session ${f.session} --takeover --wait 60")
        File(f.control, "display.pid").writeText("7100\n")
        File(f.control, "display.log").writeText("oneios-display: layer up\n")
        val p = feeder(f, d)
        Thread.sleep(300)
        assertTrue(p.isAlive && !File(d, "stop").exists())
        File(f.session, "ready").createNewFile()
        assertTrue(p.waitFor(30, TimeUnit.SECONDS))
        assertTrue(File(d, "stop").exists())
        // The other end: no frame of the renderer's own within 30 s.
        File(d, "stop").delete()
        File(f.control, "display.pid").delete()
        File(d, "ready").delete()
        val q = feeder(f, d)
        assertTrue(q.waitFor(60, TimeUnit.SECONDS))
        assertTrue(File(d, "stop").exists())
        assertTrue(f.lines("log/bootui").any { it.contains("the renderer posted no frame in 30 s") })
        assertEquals("running", f.state)
        assertEquals(emptyList<String>(), f.setprops)
    }

    /** In place: the screen says the return began, and is gone, processes and all, before the first gate. */
    @Test
    fun theReturnEndsTheBootScreenBeforeItsGates() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        File(d, "progress").writeText("9 12 0.512\n")
        File(d, "next").writeText("Starting the display (backboardd)\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertBootScreenEnded(f, d, r.text)
        assertEquals("Returning to One UI", shown(d, "title"))
        assertEquals("Stopping iOS", shown(d))
        // No bar on the way back: what it counted was the boot.
        assertFalse(File(d, "progress").exists() || File(d, "next").exists())
        assertTrue(r.text, r.text.indexOf("boot screen: ended") in r.text.indexOf("SIGTERM to xnuhost") until r.text.indexOf("Gate A"))
        assertTrue(f.kills.toString(), f.kills.indexOf("-TERM $XNUHOST") < f.kills.indexOf("-9 7003"))
        // The feeder at once; the supervisor and the renderer get a second to take the layer away themselves.
        assertEquals(f.kills.toString(), 1, f.kills.count { it == "-9 7002" })
    }

    /** A renderer that cannot be ended, or a pid file that names another process by now, never fails a gate. */
    @Test
    fun aBootScreenThatCannotBeEndedIsLoggedAndIsNoReboot() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        File(f.file("proc/7002"), "unkillable").createNewFile()
        File(d, "supervisor").writeText("300\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertTrue(r.text, r.text.contains("boot screen: still running after SIGKILL (7002 ): logged only"))
        // vold has pid 300: a pid alone is never signalled.
        assertFalse(f.kills.toString(), f.kills.any { it.endsWith(" 300") || it.endsWith(" 7001") })
        assertTrue(f.file("proc/300").isDirectory)
    }

    /** The failsafe reboot, the reboot return and a switch that never stopped One UI end the screen as well. */
    @Test
    fun aFailsafeEndsTheBootScreenToo() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        File(f.guest(5001, "xnuhost-tasks"), "unkillable").createNewFile()
        val r = f.returns()
        assertEquals(r.text, 1, r.exit)
        f.assertFailsafe("processes still in the session's namespace or cgroup: 5001")
        assertBootScreenEnded(f, d, r.text)
        assertTrue(f.returnLog, f.returnLog.indexOf("boot screen: ended") < f.returnLog.indexOf("FAILSAFE: "))
    }

    @Test
    fun theRebootReturnEndsTheBootScreenToo() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        val r = f.returns("reboot")
        assertEquals(r.text, 1, r.exit)
        assertEquals("reboot,oneios-return", f.rebooted)
        assertBootScreenEnded(f, d, r.text)
        assertEquals(f.kills.toString(), 3, f.kills.size)
    }

    @Test
    fun aSwitchThatNeverStoppedOneUiHasItsBootScreenEnded() = each { f ->
        f.phone(stopped = false, state = "starting")
        val d = bootScreen(f, processes = true)
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(r.text, r.text.contains("The switch ended before One UI's framework was stopped: nothing to restore."))
        assertBootScreenEnded(f, d, r.text)
        assertEquals(emptyList<String>(), f.setprops)
    }

    /** The watcher's return: the screen says why iOS stopped until the return ends it. */
    @Test
    fun theWatchersReturnSaysWhyOnTheBootScreenAndEndsIt() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        File(f.session, "xnuhost.log").writeText(
            "[1.000] xnuhost I xnuhost: session ABI 1, mode takeover, pid 1\n[1.100] xnuhost E image: /data/image/os.img is not an image of format 1\n",
        )
        val w = watcher(f)
        f.ends(XNUHOST)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertEquals(f.returnLog, 0, w.exitValue())
        assertTrue(f.returnLog, f.returnLog.contains("watcher: xnuhost $XNUHOST ended: how is not recorded (last log lines: "))
        f.assertInPlace()
        assertBootScreenEnded(f, d, f.returnLog)
        assertEquals("Returning to One UI", shown(d, "title"))
        assertEquals("xnuhost ended: image: /data/image/os.img is not an image of format 1", shown(d))
    }

    @Test
    fun theOtherReasonsOfTheWatcherAreOnTheBootScreenToo() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        File(f.session, "xnuhost.log").writeText("[1.000] xnuhost I stopping: PSCI SYSTEM_OFF (reason 0, code 0)\n[1.100] xnuhost I exit 0\n")
        val w = watcher(f, max = 30)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        f.assertInPlace()
        assertEquals("iOS did not come up within 30 s", shown(d))
        assertBootScreenEnded(f, d, f.returnLog)
        // And what the log's end says, where xnuhost itself ended.
        val g = Fake(f.sh)
        g.phone()
        val e = bootScreen(g, processes = true)
        File(g.session, "xnuhost.log").writeText("[1.000] xnuhost I stopping: PSCI SYSTEM_OFF (reason 0, code 0)\n[1.100] xnuhost I exit 0\n")
        File(g.session, "ready").createNewFile()
        val v = watcher(g)
        g.ends(XNUHOST)
        assertTrue(v.waitFor(60, TimeUnit.SECONDS))
        g.assertInPlace()
        assertEquals("iOS stopped: PSCI SYSTEM_OFF (xnuhost exit 0)", shown(e))
    }

    /** On the scripts' text: optional, after the way back is armed, no key device, and never a reason for a gate to fail. */
    @Test
    fun theBootScreenIsOptionalAndLeavesTheWayBackAlone() {
        val sw = code(switchScript).joinToString("\n")
        val session = sw.substring(sw.indexOf("echo \"=== [1/5]"))
        // It starts only after the way back is armed and checked, and before One UI's zygote stops.
        val begin = session.indexOf("\nbootui_begin\n")
        assertTrue(begin in session.indexOf("if [ -n \"\$armed\" ]; then") until session.indexOf("setprop ctl.stop zygote"))
        // Everything of it: no key device, no property, no service, no signal, no wakelock, no return request, no reboot.
        val helpers = sw.substring(sw.indexOf("BOOTUI=\"\$CTL/bootui\""), sw.indexOf("hard_reboot() {"))
        val mode = sw.substring(sw.indexOf("    --bootui)"), sw.indexOf("    --keys)"))
        for (never in listOf("getevent", "/dev/input", "setprop", "kill ", "ctl.", "wake_lock", "return.request", "reboot", "refuse", "exit 4", "> \"\$CTL/state\"")) {
            assertFalse("the boot screen has '$never'", (helpers + mode).contains(never))
        }
        // Only files root staged and owns are run, and a missing one is the switch as it was before.
        assertTrue(helpers.contains("[ -f \"\$BOOTBIN/\$f\" ] && root_only \"\$BOOTBIN/\$f\" ||"))
        assertTrue(helpers.contains("BOOTBIN=\"\$STAGE/bin\"") && helpers.contains("BOOTUI=\"\$CTL/bootui\""))
        val start = helpers.substring(helpers.indexOf("bootui_begin() {"), helpers.indexOf("log_scan() {"))
        assertFalse(start, Regex("""(^|\s)exit [0-9]""").containsMatchIn(start.replace(". \"\$BOOTBIN/boot_status.sh\" || exit 1", "")))
        // The watcher's own check of xnuhost does not rest on anything of the screen's.
        val watch = sw.substring(sw.indexOf("    --watch)"), sw.indexOf("    session|--check) ;;"))
        assertTrue(watch.contains("if ! { [ -n \"\$pid\" ] && [ \"\$(readlink \"\$P/\$pid/ns/mnt\" 2>/dev/null)\" = \"\$ns\" ]; }; then"))
        // The return: ended in its first step, before the gates and before the branch for a switch that never
        // stopped One UI; on every reboot; and nothing in it can fail the return.
        val ret = code(returnScript).joinToString("\n")
        val ended = ret.indexOf("\nbootui_end\n")
        assertTrue(ended in ret.indexOf("step \"[1/5]") until ret.indexOf("step \"[2/5] Gate A"))
        assertTrue(ended < ret.indexOf("if [ ! -e \"\$CTL/stopped\" ]"))
        val reboot = ret.substring(ret.indexOf("do_reboot() {"), ret.indexOf("failsafe() {"))
        assertTrue(reboot.indexOf("bootui_end") in 0 until reboot.indexOf("sys.powerctl"))
        val end = ret.substring(ret.indexOf("BOOTUI=\$CTL/bootui"), ret.indexOf("wait_found() {"))
        for (never in listOf("failsafe", "exit ", "setprop", "do_reboot")) assertFalse("the boot screen's end has '$never'", end.contains(never))
    }

    // --- What the first runs on the phone found (0.4.81) ----------------------------

    /**
     * Android's sh (mksh) ends a script, silently with `2>/dev/null`, when the redirection of a special builtin fails.
     * `:` is one: the inner shell's check that control/ is read-only ended it every time the check succeeded, and
     * xnuhost never started. No script here redirects `:`; the check goes on under every shell.
     */
    @Test
    fun noScriptRedirectsTheColonBuiltin() = each { f ->
        // (":>file" and ": 2>/dev/null >file" too.)
        val colon = Regex("""(^|[;&|({]|\bthen|\bdo|\belse)\s*:(\s[^#]*)?[<>]""")
        // boot_status.sh whole: the switch runs it, and OneOS's own guests share it.
        for (s in listOf(switchScript, returnScript, rootScript, File(Shipped.switcherAssets, "boot_status.sh"))) {
            val bad = code(s).filter { colon.containsMatchIn(it) }
            assertTrue("${s.name} redirects ':': $bad", bad.isEmpty())
        }
        // The check itself, as the inner shell has it, with a folder that cannot be written.
        val probe = "if true 2>/dev/null > /data/control/.w; then"
        assertTrue(code(switchScript).any { it.trim() == probe })
        fun run(script: String): Pair<Int, String> {
            val p = ProcessBuilder(f.sh, "-c", script).redirectErrorStream(true).start()
            val out = p.inputStream.readBytes().toString(Charsets.UTF_8)
            return p.waitFor() to out
        }
        val missing = File(f.root, "no-such-folder/.w").path
        val (rc, out) = run("${probe.replace("/data/control/.w", missing)} echo writable; fi; echo went-on")
        assertEquals(out, 0, rc)
        assertEquals("went-on", out.trim())
        // And the trace: a shell that ends before xnuhost starts says with what status and in which step.
        val (rc2, out2) = run(
            "AT=start; at() { AT=\$*; echo \"oneios inner: \$*\"; }; trap 'echo \"oneios inner: ended with status \$? in step: \$AT\"' EXIT; " +
                "at 'checking that /data/control is read-only'; exit 70",
        )
        assertEquals(out2, 70, rc2)
        assertTrue(out2, out2.trim().endsWith("oneios inner: ended with status 70 in step: checking that /data/control is read-only"))
    }

    /** The inner shell says each step before it takes it, and the switch waits for it by its progress. */
    @Test
    fun theInnerShellTracesItselfAndIsWaitedForByItsProgress() {
        val sw = code(switchScript).joinToString("\n")
        val inner = sw.substring(sw.indexOf("    --inner)"), sw.indexOf("    --stop-loop)"))
        assertTrue(inner.contains("trap 'echo \"oneios inner: \$(date +%T) ended with status \$? in step: \$AT\"' EXIT"))
        assertTrue(inner.contains("at() { AT=\$*; echo \"oneios inner: \$(date +%T) \$*\"; }"))
        assertTrue(inner.indexOf("echo \$\$ 2>/dev/null > \"\$CTL/inner.pid\"") in 0 until inner.indexOf("cp \"\$BB\" \"\$CTL/busybox\""))
        // A step line before every command of the setup that can fail or stand still.
        val steps = listOf(
            "at \"copying busybox to \$CTL/busybox\"" to "cp \"\$BB\" \"\$CTL/busybox\"",
            "at \"making the mounts private\"" to "mount --make-rprivate /",
            "at \"binding the stage over /data\"" to "mount --bind \"\$STAGE\" /data",
            "at \"running busybox from the stage\"" to "\"\$BB\" true 2>/dev/null",
            "at \"making /data/\$d read-only\"" to "mount -o remount,bind,ro",
            "at \"checking that /data/control is read-only\"" to "> /data/control/.w",
            "at \"checking that One UI's /data is not visible\"" to "[ ! -e /data/system ]",
            "at \"session folders\"" to "mkdir -p /data/data /data/session/tmp",
            "at \"the session's cgroup\"" to "CG=/sys/fs/cgroup/oneios_session",
        )
        for ((say, cmd) in steps) assertTrue("$say before $cmd", inner.indexOf(say) in 0 until inner.indexOf(cmd))
        // Nothing starts under a switch that gave up meanwhile; the trap stays for a start that fails.
        val exec = inner.indexOf(LAUNCH)
        assertTrue(inner, exec > 0)
        // "running" is no reason to give up: the outer switch writes it as soon as it reads the pid (7129c37).
        val state = inner.indexOf("ST=\$(cat /data/control/state 2>/dev/null)")
        assertTrue(state in 0 until exec)
        assertTrue(inner.indexOf("starting|running) ;;", state) in state until exec)
        assertTrue(inner.indexOf("die_inner \"the switch is no longer starting", state) in state until exec)
        assertFalse(inner.contains("trap - EXIT"))
        // The switch: until the pid is written, for as long as the inner shell runs, 30 s at most.
        val session = sw.substring(sw.indexOf("echo \"=== [4/5]"))
        val wait = session.substring(session.indexOf("unshare -m"), session.indexOf("XP=\$(cat \"\$SESSION/xnuhost.pid\""))
        assertTrue(wait.contains("while [ \$n -lt 150 ] && [ ! -s \"\$SESSION/xnuhost.pid\" ]; do"))
        assertTrue(wait.contains("[ -n \"\$ip\" ] && kill -0 \"\$ip\" 2>/dev/null || break"))
        assertTrue(session.contains("the last lines of \$SESSION/xnuhost.log"))
    }

    /**
     * The inner shell runs xnuhost as its child and waits for it (after the app 0.5.80): its exit code, or the signal that killed
     * it, goes to the log and to session/xnuhost.exit. The phone, 2026-11-23 19:06: xnuhost ended without a line and
     * nothing said how. Run here on the inner shell's own lines, with a stand-in xnuhost that ends each way.
     */
    @Test
    fun theInnerShellWaitsForXnuhostAndRecordsHowItEnded() {
        val sw = code(switchScript).joinToString("\n")
        val inner = sw.substring(sw.indexOf("    --inner)"), sw.indexOf("    --stop-loop)"))
        val block = inner.substring(inner.indexOf("AT=\"running /data/runtime/\$R_XNUHOST\""), inner.indexOf("exit \"\$rc\"") + "exit \"\$rc\"".length)
        // In the foreground (a shell without job control starts a background command with SIGINT and SIGQUIT ignored).
        assertTrue(block, block.contains("$LAUNCH\n") && !block.contains("$LAUNCH &"))
        assertTrue(block.indexOf("rc=\$?") > block.indexOf(LAUNCH))
        val helpers = sw.substring(sw.indexOf("end_record() {"), sw.indexOf("end_of() {"))
        val linux = File("/proc/self/status").isFile
        for (sh in shells) {
            for ((action, record, how) in listOf(
                Triple("exit 4", "exit 4", "exit 4"),
                Triple("exit 0", "exit 0", "exit 0"),
                Triple("kill -KILL \$\$", "signal 9", "killed by signal 9 (SIGKILL)"),
                Triple("kill -SEGV \$\$", "signal 11", "killed by signal 11 (SIGSEGV)"),
                Triple("kill -ABRT \$\$", "signal 6", "killed by signal 6 (SIGABRT)"),
            )) {
                val dir = Files.createTempDirectory("oneios-inner").toFile().also { roots += it }
                val fake = File(dir, "xnuhost").apply {
                    writeText("#!/bin/sh\nulimit -c 0\necho \$\$ > '${dir.path}/own.pid'\n" + (if (linux) "grep SigIgn /proc/self/status > '${dir.path}/ign'\n" else "") + "$action\n")
                    setExecutable(true)
                }
                val script = helpers + "\nR_XNUHOST=xnuhost\nset -- '${fake.path}' --session-abi 1\n" +
                    block.replace("/system/bin/sh", sh).replace("/data/session", dir.path)
                val p = ProcessBuilder(sh, "-c", script).redirectErrorStream(true).start()
                val out = p.inputStream.bufferedReader().readText()
                val rc = p.waitFor()
                val pid = File(dir, "own.pid").readText().trim()
                assertEquals("$sh $action: $out", pid, File(dir, "xnuhost.pid").readText().trim())
                assertEquals("$sh $action: $out", "pid $pid $record\n", File(dir, "xnuhost.exit").readText())
                assertTrue("$sh $action: $out", out.lines().any { Regex("""^oneios inner: \S+ \S+ xnuhost $pid ended: \Q$how\E$""").matches(it) })
                assertEquals("$sh $action: $out", if (record.startsWith("signal ")) 128 + record.substringAfter(' ').toInt() else record.substringAfter(' ').toInt(), rc)
                if (linux) {
                    val ign = File(dir, "ign").readText().substringAfter(':').trim().toLong(16)
                    assertEquals("$sh: SIGINT and SIGQUIT ignored in xnuhost (${File(dir, "ign").readText().trim()})", 0L, ign and 0x6L)
                }
            }
        }
    }

    /** The watcher says how xnuhost ended (the inner shell's record) and what the host saw: dmesg, lmkd, logcat, the memory. */
    @Test
    fun theWatcherSaysHowXnuhostEndedAndWhatTheHostSaw() = each { f ->
        f.phone()
        val d = bootScreen(f, processes = true)
        File(f.session, "xnuhost.exit").writeText("pid $XNUHOST signal 9\n")
        f.file("dmesg").writeText("[86100.0] unrelated: a line of no interest\n[86175.2] Out of memory: Killed process $XNUHOST (xnuhost) total-vm:9000000kB\n")
        f.file("logcat").writeText(
            "11-23 19:06:30.100  1100  1100 I lowmemorykiller: Kill 'xnuhost' ($XNUHOST), uid 0, oom_score_adj 500 to free 5800000kB rss; reason: device is low on swap and thrashing\n" +
                "11-23 19:06:29.900  $XNUHOST  $XNUHOST F scudo   : ERROR: corrupted chunk header\n" +
                "11-23 19:06:20.000  1100  1100 I lowmemorykiller: Kill 'com.example' (77), uid 10100\n",
        )
        f.file("proc/meminfo").writeText("MemTotal: 11350016 kB\nMemAvailable: 1102848 kB\nSwapTotal: 12582912 kB\nSwapFree: 11657216 kB\n")
        f.file("proc/pressure").mkdirs()
        f.file("proc/pressure/memory").writeText("some avg10=40.00 avg60=35.00 avg300=10.00 total=1\nfull avg10=20.00 avg60=15.00 avg300=5.00 total=2\n")
        f.file("sys/fs/cgroup/oneios_session/memory.events").writeText("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n")
        val w = watcher(f)
        f.ends(XNUHOST)
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        assertEquals(f.returnLog, 0, w.exitValue())
        val log = f.returnLog
        assertTrue(log, log.contains("watcher: xnuhost $XNUHOST ended: killed by signal 9 (SIGKILL) (last log lines: "))
        assertTrue(log, log.contains("watcher: after xnuhost's end: kernel: [86175.2] Out of memory: Killed process $XNUHOST (xnuhost)"))
        assertFalse(log, log.contains("a line of no interest"))
        assertTrue(log, log.contains("watcher: after xnuhost's end: lmkd: 11-23 19:06:30.100  1100  1100 I lowmemorykiller: Kill 'xnuhost' ($XNUHOST)"))
        assertFalse(log, log.contains("com.example"))
        assertTrue(log, log.contains("watcher: after xnuhost's end: logcat of pid $XNUHOST: 11-23 19:06:29.900  $XNUHOST  $XNUHOST F scudo   : ERROR: corrupted chunk header"))
        assertTrue(log, log.contains("watcher: after xnuhost's end: host memory now: MemAvailable: 1077 MiB, SwapTotal: 12288 MiB, SwapFree: 11384 MiB; pressure: some avg10=40.00 avg60=35.00 avg300=10.00 total=1 | full avg10=20.00"))
        assertTrue(log, log.contains("watcher: after xnuhost's end: the session cgroup's memory.events: low 0, high 0, max 0, oom 0, oom_kill 0"))
        // The return says the record too (it does on every return that stops xnuhost, where the inner shell wrote one).
        assertTrue(log, log.contains("xnuhost's end, as its inner shell recorded it: pid $XNUHOST signal 9"))
        f.assertInPlace()
        assertEquals("xnuhost ended: killed by signal 9 (SIGKILL)", shown(d))
        // A record of another pid, or not of the form, is not taken.
        val g = Fake(f.sh)
        g.phone()
        File(g.session, "xnuhost.exit").writeText("pid 1 signal 9\n")
        val v = watcher(g)
        g.ends(XNUHOST)
        assertTrue(v.waitFor(60, TimeUnit.SECONDS))
        assertTrue(g.returnLog, g.returnLog.contains("watcher: xnuhost $XNUHOST ended: how is not recorded (last log lines: "))
        assertTrue(g.returnLog, g.returnLog.contains("after xnuhost's end: kernel: no OOM kill and no line of xnuhost or pid $XNUHOST in dmesg"))
        assertTrue(g.returnLog, g.returnLog.contains("after xnuhost's end: lmkd: no kill of xnuhost or pid $XNUHOST in logcat"))
        assertTrue(g.returnLog, g.returnLog.contains("the session cgroup has no memory.events (no memory controller there)"))
        g.assertInPlace()
    }

    /**
     * toybox's tr reads again for ever when a read fails, and a read of /proc/PID/cmdline fails (ESRCH) when the
     * process ended after the open: the return's Gate B stood still there, with a black screen, when the stop loop
     * ended at that moment. No script lets tr read a /proc file itself, and a cmdline that cannot be read is no stall.
     */
    @Test
    fun aCmdlineThatCannotBeReadDoesNotStallTheReturn() = each { f ->
        for (s in listOf(switchScript, returnScript, rootScript, File(Shipped.switcherAssets, "boot_status.sh"))) {
            val bad = code(s).filter { Regex("""\btr\b[^|]*<\s*"?(\${'$'}P|/proc)/""").containsMatchIn(it) }
            assertTrue("${s.name}: tr reads a /proc file: $bad", bad.isEmpty())
        }
        assertTrue(code(returnScript).any { it.contains("case \"\$(cat \"\$P/\$1/cmdline\" 2>/dev/null | tr '\\0' ' ')\" in") })
        f.phone()
        // A tr like toybox's: it never ends when its input cannot be read (here: a folder).
        val real = listOf("/usr/bin/tr", "/bin/tr").first { File(it).canExecute() }
        f.file("bin/tr").apply {
            writeText("#!/bin/sh\nif [ -d /proc/self/fd/0 ]; then n=0; while [ ! -e \"\$ONEIOS_TEST_ROOT/behave/unhang\" ] && [ \$n -lt 300 ]; do sleep 0.1; n=\$((n + 1)); done; exit 1; fi\nexec $real \"\$@\"\n")
            setExecutable(true)
        }
        // The stop loop and a leftover inner shell, each gone between the open and the read of its cmdline.
        for ((pid, file) in listOf(7200 to "stop-loop.pid", 7300 to "inner.pid")) {
            val d = f.proc(pid, "sh")
            File(d, "cmdline").delete()
            File(d, "cmdline").mkdir()
            File(f.control, file).writeText("$pid\n")
        }
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        f.assertInPlace(r.text)
        assertFalse(f.kills.toString(), f.kills.any { it.endsWith(" 7200") || it.endsWith(" 7300") })
    }

    /** An inner shell that is still setting up when the return begins is ended by its pid: it has no stage mount yet. */
    @Test
    fun theReturnEndsAnInnerShellThatIsStillSettingUp() = each { f ->
        f.phone(state = "failed")
        f.proc(7300, "sh", ns = "mnt:[80]", cmdline = "/system/bin/sh ${f.stage}/oneios_switch.sh --inner")
        File(f.control, "inner.pid").writeText("7300\n")
        val r = f.returns()
        assertEquals(r.text, 0, r.exit)
        assertTrue(f.kills.toString(), f.kills.contains("-9 7300"))
        assertFalse(f.file("proc/7300").exists())
        f.assertInPlace(r.text)
    }

    /** A step that stands still is rebooted out of at its own limit (Gate B: 75 s), long before the guard's ten minutes. */
    @Test
    fun aStepThatStandsStillIsRebootedAtItsOwnLimit() = each { f ->
        f.phone()
        f.behave("hang_ctl.restart_$COMPOSER")
        // (The test's clock runs 100 times faster than its commands: its limits are 4 times the phone's.)
        val p = f.start("oneios_return.sh", "manual", env = mapOf("ONEIOS_TEST_STEP_K" to "4"), log = "log/return")
        await("the guard's reboot", 60_000) { f.rebooted == "reboot,oneios-return-guard" }
        assertTrue(p.isAlive)
        val why = "'[3/5] Gate B: One UI's display and services' did not finish within 300s"
        assertTrue(f.outcome, f.outcome.startsWith("failsafe ") && f.outcome.contains(why))
        assertTrue(f.returnLog, f.returnLog.contains("GUARD: $why"))
        assertFalse(f.returnLog, f.returnLog.contains("the return did not finish within"))
        assertFalse(f.setprops.any { it == "ctl.restart netd" || it == "ctl.start zygote" })
        // On the phone: every step has a limit, and all of them together stay under the guard's.
        val ret = code(returnScript).joinToString("\n")
        val limits = Regex("""(?m)^step "\[(\d)/5] [^"]*" (\d+)$""").findAll(ret).map { it.groupValues[1].toInt() to it.groupValues[2].toInt() }.toMap()
        assertEquals(mapOf(1 to 90, 2 to 45, 3 to 75, 4 to 45, 5 to 290), limits)
        assertTrue(limits.values.sum() < 600 && ret.contains("GUARD_MAX=600") && ret.contains("STEP_K=1"))
    }

    // --- Hardware checks: the check runner, with stand-ins for OneiOS's tools ----------

    /** Stages a runtime whose bin/ holds [tools] (shell scripts standing in for OneiOS's phone tools). */
    private fun runtimeWith(f: Fake, tools: Map<String, String>) {
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertOk(f.receive("runtime", "runtime.json", "{}".toByteArray()))
        assertOk(f.receive("runtime", "bin/xnuhost", ELF, "0755"))
        for ((name, body) in tools) assertOk(f.receive("runtime", "bin/$name", "#!/bin/sh\n$body\n".toByteArray(), "0755"))
        assertOk(f.verb(OneiosRoot.Verb.FINISH, listOf("runtime", (tools.size + 2).toString(), "0.1.0", "1", "bin/xnuhost", "1", "0", "none", "none", "none")))
    }

    private fun checkRun(f: Fake, id: String, limit: Int? = null): Pair<Fake.Out, OneiosChecks.Run?> {
        val o = f.verb(OneiosRoot.Verb.CHECK, listOf(id), env = limit?.let { mapOf("ONEIOS_CHECK_LIMIT" to it.toString()) }.orEmpty())
        return o to OneiosChecks.parseRun(id, o.reply.results, o.text.lines())
    }

    /** The script's table of checks is the app's: the same tool, arguments and time limit for every id. */
    @Test
    fun theScriptsChecksAreTheApps() {
        val text = rootScript.readText()
        for (c in OneiosChecks.ALL) {
            val args = c.args.replace("@BIN@", "\$R").replace("@OUT@", "\$CHECKS")
            val line = "        ${c.id}) TOOL=${c.tool} ARGS=\"$args\" LIMIT=${c.limitSeconds} ;;\n"
            assertTrue("oneios_root.sh lacks: $line", text.contains(line))
        }
        assertEquals(OneiosChecks.ALL.size, Regex("""(?m)^        [a-z-]+\) TOOL=""").findAll(text).count())
        // Only these ids reach the launcher, and only the camera checks have a picture.
        assertEquals(emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.CHECK, listOf("gpu")))
        assertEquals(emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.UNCHECK, listOf("levels")))
        assertEquals(emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.CHECKFILE, listOf("camera")))
        assertTrue(OneiosRoot.problems(OneiosRoot.Verb.CHECK, listOf("reboot")).isNotEmpty())
        assertTrue(OneiosRoot.problems(OneiosRoot.Verb.CHECK, listOf("gpu", "-v")).isNotEmpty())
        assertTrue(OneiosRoot.problems(OneiosRoot.Verb.CHECK, emptyList()).isNotEmpty())
        assertTrue(OneiosRoot.problems(OneiosRoot.Verb.CHECKFILE, listOf("gpu")).isNotEmpty())
    }

    /** The checks never stop or start anything of One UI's, never start a session, and write outside the stage only to put back. */
    @Test
    fun theChecksLeaveOneUiAlone() {
        val lines = code(rootScript)
        val from = lines.indexOfFirst { it.startsWith("CHECKS=") }
        val to = lines.indexOfFirst { it.contains("refuse \"not root\"") }
        assertTrue(from in 1 until to)
        val checks = lines.subList(from, to).joinToString("\n") { it.replace(Regex(""" # .*$"""), "") }
        for (never in listOf("setprop", "ctl.stop", "ctl.start", "ctl.restart", "zygote", "oneios_switch.sh", "oneios_return.sh", "nsenter", "mount", "reboot",
            "am ", "svc ", "settings put", "/data/data", "/sdcard", "rm -rf", "rm -r")) {
            assertFalse("the checks have '$never'", checks.contains(never))
        }
        // Every write goes under the checks folder, except the two put-back writes.
        val writes = Regex("""(?<![0-9&])>>?\s*("?[^\s;&|)]+)""").findAll(checks).map { it.groupValues[1].trim('"') }
            .filterNot { it.isEmpty() || it == "/dev/null" || it.startsWith("&") }.toSet()
        assertEquals(setOf("\$CHECKS/saved.backlight", "\$CHECKS/saved.als", "\$n", "\$log", "\$CHECKS/timeout"), writes)
        assertTrue(checks.contains("n=\"\$T/sys/class/backlight/\$name/brightness\"") && checks.contains("n=\"\$T/sys/class/input/\$name/device/enable\""))
        // Only processes of the runtime's own bin/, or the display test's layer, are ever ended by name.
        for (kill in Regex("""pkill [^\n;]*""").findAll(checks).map { it.value }) {
            assertTrue(kill, kill.contains("\"\$STAGE/runtime/bin/") || kill.contains("OneiOSDisplay"))
        }
        assertTrue(checks.contains("session_open && refuse \"an iOS session is running: the hardware checks only run beside One UI\""))
    }

    @Test
    fun aCheckRunsTheStagedToolAndReportsItsOutputAndExitCode() = each { f ->
        // No stage, then no runtime: refused, nothing run.
        assertRefused(f.verb(OneiosRoot.Verb.CHECK, listOf("gpu")), "not in the stage")
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        assertRefused(f.verb(OneiosRoot.Verb.CHECK, listOf("gpu")), "no OneiOS runtime is staged")
        runtimeWith(
            f,
            mapOf(
                "gpuctl" to "echo \"/dev/kgsl-3d0 opens\"; echo \"args:\$*:\"; echo \"tmp:\$TMPDIR\"; echo to-stderr >&2; echo ok",
                "bridgectl" to "echo \"args:\$*:\"; if [ \"\$1\" = bt ]; then echo 'the HAL did not become ready (state -1)'; echo failed; exit 1; fi; echo ok",
                "camctl" to "o=; while [ \$# -gt 0 ]; do [ \"\$1\" = --out ] && o=\$2; shift; done; " +
                    "echo 'frames: 90 read, 0 missed by the reader; first frame 400 ms after the start'; printf '\\211PNG\\r\\n\\032\\n-picture' > \"\$o\"; echo \"wrote \$o\"",
            ),
        )
        val (o, run) = checkRun(f, "gpu")
        assertOk(o)
        assertEquals(0, run!!.exit)
        assertEquals(listOf("/dev/kgsl-3d0 opens", "args::", "tmp:${f.stage.path}/checks", "to-stderr", "ok"), run.output)
        assertEquals(OneiosCheckOutcome.PASS, OneiosChecks.classify(OneiosChecks.byId("gpu")!!, run).outcome)
        // The arguments are the table's, with the stage's folders in them.
        assertEquals("args:audio ${f.stage.path}/runtime/bin/oneios-audio:", checkRun(f, "audio").second!!.output.first())
        assertEquals("args:haptic 200 1000:", checkRun(f, "haptic").second!!.output.first())
        // A failing tool: its exit code and its lines.
        val bt = checkRun(f, "bt").second!!
        assertEquals(1, bt.exit)
        val verdict = OneiosChecks.classify(OneiosChecks.byId("bt")!!, bt)
        assertEquals(OneiosCheckOutcome.FAIL, verdict.outcome)
        assertEquals("failed: the HAL did not become ready (state -1)", verdict.line)
        // A tool the runtime does not have is reported, not an error.
        val (d, missing) = checkRun(f, "display")
        assertOk(d)
        assertEquals("displayctl", missing!!.missing)
        assertEquals(OneiosCheckOutcome.SKIPPED, OneiosChecks.classify(OneiosChecks.byId("display")!!, missing).outcome)
        // The camera's picture comes back whole, and only a camera check has one.
        assertRefused(f.verb(OneiosRoot.Verb.CHECKFILE, listOf("camera")), "left no picture")
        assertEquals(OneiosCheckOutcome.PASS, OneiosChecks.classify(OneiosChecks.byId("camera")!!, checkRun(f, "camera").second!!).outcome)
        val file = f.verb(OneiosRoot.Verb.CHECKFILE, listOf("camera"))
        assertOk(file)
        val png = File(f.stage, "checks/camera.png").readBytes()
        assertEquals("file camera ${png.size} ${Hashes.sha256(png)}", file.reply.results.single())
        val sent = java.util.Base64.getMimeDecoder().decode(file.text.lines().filter { it.startsWith("| ") }.joinToString("") { it.removePrefix("| ") })
        assertTrue(sent.contentEquals(png))
        // A tool that is not the file root hashed at staging is not run.
        File(f.stage, "runtime/bin/gpuctl").appendText("echo changed\n")
        assertRefused(f.verb(OneiosRoot.Verb.CHECK, listOf("gpu")), "is not the file that was staged")
        // Never during a session.
        File(f.stage, "control").mkdirs()
        File(f.stage, "control/boot").writeText("boot-1\n")
        File(f.stage, "control/state").writeText("running\n")
        assertRefused(f.verb(OneiosRoot.Verb.CHECK, listOf("audio")), "an iOS session is running")
        assertRefused(f.verb(OneiosRoot.Verb.UNCHECK, listOf("audio")), "an iOS session is running")
    }

    @Test
    fun aHungToolIsEndedAtTheLimitAndWhatItChangedIsPutBack() = each { f ->
        val backlight = f.file("sys/class/backlight/panel/brightness").also { it.parentFile.mkdirs(); it.writeText("97\n") }
        val enable = f.file("sys/class/input/event9/device/enable").also { it.parentFile.mkdirs(); it.writeText("0\n") }
        f.file("sys/class/input/event9/device/name").writeText("als_rear\n")
        f.file("sys/class/input/event3/device").mkdirs()
        f.file("sys/class/input/event3/device/name").writeText("gpio-keys\n")
        val sys = f.root.path + "/sys/class"
        runtimeWith(
            f,
            mapOf(
                // Dims the panel, turns the sensor on, then hangs: one that ends on SIGTERM, one that ignores it.
                "brightctl" to "echo 3 > $sys/backlight/panel/brightness; echo 1 > $sys/input/event9/device/enable; echo 'slider   5% -> wanted 3, the node was written 3'; " +
                    "if [ \"\$1\" = als ]; then trap '' TERM; fi; while :; do sleep 0.2; done",
                "bridgectl" to "echo started; while :; do sleep 0.2; done",
                "gpuctl" to "echo ok",
            ),
        )
        val t0 = System.currentTimeMillis()
        val (o, run) = checkRun(f, "levels", limit = 1)
        assertOk(o)
        assertEquals(1, run!!.timeoutSeconds)
        assertTrue("took ${System.currentTimeMillis() - t0} ms", System.currentTimeMillis() - t0 < 10_000)
        assertEquals(listOf("slider   5% -> wanted 3, the node was written 3"), run.output)
        assertEquals("97", backlight.readText().trim())
        assertEquals("0", enable.readText().trim())
        assertTrue(o.reply.infos.toString(), o.reply.infos.containsAll(listOf("put back: backlight panel 97", "put back: light sensor event9 enable 0")))
        val verdict = OneiosChecks.classify(OneiosChecks.byId("levels")!!, run)
        assertEquals(OneiosCheckOutcome.FAIL, verdict.outcome)
        assertTrue(verdict.line, verdict.line.startsWith("Ended after 1 s"))
        // A tool that ignores SIGTERM is killed 2 s later; the sensor goes back, the backlight is not this check's to write.
        backlight.writeText("97\n")
        val (o2, run2) = checkRun(f, "als", limit = 1)
        assertOk(o2)
        assertEquals(1, run2!!.timeoutSeconds)
        assertEquals("0", enable.readText().trim())
        assertEquals("3", backlight.readText().trim())
        // A check with nothing to put back is ended the same way, and the next check runs.
        assertEquals(1, checkRun(f, "haptic", limit = 1).second!!.timeoutSeconds)
        assertEquals(0, checkRun(f, "gpu", limit = 1).second!!.exit)
        // Without the test root's override the limit is the table's (the fake root is the only place it can be set).
        assertTrue(rootScript.readText().contains("if [ -n \"\$T\" ] && is_dec \"\${ONEIOS_CHECK_LIMIT:-x}\"; then limit=\$ONEIOS_CHECK_LIMIT; fi"))
    }

    /** The app ends a root command that never answers, then asks for the put-back step alone. */
    @Test
    fun thePutBackStepRunsAgainByItself() = each { f ->
        val backlight = f.file("sys/class/backlight/panel/brightness").also { it.parentFile.mkdirs(); it.writeText("120\n") }
        assertRefused(f.verb(OneiosRoot.Verb.UNCHECK, listOf("levels")), "not in the stage")
        runtimeWith(f, mapOf("brightctl" to "echo ok"))
        assertEquals("uncheck nothing", f.verb(OneiosRoot.Verb.UNCHECK, listOf("levels")).reply.ok)
        // As a killed check leaves it: the value read before the tool ran, the panel at the tool's last level,
        // the display test's socket folder.
        val checks = File(f.stage, "checks").also { it.mkdirs() }
        File(checks, "saved.backlight").writeText("panel 120\n../../etc 5\npanel x\n")
        File(checks, "saved.als").writeText("event9 7\n")
        File(checks, "displayctl.Ab12Cd").mkdirs()
        File(checks, "displayctl.Ab12Cd/display.sock").writeText("")
        backlight.writeText("1\n")
        val o = f.verb(OneiosRoot.Verb.UNCHECK, listOf("levels"))
        assertOk(o)
        assertEquals("120", backlight.readText().trim())
        assertEquals(listOf("put back: backlight panel 120"), o.reply.infos)
        assertFalse(File(checks, "displayctl.Ab12Cd").exists())
        // Once: a second call has nothing saved and writes nothing.
        backlight.writeText("44\n")
        assertOk(f.verb(OneiosRoot.Verb.UNCHECK, listOf("levels")))
        assertEquals("44", backlight.readText().trim())
    }

    // --- Session logs: the two read-only verbs ------------------------------------------

    private fun logList(f: Fake): OneiosLogs.Listing {
        val o = f.verb(OneiosRoot.Verb.LOGS)
        assertOk(o)
        assertEquals("logs", o.reply.ok)
        return OneiosLogs.parseList(o.reply.results, o.text.lines())
    }

    private fun logChunk(f: Fake, id: String, end: Long = 0, bytes: Int = OneiosLogs.CHUNK_MAX): OneiosLogs.Chunk {
        val o = f.verb(OneiosRoot.Verb.LOGFILE, listOf(id, end.toString(), bytes.toString()))
        assertOk(o)
        return OneiosLogs.parseChunk(id, o.reply.results, o.text.lines())!!
    }

    /** The script run by itself, past the launcher: for the arguments the launcher never carries. */
    private fun direct(f: Fake, vararg args: String): Fake.Out {
        val pb = ProcessBuilder(f.sh, File(f.stage, "bin/oneios_root.sh").path, *args).redirectErrorStream(true)
        pb.environment()["ONEIOS_TEST_ROOT"] = f.root.path
        HostTools.into(pb.environment())   // the stand-ins (macOS: gnu-stat.sh), as the launcher's runs have
        val p = pb.start()
        p.outputStream.close()
        val text = p.inputStream.readBytes().toString(Charsets.UTF_8)
        return f.Out(p.waitFor(), text)
    }

    /** Every file under the stage: its kind, size, time and mode. */
    private fun snapshot(f: Fake): Map<String, String> = f.stage.walkTopDown().associate { file ->
        val a = Files.readAttributes(file.toPath(), "unix:mode,size,lastModifiedTime,nlink", java.nio.file.LinkOption.NOFOLLOW_LINKS)
        file.relativeTo(f.stage).path to "${a["mode"]} ${if (file.isDirectory) 0 else a["size"]} ${a["lastModifiedTime"]} ${a["nlink"]}"
    }

    private fun xnuhostLog(lines: Int, exit: Int) = buildString {
        append("[     5.000] xnuhost I xnuhost: session ABI 1, mode takeover, pid 5000\n")
        append("[     5.100] xnuhost I cpu0: entering the kernel at 0x2003dcc488\n")
        append("[     5.200] guest     Darwin Kernel Version 25.5.0: Wed Nov 11 04:04:41 IST 2026; akshay:ios-obj/DEVELOPMENT_ARM64_BCM2837\n")
        for (i in 1..lines) append("[%6d.%03d] guest     line %d of the kernel's console: %s\n".format(5 + i / 1000, i % 1000, i, "x".repeat(i % 97)))
        append("[   900.000] guest     panic(cpu 1 caller 0xfffffff00ad8d2c4): Console I/O from interrupt-disabled context @serial_console.c:175\n")
        append("[   900.100] xnuhost I stopping: the guest halted on cpu1 (reason 2, code 0)\n")
        append("[   900.200] xnuhost I exit $exit\n")
    }

    @Test
    fun theLogVerbsListTheSessionLogsAndReadThemInWholeLines() = each { f ->
        assertRefused(f.verb(OneiosRoot.Verb.LOGS), "not in the stage")
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        // A stage no session ran in: nothing to list, and no log to read.
        assertEquals(emptyList<String>(), logList(f).files.map { it.id })
        assertRefused(f.verb(OneiosRoot.Verb.LOGFILE, listOf("session", "0", "1000")), "no such log")

        for (d in listOf("session", "logs", "control")) File(f.stage, d).mkdirs()
        val session = xnuhostLog(6000, 4)
        File(f.stage, "session/xnuhost.log").writeText(session)
        // Seven earlier logs: the five newest are listed.
        for (i in 1..7) File(f.stage, "logs/xnuhost-170000000$i.log").writeText(xnuhostLog(i, 0))
        File(f.stage, "logs/notes.txt").writeText("not a log\n")
        File(f.stage, "switch.log").writeText("=== OneOS app switch 2026-11-11 10:00:00 epoch 1794300000 versionCode 100 ===\n=== ONEIOS SESSION LAUNCHED ===\n")
        // No line break at its end, a line longer than a list row, and bytes that are no UTF-8.
        File(f.stage, "return.log").writeBytes("10:15:02 === Return to One UI (app), session state 'running', boot b ===\n".toByteArray() +
            ("y".repeat(900) + "\n").toByteArray() + byteArrayOf(0xff.toByte(), 0xfe.toByte(), '\n'.code.toByte()) + "10:15:40 One UI restored in place (Enforcing).".toByteArray())
        File(f.stage, "control/display.log").writeText("oneios-display: connected\n")
        val before = snapshot(f)

        val list = logList(f)
        assertFalse(list.sessionOpen)
        assertEquals(listOf("session") + (7 downTo 3).map { "xnuhost-170000000$it" } + listOf("switch", "return", "display"), list.files.map { it.id })
        val row = list.files.first()
        assertEquals(session.length.toLong(), row.bytes)
        assertEquals(File(f.stage, "session/xnuhost.log").lastModified() / 1000, row.modified)
        // Its last 40 lines, whole: the end of the session is read from them.
        assertEquals(session.lines().dropLast(1).takeLast(40), row.tail)
        assertEquals("exit 4 · kernel panic", OneiosLogs.endLine(row.tail))
        assertEquals("exit 0 · kernel panic", OneiosLogs.endLine(list.files[1].tail))
        val ret = list.files.first { it.id == "return" }
        assertEquals(4, ret.tail.size)
        assertEquals(400, ret.tail[1].length)
        assertEquals("10:15:40 One UI restored in place (Enforcing).", ret.tail.last())

        // The end first, then earlier chunks, each of whole lines, each ending where the one after it starts.
        val parts = ArrayList<List<String>>()
        var end = 0L
        for (n in 0 until 200) {
            val c = logChunk(f, "session", end, 65_536)
            assertEquals(session.length.toLong(), c.size)
            if (end != 0L) assertEquals(end, c.end)
            assertTrue(c.end - c.start in 1..65_536)
            parts += c.lines
            end = c.start
            if (c.first) break
        }
        assertTrue(parts.size in 5..20)
        assertEquals(session.lines().dropLast(1), parts.reversed().flatten())
        assertTrue(parts.first().last() == "[   900.200] xnuhost I exit 4")
        val whole = OneiosLogs.summarize(parts.reversed().flatten())
        assertEquals(OneiosEndKind.PANIC, whole.end.kind)
        assertEquals(6006, whole.lines)

        // A small log is one chunk; a last line with no line break still ends before root's own answer.
        val small = logChunk(f, "return")
        assertTrue(small.first)
        assertEquals(4, small.lines.size)
        assertEquals(900, small.lines[1].length)
        assertEquals("10:15:40 One UI restored in place (Enforcing).", small.lines.last())
        assertEquals(listOf("oneios-display: connected"), logChunk(f, "display").lines)
        assertEquals(xnuhostLog(7, 0).lines().dropLast(1), logChunk(f, "xnuhost-1700000007").lines)
        // An end past the file is the file's end; an older log that is not there is refused.
        assertEquals(small.lines, logChunk(f, "return", 999_999).lines)
        assertRefused(f.verb(OneiosRoot.Verb.LOGFILE, listOf("xnuhost-1600000000", "0", "1000")), "no such log")
        assertRefused(f.verb(OneiosRoot.Verb.LOGFILE, listOf("feeder", "0", "1000")), "no such log")

        // Nothing in the stage was made, changed, moved or touched.
        assertEquals(before, snapshot(f))
    }

    @Test
    fun theLogVerbsTakeOnlyTheirOwnIdsAndAtMostOneMebibyte() = each { f ->
        fun bad(vararg args: String) = assertTrue(args.toList().toString(), OneiosRoot.problems(OneiosRoot.Verb.LOGFILE, args.toList()).isNotEmpty())
        assertEquals(emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.LOGS, emptyList()))
        assertEquals(emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.LOGFILE, listOf("session", "0", "1048576")))
        assertEquals(emptyList<String>(), OneiosRoot.problems(OneiosRoot.Verb.LOGFILE, listOf("xnuhost-1794300000", "4096", "1")))
        assertTrue(OneiosRoot.problems(OneiosRoot.Verb.LOGS, listOf("session")).isNotEmpty())
        bad("session", "0", "1048577"); bad("session", "0", "0"); bad("session", "-1", "10"); bad("session", "0")
        bad("xnuhost.log", "0", "10"); bad("../switch", "0", "10"); bad("control/state", "0", "10"); bad("checks", "0", "10"); bad("xnuhost-1a", "0", "10")
        // The script refuses the same by itself.
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        File(f.stage, "session").mkdirs()
        File(f.stage, "session/xnuhost.log").writeText("a\n")
        File(f.stage, "runtime.conf").writeText("version=0.1.0\n")
        for (args in listOf(
            listOf("logfile", "session", "0", "1048577"), listOf("logfile", "session", "0", "0"), listOf("logfile", "session", "x", "10"),
            listOf("logfile", "runtime.conf", "0", "10"), listOf("logfile", "../session/xnuhost", "0", "10"), listOf("logfile", "xnuhost-", "0", "10"),
            listOf("logfile", "xnuhost-1/../../runtime.conf", "0", "10"), listOf("logfile", "session"), listOf("logs", "session"),
        )) {
            val o = direct(f, *args.toTypedArray())
            assertEquals(args.toString() + o.text, 3, o.exit)
            assertTrue(o.text, o.reply.refused != null && !o.text.contains("version="))
        }
        assertEquals(listOf("a"), OneiosLogs.parseChunk("session", direct(f, "logfile", "session", "0", "1048576").let { it.reply.results }, listOf("| a"))!!.lines)
    }

    /** session/ is the guest's to write: a link left there, or a second name for a file, is never read. */
    @Test
    fun aLinkInPlaceOfALogIsNotRead() = each { f ->
        assertOk(f.verb(OneiosRoot.Verb.BEGIN, listOf("runtime")))
        val secret = File(f.root, "data/system-secret").apply { writeText("ONE-UI-SECRET\n") }
        for (d in listOf("session", "logs")) File(f.stage, d).mkdirs()
        Files.createSymbolicLink(File(f.stage, "session/xnuhost.log").toPath(), secret.toPath())
        Files.createLink(File(f.stage, "logs/xnuhost-1700000001.log").toPath(), secret.toPath())
        Files.createSymbolicLink(File(f.stage, "control").toPath(), File(f.root, "data").toPath())
        File(f.root, "data/display.log").writeText("ONE-UI-SECRET\n")
        val o = f.verb(OneiosRoot.Verb.LOGS)
        assertOk(o)
        assertFalse(o.text, o.text.contains("ONE-UI-SECRET"))
        assertEquals(emptyList<String>(), OneiosLogs.parseList(o.reply.results, o.text.lines()).files.map { it.id })
        for (id in listOf("session", "xnuhost-1700000001", "display")) {
            val c = f.verb(OneiosRoot.Verb.LOGFILE, listOf(id, "0", "1000"))
            assertRefused(c, "no such log")
            assertFalse(c.text, c.text.contains("ONE-UI-SECRET"))
        }
        // logs/ itself as a link: nothing of where it points is listed.
        File(f.stage, "logs").deleteRecursively()
        File(f.root, "data/elsewhere").mkdirs()
        File(f.root, "data/elsewhere/xnuhost-1700000002.log").writeText("ONE-UI-SECRET\n")
        Files.createSymbolicLink(File(f.stage, "logs").toPath(), File(f.root, "data/elsewhere").toPath())
        assertFalse(f.verb(OneiosRoot.Verb.LOGS).text.contains("xnuhost-1700000002"))
        assertRefused(f.verb(OneiosRoot.Verb.LOGFILE, listOf("xnuhost-1700000002", "0", "1000")), "no such log")
    }

    /** The two verbs write nothing: no redirection but to /dev/null, and no command that makes, changes or removes a file. */
    @Test
    fun theLogVerbsOnlyRead() {
        val lines = code(rootScript)
        val from = lines.indexOfFirst { it.startsWith("LOG_CHUNK_MAX=") }
        val to = lines.indexOfFirst { it.contains("refuse \"not root\"") }
        assertTrue(from in 1 until to)
        val logs = lines.subList(from, to).joinToString("\n") { it.replace(Regex(""" # .*$"""), "") }
        assertTrue(logs.contains("do_logs()") && logs.contains("do_logfile()"))
        val writes = Regex("""(?<![0-9&])>>?\s*("?[^\s;&|)]+)""").findAll(logs).map { it.groupValues[1].trim('"') }
            .filterNot { it.isEmpty() || it == "/dev/null" || it.startsWith("&") }.toSet()
        assertEquals(emptySet<String>(), writes)
        assertFalse(Regex("""[^2]>\s*/dev/null""").containsMatchIn(logs.replace("2>/dev/null", "")))
        val words = Regex("""[A-Za-z_][A-Za-z0-9_.-]*""").findAll(logs).map { it.value }.toSet()
        for (never in listOf("rm", "mv", "cp", "mkdir", "rmdir", "unlink", "touch", "chmod", "chown", "tee", "dd", "truncate", "ln", "setprop", "kill", "pkill",
            "nsenter", "sh", "eval", "exec", "own", "take", "base64")) {
            assertFalse("the log verbs use '$never'", never in words)
        }
        // A time limit on every read of a file, one mebibyte a call, and the plain-file test before each.
        assertEquals(Regex("""tail -c""").findAll(logs).count(), Regex("""timeout "\${'$'}LOG_READ_LIMIT" tail -c""").findAll(logs).count())
        assertTrue(logs.contains("LOG_CHUNK_MAX=${OneiosLogs.CHUNK_MAX}\n"))
        assertTrue(logs.contains("log_plain \"\$F\" || return 0") && logs.contains("log_plain \"\$F\" || refuse"))
        assertTrue(logs.contains("for id in switch return display feeder; do"))
        assertEquals(OneiosLogs.OTHERS, listOf("switch", "return", "display", "feeder"))
        // The app's paths are the script's.
        val text = rootScript.readText()
        for (id in listOf("session") + OneiosLogs.OTHERS) assertTrue(id, text.contains("        $id) F=\"\$STAGE/${OneiosLogs.path(id)}\" ;;\n"))
        assertTrue(text.contains("F=\"\$STAGE/logs/\$1.log\" ;;"))
        assertEquals("logs/xnuhost-17.log", OneiosLogs.path("xnuhost-17"))
        // And the switch keeps its logs where they are read: this session's, and the five before.
        val sw = switchScript.readText()
        assertTrue(sw.contains("mv -f \"\$SESSION/xnuhost.log\" \"\$STAGE/logs/xnuhost-\$(date +%s).log\""))
        assertTrue(sw.contains("ls -1t \"\$STAGE/logs\"/xnuhost-*.log 2>/dev/null | tail -n +6"))
        assertTrue(sw.contains(">>\"\$SESSION/xnuhost.log\" 2>&1 &") && sw.contains(">>\"\$CTL/display.log\" 2>&1 &") && sw.contains("L=\"\$CTL/watchdog_feeder.log\""))
        assertTrue(text.contains(">>\"\$STAGE/switch.log\"") && text.contains(">>\"\$STAGE/return.log\""))
    }

    /**
     * The session's namespace binds the stage over /data, which hides the root manager's busybox (/data/adb): every
     * busybox call after the bind is the copy in the control folder (phone run of 0.4.77: "busybox: inaccessible or
     * not found", then "could not make /data/runtime read-only").
     */
    @Test
    fun theSessionsNamespaceRunsBusyboxFromTheStageAfterTheBind() {
        val sw = switchScript.readText()
        val inner = sw.substringAfter("    --inner)\n").substringBefore("\n        ;;\n")
        val bind = inner.indexOf("\"\$BB\" mount --bind \"\$STAGE\" /data")
        val copy = inner.indexOf("cp \"\$BB\" \"\$CTL/busybox\"")
        val switchTo = inner.indexOf("BB=/data/control/busybox")
        assertTrue("bind $bind, copy $copy, switch $switchTo", bind > 0 && copy in 0 until bind && switchTo > bind)
        // The bind's own line runs the host's busybox (still visible then); nothing between it and the switch may.
        val between = inner.substring(inner.indexOf('\n', bind) + 1, switchTo)
        assertFalse("busybox from /data/adb after the bind: $between", between.contains("\"\$BB\""))
    }

    /** What the return and the watcher write to return.log is what the summary's "Return:" reads. */
    @Test
    fun theReturnsLogSaysWhoReturnedAndHow() = each { f ->
        f.phone()
        File(f.session, "ready").createNewFile()
        val w = watcher(f)
        File(f.session, "return.request").writeText("keys: Volume Up + Volume Down down for 3 s at 2026-11-11 10:15:01\n")
        assertTrue(w.waitFor(60, TimeUnit.SECONDS))
        f.assertInPlace()
        val notes = OneiosLogs.returns(f.returnLog.lines())
        assertEquals(f.returnLog, 1, notes.size)
        val n = notes.single()
        assertEquals("watcher", n.who)
        assertTrue(n.keys)
        assertEquals("return asked (keys: Volume Up + Volume Down down for 3 s at 2026-11-11 10:15:01)", n.why)
        assertEquals("One UI restored in place (Enforcing).", n.result)
        assertTrue(Regex("""\d{4}-\d\d-\d\d""").matches(n.date!!))
        // Read through root, as the app does.
        val chunk = logChunk(f, "return")
        assertEquals(notes, OneiosLogs.returns(chunk.lines))
        // A return asked again with nothing open does nothing, and is not counted as a return.
        val again = f.returns("app")
        assertEquals(again.text, 0, again.exit)
        assertTrue(f.returnLog, f.returnLog.contains("=== Return to One UI (app), session state 'returned'"))
        assertEquals(notes, OneiosLogs.returns(f.returnLog.lines()))
    }

    private companion object {
        const val XNUHOST = 5000
        const val INIT_NS = "mnt:[1]"
        const val GUEST_NS = "mnt:[77]"
        const val COMPOSER = "vendor.qti.hardware.display.composer"
        const val TOKEN = "4242.1700000000"

        /** The inner shell's start of xnuhost: a shell that writes its pid and execs xnuhost, waited for (after the app 0.5.80). */
        const val LAUNCH = "/system/bin/sh -c 'echo \$\$ > /data/session/xnuhost.pid || exit 70; exec \"\$@\"' xnuhost \"\$@\""

        /** The S24 Ultra's USB controller (sys.usb.controller): a UDC name, as a guess until the phone's lines come. */
        const val UDC = "a600000.dwc3"

        /** A 64-byte arm64 ELF header: "\u007fELF", 64-bit, e_machine 0xb7. */
        val ELF: ByteArray = ByteArray(64).also {
            byteArrayOf(0x7f, 'E'.code.toByte(), 'L'.code.toByte(), 'F'.code.toByte(), 2, 1, 1).copyInto(it)
            it[16] = 2
            it[18] = 0xb7.toByte()
        }
    }
}
