package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import java.io.File
import java.nio.file.Files

/**
 * A fake root folder (`ONEIOS_TEST_ROOT`) for the OneiOS root script, driven
 * through the app's own [RootShell] with [sh] in su's place: what the import
 * does on the phone, against a folder of the test.
 */
class OneiosFakeStage(val sh: String, parent: File? = null, scriptFile: File = File(Shipped.fullAssets, OneiosRoot.ASSET)) {
    val root: File = (if (parent != null) Files.createTempDirectory(parent.toPath(), "oneios-fakeroot") else Files.createTempDirectory("oneios-fakeroot")).toFile()
    val stage = File(root, "data/local/tmp/oneios")
    private val script = scriptFile.readBytes()
    private val uid = run("id", "-u")
    private val layout = OneiosRoot.Layout(stage.path, sh, File(root, "proc").path, uid, "$uid:${run("id", "-g")}")

    /** Every verb that ran, in order, with its arguments. */
    val calls = mutableListOf<String>()

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

    fun verb(verb: OneiosRoot.Verb, args: List<String>, feed: RootShell.Feed? = null, silenceMs: Long = 120_000): Pair<RootReply, RootShell.End> {
        synchronized(calls) { calls += (listOf(verb.word) + args).joinToString(" ") }
        val command = OneiosRoot.launcher(verb, args, Hashes.sha256(script), script.size.toLong(), layout)
        val input = when (verb.stdin) {
            OneiosRoot.Stdin.SCRIPT -> RootShell.Feed { it.write(script) }
            OneiosRoot.Stdin.DATA -> feed!!
            OneiosRoot.Stdin.NONE -> null
        }
        val reply = RootReply()
        val end = RootShell(command, listOf(sh, "-c"), mapOf("ONEIOS_TEST_ROOT" to root.path, "PATH" to HostTools.path())).run(input, { reply.accept(it) }, { silenceMs }, 30 * 60_000L)
        return reply to end
    }

    val asRoot = OneiosImport.Root { verb, args, feed, silenceMs ->
        val (reply, end) = verb(verb, args, feed, silenceMs)
        OneiosImport.problem(reply, end)
    }

    fun delete() {
        root.deleteRecursively()
    }
}
