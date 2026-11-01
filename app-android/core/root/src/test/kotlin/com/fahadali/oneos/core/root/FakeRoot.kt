package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import java.io.File
import java.nio.file.Files
import java.util.concurrent.TimeUnit

/** Where the shipped files are (system properties set by core/root/build.gradle.kts). */
object Shipped {
    /** Both editions' assets (the probe runner and list). */
    val appAssets = File(System.getProperty("oneos.appAssets") ?: "../../app/src/main/assets")

    /** OneOS's (full edition) own: the root script, the stage, installd and log lists. */
    val fullAssets = File(System.getProperty("oneos.fullAssets") ?: "../../app/src/full/assets")

    /** app/src: main, full and probe source sets. */
    val appSources = File(System.getProperty("oneos.appSources") ?: "../../app/src")
    val switcherAssets = File(System.getProperty("oneos.switcherAssets") ?: "../../../switcher/assets")
    val installdFixture = File(System.getProperty("oneos.installdFixture") ?: "../../../switcher/patches/host_installd.txt")
    val runLogs = File(System.getProperty("oneos.runLogs") ?: "../../../out/logs")

    val rootScript: File get() = File(fullAssets, RootScript.ASSET)
    val rootScriptText: String by lazy { rootScript.readText() }
}

/**
 * A shell to run the root script under: dash, busybox ash with busybox's own
 * applets first on PATH, and mksh (Android's /system/bin/sh) when there is one,
 * installed or named by ONEOS_TEST_MKSH.
 */
data class TestShell(val name: String, val path: String, val appletsFirst: Boolean) {
    companion object {
        fun available(): List<TestShell> {
            val out = mutableListOf<TestShell>()
            listOf("/usr/bin/dash", "/bin/dash").firstOrNull { File(it).canExecute() }?.let { out += TestShell("dash", it, false) }
            listOf("/usr/bin/busybox", "/bin/busybox").firstOrNull { File(it).canExecute() }?.let { out += TestShell("busybox ash", it, true) }
            listOfNotNull(System.getenv("ONEOS_TEST_MKSH"), "/usr/bin/mksh", "/bin/mksh").firstOrNull { File(it).canExecute() }
                ?.let { out += TestShell("mksh", it, false) }
            return out
        }
    }
}

/**
 * A fake root folder for the root script (ONEOS_TEST_ROOT): stage, /proc
 * mount tables, boot id, battery, a framework jar, the root manager's tools
 * and stubs for getprop, pm and getevent. The script and the launcher see
 * only this folder; launch refuses under it after its checks.
 */
class FakeRoot(
    val shell: TestShell,
    /** The root script the launcher runs and pins: the shipped one, or a test's patched copy with its own pin. */
    val script: ByteArray = Shipped.rootScript.readBytes(),
) : AutoCloseable {
    val root: File = Files.createTempDirectory("oneos-fakeroot").toFile()
    val stage = File(root, "data/local/tmp/oneos")

    /** The stage's path up to 0.3.6, which the script renames to [stage]. */
    val legacy = File(root, "data/local/tmp/lineage_stage")
    private val stubs = File(root, "stubs")
    private val applets = File(root, "applets")
    private val propsFile = File(root, "props")
    val uid: String = exec(listOf("id", "-u")).trim()
    private val gid: String = exec(listOf("id", "-g")).trim()
    val layout: RootScript.Layout
    val env = linkedMapOf<String, String>()
    val props = linkedMapOf(
        "ro.build.fingerprint" to "samsung/m3qxxx/m3q:17/BP4A.251205.006/S948BXXU1AZJ1:user/release-keys",
        "ro.product.model" to "SM-S948B",
        "ro.product.device" to "m3q",
        "ro.soc.model" to "SM8850",
        "ro.build.version.sdk" to "37",
    )
    val frameworkJar = File(root, "system/framework/framework.jar")

    init {
        File(root, "data/local/tmp").mkdirs()
        File(root, "proc/1").mkdirs()
        File(root, "proc/self").mkdirs()
        mountinfo(emptyList())
        File(root, "proc/sys/kernel/random").mkdirs()
        File(root, "proc/sys/kernel/random/boot_id").writeText("11111111-2222-3333-4444-555555555555\n")
        battery("80", "Discharging", "300")
        File(root, "sys/block/loop0/loop").mkdirs()
        frameworkJar.parentFile.mkdirs()
        frameworkJar.writeBytes(ByteArray(4096) { (it * 7).toByte() })
        stubs.mkdirs()
        // Fake-device capacity must not depend on the developer machine's disk.
        // All actual file identity/mode checks still use the real stat implementation.
        val stat = exec(listOf("sh", "-c", "command -v stat")).trim()
        stub("stat", """
            if [ "${'$'}1" = -f ] && [ "${'$'}2" = -c ] && [ "${'$'}3" = '%a %S' ]; then
                echo '8388608 4096'
            else
                exec '$stat' "${'$'}@"
            fi
        """)
        stub("getprop", """
            [ -n "${'$'}1" ] || exit 0
            sed -n "s|^${'$'}1=||p" "${'$'}ONEOS_TEST_ROOT/props" | head -n 1
        """)
        stub("pm", """
            [ "${'$'}1" = path ] || exit 1
            case "${'$'}2" in
              android) echo "package:/system/framework/framework-res.apk" ;;
              com.wewaffles.onelineage) [ -f "${'$'}ONEOS_TEST_ROOT/old_switcher" ] && echo "package:/data/app/x/base.apk" ;;
            esac
            exit 0
        """)
        stub("getevent", """
            echo "add device 1: /dev/input/event2"
            echo "  name:     \"gpio_keys\""
            [ -f "${'$'}ONEOS_TEST_ROOT/no_keys" ] && exit 0
            echo "    KEY (0001): KEY_VOLUMEDOWN KEY_VOLUMEUP KEY_POWER"
        """)
        val ksu = File(root, "data/adb/ksu/bin").apply { mkdirs() }
        // The root manager's busybox: --list and nsenter (runs the command in "init's namespace", here: as is).
        File(ksu, "busybox").apply {
            writeText(
                "#!/bin/sh\ncase \"$1\" in\n  --list) printf '%s\\n' sh nsenter setsid mount losetup ;;\n" +
                    "  nsenter) shift; while [ \"$1\" != \"--\" ]; do shift; done; shift\n" +
                    "    [ \"$1\" = /system/bin/sh ] && { shift; exec sh \"$@\"; }; exec \"$@\" ;;\n  *) exit 1 ;;\nesac\n",
            )
            setExecutable(true)
        }
        File(ksu, "resetprop").apply {
            writeText("#!/bin/sh\nexit 0\n")
            setExecutable(true)
        }
        if (shell.appletsFirst) {
            applets.mkdirs()
            for (a in APPLETS) Files.createSymbolicLink(File(applets, a).toPath(), File(shell.path).toPath())
            Files.createSymbolicLink(File(applets, "ash").toPath(), File(shell.path).toPath())
        }
        layout = RootScript.Layout(
            stage = stage.path,
            legacy = legacy.path,
            sh = if (shell.appletsFirst) File(applets, "ash").path else shell.path,
            proc = File(root, "proc").path,
            uid = uid,
            owner = "$uid:$gid",
        )
        writeProps()
    }

    private fun stub(name: String, body: String) {
        File(stubs, name).apply {
            writeText("#!/bin/sh\n" + body.trimIndent() + "\n")
            setExecutable(true)
        }
    }

    fun writeProps() {
        propsFile.writeText(props.entries.joinToString("") { "${it.key}=${it.value}\n" })
    }

    /** Mount table lines (mount point = field 5), after the root mount. */
    fun mountinfo(points: List<String>, self: List<String> = points) {
        fun table(ps: List<String>) = "22 1 253:0 / / rw,relatime - ext4 /dev/root rw\n" +
            ps.mapIndexed { i, p -> "${30 + i} 22 0:${40 + i} / $p rw,relatime - tmpfs tmpfs rw\n" }.joinToString("")
        File(root, "proc/1/mountinfo").writeText(table(points))
        File(root, "proc/self/mountinfo").writeText(table(self))
    }

    fun battery(capacity: String, status: String, temp: String) {
        val b = File(root, "sys/class/power_supply/battery").apply { mkdirs() }
        File(b, "capacity").writeText("$capacity\n")
        File(b, "status").writeText("$status\n")
        File(b, "temp").writeText("$temp\n")
    }

    data class Run(val exit: Int, val out: String, val err: String) {
        val reply: RootReply = RootReply().also { r -> out.lines().forEach { r.accept(it) } }
        override fun toString() = "exit $exit\n$out\n--- stderr\n$err"
    }

    val scriptSha: String = Hashes.sha256(script)

    /** Runs a verb through the launcher; [stdin] null = for begin, the script itself (as the app sends it). */
    fun run(verb: RootScript.Verb, vararg args: String, stdin: ByteArray? = null): Run {
        val text = RootScript.launcher(verb, args.toList(), scriptSha, script.size.toLong(), layout)
        val input = stdin ?: if (verb.stdin == RootScript.Stdin.SCRIPT) script else ByteArray(0)
        return sh(text, input)
    }

    fun sh(text: String, input: ByteArray = ByteArray(0)): Run {
        val cmd = if (shell.appletsFirst) listOf(shell.path, "ash", "-c", text) else listOf(shell.path, "-c", text)
        val pb = ProcessBuilder(cmd)
        val e = pb.environment()
        e["ONEOS_TEST_ROOT"] = root.path
        e["PATH"] = listOfNotNull(stubs.path, applets.path.takeIf { shell.appletsFirst }, System.getenv("PATH")).joinToString(":")
        e.putAll(env)
        val p = pb.start()
        val writer = Thread {
            runCatching { p.outputStream.use { it.write(input) } }
        }.apply { start() }
        val err = StringBuilder()
        val errThread = Thread { err.append(p.errorStream.bufferedReader().readText()) }.apply { start() }
        val out = p.inputStream.bufferedReader().readText()
        check(p.waitFor(120, TimeUnit.SECONDS)) { "shell did not finish" }
        writer.join()
        errThread.join()
        return Run(p.exitValue(), out, err.toString())
    }

    /** Every file and folder under the stage's parent, with size and mode: compared before and after a refusal. */
    fun snapshot(): String = exec(listOf("find", File(root, "data/local/tmp").path, "-printf", "%P %y %m %s\\n")).lines().sorted().joinToString("\n")

    fun mode(f: File): String = exec(listOf("stat", "-c", "%a", f.path)).trim()

    override fun close() {
        exec(listOf("chmod", "-R", "u+rwX", root.path))
        root.deleteRecursively()
    }

    companion object {
        val APPLETS = listOf(
            "head", "tail", "sha256sum", "stat", "awk", "sed", "grep", "sort", "cut", "tr", "wc", "cat", "ls", "mkdir", "mv",
            "cp", "rm", "chown", "chmod", "date", "env", "id", "od", "sh",
        )

        fun exec(cmd: List<String>): String {
            val p = ProcessBuilder(cmd).redirectErrorStream(true).start()
            val out = p.inputStream.bufferedReader().readText()
            p.waitFor()
            return out
        }
    }
}
