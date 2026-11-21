package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.ByteMeter
import com.fahadali.oneos.core.model.OneiosFile
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosManifests
import com.fahadali.oneos.core.model.OneiosPackage
import com.fahadali.oneos.core.model.ReadAhead
import com.github.luben.zstd.ZstdInputStream
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.BufferedInputStream
import java.io.File
import java.io.InputStream
import java.security.MessageDigest

/**
 * Not a test: how fast an image set goes through the import on this machine,
 * stage by stage, the 0.4.76 way and this version's. Runs only with
 *
 *   ONEIOS_BENCH_PACKAGE=<a .tar.zst image set, manifest.json first>
 *   ONEIOS_BENCH_DIR=<a folder on a real disk for the fake stage and results.txt>
 *   ONEIOS_BENCH_OLD_SCRIPT=<oneios_root.sh of 0.4.76>      (optional)
 *
 *   ./gradlew :core:root:testDebugUnitTest --rerun --tests '*OneiosImportBench*'
 *
 * The package must be a synthetic one (docs/oneios.md, "Measuring the import").
 */
class OneiosImportBench {
    private val pkg = System.getenv("ONEIOS_BENCH_PACKAGE")?.let(::File)
    private val dir = System.getenv("ONEIOS_BENCH_DIR")?.let(::File)
    private val oldScript = System.getenv("ONEIOS_BENCH_OLD_SCRIPT")?.let(::File)
    private val only = System.getenv("ONEIOS_BENCH_ONLY")?.split(',')?.toSet()

    private fun tar(): InputStream = ZstdInputStream(BufferedInputStream(pkg!!.inputStream(), 1 shl 20)).setContinuous(false).setLongMax(27)

    private fun say(line: String) {
        File(dir, "results.txt").appendText(line + "\n")
        println(line)
    }

    private fun timed(name: String, bytes: () -> Long) {
        if (only != null && name.substringBefore(':') !in only) return
        val t = System.nanoTime()
        val n = bytes()
        val s = (System.nanoTime() - t) / 1e9
        say(String.format("%-58s %7.1f MB/s  %6.2f s  %5.2f GB", name, n / 1e6 / s, s, n / 1e9))
    }

    @Test
    fun bench() {
        assumeTrue(pkg != null && dir != null && pkg.isFile)
        dir!!.mkdirs()
        say("--- ${pkg!!.name}, ${pkg.length()} bytes, ${java.time.Instant.now()}")

        timed("a: zstd alone") {
            var n = 0L
            tar().use { s ->
                val buf = ByteArray(1 shl 20)
                while (true) {
                    val k = s.read(buf)
                    if (k < 0) break
                    n += k
                }
            }
            n
        }
        timed("b: zstd, tar and SHA-256 on one thread (0.4.76's app side)") {
            val found = tar().use { OneiosPackage.readManifest(it, OneiosKind.IMAGE) }
            val m = OneiosManifests.parse(OneiosKind.IMAGE, found.text).getOrThrow()
            val buf = ByteArray(1 shl 20)
            tar().use { s -> OneiosPackage.unpack(s, m, found.prefix, { _, data -> while (data.read(buf) >= 0) Unit }) }
            m.bytes
        }
        timed("c: SHA-256 alone (this JVM)") {
            val md = MessageDigest.getInstance("SHA-256")
            val buf = ByteArray(4 shl 20) { it.toByte() }
            repeat(256) { md.update(buf) }
            md.digest()
            256L * buf.size
        }
        // Root's side alone: 1 GiB from memory into `receive`.
        val gib = 1L shl 30
        val block = ByteArray(4 shl 20) { (it * 31 + it / 4096).toByte() }
        val sum = MessageDigest.getInstance("SHA-256").also { md -> repeat((gib / block.size).toInt()) { md.update(block) } }
            .digest().joinToString("") { "%02x".format(it) }
        for ((name, script) in listOfNotNull(oldScript?.let { "0.4.76" to it }, "this version" to File(Shipped.fullAssets, OneiosRoot.ASSET))) {
            val f = OneiosFakeStage("/bin/sh", dir, script)
            try {
                check(f.asRoot.run(OneiosRoot.Verb.BEGIN, listOf("image"), null, 60_000) == null)
                var fed = 0L
                val t = System.nanoTime()
                timed("d: root's receive alone, $name's script (write + check)") {
                    val p = f.asRoot.run(OneiosRoot.Verb.RECEIVE, listOf("image", "os.img", gib.toString(), sum, "0644"), { out ->
                        repeat((gib / block.size).toInt()) { out.write(block) }
                        out.flush()
                        fed = System.nanoTime() - t
                    }, 600_000)
                    check(p == null) { p!! }
                    gib
                }
                if (fed > 0) say(String.format("   of which the write %.2f s, root's check after it %.2f s", fed / 1e9, (System.nanoTime() - t - fed) / 1e9))
            } finally {
                f.delete()
            }
        }

        if (oldScript != null) {
            val f = OneiosFakeStage("/bin/sh", dir, oldScript)
            var updates = 0L
            try {
                timed("e: the whole import, 0.4.76 (two passes, one thread, old script)") { legacy(f) { updates++ } }
                say("   screen updates sent: $updates")
            } finally {
                f.delete()
            }
        }
        for ((name, hash) in listOf("f: the whole import, this version" to true, "g: the whole import, this version without the app's SHA-256" to false)) {
            val f = OneiosFakeStage("/bin/sh", dir)
            var updates = 0L
            var single = false
            try {
                timed(name) {
                    val meter = ByteMeter(System::currentTimeMillis)
                    val r = OneiosImport(OneiosKind.IMAGE, f.asRoot, object : OneiosImport.Listener {
                        override fun bytes(done: Long, total: Long) {
                            if (meter.tick(done, total) != null) updates++
                        }
                    }, appHash = hash).run({ tar() }, emptyList())
                    single = r.singlePass
                    r.manifest.bytes
                }
                say("   screen updates sent: $updates, single pass: $single")
            } finally {
                f.delete()
            }
        }
    }

    /** 0.4.76's OneiosJob.stage, as it was: the manifest pass, then read, hash and write on the stdin thread, 1 MiB at a time. */
    private fun legacy(f: OneiosFakeStage, update: () -> Unit): Long {
        fun must(p: String?) = check(p == null) { p!! }
        val found = tar().use { OneiosPackage.readManifest(it, OneiosKind.IMAGE) }
        val m = OneiosManifests.parse(OneiosKind.IMAGE, found.text).getOrThrow()
        must(f.asRoot.run(OneiosRoot.Verb.BEGIN, listOf("image"), null, 60_000))
        val text = found.text.toByteArray()
        must(f.asRoot.run(OneiosRoot.Verb.RECEIVE, listOf("image", "manifest.json", text.size.toString(), com.fahadali.oneos.core.model.Hashes.sha256(text), "0644"), { it.write(text) }, 60_000))
        var shown = 0L
        tar().use { s ->
            OneiosPackage.unpack(s, m, found.prefix, { file: OneiosFile, data: InputStream ->
                must(f.asRoot.run(OneiosRoot.Verb.RECEIVE, listOf("image", file.path, file.size.toString(), file.sha256, file.mode), { out ->
                    val buf = ByteArray(1 shl 20)
                    while (true) {
                        val n = data.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                    }
                }, 20 * 60_000L))
            }) { done ->
                // "A state per MB at most."
                if (done - shown >= (1 shl 20) || done >= m.bytes) {
                    shown = done
                    update()
                }
            }
        }
        must(f.asRoot.run(OneiosRoot.Verb.FINISH, listOf("image", (m.files.size + 1).toString(), m.format.toString(), m.version, m.build ?: "unknown"), null, 600_000))
        return m.bytes
    }
}
