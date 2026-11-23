package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The iOS screens' plain words (OneiosPlain): a refusal of root, of the preflight or of the app's own
 * download and import becomes a short title, one line, the step it is about and the one fix. The
 * scripts' every refusal line is covered by OneiosFlowTest (core:root), which reads them.
 */
class OneiosPlainTest {
    private fun of(problem: String, kind: OneiosKind? = null) = OneiosPlain.refused(problem, kind)

    private fun assertPlain(m: OneiosMessage) {
        assertTrue("title too long: ${m.title}", m.title.length <= OneiosPlain.MAX_TITLE)
        assertTrue("line too long: ${m.line}", m.line.length <= OneiosPlain.MAX_LINE)
        assertTrue(m.title.isNotBlank() && m.line.isNotBlank())
        assertFalse("a script's words in the title: ${m.title}", m.title.contains('$') || m.title.contains("/data"))
    }

    @Test
    fun notSetUpIsTheNextStepNotAFault() {
        for (p in listOf(
            "OneiOS is not set up on this phone yet",
            "OneiOS is not set up on this phone (/data/local/tmp/oneios is missing)",
            "no OneiOS runtime is staged: xnuhost, the program that runs iOS, comes with it (download or import the runtime in the OneOS app)",
        )) {
            val m = of(p)
            assertEquals(p, OneiosFix.GET_RUNTIME, m.fix)
            assertEquals(OneiosPart.RUNTIME, m.part)
            assertTrue(m.isNextStep)
            assertPlain(m)
        }
        val image = of("no iOS image set is staged: import the one you built with OneiOS's scripts in the OneOS app")
        assertEquals(OneiosFix.IMPORT_IMAGE, image.fix)
        assertEquals(OneiosPart.IMAGE, image.part)
        assertTrue(image.isNextStep)
    }

    @Test
    fun thePreflightsPrefixAndRootsAreDropped() {
        val m = of("PREFLIGHT REFUSED: battery at 12% and not charging")
        assertEquals("Charge your phone", m.title)
        assertTrue(m.line, m.line.startsWith("The battery is at 12%."))
        assertEquals("battery at 12% and not charging", m.detail)
        assertEquals(OneiosPart.SWITCH, m.part)
        assertEquals(OneiosFix.NONE, m.fix)
        assertNull(m.fixLabel)
    }

    @Test
    fun eachPartIsWhereThePreflightChecksIt() {
        // This phone and root, before the stage.
        assertEquals(OneiosPart.PHONE, of("not running as root").part)
        assertEquals(OneiosPart.PHONE, of("iOS runs on the Galaxy S24 Ultra (SM-S928) only; this phone is SM-S918B").part)
        // (an older switch's refusal) Its words name both phones it runs on now: the A56 with iOS 16.5, untested there.
        assertEquals(
            "It runs on the Galaxy S24 Ultra (SM-S928), and on the Galaxy A56 (SM-A566) with iOS 16.5 (untested there).",
            of("iOS runs on the Galaxy S24 Ultra (SM-S928) only; this phone is SM-S918B").line,
        )
        // Root's busybox line comes before the preflight could run; the preflight's own (with the paths) after the stage.
        assertEquals(OneiosPart.PHONE, of("no busybox at the root manager's paths").part)
        assertEquals(OneiosPart.SWITCH, of("no busybox at the root manager's paths (/data/adb/ksu/bin, /data/adb/ap/bin, /data/adb/magisk)").part)
        // The runtime, then the image set.
        assertEquals(OneiosPart.RUNTIME, of("the runtime 0.1.6 carries a placeholder instead of xnuhost (OneiOS has not built xnuhost yet): it cannot start iOS").part)
        assertEquals(OneiosPart.RUNTIME, of("runtime/bin/xnuhost does not match its SHA-256: stage the runtime again").part)
        assertEquals(OneiosPart.IMAGE, of("image/os.img changed since it was staged: stage the image again").part)
        assertEquals(OneiosPart.IMAGE, of("the image set is format 2, the runtime 0.1.6 boots format(s) 1: build the image again or take a matching runtime").part)
        // The rest of the phone's state.
        assertEquals(OneiosPart.SWITCH, of("less than 2 GiB free on /data").part)
        assertEquals(OneiosPart.SWITCH, of("no Volume Down key found (getevent)").part)
    }

    @Test
    fun theFixIsTheOneThatHelps() {
        assertEquals(OneiosFix.GET_RUNTIME, of("runtime.sha256 is missing or not root's: stage the runtime again").fix)
        assertEquals(OneiosFix.IMPORT_IMAGE, of("image/ holds files its list does not name (x ): stage the image again").fix)
        assertEquals(OneiosFix.GET_RUNTIME, of("the runtime 0.2.0 speaks session ABI 2, this OneOS speaks 1: update the OneOS app or the runtime").fix)
        assertEquals(OneiosFix.BACK_TO_ONE_UI, of("an iOS session of this boot is still open (running): restart the phone first").fix)
        assertEquals(OneiosFix.BACK_TO_ONE_UI, of("an iOS session is running: return to One UI first").fix)
        assertEquals(OneiosFix.CHECK_AGAIN, of("One UI has not finished starting").fix)
        assertEquals(OneiosFix.REMOVE, of("/data/local/tmp/oneios is not root's or is writable by others").fix)
        assertEquals(OneiosFix.GET_RUNTIME, of("/data/local/tmp/oneios/oneios_switch.sh is missing or not root's").fix)
        assertEquals("Check again", OneiosPlain.label(OneiosFix.CHECK_AGAIN))
        assertEquals("Back to One UI", of("an iOS session is already running").fixLabel)
    }

    @Test
    fun anEarlierSessionsXnuhostIsARestartNotTheRuntime() {
        val m = of("xnuhost of an earlier session is still running (pid 812): restart the phone first")
        assertEquals("Restart your phone first", m.title)
        assertEquals(OneiosPart.SWITCH, m.part)
        val r = of("xnuhost is not an arm64 program")
        assertEquals(OneiosPart.RUNTIME, r.part)
        assertEquals(OneiosFix.GET_RUNTIME, r.fix)
    }

    @Test
    fun anImportsFailureNamesItsPackage() {
        val damaged = of("os.img did not arrive intact (SHA-256 differs)", OneiosKind.IMAGE)
        assertEquals("The iOS image set is damaged", damaged.title)
        assertEquals(OneiosFix.IMPORT_IMAGE, damaged.fix)
        assertEquals(OneiosPart.IMAGE, damaged.part)
        val runtime = of("oneios-runtime-0.1.6-arm64.tar.zst did not arrive intact (size or SHA-256 differs). Try again.", OneiosKind.RUNTIME)
        assertEquals("The OneiOS runtime is damaged", runtime.title)
        assertEquals(OneiosFix.GET_RUNTIME, runtime.fix)
        // "manifest.json was not received" is an import that stopped, not a file that is no image set.
        assertEquals("The import didn't finish", of("manifest.json was not received", OneiosKind.IMAGE).title)
        assertEquals("This isn't an iOS image set", of("no manifest.json in this file: it is not a iOS image set", OneiosKind.IMAGE).title)
        assertEquals("This isn't a OneiOS runtime", of("This file is not a .tar.zst OneiOS runtime: bad magic", OneiosKind.RUNTIME).title)
        assertEquals(OneiosFix.IMPORT_RUNTIME, of("the picked file cannot be opened", OneiosKind.RUNTIME).fix)
        val stopped = of("stopped", OneiosKind.IMAGE)
        assertEquals("Stopped", stopped.title)
        assertEquals(Level.WARN, stopped.level)
        assertEquals(OneiosFix.IMPORT_IMAGE, stopped.fix)
        assertEquals("Not enough space for the iOS image set", of("not enough free space on /data for os.img", OneiosKind.IMAGE).title)
    }

    @Test
    fun theDownloadsFailuresSayWhatToDo() {
        assertEquals(OneiosFix.DOWNLOAD_RUNTIME, of("No connection to GitHub (timeout).", OneiosKind.RUNTIME).fix)
        assertEquals(OneiosFix.IMPORT_RUNTIME, of(OneiosReleases.noRelease(null), OneiosKind.RUNTIME).fix)
        assertEquals("No release with that name", of(OneiosReleases.noRelease("v9.9.9"), OneiosKind.RUNTIME).title)
        assertEquals("No release with that name", of("'..' is not a release tag", OneiosKind.RUNTIME).title)
        assertEquals("The download didn't finish", of("GitHub answered 503 for the release", OneiosKind.RUNTIME).title)
        assertEquals("This release has no runtime", of("release v0.1.0 has no runtime package (oneios-runtime-<version>-arm64.tar.zst)", OneiosKind.RUNTIME).title)
    }

    @Test
    fun theAppsOwnAndRootsFailures() {
        assertEquals("This copy of OneOS is damaged", of("the OneiOS root script in the app is not the pinned one").title)
        assertEquals("Allow root access", of("root did not answer in time").title)
        assertEquals("Allow root access", of("su could not be started: No such file").title)
        assertEquals("Tick both boxes first", of("Tick the box first: iOS 27 (OneiOS) is experimental.").title)
        assertEquals("Root couldn't write the files", of("failed: could not make the stage", OneiosKind.IMAGE).title)
        assertEquals(OneiosFix.CHECK_AGAIN, of("the preflight gave no answer: restart the phone").fix)
        assertEquals("The last check gave no answer", of("the preflight gave no answer: restart the phone").title)
    }

    @Test
    fun anythingElseIsCouldntFinishWithTheScriptsWords() {
        val m = of("something nobody wrote yet")
        assertEquals("Couldn't finish", m.title)
        assertEquals(OneiosFix.CHECK_AGAIN, m.fix)
        assertEquals("something nobody wrote yet", m.detail)
        assertEquals("Couldn't finish", of("").title)
    }

    @Test
    fun everyMessageIsShortEnough() {
        val corpus = listOf(
            "not running as root", "no sha256sum", "battery too warm (44 C)", "battery not readable", "the experimental tick was not given",
            "no /sys/power/wake_lock: the phone would sleep with One UI's framework stopped",
            "not in init's mount namespace (this shell: mnt:[1], init: mnt:[2])", "One UI's surfaceflinger is not running",
            "mounted under a stage (/data/local/tmp/oneios/x ): a session is running or never returned; restart the phone first",
            "os.img: 3 of 9 bytes arrived", "os.img is too large", "3 of 21 files were received", "the runtime has no bin/xnuhost",
            "bin/xnuhost is not executable (mode 0755 in runtime.json)", "This runtime needs OneOS 0.9 or newer; this is 0.5.14.",
            "manifest.json is format 2; this version of OneOS reads format 1",
        )
        for (k in listOf(null, OneiosKind.RUNTIME, OneiosKind.IMAGE)) for (p in corpus) {
            val m = of(p, k)
            assertPlain(m)
            assertNotEquals("$p ($k)", "Couldn't finish", m.title)
        }
    }

    @Test
    fun theRecordOfAStagedPackageRoundTrips() {
        val image = OneiosStaged(OneiosKind.IMAGE, "27.0.1", "24A446", 21, 17_900_000_000L, 1_763_000_000_000L)
        assertEquals(image, OneiosStaged.decode(image.encode()))
        val runtime = OneiosStaged(OneiosKind.RUNTIME, "0.1.6", null, 12, 12_345_678L, 5L)
        assertEquals("runtime 0.1.6 - 12 12345678 5 - -", runtime.encode())
        assertEquals(runtime, OneiosStaged.decode(runtime.encode()))
        // Before kernels were recorded (6 fields): still read, with no kernel.
        assertEquals(runtime, OneiosStaged.decode("runtime 0.1.6 - 12 12345678 5"))
        val withKernel = OneiosStaged(OneiosKind.RUNTIME, "0.1.6", null, 12, 12_345_678L, 5L, "kernel/xnu.macho", "xnu-1-2-3")
        assertEquals("runtime 0.1.6 - 12 12345678 5 kernel/xnu.macho xnu-1-2-3", withKernel.encode())
        assertEquals(withKernel, OneiosStaged.decode(withKernel.encode()))
        for (bad in listOf(null, "", "runtime 0.1.6", "kernel 1 - 1 1 1", "image 27 24A 1 -1 1", "image ../x - 1 1 1", "image 27 - x 1 1")) {
            assertNull(bad, OneiosStaged.decode(bad))
        }
        // Shown only while root still reports that version (and build).
        assertTrue(image.matches("27.0.1", "24A446"))
        assertTrue(image.matches("27.0.1", "unknown"))
        assertFalse(image.matches("27.0.1", "24A999"))
        assertFalse(runtime.matches("0.1.7"))
        assertTrue(runtime.matches("0.1.6", "anything"))
        val m = OneiosManifest(OneiosKind.IMAGE, 1, "27.0.1", listOf(OneiosFile("os.img", 10, "a".repeat(64)), OneiosFile("k", 5, "b".repeat(64))), build = "24A446")
        assertEquals(OneiosStaged(OneiosKind.IMAGE, "27.0.1", "24A446", 2, 15, 9), OneiosStaged.of(m, 9))
    }

    /**
     * Update the kernel's stops (docs/oneios.md, "Kernel updates"): each in plain words within the limits, the
     * tool's own words kept as the detail, and the line says whether the download goes on or starts over.
     */
    @Test
    fun theKernelUpdatesStopsArePlainWords() {
        val end = OneiosToolFlow.End.entries
        val steps = listOf("kbinput", "fetch", "im4p", "kbcache", "prelink")
        val codes = listOf(null, "space", "network", "changed", "heat", "battery", "session", "unknown", "not-ported", "mismatch", "not-found", "audit", "io", "internal")
        for (s in steps) for (e in end) for (c in codes) assertPlain(OneiosPlain.kernelUpdate(s, e, c, "the tool's words: /data/local/tmp/oneios", cleaned = true))

        fun k(step: String, e: OneiosToolFlow.End, code: String?, text: String? = null, cleaned: Boolean = false) = OneiosPlain.kernelUpdate(step, e, code, text, cleaned)
        val net = k("fetch", OneiosToolFlow.End.FAILED, "network", "no byte for 120 s")
        assertEquals("No connection to Apple", net.title)
        assertTrue(net.line, "goes on from where it stopped" in net.line)
        assertEquals("fetch: network: no byte for 120 s", net.detail)
        assertEquals("Not enough space for the update", k("im4p", OneiosToolFlow.End.REFUSED, "space").title)
        val pin = k("im4p", OneiosToolFlow.End.REFUSED, "mismatch", "the decoded kernelcache's SHA-256 is 00, the profile pins 34: nothing was kept", cleaned = true)
        assertEquals("Apple's kernelcache didn't check out", pin.title)
        assertTrue(pin.line, "nothing was kept" in pin.line)
        assertEquals("Apple's kernelcache didn't check out", k("fetch", OneiosToolFlow.End.REFUSED, "mismatch", "kernelcache.release.v54: sha384 ab, the profile pins cd").title)
        assertEquals("Apple's kernelcache didn't check out", k("kbcache", OneiosToolFlow.End.REFUSED, "mismatch", "the fetched kernelcache is not the one the profile pins").title)
        assertEquals("Apple's file changed while it came", k("fetch", OneiosToolFlow.End.FAILED, "changed").title)
        val stop = k("fetch", OneiosToolFlow.End.CANCELLED, null, "stopped", cleaned = true)
        assertEquals("Stopped", stop.title)
        assertTrue(stop.line, "removed" in stop.line)
        assertTrue("interrupted" in k("prelink", OneiosToolFlow.End.LOST, null, "the tool ended").title)
        assertEquals("The new kernel didn't pass its checks", k("prelink", OneiosToolFlow.End.REFUSED, "audit").title)
        assertEquals("This copy of OneOS is damaged", k("kbinput", OneiosToolFlow.End.REFUSED, "mismatch", "the app's kb/pairs.json is not the pinned one: reinstall OneOS").title)
        assertEquals("This runtime's tool is too old", k("im4p", OneiosToolFlow.End.REFUSED, "unknown").title)
        assertEquals("An iOS session is still open", k("kbcache", OneiosToolFlow.End.REFUSED, null, "an iOS session is running: return to One UI first").title)
        // Make iOS image's stops: every step, end and code in plain words within the limits, and none sends the user to a PC.
        val makeSteps = listOf("status", "runtime", "kbinput", "begin", "tool", "make-image", "finish")
        val makeCodes = codes + listOf("auth", "exists", "usage", "outside", "failed", "changed", "no-kernel", "no-make-image")
        for (s in makeSteps) for (e in end) for (c in makeCodes) {
            for (m in listOf(OneiosPlain.makeImage(s, e, c, "the tool's words: step decrypt", 39_000_000_000L, 12_000_000_000L), OneiosPlain.makeImage(s, e, c, null))) {
                assertPlain(m)
                assertTrue(m.line, "PC" !in m.line && "PC" !in m.title)
            }
        }
        fun mk(step: String, e: OneiosToolFlow.End, code: String?, text: String? = null, need: Long? = null, free: Long? = null) = OneiosPlain.makeImage(step, e, code, text, need, free)
        val room = mk("make-image", OneiosToolFlow.End.REFUSED, "space", "Not enough free space", 39_000_000_000L, 12_000_000_000L)
        assertEquals("Not enough space", room.title)
        assertTrue(room.line, Units.bytes(39_000_000_000L) in room.line && Units.bytes(12_000_000_000L) in room.line)
        assertEquals("make-image: space: Not enough free space", room.detail)
        assertEquals(
            "This runtime can't decrypt iOS yet",
            mk("make-image", OneiosToolFlow.End.REFUSED, "not-ported", "step decrypt: the AEA decryption is not in this tool yet (043-69487-662.dmg.aea must be decrypted)").title,
        )
        assertEquals("This runtime's tool is too old", mk("make-image", OneiosToolFlow.End.REFUSED, "unknown", "no such cmd: make-image").title)
        assertEquals("Apple's iOS image didn't check out", mk("make-image", OneiosToolFlow.End.REFUSED, "auth", "does not authenticate").title)
        assertEquals("No connection to Apple", mk("make-image", OneiosToolFlow.End.FAILED, "network").title)
        assertTrue(mk("make-image", OneiosToolFlow.End.FAILED, "network").line.contains("goes on from what it downloaded"))
        assertTrue(mk("make-image", OneiosToolFlow.End.CANCELLED, null, "stopped").line.contains("stays for the next run"))
        assertTrue("interrupted" in mk("make-image", OneiosToolFlow.End.LOST, null, "the tool ended").title)
        assertEquals("The kernel didn't pass its checks", mk("make-image", OneiosToolFlow.End.REFUSED, "audit").title)
        assertEquals("A file of the build is missing", mk("make-image", OneiosToolFlow.End.REFUSED, "not-found", "the kernel's inputs are missing: kb/stubs.json").title)
        assertEquals("Couldn't get the OneiOS runtime", mk("runtime", OneiosToolFlow.End.FAILED, null, "No connection to GitHub").title)
        assertEquals(OneiosPart.IMAGE, room.part)
        // The image step's button and its words: Make iOS image, on this phone.
        assertEquals("Get the iOS image", OneiosPlain.label(OneiosFix.IMPORT_IMAGE))
        val noImage = of("no iOS image set is staged: import the one you built with OneiOS's scripts in the OneOS app")
        assertTrue(noImage.line, "PC" !in noImage.line && "this phone" in noImage.line.lowercase())

        // Root's words of a kernel that is not ready point at the Update button, not at a PC.
        val notReady = of("the Apple kernelcache is not staged: run the kernel update first")
        assertEquals("The phone-built kernel isn't ready", notReady.title)
        assertTrue(notReady.line, "Update the kernel" in notReady.line && "PC" !in notReady.line)
    }

    /** su that never answers (no grant) or refuses: the phone step, in words that say where to allow root. */
    @Test
    fun rootThatDoesNotAnswerOrRefusesSaysWhereToAllowIt() {
        val silent = of("Root did not answer within 20 s. Open your root manager (KernelSU, Magisk or APatch), allow root for OneOS, then Check again.")
        assertEquals("Root didn't answer", silent.title)
        assertEquals(OneiosPart.PHONE, silent.part)
        assertEquals(OneiosFix.CHECK_AGAIN, silent.fix)
        assertTrue(silent.line, silent.line.startsWith("Open your root manager") && "KernelSU" in silent.line)
        val refused = of("Root was refused. Allow root for OneOS in your root manager (KernelSU, Magisk or APatch), then Check again (exit 1)")
        assertEquals("Root isn't allowed for OneOS", refused.title)
        assertEquals(OneiosPart.PHONE, refused.part)
    }
}
