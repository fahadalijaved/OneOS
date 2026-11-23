package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.HashedCopy
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosFile
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosManifest
import com.fahadali.oneos.core.model.OneiosManifests
import com.fahadali.oneos.core.model.OneiosPackage
import com.fahadali.oneos.core.model.ReadAhead
import com.fahadali.oneos.core.model.TarReader
import com.fahadali.oneos.core.model.Units
import java.io.IOException
import java.io.InputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.Future

/**
 * The import of a OneiOS package (a runtime package or the iOS image set) into
 * the stage, over the same road as an Android system's image: the app unpacks
 * and streams, [RootShell] carries each file to the root script's `receive`,
 * root checks its size and SHA-256 and only `finish` puts anything in place
 * (docs/oneios.md, "Importing either package").
 *
 * One pass over the archive when its manifest is the first file, which is how
 * OneiOS packs both packages; otherwise a pass for the manifest and one to
 * unpack. Three threads share the work of a file: one reads ahead (under it the
 * caller's decompressor), one writes to root's stdin, one hashes the buffer
 * being written. Root's check of a large file, for which it reads the file
 * again, runs while the next file is sent. Here, in :core:root, so the tests run it whole against the
 * root script and a fake root.
 */
class OneiosImport(
    private val kind: OneiosKind,
    private val root: Root,
    private val listener: Listener,
    /** The app's own SHA-256 of every file, beside root's. Root's is the one that decides. */
    private val appHash: Boolean = true,
    /** [OVERLAP_BYTES]; smaller in the tests. Never under a pipe's 64 KiB: root must be past the file's folders when the next file starts. */
    private val overlapBytes: Long = OVERLAP_BYTES,
) {
    fun interface Root {
        /**
         * Runs one verb; null when root said OK, otherwise why not, in words.
         * Two may run at a time: a `receive` whose file root still checks, and the next one.
         */
        fun run(verb: OneiosRoot.Verb, args: List<String>, feed: RootShell.Feed?, silenceMs: Long): String?

        /** The import failed: end the verbs that still run. */
        fun abandon() {}
    }

    interface Listener {
        /** A step without a byte count ("Reading the image set's manifest.json…"). */
        fun step(text: String) {}

        /** File [index] of [count] (from 1) starts. */
        fun file(index: Int, count: Int, file: OneiosFile) {}

        /** [done] of [total] bytes of the package's files are with root; called for every buffer. */
        fun bytes(done: Long, total: Long) {}

        fun stopped(): Boolean = false
    }

    /** A session script this app pins, staged with every import. */
    class Script(val name: String, val bytes: ByteArray, val sha256: String)

    class Failed(message: String) : IOException(message)

    data class Result(val manifest: OneiosManifest, val singlePass: Boolean)

    private fun must(problem: String?) {
        if (listener.stopped()) throw Failed("stopped")
        if (problem != null) throw Failed(problem)
    }

    /**
     * [open] gives the package's tar (the caller decompresses) from its start,
     * each time it is called: once, or twice when the manifest is not first.
     * [accept] may refuse the parsed manifest (by throwing) before root is asked
     * for anything.
     */
    fun run(open: () -> InputStream, scripts: List<Script>, accept: (OneiosManifest) -> Unit = {}): Result {
        val label = kind.label
        listener.step("Reading the $label's ${kind.manifestName}…")
        var stream: InputStream = ReadAhead(open(), name = "oneios-read")
        val verbs = Executors.newFixedThreadPool(2) { r -> Thread(r, "oneios-receive").apply { isDaemon = true } }
        var done = false
        checking = null
        val hasher = if (appHash) Executors.newSingleThreadExecutor { r -> Thread(r, "oneios-sha256").apply { isDaemon = true } } else null
        try {
            var reader = TarReader(stream)
            var single = true
            val found = try {
                OneiosPackage.manifestFirst(reader, kind) ?: run {
                    // Not packed by OneiOS's tools: the old way, a pass for the manifest and one to unpack.
                    single = false
                    val f = OneiosPackage.readManifest(reader, kind)
                    stream.close()
                    stream = ReadAhead(open(), name = "oneios-read")
                    reader = TarReader(stream)
                    f
                }
            } catch (e: IOException) {
                throw Failed(notOurs(e))
            }
            val manifest = OneiosManifests.parse(kind, found.text).getOrElse { throw Failed(it.message ?: "${kind.manifestName} is not valid") }
            accept(manifest)
            val total = manifest.bytes
            must(root.run(OneiosRoot.Verb.BEGIN, listOf(kind.word), null, SHORT_MS))
            for (s in scripts) {
                must(root.run(OneiosRoot.Verb.SCRIPT, listOf(s.name, s.bytes.size.toString(), s.sha256), RootShell.Feed { it.write(s.bytes) }, SHORT_MS))
            }
            val text = found.text.toByteArray(Charsets.UTF_8)
            must(
                root.run(
                    OneiosRoot.Verb.RECEIVE, listOf(kind.word, kind.manifestName, text.size.toString(), Hashes.sha256(text), "0644"),
                    RootShell.Feed { it.write(text) }, SHORT_MS,
                ),
            )
            var index = 0
            try {
                OneiosPackage.unpack(reader, manifest, found.prefix, { f, data ->
                    if (listener.stopped()) throw Failed("stopped")
                    index++
                    listener.file(index, manifest.files.size, f)
                    var sha: String? = null
                    var whole = false
                    // What the archive itself did wrong while this file was read, apart from what root answers.
                    var damaged: IOException? = null
                    val source = object : InputStream() {
                        override fun read(): Int = throw IOException("whole buffers only")

                        override fun read(b: ByteArray, off: Int, len: Int): Int = try {
                            data.read(b, off, len)
                        } catch (e: IOException) {
                            damaged = e
                            throw e
                        }
                    }
                    val fed = CountDownLatch(1)
                    val answer = verbs.submit<String?> {
                        try {
                            root.run(
                                OneiosRoot.Verb.RECEIVE, listOf(kind.word, f.path, f.size.toString(), f.sha256, f.mode),
                                RootShell.Feed { out ->
                                    try {
                                        // Ends early when the file before this one turned out wrong.
                                        sha = HashedCopy.copy(source, out, hasher, stop = { listener.stopped() || checking?.refused() == true })
                                        out.flush()
                                        whole = true
                                    } finally {
                                        fed.countDown()
                                    }
                                },
                                // Root hashes the file after its last byte: no output while it reads several GB again.
                                RECEIVE_MS,
                            )
                        } finally {
                            fed.countDown()
                        }
                    }
                    fed.await()
                    val now = Checking(f, answer)
                    if (whole && f.size >= overlapBytes) {
                        // Root now reads this file again for its SHA-256. The next file is sent meanwhile; root's
                        // answer for this one is taken before the one after that is over, and before finish.
                        val before = checking
                        checking = now
                        before?.let(::settle)
                    } else {
                        checking?.let { if (it.answer.isDone) settle(it) }
                        if (listener.stopped()) throw Failed("stopped")
                        damaged?.let { throw it }
                        settle(now)
                    }
                    sha
                }) { done -> listener.bytes(done, total) }
                checking?.let {
                    listener.step("Root is checking ${it.file.path}…")
                    settle(it)
                }
            } catch (e: Failed) {
                throw e
            } catch (e: IOException) {
                throw Failed("The $label is damaged or incomplete: ${e.message}. Nothing staged before was changed.")
            }
            listener.step("Putting the $label in place…")
            val count = (manifest.files.size + 1).toString()
            val finish = when (kind) {
                OneiosKind.RUNTIME -> listOf(
                    kind.word, count, manifest.version, manifest.sessionAbi.toString(), manifest.xnuhost!!,
                    manifest.imageFormats.joinToString(","), if (manifest.placeholder) "1" else "0",
                    manifest.kernel?.buildId ?: "none", manifest.kernel?.sha256 ?: "none", manifest.kernel?.xnu ?: "none",
                )
                OneiosKind.IMAGE -> listOf(kind.word, count, manifest.format.toString(), manifest.version, manifest.build ?: "unknown")
            }
            must(root.run(OneiosRoot.Verb.FINISH, finish, null, FINISH_MS))
            done = true
            return Result(manifest, single)
        } finally {
            // A receive that still runs after a failure is ended; what it wrote is in <kind>.new, which the next begin clears.
            if (!done) runCatching { root.abandon() }
            runCatching { stream.close() }
            hasher?.shutdown()
            verbs.shutdown()
        }
    }

    /** A file root has all bytes of and still checks. */
    private inner class Checking(val file: OneiosFile, val answer: Future<String?>) {
        fun refused(): Boolean = answer.isDone && runCatching { answer.get() }.getOrNull() != null
    }

    private var checking: Checking? = null

    private fun settle(c: Checking) {
        if (checking === c) checking = null
        val problem = try {
            c.answer.get()
        } catch (e: Exception) {
            "${c.file.path}: ${e.cause?.message ?: e.message}"
        }
        must(problem)
    }

    private fun notOurs(e: IOException): String {
        val m = e.message.orEmpty()
        return when {
            e is OneiosPackage.Problem -> m
            m.contains("tar") -> "This file is not a ${kind.label} ($m)."
            else -> "This file is not a .tar.zst ${kind.label}: $m"
        }
    }

    companion object {
        private const val SHORT_MS = 120_000L
        private const val RECEIVE_MS = 20 * 60_000L
        private const val FINISH_MS = 10 * 60_000L

        /**
         * From this size on root's check of a file (it reads the file again for its SHA-256) runs while the next
         * file is sent. Smaller files are answered one by one: two of them at once could make the same folder.
         */
        const val OVERLAP_BYTES = 64L shl 20

        /** Why a verb of the OneiOS root script did not work, in one line; null when it did. */
        fun problem(reply: RootReply, end: RootShell.End): String? = when {
            end.exitCode == 0 && reply.ok != null && end.error == null -> null
            end.error != null -> end.error
            end.cancelled -> "stopped"
            end.killed && reply.refused == null -> "root did not answer in time"
            else -> reply.problem(end.exitCode) ?: "no answer from root"
        }

        /** "File 3 of 21: os.img (10.6 GB)". */
        fun fileLine(index: Int, count: Int, file: OneiosFile): String = "File $index of $count: ${file.path} (${Units.bytes(file.size)})"
    }
}
