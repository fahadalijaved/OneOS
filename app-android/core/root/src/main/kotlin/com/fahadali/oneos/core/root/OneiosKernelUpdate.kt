package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow

/**
 * **Update the kernel**, with no PC (docs/oneios.md, "Kernel updates"): what cannot be shipped is fetched and built
 * on the phone itself. In this order, each step only after the one before it ended well:
 *
 * 1. the pairing files the app carries (`assets/kb/`, each checked against `kb/kb.json` first) into `kb/`, root's
 *    `kbinput` (root checks each size and SHA-256 again);
 * 2. unless `kb/kernelcache.macho` is already the pinned one (root's `status`, the `kb` line): the tool's `fetch` of
 *    only the profile's kernelcache member from Apple ([OneiosTool.kernelcacheFetchRequest], `resume`), its `im4p`
 *    ([OneiosTool.kernelcacheDecodeRequest]), the decoded SHA-256 against `kb.json`'s `kernelcache_sha256`, and
 *    root's `kbcache` (root hashes the file again, moves it into `kb/` and removes the downloaded IM4P);
 * 3. the tool's `prelink` ([OneiosTool.prelinkRequest]) into `make-kernel/out`. The activation stays root's
 *    `finish kernel`, after the user saw the build's result ([Outcome.Built]).
 *
 * Every step of the tool says the room it needs before it writes (its `space` events) and refuses when it is short.
 * What a step that did not end well leaves: a pause, a lost network, an ended app and a refusal for room, heat, the
 * battery or a session keep the download's parts (the next run goes on from them); a Stop, a pin that does not
 * match, a server file that changed, a decode or a build that failed remove the work folder (root's `kbclean`).
 * The cached kernelcache in `kb/` is never part of it.
 */
class OneiosKernelUpdate(
    private val stage: String,
    private val kb: OneiosKb,
    /** The staged runtime's kernel (`runtime.json`'s `kernel.path`, e.g. `kernel/xnu.macho`). */
    private val xnuPath: String,
    /** The app's `kb/` files by name ([OneiosKbFiles.NAMES] but `kernelcache.macho`), as read from its assets. */
    private val assets: Map<String, ByteArray>,
) {
    /** What the update needs from the app: the tool's requests, root's verbs, the screen, the user's Stop. */
    interface Io {
        /** One request of the tool; its lines go to the screen as they come. Returns the request's view at its end. */
        fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow

        /** One verb of the root script ([data]: its stdin); null when it answered OK, else why not. */
        fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray? = null): String?

        /** What runs now, for the screens. */
        fun phase(phase: Phase)

        /** A step of the update's own (not the tool's) that ended well: one line for the screen. */
        fun done(line: String)

        /** The user's Stop. */
        val stopped: Boolean
    }

    enum class Phase(val words: String) {
        INPUTS("Putting the pairing files on this phone"),
        CACHED("Apple's kernelcache is already on this phone"),
        DOWNLOAD("Downloading Apple's kernelcache from Apple"),
        DECODE("Decoding Apple's kernelcache"),
        KEEP("Keeping Apple's kernelcache on this phone"),
        BUILD("Building the kernel on this phone"),
        CLEAN("Removing what the update downloaded"),
    }

    sealed class Outcome {
        /** `make-kernel/out` holds the new kernel.kc ([sha256]), audited: root's `finish kernel` may activate it. */
        data class Built(val sha256: String, val bytes: Long?, val downloaded: Boolean) : Outcome()

        /** The [step] (the tool's command, or root's verb) that did not end with ok: its end, code and words. */
        data class Stopped(val step: String, val end: OneiosToolFlow.End, val code: String?, val text: String?, val cleaned: Boolean) : Outcome()
    }

    /** [cachedSha256]: root's `kb` line, the SHA-256 recorded for `kb/kernelcache.macho`; null = none there. */
    fun run(io: Io, cachedSha256: String?): Outcome {
        // 1. The pairing files, each the pinned one, before root is asked for anything.
        io.phase(Phase.INPUTS)
        val files = OneiosKbFiles.NAMES.filter { it != KERNELCACHE }.sorted()
        for (name in files) {
            val bytes = assets[name] ?: return stopped("kbinput", OneiosToolFlow.End.REFUSED, "not-found", "the app has no kb/$name: reinstall OneOS", io, clean = false)
            val sha = Hashes.sha256(bytes)
            if (kb.files[name] != sha) return stopped("kbinput", OneiosToolFlow.End.REFUSED, "mismatch", "the app's kb/$name is not the pinned one: reinstall OneOS", io, clean = false)
        }
        for (name in files) {
            if (io.stopped) return cancelled("kbinput", io)
            val bytes = assets.getValue(name)
            io.root(OneiosRoot.Verb.KBINPUT, listOf(name, bytes.size.toString(), Hashes.sha256(bytes)), bytes)?.let {
                return stopped("kbinput", OneiosToolFlow.End.REFUSED, null, it, io, clean = false)
            }
        }
        io.done("The pairing files are on this phone (${files.size}, each the pinned one).")

        // 2. Apple's kernelcache: the cached one, or fetched from Apple and decoded on this phone.
        val pin = kb.kernelcacheSha256.lowercase()
        val cached = cachedSha256?.lowercase() == pin
        if (cached) {
            io.phase(Phase.CACHED)
            io.done("Apple's kernelcache is already on this phone (the pinned one): not downloaded again.")
        } else {
            if (io.stopped) return cancelled(OneiosTool.Cmd.FETCH, io)
            io.phase(Phase.DOWNLOAD)
            val (fetchCmd, fetchKeys) = OneiosTool.kernelcacheFetchRequest(stage)
            val fetched = io.tool(fetchCmd, fetchKeys)
            if (fetched.end != OneiosToolFlow.End.OK) return ended(fetchCmd, fetched, io)

            if (io.stopped) return cancelled(OneiosTool.Cmd.IM4P, io)
            io.phase(Phase.DECODE)
            val (decodeCmd, decodeKeys) = OneiosTool.kernelcacheDecodeRequest(stage)
            val decoded = io.tool(decodeCmd, decodeKeys)
            if (decoded.end != OneiosToolFlow.End.OK) return ended(decodeCmd, decoded, io)
            val got = (decoded.result?.get("sha256") as? String)?.lowercase()
            val bytes = (decoded.result?.get("bytes") as? Number)?.toLong()
            if (got != pin || bytes == null || bytes <= 0) {
                return stopped(
                    decodeCmd, OneiosToolFlow.End.REFUSED, "mismatch",
                    "the decoded kernelcache's SHA-256 is ${got ?: "missing"}, the profile pins $pin: nothing was kept",
                    io, clean = true,
                )
            }

            if (io.stopped) return cancelled("kbcache", io)
            io.phase(Phase.KEEP)
            io.root(OneiosRoot.Verb.KBCACHE, listOf(bytes.toString(), pin))?.let {
                return stopped("kbcache", OneiosToolFlow.End.REFUSED, if ("pins" in it) "mismatch" else null, it, io, clean = true)
            }
            io.done("Apple's kernelcache is on this phone: downloaded from Apple, decoded and the pinned one (${bytes / 1_000_000} MB).")
        }

        // 3. The build.
        if (io.stopped) return cancelled(OneiosTool.Cmd.PRELINK, io)
        io.phase(Phase.BUILD)
        val (buildCmd, buildKeys) = OneiosTool.prelinkRequest(xnuPath, stage)
        val built = io.tool(buildCmd, buildKeys)
        if (built.end != OneiosToolFlow.End.OK) return ended(buildCmd, built, io)
        val kc = (built.result?.get("sha256") as? String)?.lowercase()
        if (kc == null || !HEX64.matches(kc)) {
            return stopped(buildCmd, OneiosToolFlow.End.FAILED, "internal", "the build's result names no kernel.kc SHA-256", io, clean = true)
        }
        return Outcome.Built(kc, (built.result?.get("bytes") as? Number)?.toLong(), downloaded = !cached)
    }

    /** A tool request that did not end with ok: kept for a resume, or the work folder removed (the class's rule). */
    private fun ended(cmd: String, v: OneiosToolFlow, io: Io): Outcome {
        val end = v.end ?: OneiosToolFlow.End.LOST
        // (a Stop the tool did not answer in time is still a Stop: the work goes)
        return stopped(cmd, end, v.code, v.text, io, clean = io.stopped || !keeps(end, v.code))
    }

    private fun cancelled(step: String, io: Io): Outcome =
        stopped(step, OneiosToolFlow.End.CANCELLED, null, "stopped", io, clean = true)

    private fun stopped(step: String, end: OneiosToolFlow.End, code: String?, text: String?, io: Io, clean: Boolean): Outcome {
        var cleaned = false
        if (clean) {
            io.phase(Phase.CLEAN)
            cleaned = io.root(OneiosRoot.Verb.KBCLEAN, emptyList()) == null
        }
        return Outcome.Stopped(step, end, code, text, cleaned)
    }

    companion object {
        /** The tool's requests of a run, in order, when the kernelcache is (`cached`) or is not on the phone yet. */
        fun toolRequests(stage: String, xnuPath: String, cached: Boolean): List<Pair<String, Map<String, Any?>>> =
            (if (cached) emptyList() else listOf(OneiosTool.kernelcacheFetchRequest(stage), OneiosTool.kernelcacheDecodeRequest(stage))) +
                OneiosTool.prelinkRequest(xnuPath, stage)

        private const val KERNELCACHE = "kernelcache.macho"
        private val HEX64 = Regex("^[0-9a-f]{64}$")

        /** The refusals a later run gets past by itself or with the user's help, so the parts stay. */
        private val KEEP_CODES = setOf("space", "heat", "battery", "session")

        /** Whether a request that ended so keeps the update's work folder (the next run goes on from it). */
        fun keeps(end: OneiosToolFlow.End, code: String?): Boolean = when (end) {
            OneiosToolFlow.End.LOST -> true
            OneiosToolFlow.End.FAILED -> code == "network"
            OneiosToolFlow.End.REFUSED -> code in KEEP_CODES
            OneiosToolFlow.End.CANCELLED, OneiosToolFlow.End.OK -> false
        }
    }
}
