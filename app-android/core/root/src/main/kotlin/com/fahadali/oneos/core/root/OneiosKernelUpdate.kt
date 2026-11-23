package com.fahadali.oneos.core.root

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
 *    root's `kbcache` (root hashes the file again, moves it into `kb/` and removes the downloaded IM4P). This step
 *    is [kernelcache], which Make iOS image runs too for the Galaxy A56's profile;
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

    /** Step 2's answer ([kernelcache]). */
    sealed class Kernelcache {
        /** `kb/kernelcache.macho` is the pinned one already: nothing was fetched. */
        object Cached : Kernelcache()

        /** Fetched from Apple, decoded, the pinned one ([bytes]), and moved into `kb/` by root's `kbcache`. */
        data class Kept(val bytes: Long) : Kernelcache()

        /** The [step] that did not end well; [clean]: the work folder goes (root's `kbclean`), by the class's rule. */
        data class Stopped(val step: String, val end: OneiosToolFlow.End, val code: String?, val text: String?, val clean: Boolean) : Kernelcache()
    }

    /** [cachedSha256]: root's `kb` line, the SHA-256 recorded for `kb/kernelcache.macho`; null = none there. */
    fun run(io: Io, cachedSha256: String?): Outcome {
        // 1. The pairing files, each the pinned one, before root is asked for anything.
        io.phase(Phase.INPUTS)
        OneiosKbInput.put(kb, assets, { verb, args, data -> io.root(verb, args, data) }, { io.stopped })?.let { r ->
            if (r === OneiosKbInput.STOPPED) return cancelled("kbinput", io)
            return stopped("kbinput", OneiosToolFlow.End.REFUSED, r.code, r.text, io, clean = false)
        }
        io.done("The pairing files are on this phone (${OneiosKbInput.NAMES.size}, each the pinned one).")

        // 2. Apple's kernelcache: the cached one, or fetched from Apple and decoded on this phone.
        val cached = when (val k = kernelcache(stage, kb, cachedSha256, { cmd, keys -> io.tool(cmd, keys) }, { verb, args -> io.root(verb, args) }, { io.stopped }, io::phase)) {
            Kernelcache.Cached -> {
                io.done("Apple's kernelcache is already on this phone (the pinned one): not downloaded again.")
                true
            }
            is Kernelcache.Kept -> {
                io.done("Apple's kernelcache is on this phone: downloaded from Apple, decoded and the pinned one (${k.bytes / 1_000_000} MB).")
                false
            }
            is Kernelcache.Stopped -> return stopped(k.step, k.end, k.code, k.text, io, k.clean)
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

        /**
         * Step 2 on its own: Apple's kernelcache in `kb/` unless [cachedSha256] (root's `kb` line) is the pin of
         * [kb] already. The tool's `fetch` of only the kernel profile's kernelcache member
         * ([OneiosTool.kernelcacheFetchRequest], always [OneiosTool.IPSW_PROFILE]: the 24A446 one), its `im4p`, the
         * decoded SHA-256 against the pin, root's `kbcache`. Update the kernel runs it, and so does Make iOS image for
         * a profile without a kernelcache member (the Galaxy A56's iOS 16.5: [OneiosMakeImage]). [phase] gets
         * [Phase.CACHED], or [Phase.DOWNLOAD], [Phase.DECODE] and [Phase.KEEP] as they start.
         */
        fun kernelcache(
            stage: String,
            kb: OneiosKb,
            cachedSha256: String?,
            tool: (String, Map<String, Any?>) -> OneiosToolFlow,
            root: (OneiosRoot.Verb, List<String>) -> String?,
            stopped: () -> Boolean,
            phase: (Phase) -> Unit,
        ): Kernelcache {
            val pin = kb.kernelcacheSha256.lowercase()
            if (cachedSha256?.lowercase() == pin) {
                phase(Phase.CACHED)
                return Kernelcache.Cached
            }
            fun cancelled(step: String) = Kernelcache.Stopped(step, OneiosToolFlow.End.CANCELLED, null, "stopped", clean = true)
            // (a Stop the tool did not answer in time is still a Stop: the work goes)
            fun ended(cmd: String, v: OneiosToolFlow): Kernelcache {
                val end = v.end ?: OneiosToolFlow.End.LOST
                return Kernelcache.Stopped(cmd, end, v.code, v.text, clean = stopped() || !keeps(end, v.code))
            }

            if (stopped()) return cancelled(OneiosTool.Cmd.FETCH)
            phase(Phase.DOWNLOAD)
            val (fetchCmd, fetchKeys) = OneiosTool.kernelcacheFetchRequest(stage)
            val fetched = tool(fetchCmd, fetchKeys)
            if (fetched.end != OneiosToolFlow.End.OK) return ended(fetchCmd, fetched)

            if (stopped()) return cancelled(OneiosTool.Cmd.IM4P)
            phase(Phase.DECODE)
            val (decodeCmd, decodeKeys) = OneiosTool.kernelcacheDecodeRequest(stage)
            val decoded = tool(decodeCmd, decodeKeys)
            if (decoded.end != OneiosToolFlow.End.OK) return ended(decodeCmd, decoded)
            val got = (decoded.result?.get("sha256") as? String)?.lowercase()
            val bytes = (decoded.result?.get("bytes") as? Number)?.toLong()
            if (got != pin || bytes == null || bytes <= 0) {
                return Kernelcache.Stopped(
                    decodeCmd, OneiosToolFlow.End.REFUSED, "mismatch",
                    "the decoded kernelcache's SHA-256 is ${got ?: "missing"}, the profile pins $pin: nothing was kept",
                    clean = true,
                )
            }

            if (stopped()) return cancelled(STEP_KBCACHE)
            phase(Phase.KEEP)
            root(OneiosRoot.Verb.KBCACHE, listOf(bytes.toString(), pin))?.let {
                return Kernelcache.Stopped(STEP_KBCACHE, OneiosToolFlow.End.REFUSED, if ("pins" in it) "mismatch" else null, it, clean = true)
            }
            return Kernelcache.Kept(bytes)
        }

        /** Root's `kbcache` as a step's name (OneiosPlain's download steps). */
        const val STEP_KBCACHE = "kbcache"

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
