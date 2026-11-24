package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosTool
import com.fahadali.oneos.core.model.OneiosToolFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Update the kernel's order and its rules ([OneiosKernelUpdate]; docs/oneios.md, "Kernel updates"), against a
 * stand-in of the tool and of root that records what was asked: the requests and verbs in order, a kernelcache
 * already on the phone skipping the download, a decoded file that is not the pinned one refused and removed, a
 * Stop removing the work, a lost network keeping the parts for the next run. OneiosScriptTest runs root's two new
 * verbs themselves, and the same update against the real tool when one is given.
 */
class OneiosKernelUpdateTest {
    private val stage = "/data/local/tmp/oneios"
    private val pin = "349c4692a6a85df0d396681f28d2d48dc04b95c6d60df0f94d84501e3d0c57e3"
    private val kc = "e".repeat(64)
    private val names = OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }
    private val assets = names.associateWith { "kb-$it".toByteArray() }
    private val kb = OneiosKb("24A446", "iPhone18,2", pin, assets.mapValues { Hashes.sha256(it.value) })

    /** What a stand-in answers: per command, the end and the result. */
    private class Fake(
        val ends: Map<String, OneiosToolFlow> = emptyMap(),
        val roots: Map<OneiosRoot.Verb, String?> = emptyMap(),
        val stopAt: String? = null,
    ) : OneiosKernelUpdate.Io {
        val asked = mutableListOf<String>()
        val keys = mutableListOf<Map<String, Any?>>()
        val phases = mutableListOf<OneiosKernelUpdate.Phase>()
        val lines = mutableListOf<String>()
        var stop = false

        override fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow {
            asked += cmd
            this.keys += keys
            if (cmd == stopAt) {
                stop = true
                return OneiosToolFlow(end = OneiosToolFlow.End.CANCELLED, text = "cancelled: removed 1 file")
            }
            return ends[cmd] ?: error("no answer for $cmd")
        }

        override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? {
            asked += if (verb == OneiosRoot.Verb.KBINPUT) "kbinput ${args[0]}" else (listOf(verb.word) + args).joinToString(" ")
            if (verb == OneiosRoot.Verb.KBINPUT) {
                assertEquals(args[1], data!!.size.toString())
                assertEquals(args[2], Hashes.sha256(data))
            }
            return roots[verb]
        }

        override fun phase(phase: OneiosKernelUpdate.Phase) {
            phases += phase
        }

        override fun done(line: String) {
            lines += line
        }

        override val stopped: Boolean get() = stop
    }

    private fun ok(vararg result: Pair<String, Any?>) = OneiosToolFlow(end = OneiosToolFlow.End.OK, result = mapOf(*result), text = "ok")
    private fun no(end: OneiosToolFlow.End, code: String?, text: String) = OneiosToolFlow(end = end, code = code, text = text)

    private val good = mapOf(
        OneiosTool.Cmd.FETCH to ok("indir" to "$stage/make-kernel/inputs", "bytes" to 23_391_114L),
        OneiosTool.Cmd.IM4P to ok("kind" to "krnl", "bytes" to 78_135_296L, "sha256" to pin),
        OneiosTool.Cmd.PRELINK to ok("kc" to "$stage/make-kernel/out/kernel.kc", "bytes" to 100L, "sha256" to kc),
    )

    private fun update() = OneiosKernelUpdate(stage, kb, "kernel/xnu.macho", assets)

    private val inputs = names.sorted().map { "kbinput $it" }

    @Test
    fun withNoKernelcacheTheUpdateFetchesDecodesKeepsAndBuilds() {
        val io = Fake(good)
        val o = update().run(io, cachedSha256 = null)
        assertEquals(OneiosKernelUpdate.Outcome.Built(kc, 100L, downloaded = true), o)
        assertEquals(inputs + listOf("fetch", "im4p", "kbcache 78135296 $pin", "prelink"), io.asked)
        // The requests' keys are the tool's (OneiosTest checks each), in this order.
        assertEquals(
            listOf(OneiosTool.kernelcacheFetchRequest(stage).second, OneiosTool.kernelcacheDecodeRequest(stage).second, OneiosTool.prelinkRequest("kernel/xnu.macho", stage).second),
            io.keys,
        )
        assertEquals(
            listOf(OneiosKernelUpdate.Phase.INPUTS, OneiosKernelUpdate.Phase.DOWNLOAD, OneiosKernelUpdate.Phase.DECODE, OneiosKernelUpdate.Phase.KEEP, OneiosKernelUpdate.Phase.BUILD),
            io.phases,
        )
        assertEquals(listOf("fetch", "im4p", "prelink"), OneiosKernelUpdate.toolRequests(stage, "kernel/xnu.macho", cached = false).map { it.first })
        assertTrue(io.lines.any { "downloaded from Apple" in it })
    }

    @Test
    fun aKernelcacheAlreadyOnThePhoneIsNotDownloadedAgain() {
        val io = Fake(good)
        // (root's `kb` line, as status prints it; any case)
        val o = update().run(io, cachedSha256 = pin.uppercase())
        assertEquals(OneiosKernelUpdate.Outcome.Built(kc, 100L, downloaded = false), o)
        assertEquals(inputs + "prelink", io.asked)
        assertTrue(OneiosKernelUpdate.Phase.CACHED in io.phases)
        assertEquals(listOf("prelink"), OneiosKernelUpdate.toolRequests(stage, "kernel/xnu.macho", cached = true).map { it.first })
        // Another file in kb/ (an older pin): fetched again.
        val again = Fake(good)
        update().run(again, cachedSha256 = "0".repeat(64))
        assertTrue("fetch" in again.asked)
    }

    @Test
    fun aDecodedKernelcacheThatIsNotThePinnedOneIsRefusedAndRemoved() {
        val io = Fake(good + (OneiosTool.Cmd.IM4P to ok("kind" to "krnl", "bytes" to 78_135_296L, "sha256" to "0".repeat(64))))
        val o = update().run(io, null) as OneiosKernelUpdate.Outcome.Stopped
        assertEquals("im4p", o.step)
        assertEquals("mismatch", o.code)
        assertTrue(o.text!!, "the profile pins $pin" in o.text!!)
        assertTrue(o.cleaned)
        // Never into kb/, never built: the work folder goes.
        assertEquals(inputs + listOf("fetch", "im4p", "kbclean"), io.asked)
        // Root's own check refusing it (root hashes the file again) is the same refusal.
        val rootSays = Fake(good, roots = mapOf(OneiosRoot.Verb.KBCACHE to "the fetched kernelcache is not the one the profile pins (its SHA-256 differs): nothing was kept"))
        val r = update().run(rootSays, null) as OneiosKernelUpdate.Outcome.Stopped
        assertEquals("kbcache" to "mismatch", r.step to r.code)
        assertEquals(inputs + listOf("fetch", "im4p", "kbcache 78135296 $pin", "kbclean"), rootSays.asked)
        // The tool's own pin of the IPSW member (the profile's SHA-384): refused before anything is decoded.
        val member = Fake(good + (OneiosTool.Cmd.FETCH to no(OneiosToolFlow.End.REFUSED, "mismatch", "kernelcache.release.v54: sha384 ab, the profile pins cd")))
        assertEquals("mismatch", (update().run(member, null) as OneiosKernelUpdate.Outcome.Stopped).code)
        assertEquals(inputs + listOf("fetch", "kbclean"), member.asked)
    }

    @Test
    fun aStopRemovesTheWorkAndTheKernelcacheInKbStays() {
        for (at in listOf("fetch", "im4p", "prelink")) {
            val io = Fake(good, stopAt = at)
            val o = update().run(io, null) as OneiosKernelUpdate.Outcome.Stopped
            assertEquals(at, o.step)
            assertEquals(OneiosToolFlow.End.CANCELLED, o.end)
            assertTrue(o.cleaned)
            assertEquals("kbclean", io.asked.last())
            assertFalse("prelink after a stop", at != "prelink" && "prelink" in io.asked)
            // (kbclean removes make-kernel/ only: OneiosScriptTest checks kb/kernelcache.macho stays)
        }
        // A Stop between two steps: the next step does not start.
        val between = object : OneiosKernelUpdate.Io by Fake(good) {
            val asked = mutableListOf<String>()
            override fun tool(cmd: String, keys: Map<String, Any?>): OneiosToolFlow = error("no request after a stop: $cmd")
            override fun root(verb: OneiosRoot.Verb, args: List<String>, data: ByteArray?): String? = null.also { asked += verb.word }
            override val stopped = true
        }
        val o = update().run(between, null) as OneiosKernelUpdate.Outcome.Stopped
        assertEquals(OneiosToolFlow.End.CANCELLED, o.end)
        assertEquals(listOf("kbclean"), between.asked)
    }

    @Test
    fun whatCanGoOnLaterKeepsTheDownloadsParts() {
        for ((end, code) in listOf(
            OneiosToolFlow.End.FAILED to "network", OneiosToolFlow.End.LOST to null,
            OneiosToolFlow.End.REFUSED to "space", OneiosToolFlow.End.REFUSED to "heat", OneiosToolFlow.End.REFUSED to "battery",
        )) {
            val io = Fake(good + (OneiosTool.Cmd.FETCH to no(end, code, "the tool's words")))
            val o = update().run(io, null) as OneiosKernelUpdate.Outcome.Stopped
            assertEquals(end to code, o.end to o.code)
            assertFalse("$end $code", o.cleaned)
            assertEquals(inputs + "fetch", io.asked)
        }
        // A server file that changed, a decode or a build that failed: nothing to go on from.
        for ((cmd, v) in listOf(
            OneiosTool.Cmd.FETCH to no(OneiosToolFlow.End.FAILED, "changed", "the server's file changed"),
            OneiosTool.Cmd.IM4P to no(OneiosToolFlow.End.FAILED, "failed", "not an IM4P"),
            OneiosTool.Cmd.PRELINK to no(OneiosToolFlow.End.REFUSED, "audit", "2 binds failed"),
        )) {
            val io = Fake(good + (cmd to v))
            val o = update().run(io, null) as OneiosKernelUpdate.Outcome.Stopped
            assertTrue(cmd, o.cleaned)
            assertEquals("kbclean", io.asked.last())
        }
        // The room for the decode short: the IM4P stays for the next run.
        val room = Fake(good + (OneiosTool.Cmd.IM4P to no(OneiosToolFlow.End.REFUSED, "space", "Not enough free space")))
        assertFalse((update().run(room, null) as OneiosKernelUpdate.Outcome.Stopped).cleaned)
    }

    @Test
    fun theAppsPairingFilesMustBeThePinnedOnesBeforeRootIsAsked() {
        val bad = assets + (names.first() to "not it".toByteArray())
        val io = Fake(good)
        val o = OneiosKernelUpdate(stage, kb, "kernel/xnu.macho", bad).run(io, null) as OneiosKernelUpdate.Outcome.Stopped
        assertEquals("kbinput" to "mismatch", o.step to o.code)
        assertTrue(o.text!!, "not the pinned one" in o.text!!)
        assertEquals(emptyList<String>(), io.asked)
        // Root refusing one (a session, a link): stopped there, nothing of the tool asked.
        val refused = Fake(good, roots = mapOf(OneiosRoot.Verb.KBINPUT to "an iOS session is running: return to One UI first"))
        val r = update().run(refused, null) as OneiosKernelUpdate.Outcome.Stopped
        assertEquals("kbinput", r.step)
        assertEquals(listOf(inputs.first()), refused.asked)
    }

    @Test
    fun aBuildWithNoKernelShaIsNotOfferedForActivation() {
        val io = Fake(good + (OneiosTool.Cmd.PRELINK to ok("kc" to "x", "bytes" to 1L)))
        val o = update().run(io, pin) as OneiosKernelUpdate.Outcome.Stopped
        assertEquals("prelink" to "internal", o.step to o.code)
    }

    /** The message after Activate names what root did with the A56's GPU addon, and only for a set whose finish said. */
    @Test
    fun theActivationTextSaysWhatHappenedToTheA56GpuAddon() {
        val bid = "xnu-12377.121.6-ios-27.0.1-24A446-abcdef012345"
        val plain = "kernel.kc $bid is activated for the next session; the previous set is kept as the fallback."
        assertEquals(plain, OneiosKernelUpdate.activatedText(bid, emptyList()))
        assertEquals(plain, OneiosKernelUpdate.activatedText(bid, listOf("a56-gpu maybe something")))
        val placed = OneiosKernelUpdate.gpuAddon(listOf("a56-gpu placed kernel.kc.gpuaddon ab (9 bytes), owner-trust.json cd"))!!
        assertEquals(OneiosKernelUpdate.GpuAddon.State.PLACED, placed.state)
        assertEquals("kernel.kc.gpuaddon ab (9 bytes), owner-trust.json cd", placed.words)
        val text = OneiosKernelUpdate.activatedText(bid, listOf("a56-gpu placed kernel.kc.gpuaddon ab (9 bytes), owner-trust.json cd"))
        assertTrue(text, text.startsWith(plain) && text.contains("GPU addon (Metal and OpenGL ES for iOS 16.5) is in place too: kernel.kc.gpuaddon ab"))
        val none = OneiosKernelUpdate.activatedText(bid, listOf("a56-gpu none the runtime carries no A56 plug-ins"))
        assertTrue(none, none.contains("No GPU addon was placed: the runtime carries no A56 plug-ins."))
        val skipped = OneiosKernelUpdate.activatedText(bid, listOf("a56-gpu skipped oneios-tool image a56-gpu-place ended with status 101"))
        assertTrue(skipped, skipped.contains("was not placed: oneios-tool image a56-gpu-place ended with status 101.") && skipped.contains("2D"))
    }
}
