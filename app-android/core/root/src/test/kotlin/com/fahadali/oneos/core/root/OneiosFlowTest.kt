package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosFix
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosPart
import com.fahadali.oneos.core.model.OneiosPlain
import com.fahadali.oneos.core.model.OneiosStaged
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * The iOS flow's screens (docs/oneios.md, "In the app") from root's `status`: the steps and their
 * marks, each package's check, the one next action, and every refusal the scripts can print in plain
 * words. Pure Kotlin on the scripts' text and on status lines: no shell and no tool runs here, so it
 * runs as it is on Linux and macOS.
 */
class OneiosFlowTest {
    private fun status(vararg lines: String) = OneiosStatus.parse(lines.toList())

    private val runtime = "runtime 0.1.6 1 bin/xnuhost 1 0"
    private val image = "image 1 27.0.1 24A446 17900000000"

    private fun flow(
        st: OneiosStatus?,
        running: OneiosFlow.Job? = null,
        last: OneiosFlow.Job? = null,
        failure: String? = null,
        offered: Boolean? = true,
        runtimeRecord: OneiosStaged? = null,
        imageRecord: OneiosStaged? = null,
    ) = OneiosFlow.of(OneiosFlow.Input(st, offered, running, last, failure, runtimeRecord, imageRecord))

    private fun marks(v: OneiosFlow.View) = v.rows.map { it.mark }

    // --- Every refusal of the scripts has plain words ----------------------------------

    /** `refuse "..."` of a script, its shell expansions filled in with values like the phone's. */
    private fun refusals(text: String): List<String> {
        val samples = mapOf(
            "STAGE" to "/data/local/tmp/oneios", "S" to "/data/local/tmp/oneios", "f" to "oneios_switch.sh", "name" to "bin/xnuhost",
            "path" to "os.img", "R_VERSION" to "0.1.6", "R_ABI" to "2", "ABI" to "1", "R_XNUHOST" to "bin/xnuhost", "R_FORMATS" to "1",
            "I_FORMAT" to "2", "CAP" to "12", "P_MODEL" to "SM-S918B", "P_DEVICE" to "dm3q", "P_SOC" to "SM8550", "BB" to "/data/adb/ksu/bin/busybox",
            "xnuhost" to "bin/xnuhost", "got" to "3", "files" to "21", "onDisk" to "4", "man" to "manifest.json", "n" to "/data/local/tmp/oneios/image.new",
            "d" to "/data/local/tmp/oneios/image.new/overlay", "to" to "/data/local/tmp/oneios/oneios_switch.sh", "op" to "812", "old" to "901 ",
            "left" to "/data/local/tmp/oneios/x ", "extra" to "x ", "bad" to "3: x", "missing" to " nsenter", "a" to "nsenter", "m" to "/proc/1/mountinfo",
            "SESSION" to "/data/local/tmp/oneios/session", "CTL" to "/data/local/tmp/oneios/control", "SELF_NS" to "mnt:[1]", "INIT_NS" to "mnt:[2]",
            "2" to "9", "why" to "",
        )
        val out = mutableListOf<String>()
        for (m in Regex("""refuse "([^"]*(?:"[^"]*"\)[^"]*)?)"""").findAll(text)) {
            var t = m.groupValues[1]
            if (t == "\$*" || t == "\$why") continue
            t = t.replace(Regex("""\$\(\(BTEMP / 10\)\)"""), "44")
                .replace(Regex("""\$\(cat "\${'$'}CTL/state"\)"""), "running")
                .replace(Regex("""\$\(printf .*"""), "x")
                .replace(Regex("""\$\{f##\*/\}"""), "os.img")
                .replace(Regex("""\$\{to%/\*\}"""), "/data/local/tmp/oneios")
                .replace(Regex("""\$\{([A-Za-z_0-9]+)(:-[^}]*)?\}""")) { samples[it.groupValues[1]] ?: "x" }
            for (kind in listOf("runtime", "image")) {
                out += t.replace("\$kind", kind).replace(Regex("""\$([A-Za-z_][A-Za-z_0-9]*|[0-9])""")) { samples[it.groupValues[1]] ?: "x" }
            }
        }
        return out.distinct()
    }

    /** Lines that are generic by design: the test root's, the shell's argument check, a read that failed. */
    private val generic = Regex("""^(test root|could not read|could not make|ONEIOS_TEST_ROOT)""")

    @Test
    fun everyRefusalOfTheSwitchAndRootScriptsHasPlainWords() {
        val switch = File(Shipped.switcherAssets, "oneios_switch.sh").readText()
        val root = File(Shipped.fullAssets, OneiosRoot.ASSET).readText()
        // The hardware checks' refusals are their own screen's (OneiosChecks), not this flow's.
        val rootFlow = root.substringBefore("# --- Hardware checks")
        val launcher = Regex("""@@REFUSED ([^"]*)"""").findAll(OneiosRoot.TEMPLATE).map { it.groupValues[1].replace("\$S", "/data/local/tmp/oneios").replace("\$m", "/proc/1/mountinfo") }.toList()
        val all = refusals(switch) + refusals(rootFlow) + launcher
        assertTrue("found only ${all.size} refusals", all.size > 60)
        for (p in all) {
            for (kind in listOf(null, OneiosKind.RUNTIME, OneiosKind.IMAGE)) {
                val m = OneiosPlain.refused(p, kind)
                assertTrue("$p: title '${m.title}'", m.title.length <= OneiosPlain.MAX_TITLE)
                assertTrue("$p: line '${m.line}'", m.line.length <= OneiosPlain.MAX_LINE)
                if (!generic.containsMatchIn(p)) assertNotEquals("no plain words for: $p", "Couldn't finish", m.title)
                assertEquals(p.trim(), m.detail)
            }
        }
    }

    @Test
    fun thePreflightsRefusalsComeInTheOrderTheChecksAssume() {
        // What OneiosFlow.check reads from a refusal rests on this order: this phone and root, then
        // stage_checks (the runtime's lines, then the image set's), then the phone's state.
        val switch = File(Shipped.switcherAssets, "oneios_switch.sh").readText()
        val preflight = switch.substringAfter("# --- PREFLIGHT").substringBefore("PREFLIGHT OK")
        assertTrue("the preflight's stage line moved", preflight.contains("# The stage first"))
        fun parts(text: String) = refusals(text).map { OneiosPlain.refused(it).part }
        val before = parts(preflight.substringBefore("# The stage first"))
        val after = parts(preflight.substringAfter("# The stage first"))
        assertTrue(before.isNotEmpty() && after.isNotEmpty())
        assertTrue("before the stage: $before", before.all { it == OneiosPart.PHONE })
        assertTrue("after the stage: $after", after.all { it == OneiosPart.SWITCH })
        // stage_checks itself, without check_list (whose lines are of the kind it is called for).
        val stage = parts(switch.substringAfter("stage_checks() {").substringBefore("# <runtime|image> <full|ids>"))
        val firstImage = stage.indexOf(OneiosPart.IMAGE)
        assertTrue("no image line in stage_checks: $stage", firstImage > 0)
        assertTrue("stage_checks: $stage", stage.lastIndexOf(OneiosPart.RUNTIME) < firstImage)
        assertTrue("stage_checks: $stage", stage.none { it == OneiosPart.PHONE || it == OneiosPart.SWITCH })
    }

    // --- The steps -----------------------------------------------------------------------

    @Test
    fun aPhoneWithNoStageStartsWithTheRuntime() {
        val v = flow(status("stage none"))
        assertEquals(OneiosFlow.Mark.DONE, v.mark(OneiosFlow.Step.PHONE))
        assertEquals(OneiosFlow.Mark.NEXT, v.mark(OneiosFlow.Step.RUNTIME))
        assertEquals(OneiosFlow.Mark.PENDING, v.mark(OneiosFlow.Step.IMAGE))
        assertEquals(OneiosFlow.Next.GET_RUNTIME, v.next)
        assertEquals(OneiosFlow.Step.RUNTIME, v.current)
        assertEquals(OneiosFlow.Step.IMAGE, v.then)
        assertTrue(v.problem!!.isNextStep)
        assertEquals(OneiosFlow.Check.NOT_STAGED, v.runtime)
        assertFalse(v.ready)
    }

    @Test
    fun beforeRootAnsweredTheFirstStepRuns() {
        val v = flow(null, running = OneiosFlow.Job.CHECK)
        assertEquals(OneiosFlow.Mark.RUNNING, v.mark(OneiosFlow.Step.PHONE))
        assertEquals(OneiosFlow.Next.WAIT, v.next)
        val failed = flow(null, last = OneiosFlow.Job.CHECK, failure = "root did not answer in time")
        assertEquals(OneiosFlow.Mark.FAILED, failed.mark(OneiosFlow.Step.PHONE))
        assertEquals("Allow root access", failed.problem!!.title)
        assertEquals(OneiosFlow.Next.CHECK_AGAIN, failed.next)
        assertEquals(OneiosFlow.Next.NOT_THIS_PHONE, flow(null, offered = false).next)
        assertEquals(OneiosFlow.Mark.FAILED, flow(null, offered = false).mark(OneiosFlow.Step.PHONE))
    }

    @Test
    fun aRuntimeAloneAsksForTheImageSet() {
        val st = status("stage present", runtime, "image none", "session none never", "outcome none",
            "ready 0 no iOS image set is staged: import the one you built with OneiOS's scripts in the OneOS app")
        val record = OneiosStaged(OneiosKind.RUNTIME, "0.1.6", null, 12, 12_000_000, 1)
        val v = flow(st, runtimeRecord = record)
        assertEquals(listOf(OneiosFlow.Mark.DONE, OneiosFlow.Mark.DONE, OneiosFlow.Mark.NEXT, OneiosFlow.Mark.PENDING, OneiosFlow.Mark.PENDING), marks(v))
        assertEquals(OneiosFlow.Next.IMPORT_IMAGE, v.next)
        // The image refusal comes after the runtime's checks: the runtime passed them.
        assertEquals(OneiosFlow.Check.PASSED, v.runtime)
        assertEquals(OneiosFlow.Check.NOT_STAGED, v.image)
        assertEquals("Version 0.1.6 · 12 files, 12 MB · every file checked", v.runtimeLine)
        // The app's record of another version is not shown.
        assertEquals("Version 0.1.6 · every file checked", flow(st, runtimeRecord = record.copy(version = "0.1.5")).runtimeLine)
    }

    @Test
    fun bothStagedAndThePreflightPassedIsReady() {
        val st = status("stage present", runtime, image, "session none returned", "outcome inplace 1763000000", "ready 1")
        val v = flow(st)
        assertTrue(marks(v).all { it == OneiosFlow.Mark.DONE })
        assertEquals(OneiosFlow.Next.SWITCH, v.next)
        assertTrue(v.ready)
        assertNull(v.current)
        assertNull(v.problem)
        assertEquals(OneiosFlow.Check.PASSED, v.image)
        assertEquals("iOS 27.0.1 (24A446) · 17.9 GB · every file as staged", v.imageLine)
        assertEquals("Kept from earlier sessions", v.dataLine)
        assertEquals("Back in One UI without a restart", OneiosFlow.lastReturn(st)!!.title)
    }

    @Test
    fun aPhoneStateRefusalMeansBothPackagesPassed() {
        val st = status("stage present", runtime, image, "session none never", "outcome none", "ready 0 battery at 12% and not charging")
        val v = flow(st)
        assertEquals(OneiosFlow.Check.PASSED, v.runtime)
        assertEquals(OneiosFlow.Check.PASSED, v.image)
        assertEquals(OneiosFlow.Mark.FAILED, v.mark(OneiosFlow.Step.READY))
        assertEquals("Charge your phone", v.problem!!.title)
        assertEquals(OneiosFlow.Next.CHECK_AGAIN, v.next)
        assertFalse(v.ready)
        assertEquals("New: made at the first switch", v.dataLine)
        assertTrue(OneiosFlow.dataNew(st))
    }

    @Test
    fun aChangedImageFailsItsStepAndAsksForItAgain() {
        val st = status("stage present", runtime, image, "session none returned", "outcome none",
            "ready 0 image/os.img changed since it was staged: stage the image again")
        val v = flow(st)
        assertEquals(OneiosFlow.Check.PASSED, v.runtime)
        assertEquals(OneiosFlow.Check.FAILED, v.image)
        assertEquals(OneiosFlow.Mark.FAILED, v.mark(OneiosFlow.Step.IMAGE))
        assertEquals(OneiosFlow.Mark.PENDING, v.mark(OneiosFlow.Step.READY))
        assertEquals(OneiosFlow.Next.IMPORT_IMAGE, v.next)
        assertEquals("iOS 27.0.1 (24A446) · 17.9 GB · check failed", v.imageLine)
    }

    @Test
    fun aPlaceholderRuntimeFailsTheRuntimeStepAndLeavesTheImageUnchecked() {
        val st = status("stage present", "runtime 0.1.0 1 bin/xnuhost 1 1", image, "session none never", "outcome none",
            "ready 0 the runtime 0.1.0 carries a placeholder instead of xnuhost (OneiOS has not built xnuhost yet): it cannot start iOS")
        val v = flow(st)
        assertEquals(OneiosFlow.Check.FAILED, v.runtime)
        assertEquals(OneiosFlow.Check.NOT_CHECKED, v.image)
        assertEquals(OneiosFlow.Mark.FAILED, v.mark(OneiosFlow.Step.RUNTIME))
        assertEquals(OneiosFlow.Next.GET_RUNTIME, v.next)
        assertEquals("Version 0.1.0 · placeholder, can't start iOS", v.runtimeLine)
    }

    @Test
    fun anOpenSessionsOnlyActionIsBackToOneUi() {
        val st = status("stage present", runtime, image, "session open running", "outcome none",
            "ready 0 an iOS session of this boot is still open (running): restart the phone first")
        val v = flow(st)
        assertEquals(OneiosFlow.Next.BACK_TO_ONE_UI, v.next)
        assertEquals(OneiosFix.BACK_TO_ONE_UI, v.problem!!.fix)
        assertFalse(v.ready)
    }

    @Test
    fun aJobShowsOnItsStepAndItsFailureStaysThere() {
        val st = status("stage present", runtime, "image none", "session none never", "outcome none",
            "ready 0 no iOS image set is staged: import the one you built with OneiOS's scripts in the OneOS app")
        val importing = flow(st, running = OneiosFlow.Job.IMPORT_IMAGE)
        assertEquals(OneiosFlow.Mark.RUNNING, importing.mark(OneiosFlow.Step.IMAGE))
        assertEquals(OneiosFlow.Next.WAIT, importing.next)
        val failed = flow(st, last = OneiosFlow.Job.IMPORT_IMAGE, failure = "os.img did not arrive intact (SHA-256 differs)")
        assertEquals(OneiosFlow.Mark.FAILED, failed.mark(OneiosFlow.Step.IMAGE))
        assertEquals("The iOS image set is damaged", failed.problem!!.title)
        assertEquals(OneiosFlow.Next.IMPORT_IMAGE, failed.next)
        // A download that lost its connection: download again, the runtime's step.
        val none = status("stage none")
        val offline = flow(none, last = OneiosFlow.Job.DOWNLOAD_RUNTIME, failure = "No connection to GitHub (timeout).")
        assertEquals(OneiosFlow.Mark.FAILED, offline.mark(OneiosFlow.Step.RUNTIME))
        assertEquals(OneiosFlow.Next.DOWNLOAD_RUNTIME, offline.next)
    }

    @Test
    fun aRefusedSwitchIsTheLastChecksFailure() {
        val st = status("stage present", runtime, image, "session none returned", "outcome none", "ready 1")
        val v = flow(st, last = OneiosFlow.Job.SWITCH, failure = "battery too warm (44 C)")
        assertEquals(OneiosFlow.Mark.FAILED, v.mark(OneiosFlow.Step.READY))
        assertEquals("Your phone is too warm", v.problem!!.title)
        // A check that failed itself: the stage shown is the last answer, so no Switch is offered.
        val stale = flow(st, last = OneiosFlow.Job.CHECK, failure = "root did not answer in time")
        assertEquals(OneiosFlow.Mark.FAILED, stale.mark(OneiosFlow.Step.PHONE))
        assertEquals(OneiosFlow.Next.CHECK_AGAIN, stale.next)
        assertFalse(stale.ready)
    }

    @Test
    fun howTheLastSessionCameBack() {
        assertNull(OneiosFlow.lastReturn(status("stage present", "outcome none")))
        assertEquals("Back in One UI by a restart", OneiosFlow.lastReturn(status("outcome reboot 1763000000"))!!.title)
        val failsafe = OneiosFlow.lastReturn(status("outcome failsafe 1763000000 Gate A: vold changed"))!!
        assertEquals("Back in One UI by the failsafe", failsafe.title)
        assertTrue(failsafe.line, failsafe.line.endsWith("Gate A: vold changed"))
        assertEquals(OneiosFix.SESSION_LOGS, failsafe.fix)
    }
}
