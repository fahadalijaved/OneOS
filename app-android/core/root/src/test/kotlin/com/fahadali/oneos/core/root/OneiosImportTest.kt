package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosFile
import com.fahadali.oneos.core.model.OneiosKind
import com.github.luben.zstd.ZstdInputStream
import com.github.luben.zstd.ZstdOutputStream
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.InputStream

/**
 * The import of a OneiOS package as the app runs it ([OneiosImport] over
 * [RootShell]), against the root script and a fake root folder, from a real
 * `.tar.zst` made here of made-up bytes: one pass when the manifest is first,
 * two when it is not, and what root refuses.
 */
class OneiosImportTest {
    private val shells: List<String> =
        (listOf("/bin/sh") + TestShell.available().filterNot { it.appletsFirst }.map { it.path }).filter { File(it).canExecute() }.distinct()
    private val stages = mutableListOf<OneiosFakeStage>()

    @After
    fun cleanUp() = stages.forEach { it.delete() }

    private fun each(body: (OneiosFakeStage) -> Unit) {
        assumeTrue("no shell to run the scripts under", shells.isNotEmpty())
        for (sh in shells) body(OneiosFakeStage(sh).also { stages += it })
    }

    private class Tar {
        val out = ByteArrayOutputStream()

        private fun header(name: String, size: Long, type: Char) {
            val h = ByteArray(512)
            fun put(s: String, off: Int) = s.toByteArray().copyInto(h, off)
            put(name, 0)
            put("0000644\u0000", 100)
            put(String.format("%011o\u0000", size), 124)
            for (i in 148..155) h[i] = ' '.code.toByte()
            h[156] = type.code.toByte()
            put("ustar\u000000", 257)
            put(String.format("%06o\u0000 ", h.sumOf { it.toInt() and 0xff }), 148)
            out.write(h)
        }

        fun file(name: String, b: ByteArray) = apply {
            header(name, b.size.toLong(), '0')
            out.write(b)
            out.write(ByteArray((512 - b.size % 512) % 512))
        }

        fun dir(name: String) = apply { header("$name/", 0, '5') }
        fun link(name: String) = apply { header(name, 0, '2') }

        fun zst(): ByteArray {
            val z = ByteArrayOutputStream()
            ZstdOutputStream(z).use {
                it.write(out.toByteArray())
                it.write(ByteArray(1024))
            }
            return z.toByteArray()
        }
    }

    private val os = ByteArray(300_000) { (it * 13 + it / 977).toByte() }
    private val kc = ByteArray(70_001) { (it xor (it shr 8)).toByte() }
    private val small = "a small file\n".toByteArray()
    private val files = linkedMapOf("os.img" to os, "overlay/kernel.kc" to kc, "overlay/a/small.txt" to small)

    private fun manifest(files: Map<String, ByteArray>, wrong: Map<String, String> = emptyMap()) =
        """{ "format": 1, "name": "oneios-image", "version": "27.0.1", "build": "24A446", "files": [""" +
            files.entries.joinToString(",") { (p, b) -> """{ "path": "$p", "size": ${b.size}, "sha256": "${wrong[p] ?: Hashes.sha256(b)}" }""" } + "] }"

    private fun pack(files: Map<String, ByteArray>, manifestFirst: Boolean = true, wrong: Map<String, String> = emptyMap(), more: Tar.() -> Unit = {}): ByteArray {
        val t = Tar()
        val m = manifest(files, wrong).toByteArray()
        if (manifestFirst) t.file("manifest.json", m)
        t.dir("overlay").dir("overlay/a")
        for ((p, b) in files) t.file(p, b)
        t.more()
        if (!manifestFirst) t.file("manifest.json", m)
        return t.zst()
    }

    private class Seen : OneiosImport.Listener {
        val steps = mutableListOf<String>()
        val started = mutableListOf<String>()
        var done = 0L
        var total = 0L
        var counts = 0

        override fun step(text: String) {
            steps += text
        }

        override fun file(index: Int, count: Int, file: OneiosFile) {
            started += OneiosImport.fileLine(index, count, file)
        }

        override fun bytes(done: Long, total: Long) {
            assertTrue(done >= this.done)
            this.done = done
            this.total = total
            counts++
        }
    }

    private class Source(private val zst: ByteArray) : () -> InputStream {
        var opened = 0
        override fun invoke(): InputStream {
            opened++
            return ZstdInputStream(ByteArrayInputStream(zst))
        }
    }

    private val scripts = listOf("oneios_switch.sh", "oneios_return.sh").map { n ->
        File(Shipped.switcherAssets, n).readBytes().let { OneiosImport.Script(n, it, Hashes.sha256(it)) }
    }

    private fun import(
        f: OneiosFakeStage, zst: ByteArray, seen: Seen = Seen(), appHash: Boolean = true, overlap: Long = OneiosImport.OVERLAP_BYTES,
    ): Pair<Result<OneiosImport.Result>, Source> {
        val source = Source(zst)
        return runCatching { OneiosImport(OneiosKind.IMAGE, f.asRoot, seen, appHash, overlap).run(source, scripts) } to source
    }

    private fun staged(f: OneiosFakeStage, files: Map<String, ByteArray>) {
        for ((p, b) in files) assertTrue(p, File(f.stage, "image/$p").readBytes().contentEquals(b))
        assertFalse(File(f.stage, "image.new").exists())
    }

    @Test
    fun aPackageWithItsManifestFirstIsImportedInOnePass() = each { f ->
        val seen = Seen()
        val (r, source) = import(f, pack(files), seen)
        val result = r.getOrThrow()
        assertTrue(result.singlePass)
        assertEquals("the archive was opened once", 1, source.opened)
        staged(f, files)
        assertTrue(File(f.stage, "image/manifest.json").isFile)
        assertTrue(File(f.stage, "oneios_switch.sh").isFile)
        assertEquals(
            listOf("File 1 of 3: os.img (300 kB)", "File 2 of 3: overlay/kernel.kc (70 kB)", "File 3 of 3: overlay/a/small.txt (13 B)"),
            seen.started,
        )
        assertEquals(result.manifest.bytes, seen.done)
        assertEquals(result.manifest.bytes, seen.total)
        // begin, the two scripts, the manifest, the files, finish: nothing else was asked of root.
        assertEquals(listOf("begin", "script", "script", "receive", "receive", "receive", "receive", "finish"), f.calls.map { it.substringBefore(' ') })
        val (reply, _) = f.verb(OneiosRoot.Verb.STATUS, emptyList())
        assertEquals("27.0.1", OneiosStatus.parse(reply.results).image?.version)
    }

    @Test
    fun aPackageWhoseManifestIsNotFirstTakesTheTwoPasses() = each { f ->
        val (r, source) = import(f, pack(files, manifestFirst = false))
        assertFalse(r.getOrThrow().singlePass)
        assertEquals(2, source.opened)
        staged(f, files)
    }

    @Test
    fun rootRefusesAFileThatIsNotWhatTheManifestSaysAndNothingIsPutInPlace() = each { f ->
        import(f, pack(files)).first.getOrThrow()
        val before = File(f.stage, "image/os.img").readBytes()
        // The manifest names another SHA-256 for a file; the app's own hash is off, so the refusal is root's.
        val other = files.toMutableMap().also { it["os.img"] = ByteArray(1000) { 9 } }
        val (r, _) = import(f, pack(other, wrong = mapOf("overlay/kernel.kc" to "0".repeat(64))), appHash = false)
        val why = r.exceptionOrNull()
        assertTrue("$why", why is OneiosImport.Failed && why.message!!.contains("did not arrive intact"))
        // finish was never asked; what was staged before is as it was.
        assertFalse(f.calls.drop(8).any { it.startsWith("finish") })
        assertTrue(File(f.stage, "image/os.img").readBytes().contentEquals(before))
        assertFalse(File(f.stage, "image.new/overlay/kernel.kc").exists())
        assertFalse(File(f.stage, "image.new/overlay/kernel.kc.part").exists())
        // With the app's hash on, the same package fails as well.
        assertTrue(import(f, pack(other, wrong = mapOf("overlay/kernel.kc" to "0".repeat(64)))).first.isFailure)
        assertTrue(File(f.stage, "image/os.img").readBytes().contentEquals(before))
    }

    @Test
    fun linksUnlistedFilesAndDamageEndTheImport() = each { f ->
        fun why(zst: ByteArray) = import(f, zst).first.exceptionOrNull().also { assertTrue("$it", it is OneiosImport.Failed) }!!.message!!
        assertTrue(why(pack(files) { link("overlay/link") }).contains("link or a special file"))
        assertTrue(why(pack(files) { file("extra.bin", ByteArray(5)) }).contains("extra.bin is not in manifest.json"))
        assertTrue(why(pack(files - "overlay/a/small.txt" + ("overlay/a/small.txt" to small)).let { z -> z.copyOf(z.size / 2) }).isNotEmpty())
        assertTrue(why("not a package".toByteArray()).contains("not a .tar.zst"))
        // A file the manifest lists and the archive lacks.
        val t = Tar().file("manifest.json", manifest(files).toByteArray()).file("os.img", os).zst()
        assertTrue(why(t).contains("missing"))
        assertFalse(File(f.stage, "image").exists())
    }

    @Test
    fun rootChecksALargeFileWhileTheNextOneIsSent() = each { f ->
        // "Large" from 1 MiB here, so the test needs no 64 MiB files.
        val large = 1L shl 20
        val big = ByteArray(3 * large.toInt() + 12345) { (it * 7 + it / 4096).toByte() }
        val big2 = ByteArray(large.toInt()) { (it / 8192 + 1).toByte() }
        val set = linkedMapOf("os.img" to big, "systemos.img" to big2, "overlay/kernel.kc" to kc, "overlay/a/small.txt" to small)
        val seen = Seen()
        import(f, pack(set), seen, overlap = large).first.getOrThrow()
        staged(f, set)
        assertEquals(set.values.sumOf { it.size.toLong() }, seen.done)
        // A large file root refuses ends the import though the next file was already on its way.
        val (r, _) = import(f, pack(set, wrong = mapOf("os.img" to "f".repeat(64))), appHash = false, overlap = large)
        val why = r.exceptionOrNull()
        assertTrue("$why", why is OneiosImport.Failed && why.message!!.contains("did not arrive intact"))
        assertFalse(f.calls.takeLastWhile { !it.startsWith("begin") }.any { it.startsWith("finish") })
        // What was staged before is as it was; the refused file is not in image.new under its name.
        for ((p, b) in set) assertTrue(p, File(f.stage, "image/$p").readBytes().contentEquals(b))
        assertFalse(File(f.stage, "image.new/os.img").exists())
    }

    @Test
    fun aStopEndsTheImport() = each { f ->
        val listener = object : OneiosImport.Listener {
            var stop = false
            override fun file(index: Int, count: Int, file: OneiosFile) {
                if (index == 2) stop = true
            }

            override fun stopped() = stop
        }
        val r = runCatching { OneiosImport(OneiosKind.IMAGE, f.asRoot, listener).run(Source(pack(files)), scripts) }
        assertEquals("stopped", r.exceptionOrNull()?.message)
        assertFalse(File(f.stage, "image").exists())
    }
}
