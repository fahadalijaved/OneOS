package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosMakeImageSteps
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow

/**
 * **Make iOS image**, with no PC (docs/oneios.md, "Make iOS image"): a phone with only this app gets the whole iOS
 * image set from Apple's own files, built on the phone by the staged runtime's `oneios-tool`. In this order, each
 * step only after the one before it ended well:
 *
 * 1. root's `status`: no open session, and a staged runtime that carries a kernel (`runtime.json`'s `kernel`,
 *    OneiOS v0.1.12 or newer: the set's `kernel.kc` is prelinked from it). Without one, the latest OneiOS release's
 *    runtime is downloaded and staged first ([Io.latestRuntime], as Get the runtime does), and `status` asked again;
 * 2. the pairing files into `kb/` ([OneiosKbInput]: root's `kbinput` ×12, as Update the kernel does);
 * 3. root's `begin image` (an empty `image.new` and its two empty lists);
 * 4. the tool ([Io.openTool]); when its `hello` names no `make-image` (a runtime older than the tool's
 *    `make-image`), the latest runtime once more when that is another version, else a refusal in plain words;
 * 5. the tool's `make-image` ([OneiosTool.makeImageRequest]): fetch from Apple, decrypt, the volumes, the root
 *    tweaks, the seed, the kernelcache, the prelink with its audit, the manifest, verify, the lists. It asks its room
 *    once (`space`) before it fetches or writes anything, can be paused, and removes what it wrote when it stops; the
 *    fetched members stay in `make/inputs` for the next run;
 * 6. root's `finish image <files> <format> <version> <build>` with those four fields of `make-image`'s `ok`.
 *
 * The tool's own `tweaks` request is not sent: `make-image` runs the root tweaks itself (its `tweaks` step). Nor is
 * a `fetch` before it: `make-image` fetches, and its one room check and every refusal of its `check` step come before
 * a byte is downloaded (a `fetch` first would download 11 GB before that check).
 */
class OneiosMakeImage(
    private val stage: String,
    private val kb: OneiosKb,
    /** The app's `kb/` files by name ([OneiosKbInput.NAMES]), as read from its assets. */
    private val assets: Map<String, ByteArray>,
) {
    /** What the flow needs from the app: root, the release download, the tool, the screen, the user's Stop. */
    interface Io {
        /** Root's `status` (parsed), or the reason it did not answer. */
        fun status(): Result<OneiosStatus>

        /** The latest OneiOS release's runtime downloaded and staged, unless its version is [unless] (the staged one). */
        fun latestRuntime(unless: String?): Runtime

        /** One verb of the root script ([data]: its stdin); null when it answered OK, else why not. */
        fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray? = null): String?

        /** The staged runtime's `oneios-tool serve` started: the commands its `hello` names, or why it did not start. */
        fun openTool(): Result<List<String>>

        /** The tool ended (its pipe closed), before a new runtime replaces it. */
        fun closeTool()

        /** One request of the tool; its lines go to the screen as they come. Returns the request's view at its end. */
        fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow

        /** What runs now, for the screens. */
        fun phase(phase: Phase)

        /** A step of the flow's own (not the tool's) that ended well: one line for the screen. */
        fun done(line: String)

        /** The user's Stop. */
        val stopped: Boolean
    }

    /** [Io.latestRuntime]'s answer. */
    sealed class Runtime {
        data class Staged(val version: String) : Runtime()

        /** The latest release is [version], the one staged already: nothing was downloaded. */
        data class Same(val version: String) : Runtime()

        data class Failed(val why: String) : Runtime()
    }

    enum class Phase(val words: String) {
        STATUS("Checking what is on this phone"),
        RUNTIME("Getting the newest OneiOS runtime"),
        INPUTS("Putting the pairing files on this phone"),
        BEGIN("Making room for the new image set"),
        TOOL("Starting oneios-tool"),
        BUILD("Making the iOS image on this phone"),
        FINISH("Putting the new image set in place"),
    }

    sealed class Outcome {
        /** Root's `finish image` put the set in place: iOS [version] ([build]), [files] files, [bytes] bytes. */
        data class Staged(val files: Long, val format: Long, val version: String, val build: String, val bytes: Long?, val manifestSha256: String?) : Outcome()

        /**
         * The [step] (root's verb, `runtime`, or the tool's command) that did not end with ok: its end, code and
         * words; with the tool's `space` event's numbers when it had one.
         */
        data class Stopped(
            val step: String, val end: OneiosToolFlow.End, val code: String?, val text: String?,
            val need: Long? = null, val free: Long? = null,
        ) : Outcome()
    }

    fun run(io: Io): Outcome {
        // 1. No session, and a runtime with a kernel (else the newest one first).
        io.phase(Phase.STATUS)
        var st = io.status().getOrElse { return refused(STEP_STATUS, null, it.message ?: "root did not answer") }
        if (st.sessionOpen) return refused(STEP_STATUS, "session", "an iOS session is running: return to One UI first")
        var newRuntime = false
        if (!canBuild(st)) {
            if (io.stopped) return cancelled(STEP_RUNTIME)
            io.phase(Phase.RUNTIME)
            when (val r = io.latestRuntime(st.runtime?.version)) {
                is Runtime.Failed -> return Outcome.Stopped(STEP_RUNTIME, if (io.stopped) OneiosToolFlow.End.CANCELLED else OneiosToolFlow.End.FAILED, null, r.why)
                is Runtime.Same -> return noKernel(r.version)
                is Runtime.Staged -> {
                    newRuntime = true
                    io.done("OneiOS runtime ${r.version} is staged: it carries the kernel the image needs.")
                }
            }
            st = io.status().getOrElse { return refused(STEP_STATUS, null, it.message ?: "root did not answer") }
            if (!canBuild(st)) return noKernel(st.runtime?.version)
        }

        // 2. The pairing files (the prelink's inputs besides Apple's kernelcache, which make-image decodes itself).
        if (io.stopped) return cancelled(STEP_KBINPUT)
        io.phase(Phase.INPUTS)
        OneiosKbInput.put(kb, assets, { verb, args, data -> io.root(verb, args, data) }, { io.stopped })?.let { r ->
            if (r === OneiosKbInput.STOPPED) return cancelled(STEP_KBINPUT)
            return refused(STEP_KBINPUT, r.code, r.text)
        }
        io.done("The pairing files are on this phone (${OneiosKbInput.NAMES.size}, each the pinned one).")

        // 3. An empty image.new and its lists.
        if (io.stopped) return cancelled(STEP_BEGIN)
        io.phase(Phase.BEGIN)
        io.root(OneiosRoot.Verb.BEGIN, listOf("image"))?.let { return refused(STEP_BEGIN, null, it) }

        // 4. The tool; one that has no make-image yet: the newest runtime once, when it is another version.
        if (io.stopped) return cancelled(STEP_TOOL)
        io.phase(Phase.TOOL)
        var cmds = io.openTool().getOrElse { return refused(STEP_TOOL, null, it.message ?: "oneios-tool did not start") }
        if (OneiosTool.Cmd.MAKE_IMAGE !in cmds) {
            io.closeTool()
            val version = st.runtime?.version
            if (newRuntime) return tooOld(version)
            if (io.stopped) return cancelled(STEP_RUNTIME)
            io.phase(Phase.RUNTIME)
            when (val r = io.latestRuntime(version)) {
                is Runtime.Failed -> return Outcome.Stopped(STEP_RUNTIME, if (io.stopped) OneiosToolFlow.End.CANCELLED else OneiosToolFlow.End.FAILED, null, r.why)
                is Runtime.Same -> return tooOld(r.version)
                is Runtime.Staged -> io.done("OneiOS runtime ${r.version} is staged: its oneios-tool makes the image.")
            }
            st = io.status().getOrElse { return refused(STEP_STATUS, null, it.message ?: "root did not answer") }
            if (!canBuild(st)) return noKernel(st.runtime?.version)
            if (io.stopped) return cancelled(STEP_TOOL)
            io.phase(Phase.TOOL)
            cmds = io.openTool().getOrElse { return refused(STEP_TOOL, null, it.message ?: "oneios-tool did not start") }
            if (OneiosTool.Cmd.MAKE_IMAGE !in cmds) return tooOld(st.runtime?.version)
        }

        // 5. The image set, made by the tool.
        if (io.stopped) return cancelled(OneiosTool.Cmd.MAKE_IMAGE)
        io.phase(Phase.BUILD)
        val (cmd, keys) = OneiosTool.makeImageRequest(stage)
        val made = io.tool(cmd, keys)
        if (made.end != OneiosToolFlow.End.OK) {
            return Outcome.Stopped(cmd, made.end ?: OneiosToolFlow.End.LOST, made.code, made.text, made.spaceNeed, made.spaceFree)
        }

        // 6. Root's finish with the four fields of make-image's ok.
        val r = made.result.orEmpty()
        val files = (r["files"] as? Number)?.toLong()
        val format = (r["format"] as? Number)?.toLong()
        val version = r["version"] as? String
        val build = r["build"] as? String
        if (files == null || format == null || version == null || build == null) {
            return Outcome.Stopped(STEP_FINISH, OneiosToolFlow.End.FAILED, "internal", "make-image's result has no files, format, version or build for root's finish")
        }
        val args = listOf("image", files.toString(), format.toString(), version, build)
        OneiosRoot.problems(OneiosRoot.Verb.FINISH, args).takeIf { it.isNotEmpty() }?.let {
            return Outcome.Stopped(STEP_FINISH, OneiosToolFlow.End.FAILED, "internal", "make-image's result cannot go to root's finish: ${it.joinToString("; ")}")
        }
        // (a Stop after make-image's ok: the set is whole and checked, so it is put in place)
        io.phase(Phase.FINISH)
        io.root(OneiosRoot.Verb.FINISH, args)?.let { return refused(STEP_FINISH, null, it) }
        return Outcome.Staged(files, format, version, build, (r["bytes"] as? Number)?.toLong(), r["manifest_sha256"] as? String)
    }

    private fun refused(step: String, code: String?, text: String) = Outcome.Stopped(step, OneiosToolFlow.End.REFUSED, code, text)

    private fun cancelled(step: String) = Outcome.Stopped(step, OneiosToolFlow.End.CANCELLED, null, "stopped")

    private fun noKernel(version: String?) = refused(
        STEP_RUNTIME, CODE_NO_KERNEL,
        "the newest OneiOS runtime${version?.let { " ($it)" }.orEmpty()} carries no kernel, which the image set's kernel.kc is built from",
    )

    private fun tooOld(version: String?) = refused(
        STEP_RUNTIME, CODE_NO_MAKE_IMAGE,
        "the newest OneiOS runtime${version?.let { " ($it)" }.orEmpty()} has an oneios-tool without make-image",
    )

    companion object {
        const val STEP_STATUS = OneiosMakeImageSteps.STATUS
        const val STEP_RUNTIME = OneiosMakeImageSteps.RUNTIME
        const val STEP_KBINPUT = OneiosMakeImageSteps.KBINPUT
        const val STEP_BEGIN = OneiosMakeImageSteps.BEGIN
        const val STEP_TOOL = OneiosMakeImageSteps.TOOL
        const val STEP_FINISH = OneiosMakeImageSteps.FINISH

        /** The app's own codes for [Outcome.Stopped] at [STEP_RUNTIME]: no runtime with a kernel, or no tool with make-image. */
        const val CODE_NO_KERNEL = OneiosMakeImageSteps.NO_KERNEL
        const val CODE_NO_MAKE_IMAGE = OneiosMakeImageSteps.NO_MAKE_IMAGE

        /** A staged runtime the tool can make the image with: there, not a placeholder, and carrying a kernel. */
        fun canBuild(st: OneiosStatus): Boolean = st.runtime != null && !st.runtime.placeholder && st.runtimeKernel != null
    }
}
