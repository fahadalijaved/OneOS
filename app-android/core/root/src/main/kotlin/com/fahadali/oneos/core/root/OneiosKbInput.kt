package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosTool

/**
 * The pairing files the app carries (`assets/kb/` for 24A446: everything of [OneiosKbFiles.NAMES] but Apple's
 * `kernelcache.macho`; `assets/kb-24B156/` for iOS 27.2.1: every file its kb.json lists) into the stage's `kb/` (or
 * `kb-<BUILD>/`), one root `kbinput <name> <bytes> <sha256> [kb-<BUILD>]` each, sorted by name. The prelink reads
 * them there: Update the kernel ([OneiosKernelUpdate]) and Make iOS image ([OneiosMakeImage], whose `make-image`
 * refuses `not-found` naming them when they are missing). Every file is checked against the app's `kb.json` of that
 * build before root is asked for anything; root checks each size and SHA-256 again.
 */
object OneiosKbInput {
    private const val KERNELCACHE = "kernelcache.macho"

    /** The names `kbinput` gets for the 24A446 inputs, in the order it gets them (9). Another build's: [OneiosKb.names]. */
    val NAMES: List<String> = OneiosKbFiles.NAMES.filter { it != KERNELCACHE }.sorted()

    /** Why the files cannot go, as a (code, words) pair: one missing or not the pinned one. */
    data class Refusal(val code: String?, val text: String)

    /**
     * [assets] (by name) checked against [kb], then each into [dir] (`kb`, or `kb-24B156`: root gets it as the last
     * word only when it is not `kb`, so the 24A446 lines are the ones before) by [root] (`kbinput`'s answer: null when
     * OK, else why). [stopped] is asked before each file. Returns null when all are there, else why not; a Stop is
     * [STOPPED].
     */
    fun put(
        kb: OneiosKb,
        assets: Map<String, ByteArray>,
        root: (verb: OneiosRoot.Verb, args: List<String>, data: ByteArray) -> String?,
        stopped: () -> Boolean,
        dir: String = OneiosTool.KB,
    ): Refusal? {
        val names = kb.names
        if (names.isEmpty()) return Refusal("not-found", "the app's $dir/kb.json lists no files: reinstall OneOS")
        for (name in names) {
            val bytes = assets[name] ?: return Refusal("not-found", "the app has no $dir/$name: reinstall OneOS")
            if (kb.files[name] != Hashes.sha256(bytes)) return Refusal("mismatch", "the app's $dir/$name is not the pinned one: reinstall OneOS")
        }
        val last = if (dir == OneiosTool.KB) emptyList() else listOf(dir)
        for (name in names) {
            if (stopped()) return STOPPED
            val bytes = assets.getValue(name)
            root(OneiosRoot.Verb.KBINPUT, listOf(name, bytes.size.toString(), Hashes.sha256(bytes)) + last, bytes)?.let { return Refusal(null, it) }
        }
        return null
    }

    /** [put]'s answer for a Stop between two files. */
    val STOPPED = Refusal(null, "stopped")
}
