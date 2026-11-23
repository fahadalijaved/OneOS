package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosKbFiles

/**
 * The pairing files the app carries (`assets/kb/`: everything of [OneiosKbFiles.NAMES] but Apple's
 * `kernelcache.macho`) into the stage's `kb/`, one root `kbinput <name> <bytes> <sha256>` each, sorted by name. The
 * prelink reads them there: Update the kernel ([OneiosKernelUpdate]) and Make iOS image ([OneiosMakeImage], whose
 * `make-image` refuses `not-found` naming them when they are missing). Every file is checked against the app's
 * `kb/kb.json` before root is asked for anything; root checks each size and SHA-256 again.
 */
object OneiosKbInput {
    private const val KERNELCACHE = "kernelcache.macho"

    /** The names `kbinput` gets, in the order it gets them (12). */
    val NAMES: List<String> = OneiosKbFiles.NAMES.filter { it != KERNELCACHE }.sorted()

    /** Why the files cannot go, as a (code, words) pair: one missing or not the pinned one. */
    data class Refusal(val code: String?, val text: String)

    /**
     * [assets] (by name) checked against [kb], then each into `kb/` by [root] (`kbinput`'s answer: null when OK, else
     * why). [stopped] is asked before each file. Returns null when all 12 are there, else why not; a Stop is
     * [STOPPED].
     */
    fun put(
        kb: OneiosKb,
        assets: Map<String, ByteArray>,
        root: (verb: OneiosRoot.Verb, args: List<String>, data: ByteArray) -> String?,
        stopped: () -> Boolean,
    ): Refusal? {
        for (name in NAMES) {
            val bytes = assets[name] ?: return Refusal("not-found", "the app has no kb/$name: reinstall OneOS")
            if (kb.files[name] != Hashes.sha256(bytes)) return Refusal("mismatch", "the app's kb/$name is not the pinned one: reinstall OneOS")
        }
        for (name in NAMES) {
            if (stopped()) return STOPPED
            val bytes = assets.getValue(name)
            root(OneiosRoot.Verb.KBINPUT, listOf(name, bytes.size.toString(), Hashes.sha256(bytes)), bytes)?.let { return Refusal(null, it) }
        }
        return null
    }

    /** [put]'s answer for a Stop between two files. */
    val STOPPED = Refusal(null, "stopped")
}
