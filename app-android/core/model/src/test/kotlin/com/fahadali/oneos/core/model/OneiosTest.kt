package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream

/** The iOS 27 (OneiOS) system: where it is offered, its manifests, its packages and its releases. */
class OneiosTest {
    private fun sha(b: ByteArray) = Hashes.sha256(b)

    private val xnuhost = "xnuhost-bytes".toByteArray()
    private val stub = ByteArray(700) { (it % 251).toByte() }

    private fun runtimeJson(
        format: Int = 1,
        abi: Int = 1,
        xnuhostPath: String? = "bin/xnuhost",
        xnuhostMode: String = "0755",
        extra: String = "",
    ) = """
        {
          "format": $format, "name": "oneios-runtime", "version": "0.1.0", "arch": "arm64",
          "session_abi": $abi, "image_formats": [1],
          ${xnuhostPath?.let { "\"xnuhost\": \"$it\"," }.orEmpty()}
          "files": [
            { "path": "bin/xnuhost", "size": ${xnuhost.size}, "sha256": "${sha(xnuhost)}", "mode": "$xnuhostMode" },
            { "path": "bin/stub", "size": ${stub.size}, "sha256": "${sha(stub)}", "mode": "0755" }$extra
          ]
        }
    """.trimIndent()

    private val os = ByteArray(3000) { (it * 7).toByte() }
    private val kc = "kernel collection".toByteArray()

    private fun imageJson(format: Int = 1) = """
        { "format": $format, "name": "oneios-image", "os": "iOS", "version": "27.0.1", "build": "24A446",
          "device": "iPhone18,2", "built_by": "scripts/image/build.sh",
          "files": [
            { "path": "os.img", "size": ${os.size}, "sha256": "${sha(os)}" },
            { "path": "overlay/kernel.kc", "size": ${kc.size}, "sha256": "${sha(kc).uppercase()}" }
          ] }
    """.trimIndent()

    // --- Where it is offered ---------------------------------------------------

    @Test
    fun theGalaxyS24UltraAndTheA56AreOfferedOnlyTheS24UltraIsTested() {
        for (p in Profiles.BUILT_IN) {
            assertEquals(p.id, p.id == Profiles.ID_S_ULTRA_8650 || p.id == Profiles.ID_A56, OneiosSystem.offeredOn(p))
            assertEquals(p.id, p.id == Profiles.ID_S_ULTRA_8650, OneiosSystem.testedOn(p))
        }
        assertFalse(OneiosSystem.offeredOn(null))
        assertFalse(OneiosSystem.testedOn(null))
        assertEquals("SM-S928", Profiles.S_ULTRA_8650.modelPrefix)
        assertTrue(OneiosSystem.offeredOn("SM-S928B", "e3q", "SM8650"))
        assertTrue(OneiosSystem.offeredOn("SM-S928U1", "e3q", "SM8650"))
        // The Galaxy A56 (OneiOS issue 73): offered, with iOS 16.5; untested on an A56.
        assertTrue(OneiosSystem.offeredOn("SM-A566B", "a56x", "s5e8855"))
        assertFalse(OneiosSystem.testedOn(Profiles.resolve("SM-A566B", "a56x", "s5e8855").profile))
        // The same model number on another chip or codename is not that phone.
        assertFalse(OneiosSystem.offeredOn("SM-S928B", "e3s", "s5e9945"))
        assertFalse(OneiosSystem.offeredOn("SM-S938B", "pa3q", "SM8750"))
        assertFalse(OneiosSystem.offeredOn("SM-S921B", "e1q", "SM8650"))
        assertFalse(OneiosSystem.offeredOn("SM-F976B", "q8q", "SM8850"))
        assertFalse(OneiosSystem.offeredOn("SM-A576B", "a57x", "s5e8865"))
    }

    /**
     * Every S24 Ultra model number gets the card, the gate and the switch as the owner's SM-S928B does: the US U and
     * U1, Canada's W (stock: the US bootloader and vendor model, public issue 128), Korea's N, China's 0.
     */
    @Test
    fun everyS24UltraModelGetsTheSameCardAsTheS928B() {
        val b = OneiosSystem.gate(Profiles.resolve("SM-S928B", "e3q", "SM8650").profile, ticked = false)
        for (model in listOf("SM-S928U", "SM-S928U1", "SM-S928W", "SM-S928N", "SM-S9280")) {
            val p = Profiles.resolve(model, "e3q", "SM8650").profile
            assertEquals(model, Profiles.S_ULTRA_8650, p)
            assertTrue(model, OneiosSystem.offeredOn(model, "e3q", "SM8650"))
            assertEquals(model, b, OneiosSystem.gate(p, ticked = false))
            assertEquals(model, Level.OK, OneiosSystem.gate(p, ticked = true).level)
        }
        // The SM-S928W's stock firmware is no custom ROM, with either bootloader and with or without its vendor model.
        for (bl in listOf("S928USQU6EZIF", "S928WVLU6EZIF")) {
            assertNull(bl, CustomRomRule.check(CustomRomRule.Signals("SM-S928W", bl, "SM-S928U", "90000")))
            assertNull(bl, CustomRomRule.check(CustomRomRule.Signals("SM-S928W", bl, "", "90000")))
        }
    }

    @Test
    fun aDisabledProfileIsNotOffered() {
        assertFalse(OneiosSystem.offeredOn(Profiles.S_ULTRA_8650.copy(enabled = false, disabledReason = "x")))
    }

    @Test
    fun theGateWarnsOtherPhonesAndAsksForBothTicks() {
        val other = OneiosSystem.gate(Profiles.F8U, ticked = true)
        assertEquals(Level.WARN, other.level)
        assertEquals(OneiosSystem.R_NOT_THIS_PHONE, other.reason)
        assertTrue(other.detail.contains("mainly tested"))
        assertEquals(Level.WARN, OneiosSystem.gate(null, ticked = true).level)
        assertEquals(Level.OK, OneiosSystem.gate(Profiles.F8U, ticked = true, notThisPhoneTicked = true).level)
        val ask = OneiosSystem.gate(Profiles.S_ULTRA_8650, ticked = false)
        assertEquals(Level.WARN, ask.level)
        assertEquals(OneiosSystem.R_EXPERIMENTAL, ask.reason)
        assertTrue(ask.detail.contains("experimental"))
        assertEquals(Level.OK, OneiosSystem.gate(Profiles.S_ULTRA_8650, ticked = true).level)
    }

    /** The S26 Ultra (SM-S948, m3q, SM8850): warned, not refused (YMGPwcca/OneOS refuses it), with what another fork
     *  measured on it; once ticked it switches like any other phone. No other phone gets the note. */
    @Test
    fun theS26UltraIsWarnedWithWhatIsKnownNotRefused() {
        val r = Profiles.resolve("SM-S948B", "m3q", "SM8850")
        assertEquals(Profiles.ID_S_ULTRA_8850, r.profile?.id)
        assertFalse(OneiosSystem.offeredOn(r.profile))
        val g = OneiosSystem.gate(r.profile, ticked = true)
        assertEquals(Level.WARN, g.level)
        assertEquals(OneiosSystem.R_NOT_THIS_PHONE, g.reason)
        assertTrue(g.detail, g.detail.contains("this phone is the Galaxy S26 Ultra"))
        assertTrue(g.detail, g.detail.endsWith(OneiosSystem.NOT_THIS_PHONE_NOTES.getValue(Profiles.ID_S_ULTRA_8850)))
        assertEquals(Level.OK, OneiosSystem.gate(r.profile, ticked = true, notThisPhoneTicked = true).level)
        assertFalse(OneiosSystem.gate(Profiles.F8U, ticked = true).detail.contains("S26"))
        assertFalse(OneiosSystem.gate(null, ticked = true).detail.contains("S26"))
    }

    /**
     * The Galaxy A56 (SM-A566, a56x, s5e8855; OneiOS issue 73): offered, but not the phone it is tested on, so the
     * gate warns it with its note (iOS 16.5, not iOS 27; untested on an A56) until the not-this-phone tick, as any
     * other phone. The S24 Ultra's gate and another phone's are as before.
     */
    @Test
    fun theA56IsOfferedAndWarnedWithItsNote() {
        val a56 = Profiles.resolve("SM-A566B", "a56x", "s5e8855").profile
        assertEquals(Profiles.ID_A56, a56?.id)
        val g = OneiosSystem.gate(a56, ticked = true)
        assertEquals(Level.WARN, g.level)
        assertEquals(OneiosSystem.R_NOT_THIS_PHONE, g.reason)
        assertTrue(g.detail, g.detail.contains("this phone is the Galaxy A56"))
        val note = OneiosSystem.NOT_THIS_PHONE_NOTES.getValue(Profiles.ID_A56)
        assertTrue(g.detail, g.detail.endsWith(note))
        for (words in listOf("iOS 16.5 (20F66), not iOS 27", "Musicalista/OneiOS-A56", "touch did not work", "has not run on an A56 yet", "restarts the phone into One UI")) {
            assertTrue(words, note.contains(words))
        }
        assertEquals(Level.WARN, OneiosSystem.gate(a56, ticked = false).level)
        assertEquals(Level.OK, OneiosSystem.gate(a56, ticked = false, notThisPhoneTicked = true).level)
        // The S24 Ultra: the experimental tick only, as before; no phone note.
        val s24 = OneiosSystem.gate(Profiles.S_ULTRA_8650, ticked = false)
        assertEquals(Finding(OneiosSystem.GATE_ID, Level.WARN, "${OneiosSystem.NAME} is experimental", OneiosSystem.ACK, OneiosSystem.R_EXPERIMENTAL), s24)
        assertEquals(Level.OK, OneiosSystem.gate(Profiles.S_ULTRA_8650, ticked = true).level)
        // Another phone: warned as before, without the A56's note.
        assertFalse(OneiosSystem.gate(Profiles.F8U, ticked = true).detail.contains("A56"))
        assertFalse(OneiosSystem.gate(Profiles.S_ULTRA_8650, ticked = false).detail.contains("A56"))
    }

    /**
     * Which image a phone makes (docs/oneios.md, "Galaxy A56"): the A56 iOS 16.5 (20F66) from the runtime's
     * ios-16.5-a56.toml, with its download and room; every other phone, and an unknown one, exactly today's iOS 27
     * values. Only the A56's needs Apple's 24A446 kernelcache first.
     */
    @Test
    fun theA56MakesIos165AndEveryOtherPhoneIos27() {
        val a56 = OneiosImageChoice.of(Profiles.resolve("SM-A566B", "a56x", "s5e8855").profile)
        assertEquals(OneiosImageChoice("runtime/lib/profiles/ios-16.5-a56.toml", "16.5", "20F66", 5_825_842_914L, 24L shl 30), a56)
        assertTrue(a56.needsKernelcache)
        for (p in Profiles.BUILT_IN.filter { it.id != Profiles.ID_A56 } + listOf(null)) {
            val c = OneiosImageChoice.of(p)
            assertEquals(p?.id, OneiosImageChoice.IOS_27, c)
            assertFalse(p?.id, c.needsKernelcache)
        }
        assertEquals(
            OneiosImageChoice(OneiosTool.IPSW_PROFILE, "27.0.1", "24A446", OneiosTool.MAKE_IMAGE_DOWNLOAD_BYTES, OneiosTool.MAKE_IMAGE_ROOM_BYTES),
            OneiosImageChoice.IOS_27,
        )
        // The request names the A56's profile; the S24 Ultra's is byte for byte the default one.
        val s = OneiosSystem.STAGE
        assertEquals("$s/runtime/lib/profiles/ios-16.5-a56.toml", OneiosTool.makeImageRequest(s, a56.profile).second["profile"])
        assertEquals(OneiosTool.makeImageRequest(s), OneiosTool.makeImageRequest(s, OneiosImageChoice.of(Profiles.S_ULTRA_8650).profile))
        assertEquals(
            OneiosTool.makeImageRequest(s).second - "profile",
            OneiosTool.makeImageRequest(s, a56.profile).second - "profile",
        )
        // The kernel update keeps the 27.0.1 profile on every phone (the 24A446 kernelcache).
        assertEquals("$s/${OneiosTool.IPSW_PROFILE}", OneiosTool.kernelcacheFetchRequest(s).second["profile"])
    }

    /**
     * The Android takeover's toggle (docs/oneios.md, "Android takeover"): offered on the Galaxy S24 Ultra (every model
     * number) and the Galaxy S26 Ultra, nowhere else; root's switch gets a third word only for it.
     */
    @Test
    fun theAndroidTakeoverIsOfferedOnTheS24AndS26UltraOnly() {
        for (m in listOf("SM-S928B", "SM-S928U", "SM-S928U1", "SM-S928W", "SM-S928N", "SM-S9280")) {
            assertTrue(m, OneiosSystem.takeoverOfferedOn(Profiles.resolve(m, "e3q", "SM8650").profile))
        }
        assertTrue(OneiosSystem.takeoverOfferedOn(Profiles.resolve("SM-S948B", "m3q", "SM8850").profile))
        assertFalse(OneiosSystem.takeoverOfferedOn(Profiles.resolve("SM-S938B", "pa3q", "SM8750").profile))
        assertFalse(OneiosSystem.takeoverOfferedOn(Profiles.resolve("SM-S931B", "pa1q", "SM8750").profile))
        assertFalse(OneiosSystem.takeoverOfferedOn(Profiles.F8U))
        assertFalse(OneiosSystem.takeoverOfferedOn(null))
        assertEquals(listOf("4100", "1"), OneiosSystem.switchArgs(4100, takeover = false))
        assertEquals(listOf("4100", "1", "takeover"), OneiosSystem.switchArgs(4100, takeover = true))
        // The warning says what it takes, what it writes and the way back, restart as the fallback only.
        val w = OneiosSystem.TAKEOVER_WARNING
        assertTrue(w, w.contains("touchscreen") && w.contains("caps the CPUs") && w.contains("put back") && w.contains("stops Android services") &&
            w.contains("battery gets hot (50 C and up") && !w.contains("46 C") &&
            w.contains("Volume Up + Volume Down") && w.contains("only when the return in place cannot put One UI back"))
        assertEquals("Android takeover (faster, experimental)", OneiosSystem.TAKEOVER_TITLE)
    }

    /** It is its own kind of system: no Android image or file set stands for it. */
    @Test
    fun itIsNotAnAndroidImage() {
        assertNull(Images.byId(OneiosSystem.ID))
        assertTrue(Images.ALL.none { it.name.contains("iOS") })
        assertTrue(Profiles.BUILT_IN.none { p -> p.choices.any { it.imageId == OneiosSystem.ID } })
        assertEquals("/data/local/tmp/oneios", OneiosSystem.STAGE)
    }

    // --- Manifests ---------------------------------------------------------------

    @Test
    fun aRuntimeManifestParses() {
        val m = OneiosManifests.parse(OneiosKind.RUNTIME, runtimeJson()).getOrThrow()
        assertEquals("0.1.0", m.version)
        assertEquals(1, m.sessionAbi)
        assertEquals("bin/xnuhost", m.xnuhost)
        assertEquals(listOf(1), m.imageFormats)
        assertEquals(listOf("bin/xnuhost", "bin/stub"), m.files.map { it.path })
        assertEquals("0755", m.file("bin/xnuhost")!!.mode)
        assertEquals((xnuhost.size + stub.size).toLong(), m.bytes)
    }

    /** What OneiOS's runtime/package.sh adds: the placeholder flag and the lowest fork version. */
    @Test
    fun aPlaceholderRuntimeStagesButCannotStartIos() {
        val text = runtimeJson().replace("\"session_abi\"", "\"placeholder\": true, \"min_oneos_fork\": \"0.4.74\", \"git\": {\"commit\": \"abc\", \"dirty\": false}, \"kernel\": null, \"session_abi\"")
        val m = OneiosManifests.parse(OneiosKind.RUNTIME, text).getOrThrow()
        assertTrue(m.placeholder)
        assertEquals("0.4.74", m.minOneosFork)
        val i = OneiosManifests.parse(OneiosKind.IMAGE, imageJson()).getOrThrow()
        assertTrue(OneiosManifests.pairProblem(m, i)!!.contains("placeholder"))
        assertFalse(OneiosManifests.parse(OneiosKind.RUNTIME, runtimeJson()).getOrThrow().placeholder)
        refused(OneiosKind.RUNTIME, runtimeJson().replace("\"session_abi\"", "\"placeholder\": \"no\", \"session_abi\""), "placeholder")
        assertTrue(OneiosManifests.versionAtLeast("0.4.74", "0.4.74"))
        assertTrue(OneiosManifests.versionAtLeast("0.4.74-s25", "0.4.74"))
        assertTrue(OneiosManifests.versionAtLeast("0.5.0", "0.4.74"))
        assertTrue(OneiosManifests.versionAtLeast("0.4.100", "0.4.74"))
        assertFalse(OneiosManifests.versionAtLeast("0.4.73", "0.4.74"))
        assertFalse(OneiosManifests.versionAtLeast("0.4", "0.4.74"))
        assertFalse(OneiosManifests.versionAtLeast("dev", "0.4.74"))
    }

    @Test
    fun aManifestOfTheOtherKindIsRefused() {
        refused(OneiosKind.IMAGE, imageJson().replace("oneios-image", "oneios-runtime"), "not a oneios-image")
        refused(OneiosKind.RUNTIME, runtimeJson().replace("oneios-runtime", "oneios-image"), "not a oneios-runtime")
    }

    @Test
    fun anImageManifestParsesAndIgnoresKeysItDoesNotKnow() {
        val m = OneiosManifests.parse(OneiosKind.IMAGE, imageJson()).getOrThrow()
        assertEquals("27.0.1", m.version)
        assertEquals("24A446", m.build)
        assertEquals("iPhone18,2", m.device)
        // An upper-case hash is the same hash.
        assertEquals(sha(kc), m.file("overlay/kernel.kc")!!.sha256)
        assertEquals("0644", m.file("os.img")!!.mode)
    }

    private fun refused(kind: OneiosKind, text: String, part: String) {
        val r = OneiosManifests.parse(kind, text)
        assertTrue("accepted: $text", r.isFailure)
        assertTrue("${r.exceptionOrNull()?.message} lacks '$part'", r.exceptionOrNull()!!.message!!.contains(part))
    }

    @Test
    fun aManifestOfAnotherFormatVersionIsRefused() {
        refused(OneiosKind.IMAGE, imageJson(format = 2), "format 2")
        refused(OneiosKind.IMAGE, imageJson(format = 2), "update OneOS")
        refused(OneiosKind.RUNTIME, runtimeJson(format = 0), "format 0")
        refused(OneiosKind.IMAGE, imageJson().replace("\"format\": 1,", ""), "no format")
        refused(OneiosKind.IMAGE, imageJson().replace("\"format\": 1", "\"format\": \"1\""), "whole number")
    }

    @Test
    fun aRuntimeWithoutXnuhostIsRefused() {
        refused(OneiosKind.RUNTIME, runtimeJson(xnuhostPath = null), "names no xnuhost")
        refused(OneiosKind.RUNTIME, runtimeJson(xnuhostPath = "bin/other"), "not one of its files")
        refused(OneiosKind.RUNTIME, runtimeJson(xnuhostMode = "0644"), "not mode 0755")
    }

    @Test
    fun malformedEntriesAreRefused() {
        val h = sha(os)
        fun image(entry: String) = """{"format":1,"version":"27.0.1","files":[$entry]}"""
        refused(OneiosKind.IMAGE, image("""{"path":"../os.img","size":1,"sha256":"$h"}"""), "plain relative path")
        refused(OneiosKind.IMAGE, image("""{"path":"/os.img","size":1,"sha256":"$h"}"""), "plain relative path")
        refused(OneiosKind.IMAGE, image("""{"path":"a/../b","size":1,"sha256":"$h"}"""), "plain relative path")
        refused(OneiosKind.IMAGE, image("""{"path":".hidden","size":1,"sha256":"$h"}"""), "plain relative path")
        refused(OneiosKind.IMAGE, image("""{"path":"a b","size":1,"sha256":"$h"}"""), "plain relative path")
        refused(OneiosKind.IMAGE, image("""{"path":"os.img","size":-1,"sha256":"$h"}"""), "size")
        refused(OneiosKind.IMAGE, image("""{"path":"os.img","size":1.5,"sha256":"$h"}"""), "size")
        refused(OneiosKind.IMAGE, image("""{"path":"os.img","size":1}"""), "sha256")
        refused(OneiosKind.IMAGE, image("""{"path":"os.img","size":1,"sha256":"abc"}"""), "sha256")
        refused(OneiosKind.IMAGE, image("""{"path":"os.img","size":1,"sha256":"$h","mode":"4755"}"""), "mode")
        refused(OneiosKind.IMAGE, image("""{"path":"manifest.json","size":1,"sha256":"$h"}"""), "lists itself")
        refused(OneiosKind.IMAGE, image("""{"path":"a","size":1,"sha256":"$h"},{"path":"a","size":1,"sha256":"$h"}"""), "twice")
        refused(OneiosKind.IMAGE, image("""{"path":"a","size":1,"sha256":"$h"},{"path":"a/b","size":1,"sha256":"$h"}"""), "both a file and a folder")
        refused(OneiosKind.IMAGE, """{"format":1,"version":"27.0.1","files":[]}""", "lists no files")
        refused(OneiosKind.IMAGE, """{"format":1,"files":[{"path":"a","size":1,"sha256":"$h"}]}""", "no version")
        refused(OneiosKind.IMAGE, """[1]""", "not a JSON object")
        refused(OneiosKind.IMAGE, """{"format":1,"format":1}""", "twice")
        refused(OneiosKind.IMAGE, "not json", "JSON")
    }

    // --- Verification ------------------------------------------------------------

    @Test
    fun verifyAcceptsExactlyTheListedFiles() {
        val m = OneiosManifests.parse(OneiosKind.IMAGE, imageJson()).getOrThrow()
        val good = listOf(OneiosSeen("os.img", os.size.toLong(), sha(os)), OneiosSeen("overlay/kernel.kc", kc.size.toLong(), sha(kc)))
        assertEquals(emptyList<String>(), OneiosManifests.verify(m, good))
        // The manifest itself is not one of its files.
        assertEquals(emptyList<String>(), OneiosManifests.verify(m, good + OneiosSeen("manifest.json", 10, sha(kc))))
    }

    @Test
    fun verifyNamesEveryDifference() {
        val m = OneiosManifests.parse(OneiosKind.IMAGE, imageJson()).getOrThrow()
        val kcSeen = OneiosSeen("overlay/kernel.kc", kc.size.toLong(), sha(kc))
        fun one(seen: List<OneiosSeen>) = OneiosManifests.verify(m, seen).single()
        assertTrue(one(listOf(kcSeen)).contains("os.img is missing"))
        assertTrue(one(listOf(kcSeen, OneiosSeen("os.img", os.size - 1L, sha(os)))).contains("bytes"))
        assertTrue(one(listOf(kcSeen, OneiosSeen("os.img", os.size.toLong(), sha(kc)))).contains("SHA-256"))
        val all = listOf(kcSeen, OneiosSeen("os.img", os.size.toLong(), sha(os)))
        assertTrue(one(all + OneiosSeen("extra.bin", 1, sha(kc))).contains("extra.bin is not in manifest.json"))
        assertTrue(OneiosManifests.verify(m, all + kcSeen).any { it.contains("twice") })
        assertEquals(2, OneiosManifests.verify(m, emptyList()).size)
    }

    @Test
    fun thePairMustMatch() {
        val r = OneiosManifests.parse(OneiosKind.RUNTIME, runtimeJson()).getOrThrow()
        val i = OneiosManifests.parse(OneiosKind.IMAGE, imageJson()).getOrThrow()
        assertNull(OneiosManifests.pairProblem(r, i))
        assertTrue(OneiosManifests.pairProblem(null, i)!!.contains("xnuhost"))
        assertTrue(OneiosManifests.pairProblem(r, null)!!.contains("image set"))
        assertTrue(OneiosManifests.pairProblem(r.copy(sessionAbi = 2), i)!!.contains("session ABI 2"))
        assertTrue(OneiosManifests.pairProblem(r.copy(imageFormats = listOf(2, 3)), i)!!.contains("format 1"))
    }

    // --- Packages (the tar inside the .tar.zst) ----------------------------------

    private class Tar {
        private val out = ByteArrayOutputStream()

        private fun header(name: String, size: Long, type: Char, prefix: String = ""): ByteArray {
            val h = ByteArray(512)
            fun put(s: String, off: Int) = s.toByteArray().copyInto(h, off)
            put(name, 0)
            put("0000644\u0000", 100)
            put("0000000\u0000", 108)
            put("0000000\u0000", 116)
            put(String.format("%011o\u0000", size), 124)
            put("00000000000\u0000", 136)
            for (i in 148..155) h[i] = ' '.code.toByte()
            h[156] = type.code.toByte()
            put("ustar\u000000", 257)
            put(prefix, 345)
            val sum = h.sumOf { it.toInt() and 0xff }
            put(String.format("%06o\u0000 ", sum), 148)
            return h
        }

        private fun body(b: ByteArray) {
            out.write(b)
            out.write(ByteArray((512 - b.size % 512) % 512))
        }

        fun file(name: String, b: ByteArray, prefix: String = "") = apply { out.write(header(name, b.size.toLong(), '0', prefix)); body(b) }
        fun dir(name: String) = apply { out.write(header("$name/", 0, '5')) }
        fun link(name: String) = apply { out.write(header(name, 0, '2')) }

        /** A pax header giving the next member its path (as GNU tar writes long names with --format=pax). */
        fun paxFile(path: String, b: ByteArray) = apply {
            val rec = "path=$path\n"
            var len = rec.length + 3
            while ("$len $rec".length != len) len = "$len $rec".length
            val pax = "$len $rec".toByteArray()
            out.write(header("PaxHeaders/x", pax.size.toLong(), 'x'))
            body(pax)
            file("truncated", b)
        }

        fun bytes(): ByteArray = out.toByteArray() + ByteArray(1024)
    }

    private fun unpack(tar: ByteArray, kind: OneiosKind): Map<String, ByteArray> {
        val found = OneiosPackage.readManifest(ByteArrayInputStream(tar), kind)
        val m = OneiosManifests.parse(kind, found.text).getOrThrow()
        val got = LinkedHashMap<String, ByteArray>()
        OneiosPackage.unpack(ByteArrayInputStream(tar), m, found.prefix, { f, data -> got[f.path] = data.readBytes() })
        return got
    }

    @Test
    fun anImageSetUnpacksVerified() {
        val tar = Tar().file("manifest.json", imageJson().toByteArray()).file("os.img", os).dir("overlay")
            .file("overlay/kernel.kc", kc).bytes()
        val got = unpack(tar, OneiosKind.IMAGE)
        assertEquals(listOf("os.img", "overlay/kernel.kc"), got.keys.toList())
        assertTrue(got.getValue("os.img").contentEquals(os))
        assertTrue(got.getValue("overlay/kernel.kc").contentEquals(kc))
    }

    @Test
    fun aManifestThatIsTheFirstFileIsReadInTheSamePassAsTheFiles() {
        // As OneiOS packs both: the manifest, then the files, folders in between.
        val tar = Tar().file("manifest.json", imageJson().toByteArray()).file("os.img", os).dir("overlay")
            .file("overlay/kernel.kc", kc).bytes()
        var opened = 0
        var read = 0L
        val stream = object : ByteArrayInputStream(tar) {
            init {
                opened++
            }

            override fun read(b: ByteArray, off: Int, len: Int): Int = super.read(b, off, len).also { if (it > 0) read += it }
        }
        val reader = TarReader(stream)
        val found = OneiosPackage.manifestFirst(reader, OneiosKind.IMAGE)!!
        assertEquals("", found.prefix)
        // Only the manifest's own blocks were read so far.
        assertTrue("$read bytes read for the manifest", read <= 512 + 1024L)
        val m = OneiosManifests.parse(OneiosKind.IMAGE, found.text).getOrThrow()
        val got = LinkedHashMap<String, ByteArray>()
        // The same reader goes on behind the manifest; this copier leaves the hashing to root.
        val seen = OneiosPackage.unpack(reader, m, found.prefix, OneiosPackage.Copier { f, data ->
            got[f.path] = data.readBytes()
            null
        })
        assertEquals(listOf("os.img", "overlay/kernel.kc"), got.keys.toList())
        assertTrue(got.getValue("os.img").contentEquals(os))
        assertEquals(2, seen.size)
        assertEquals(1, opened)
        // Every byte of the archive went by once.
        assertTrue("$read of ${tar.size}", read <= tar.size)
        // Under one top folder too.
        val top = Tar().dir("set").file("set/manifest.json", imageJson().toByteArray()).file("set/os.img", os)
            .file("set/overlay/kernel.kc", kc).bytes()
        assertEquals("set/", OneiosPackage.manifestFirst(TarReader(ByteArrayInputStream(top)), OneiosKind.IMAGE)!!.prefix)
    }

    @Test
    fun aManifestThatIsNotFirstIsFoundByGoingOn() {
        val tar = Tar().dir("overlay").file("os.img", os).file("overlay/kernel.kc", kc).file("manifest.json", imageJson().toByteArray()).bytes()
        val reader = TarReader(ByteArrayInputStream(tar))
        assertEquals(null, OneiosPackage.manifestFirst(reader, OneiosKind.IMAGE))
        // The same reader finds it further on; the files before it then need a second pass.
        assertTrue(OneiosPackage.readManifest(reader, OneiosKind.IMAGE).text.contains("oneios-image"))
        // No manifest at all.
        val none = Tar().file("os.img", os).bytes()
        val e = runCatching { OneiosPackage.readManifest(TarReader(ByteArrayInputStream(none)).also { OneiosPackage.manifestFirst(it, OneiosKind.IMAGE) }, OneiosKind.IMAGE) }
        assertTrue(e.exceptionOrNull() is OneiosPackage.Problem)
    }

    @Test
    fun aCopierThatHashedIsHeldToTheManifest() {
        val tar = Tar().file("manifest.json", imageJson().toByteArray()).file("os.img", os).file("overlay/kernel.kc", kc).bytes()
        val reader = TarReader(ByteArrayInputStream(tar))
        val found = OneiosPackage.manifestFirst(reader, OneiosKind.IMAGE)!!
        val m = OneiosManifests.parse(OneiosKind.IMAGE, found.text).getOrThrow()
        val e = runCatching {
            OneiosPackage.unpack(reader, m, found.prefix, OneiosPackage.Copier { _, data ->
                data.readBytes()
                "0".repeat(64)
            })
        }.exceptionOrNull()
        assertTrue(e is OneiosPackage.Problem && e.message!!.contains("does not match its SHA-256"))
    }

    @Test
    fun theManifestMayComeLastAndUnderOneTopFolder() {
        val tar = Tar().dir("oneios-runtime-0.1.0").dir("oneios-runtime-0.1.0/bin")
            .file("bin/xnuhost", xnuhost, prefix = "oneios-runtime-0.1.0").paxFile("oneios-runtime-0.1.0/bin/stub", stub)
            .file("oneios-runtime-0.1.0/runtime.json", runtimeJson().toByteArray()).bytes()
        val found = OneiosPackage.readManifest(ByteArrayInputStream(tar), OneiosKind.RUNTIME)
        assertEquals("oneios-runtime-0.1.0/", found.prefix)
        val got = unpack(tar, OneiosKind.RUNTIME)
        assertEquals(setOf("bin/xnuhost", "bin/stub"), got.keys)
        assertTrue(got.getValue("bin/stub").contentEquals(stub))
    }

    private fun unpackFails(tar: ByteArray, kind: OneiosKind, part: String) {
        val e = runCatching { unpack(tar, kind) }.exceptionOrNull()
        assertNotNull("unpacked", e)
        assertTrue("${e!!.message} lacks '$part'", e.message!!.contains(part))
    }

    @Test
    fun aDamagedOrPaddedPackageIsRefused() {
        val manifest = imageJson().toByteArray()
        val changed = os.copyOf().also { it[100] = (it[100] + 1).toByte() }
        unpackFails(Tar().file("manifest.json", manifest).file("os.img", changed).file("overlay/kernel.kc", kc).bytes(), OneiosKind.IMAGE, "SHA-256")
        unpackFails(Tar().file("manifest.json", manifest).file("os.img", os.copyOf(10)).file("overlay/kernel.kc", kc).bytes(), OneiosKind.IMAGE, "bytes")
        unpackFails(Tar().file("manifest.json", manifest).file("os.img", os).bytes(), OneiosKind.IMAGE, "overlay/kernel.kc is missing")
        unpackFails(Tar().file("manifest.json", manifest).file("os.img", os).file("overlay/kernel.kc", kc).file("extra", kc).bytes(), OneiosKind.IMAGE, "extra is not in manifest.json")
        unpackFails(Tar().file("manifest.json", manifest).file("os.img", os).file("os.img", os).file("overlay/kernel.kc", kc).bytes(), OneiosKind.IMAGE, "twice")
        unpackFails(Tar().file("manifest.json", manifest).link("os.img").bytes(), OneiosKind.IMAGE, "link")
        unpackFails(Tar().file("os.img", os).bytes(), OneiosKind.IMAGE, "no manifest.json")
        // A runtime package is not an image set, and the other way round.
        unpackFails(Tar().file("runtime.json", runtimeJson().toByteArray()).bytes(), OneiosKind.IMAGE, "no manifest.json")
        unpackFails("this is not a tar archive".toByteArray() + ByteArray(600), OneiosKind.IMAGE, "tar")
        // Cut off in the middle of a file.
        val whole = Tar().file("manifest.json", manifest).file("os.img", os).file("overlay/kernel.kc", kc).bytes()
        unpackFails(whole.copyOf(whole.size - 1024 - 700), OneiosKind.IMAGE, "ends inside")
        unpackFails(whole.copyOf(whole.size - 1024 - 1024 - 2000), OneiosKind.IMAGE, "ends inside")
    }

    @Test
    fun aSinkThatStopsEarlyIsAnError() {
        val tar = Tar().file("manifest.json", imageJson().toByteArray()).file("os.img", os).file("overlay/kernel.kc", kc).bytes()
        val found = OneiosPackage.readManifest(ByteArrayInputStream(tar), OneiosKind.IMAGE)
        val m = OneiosManifests.parse(OneiosKind.IMAGE, found.text).getOrThrow()
        val e = runCatching { OneiosPackage.unpack(ByteArrayInputStream(tar), m, found.prefix, { _, data -> data.read(ByteArray(10)) }) }.exceptionOrNull()
        assertTrue(e!!.message!!.contains("not read to its end"))
    }

    /**
     * A package OneiOS's own scripts built, when one is at hand: `ONEIOS_RUNTIME_TAR` or `ONEIOS_IMAGE_TAR` names
     * the tar (`zstd -dc <package>.tar.zst > x.tar`). Skipped without them; never a file in git.
     */
    @Test
    fun aPackageBuiltByOneiosUnpacks() {
        val given = listOf(OneiosKind.RUNTIME to System.getenv("ONEIOS_RUNTIME_TAR"), OneiosKind.IMAGE to System.getenv("ONEIOS_IMAGE_TAR"))
            .filter { !it.second.isNullOrBlank() }
        org.junit.Assume.assumeTrue("no ONEIOS_RUNTIME_TAR or ONEIOS_IMAGE_TAR", given.isNotEmpty())
        for ((kind, path) in given) {
            val file = java.io.File(path!!)
            val found = file.inputStream().buffered().use { OneiosPackage.readManifest(it, kind) }
            val m = OneiosManifests.parse(kind, found.text).getOrThrow()
            var bytes = 0L
            val seen = file.inputStream().buffered().use { tar ->
                OneiosPackage.unpack(tar, m, found.prefix, { _, data -> bytes += data.readBytes().size })
            }
            assertEquals(m.files.map { it.path }.toSet(), seen.map { it.path }.toSet())
            assertEquals(m.bytes, bytes)
            if (kind == OneiosKind.RUNTIME) {
                assertEquals(OneiosSystem.SESSION_ABI, m.sessionAbi)
                assertTrue(OneiosSystem.FORMAT in m.imageFormats)
            }
            println("$kind ${m.version}: ${m.files.size} files, ${m.bytes} bytes, prefix '${found.prefix}', placeholder ${m.placeholder}, min fork ${m.minOneosFork}")
        }
    }

    // --- Releases ----------------------------------------------------------------

    private fun release(vararg assets: Pair<String, Long>, tag: String = "v0.1.0", host: String = "https://github.com/akshaynexus/OneiOS") = """
        {"tag_name": "$tag", "name": "OneiOS $tag", "draft": false, "assets": [
          ${assets.joinToString(",") { (n, s) -> """{"name": "$n", "size": $s, "browser_download_url": "$host/releases/download/$tag/$n"}""" }}
        ]}
    """.trimIndent()

    @Test
    fun theRuntimeAssetOfAReleaseIsFound() {
        val name = "oneios-runtime-0.1.0-arm64.tar.zst"
        val r = OneiosReleases.parse(release(name to 1234L, "$name.sha256" to 100L, "notes.txt" to 5L)).getOrThrow()
        assertEquals("v0.1.0", r.tag)
        assertEquals("0.1.0", r.version)
        assertEquals(1234L, r.assetBytes)
        assertEquals("https://github.com/akshaynexus/OneiOS/releases/download/v0.1.0/$name", r.assetUrl)
        assertEquals("https://github.com/akshaynexus/OneiOS/releases/download/v0.1.0/$name.sha256", r.sha256Url)
    }

    @Test
    fun aReleaseWithoutARuntimeSaysSo() {
        fun why(text: String) = OneiosReleases.parse(text).exceptionOrNull()!!.message!!
        assertTrue(why(release("notes.txt" to 5L)).contains("has no runtime package"))
        val name = "oneios-runtime-0.1.0-arm64.tar.zst"
        assertTrue(why(release(name to 1234L)).contains("has no $name.sha256"))
        // Never an image, never another repository's file, never an oversized asset.
        assertTrue(why(release("oneios-image-27.0.1.tar.zst" to 9L)).contains("has no runtime package"))
        assertTrue(why(release(name to 1234L, "$name.sha256" to 100L, host = "https://github.com/someone/else")).contains("not a file of"))
        assertTrue(why(release(name to OneiosReleases.MAX_ASSET_BYTES + 1, "$name.sha256" to 100L)).contains("bytes"))
        assertTrue(why(release(name to 1L, "$name.sha256" to 1L, "oneios-runtime-0.2.0-arm64.tar.zst" to 1L)).contains("2 runtime packages"))
        assertTrue(why("""{"message": "Not Found"}""").contains("no tag"))
        assertTrue(OneiosReleases.noRelease(null).contains("has not published a release yet"))
        assertTrue(OneiosReleases.noRelease("v9").contains("v9"))
    }

    @Test
    fun theLatestOrAPinnedTag() {
        assertEquals("https://api.github.com/repos/akshaynexus/OneiOS/releases/latest", OneiosReleases.apiUrl(null))
        assertEquals(OneiosReleases.LATEST_API, OneiosReleases.apiUrl("  "))
        assertEquals("https://api.github.com/repos/akshaynexus/OneiOS/releases/tags/v0.1.0", OneiosReleases.apiUrl("v0.1.0"))
        for (bad in listOf("../x", "a/b", "a b", "v1?x=1", "-v1")) {
            assertTrue(bad, runCatching { OneiosReleases.apiUrl(bad) }.isFailure)
        }
    }

    @Test
    fun theSha256FileIsOneSha256sumLine() {
        val name = "oneios-runtime-0.1.0-arm64.tar.zst"
        val h = sha(xnuhost)
        assertEquals(h, OneiosReleases.parseSha256("$h  $name\n", name))
        assertEquals(h, OneiosReleases.parseSha256("${h.uppercase()} *$name", name))
        assertEquals(h, OneiosReleases.parseSha256("$h  dist/$name", name))
        assertEquals(h, OneiosReleases.parseSha256("$h\n", name))
        assertNull(OneiosReleases.parseSha256("$h  other.tar.zst", name))
        assertNull(OneiosReleases.parseSha256("$h  $name\n$h  $name\n", name))
        assertNull(OneiosReleases.parseSha256("abc  $name", name))
        assertNull(OneiosReleases.parseSha256("<html>Not Found</html>", name))
    }

    // --- The kernel a runtime carries ---------------------------------------------

    private val xnu = "xnu-bytes".toByteArray()

    private fun kernelJson() =
        """"kernel": {"path": "kernel/xnu.macho", "build_id": "xnu-12377.121.6-ios-27.0.1-24A446-abcdef012345", "sha256": "${sha(xnu)}", "xnu": "xnu-12377.121.6", "profile": "ios-27.0.1-24A446", "record": "kernel/xnu.macho.build.json"}, """

    @Test
    fun aRuntimeKernelParses() {
        val text = runtimeJson().replace("\"files\":", kernelJson() + "\"files\":")
        val m = OneiosManifests.parse(OneiosKind.RUNTIME, text).getOrThrow()
        val k = m.kernel!!
        assertEquals("kernel/xnu.macho", k.path)
        assertEquals("xnu-12377.121.6-ios-27.0.1-24A446-abcdef012345", k.buildId)
        assertEquals(sha(xnu), k.sha256)
        assertEquals("xnu-12377.121.6", k.xnu)
        assertEquals("ios-27.0.1-24A446", k.profile)
        assertEquals("kernel/xnu.macho.build.json", k.record)
        // None, or null: no kernel to rebuild from.
        assertNull(OneiosManifests.parse(OneiosKind.RUNTIME, runtimeJson()).getOrThrow().kernel)
        assertNull(OneiosManifests.parse(OneiosKind.RUNTIME, runtimeJson().replace("\"files\":", "\"kernel\": null, \"files\":"))?.getOrThrow()?.kernel)
        // A malformed one refuses the manifest: a kernel the app cannot name must never stage as updatable.
        refused(OneiosKind.RUNTIME, runtimeJson().replace("\"files\":", "\"kernel\": {}, \"files\":"), "kernel has no path")
        refused(OneiosKind.RUNTIME, runtimeJson().replace("\"files\":", kernelJson().replace("kernel/xnu.macho", "../xnu") + "\"files\":"), "not a plain relative path")
        refused(OneiosKind.RUNTIME, runtimeJson().replace("\"files\":", kernelJson().replace(sha(xnu), "zz") + "\"files\":"), "malformed")
    }

    private val kbPin = "3".repeat(64)

    private fun kb(build: String = "24A446") = OneiosKb(
        build, "iPhone18,2", kbPin,
        OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }.associateWith { "4".repeat(64) },
    )

    @Test
    fun kbJsonParsesAndNamesEveryPrelinkInput() {
        val files = OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }
            .joinToString(",") { "\"$it\": \"${"4".repeat(64)}\"" }
        val kb = OneiosKb.parse(
            """{"kb": 2, "build": "24A446", "device": "iPhone18,2", "kernelcache_sha256": "$kbPin", "files": {$files}, "packed_by": "ci"}""",
        ).getOrThrow()
        assertEquals("24A446", kb.build)
        assertEquals(kbPin, kb.kernelcacheSha256)
        assertEquals(OneiosKb.PINNED.toSet(), kb.files.keys)
        for (bad in listOf("{}", """{"kb": 2}""", """{"kb": 1, "build": "24A446", "device": "iPhone18,2", "kernelcache_sha256": "$kbPin", "files": {$files}}""", """{"kb": 2, "build": "24A446", "device": "x", "kernelcache_sha256": "$kbPin", "files": {}}""")) {
            assertTrue(bad, OneiosKb.parse(bad).isFailure)
        }
    }

    @Test
    fun kernelProblemNamesTheMismatch() {
        val kb = kb()
        assertNull(OneiosManifests.kernelProblem("24A446", kb, kbPin, true))
        assertTrue(OneiosManifests.kernelProblem(null, kb, kbPin, true)!!.contains("No iOS image set"))
        assertTrue(OneiosManifests.kernelProblem("24A447", kb, kbPin, true)!!.contains("24A447"))
        assertTrue(OneiosManifests.kernelProblem("24A446", kb, kbPin, false)!!.contains("no kernel"))
        assertTrue(OneiosManifests.kernelProblem("24A446", kb, null, true)!!.contains("not staged"))
        assertTrue(OneiosManifests.kernelProblem("24A446", kb, "5".repeat(64), true)!!.contains("not the 24A446 one"))
    }

    /**
     * The A56's iOS 16.5 (20F66) set has the 24A446 kernel (its kernel.kc is OneiOS's XNU with the 24A446 kexts):
     * Update the kernel refused it "the staged image set is 20F66" (OneiOS issue 73, 2026-11-24). Any other build that
     * is not the inputs' is still refused.
     */
    @Test
    fun theA56s165SetTakesThe24A446Kernel() {
        val kb = kb()
        assertEquals("24A446", OneiosImageChoice.kernelBuildOf("20F66"))
        assertEquals("21A329", OneiosImageChoice.kernelBuildOf("21A329"))
        assertNull(OneiosManifests.updateProblem("20F66", kb, true))
        assertNull(OneiosManifests.kernelProblem("20F66", kb, kbPin, true))
        assertTrue(OneiosManifests.updateProblem("21A329", kb, true)!!.contains("21A329"))
        assertTrue(OneiosManifests.updateProblem("20F66", kb("22A100"), true)!!.contains("20F66"))
    }

    /** The page, the Switch button and the switching line name the staged set's iOS: "iOS 16.5" on the A56 (issue 73). */
    @Test
    fun theNameFollowsTheStagedSet() {
        assertEquals("iOS 27", OneiosSystem.shortName(null))
        assertEquals("iOS 27", OneiosSystem.shortName("27.0.1"))
        assertEquals("iOS 16.5", OneiosSystem.shortName("16.5"))
        assertEquals("iOS 16.5", OneiosSystem.shortName("16.5.1"))
        assertEquals("iOS 16.5 (OneiOS)", OneiosSystem.name(OneiosImageChoice.IOS_16_5_A56.version))
        assertEquals(OneiosSystem.NAME, OneiosSystem.name(OneiosImageChoice.IOS_27.version))
    }

    @Test
    fun kernelUpdateComparesBuildIds() {
        val latest = OneiosKernel("kernel/xnu.macho", "xnu-new", "a".repeat(64), "xnu-1", "p", "r")
        assertTrue(OneiosManifests.kernelUpdate("xnu-new", latest) == null)
        assertTrue(OneiosManifests.kernelUpdate("xnu-old", latest)!!.contains("xnu-new"))
        assertTrue(OneiosManifests.kernelUpdate(null, latest)!!.contains("stage that runtime"))
        assertTrue(OneiosManifests.kernelUpdate("xnu-old", null)!!.contains("nothing to rebuild"))
    }

    @Test
    fun thePrelinkRequestNamesEveryInputUnderTheStage() {
        val (cmd, keys) = OneiosTool.prelinkRequest("kernel/xnu.macho", OneiosSystem.STAGE)
        assertEquals("prelink", cmd)
        assertEquals("${OneiosSystem.STAGE}/runtime/kernel/xnu.macho", keys["kernel"])
        assertEquals("${OneiosSystem.STAGE}/kb/kernelcache.macho", keys["kernelcache"])
        assertEquals("${OneiosSystem.STAGE}/kb/profile.toml", keys["profile"])
        assertEquals("${OneiosSystem.STAGE}/kb/reviewed.json", keys["reviewed"])
        assertEquals(listOf("${OneiosSystem.STAGE}/kb/lead.json", "${OneiosSystem.STAGE}/kb/user.json"), keys["more_reviewed"])
        assertEquals("${OneiosSystem.STAGE}/kb/pairs.json", keys["pairs"])
        assertEquals("${OneiosSystem.STAGE}/kb/stubs.json", keys["stubs"])
        assertEquals("${OneiosSystem.STAGE}/kb/match", keys["xnuprelink"])
        assertEquals("${OneiosSystem.STAGE}/make-kernel/out", keys["out"])
        assertEquals(9, keys.size)
        // The request line the app writes: one JSON object, every path in it.
        OneiosTool.request("1", cmd, keys)
    }

    /**
     * Update the kernel's download and decode (docs/oneios.md, "Kernel updates"): the keys `oneios-tool serve`'s
     * `fetch` and `im4p` take (OneiOS's crates/oneios-serve/src/cmds.rs: fetch reads `profile`, `indir`, `only`,
     * `source`, `resume`, `give_up_s`, `connections`; im4p `in` and `out`), every path under the stage, and only the
     * profile's kernelcache member.
     */
    @Test
    fun theKernelcacheRequestsAreTheToolsKeys() {
        val s = OneiosSystem.STAGE
        val (fetch, fk) = OneiosTool.kernelcacheFetchRequest(s)
        assertEquals("fetch", fetch)
        assertEquals(
            mapOf("profile" to "$s/runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml", "indir" to "$s/make-kernel/inputs", "only" to listOf("kernelcache"), "resume" to true),
            fk,
        )
        val (im4p, ik) = OneiosTool.kernelcacheDecodeRequest(s)
        assertEquals("im4p", im4p)
        assertEquals(mapOf("in" to "$s/make-kernel/inputs/kernelcache.release.v54", "out" to "$s/make-kernel/kernelcache.macho"), ik)
        // The line the app writes: the list and the flag as JSON, not as text.
        assertEquals(
            """{"id":"3","cmd":"fetch","profile":"$s/runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml","indir":"$s/make-kernel/inputs","only":["kernelcache"],"resume":true}""" + "\n",
            OneiosTool.request("3", fetch, fk),
        )
        // The decoded file the build reads is the one kbcache puts in kb/.
        assertEquals("$s/kb/kernelcache.macho", OneiosTool.prelinkRequest("kernel/xnu.macho", s).second["kernelcache"])
    }

    /**
     * Make iOS image's one request (docs/oneios.md, "Make iOS image"): exactly the keys OneiOS's `make-image` takes
     * from the app (oneos/interface.md section 9; crates/oneios-serve cmds.rs `make_image`: `indir`, `out`, `work`
     * written under the stage, `sums_list` and `ids_list` optional, `resume` a flag), and nothing it would refuse
     * (`usage` for an unknown key). The profile is named: a released runtime packs four or more in `lib/profiles/`,
     * and the tool (up to v0.1.16) refuses a request without one there, `usage` (OneiOS issue 75). The tool's
     * defaults take the kernel and kb/ from the stage.
     */
    @Test
    fun theMakeImageRequestIsTheToolsKeys() {
        val s = OneiosSystem.STAGE
        val (cmd, keys) = OneiosTool.makeImageRequest(s)
        assertEquals("make-image", cmd)
        assertEquals(
            mapOf(
                "profile" to "$s/runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml",
                "indir" to "$s/make/inputs", "out" to "$s/image.new", "sums_list" to "$s/image.new.sha256", "ids_list" to "$s/image.new.ids",
                "work" to "$s/make", "resume" to true,
            ),
            keys,
        )
        assertEquals(
            """{"id":"m","cmd":"make-image","profile":"$s/runtime/lib/profiles/ios-27.0.1-iPhone18-2.toml","indir":"$s/make/inputs","out":"$s/image.new","sums_list":"$s/image.new.sha256","ids_list":"$s/image.new.ids","work":"$s/make","resume":true}""" + "\n",
            OneiosTool.request("m", cmd, keys),
        )
        // The room said before it starts covers the profile's need_gib (30 GiB) and the download is the profile's members.
        assertTrue(OneiosTool.MAKE_IMAGE_ROOM_BYTES > 30L shl 30)
        assertTrue(OneiosTool.MAKE_IMAGE_DOWNLOAD_BYTES in 11_000_000_000L..12_000_000_000L)
    }

    // --- The JSON reader -----------------------------------------------------------

    @Test
    fun jsonReadsWhatTheManifestsUse() {
        val v = JsonRead.parse("""{"a": [1, -2, 3.5, true, false, null], "b": {"c": "x\nA\"\\"}, "d": 17179869184}""") as Map<*, *>
        assertEquals(listOf(1L, -2L, 3.5, true, false, null), v["a"])
        assertEquals("x\nA\"\\", (v["b"] as Map<*, *>)["c"])
        assertEquals(17179869184L, v["d"])
        assertEquals(emptyMap<String, Any?>(), JsonRead.parse(" {} "))
        assertEquals(emptyList<Any?>(), JsonRead.parse("[]"))
        for (bad in listOf("", "{", "{\"a\":}", "{\"a\":1,}", "[1,]", "{\"a\":1} x", "{'a':1}", "\"abc", "01x", "{\"a\":1,\"a\":2}", "[" .repeat(100))) {
            assertTrue(bad, runCatching { JsonRead.parse(bad) }.isFailure)
        }
    }
}
