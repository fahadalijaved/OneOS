package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.CarrierRules
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.Gate
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.GateReport
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.ScreenLockRule
import com.fahadali.oneos.core.model.SuProbeResult
import com.fahadali.oneos.core.model.SuState
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.core.root.HomeState.Kind
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Home shows one status and one button, worst first (the redesign, section 2.2). */
class HomeStateTest {
    private val n6 = Images.FIND_N6

    private fun ok(id: String) = Finding(id, Level.OK, "ok")

    private fun block(id: String, reason: String) = Finding(id, Level.BLOCK, "t", "d", reason)

    private val allOk = listOf(
        SwitchGates.ID_ROOT, SwitchGates.ID_PROFILE, SwitchGates.ID_ANDROID, SwitchGates.ID_FORM, SwitchGates.ID_IMAGE,
        SwitchGates.ID_INSTALLD, SwitchGates.ID_OLD_SWITCHER, SwitchGates.ID_STAGE, SwitchGates.ID_SPACE,
        SwitchGates.ID_SCREEN_LOCK, SwitchGates.ID_BATTERY,
    )

    /** The Fold's SWITCH gates with the Find N6 staged, every gate OK but [bad]. */
    private fun report(vararg bad: Finding, image: com.fahadali.oneos.core.model.ImageRef? = n6) = GateReport(
        GatePhase.SWITCH, Profiles.F8U, image, PackageSets.N6_F8U,
        allOk.map { id -> Gate(bad.firstOrNull { it.id == id } ?: ok(id)) } +
            Gate(Finding(SwitchGates.ID_CARRIER, Level.INFO, "Calls use 2G or 3G", "", CarrierRules.R_2G_3G)),
    )

    private fun decide(
        report: GateReport?,
        checking: Boolean = false,
        failure: Finding? = null,
        job: HomeJob? = null,
        last: LastSession? = null,
        status: StageStatus? = null,
        cached: HomeSnapshot? = null,
    ) = HomeState.decide(HomeInput(report, status, checking, failure, job, last, appVersionCode = 4, cached = cached))

    private val unfinished = block(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_UNFINISHED)
    private val mounted = block(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_MOUNTED)
    private val lock = block(SwitchGates.ID_SCREEN_LOCK, ScreenLockRule.R_SET)
    private val battery = block(SwitchGates.ID_BATTERY, SwitchGates.R_BATTERY_LOW)
    private val nothing = block(SwitchGates.ID_IMAGE, SwitchGates.R_IMAGE_NOTHING)
    private val oldVersion = block(SwitchGates.ID_IMAGE, SwitchGates.R_IMAGE_OTHER_VERSION)
    private val root = block(SwitchGates.ID_ROOT, SwitchGates.R_ROOT_DENIED)
    private val installd = block(SwitchGates.ID_INSTALLD, SwitchGates.R_INSTALLD_DIFFERS)
    private val oldSwitcher = block(SwitchGates.ID_OLD_SWITCHER, SwitchGates.R_OLD_SWITCHER_INSTALLED)

    private fun last(outcome: OutcomeKind? = OutcomeKind.USER_RETURN, seen: Boolean = false, over: Boolean = true) =
        LastSession("0123456789abcdef", n6.id, dryRun = false, wallMs = 1_792_000_000_000, over = over, outcome = outcome, afterSeconds = 2520, seen = seen)

    @Test
    fun aNewerOneOsIsTheHeroBelowRestoreJobsAndRoot() {
        val offer = com.fahadali.oneos.core.model.PlainMessage("Update for ColorOS 17", "OneOS 0.4.43: Theme Store", FixAction.APP_UPDATE, "Update", Level.INFO)
        fun withUpdate(r: GateReport?, job: HomeJob? = null, busy: Boolean = false) =
            HomeState.decide(HomeInput(r, null, false, null, job, null, appVersionCode = 4, appUpdate = offer, appUpdateBusy = busy))
        // Above ready, a fix, an update of the stage, nothing set up, an unsupported phone.
        for (r in listOf(report(), report(lock), report(lock, oldVersion), report(lock, nothing), report(installd))) {
            val s = withUpdate(r)
            assertEquals(Kind.APP_UPDATE, s.kind)
            assertEquals(FixAction.APP_UPDATE, s.primary)
            assertEquals("Update", s.primaryLabel)
            assertEquals("Update for ColorOS 17", s.problem?.title)
            assertTrue(s.primaryEnabled)
        }
        // Never above a session to restore, a running job or root.
        assertEquals(Kind.RESTORE, withUpdate(report(unfinished)).kind)
        assertEquals(Kind.SETTING_UP, withUpdate(report(), job = HomeJob(HomeJob.Kind.SETUP, n6, 10)).kind)
        assertEquals(Kind.NO_ROOT, withUpdate(report(root)).kind)
        // Downloading or installing: the button is off.
        assertFalse(withUpdate(report(), busy = true).primaryEnabled)
        // No offer: Home as before.
        assertEquals(Kind.READY, decide(report()).kind)
    }

    @Test
    fun theWorstComesFirst() {
        // Each row adds the next worse problem; Home shows that one.
        val ladder = listOf(
            Kind.READY to arrayOf(),
            Kind.FIX to arrayOf(lock),
            Kind.UPDATE to arrayOf(lock, oldVersion),
            Kind.NOTHING_SET_UP to arrayOf(lock, nothing),
            Kind.RESTART to arrayOf(lock, nothing, mounted),
            Kind.OLD_SWITCHER to arrayOf(lock, nothing, mounted, oldSwitcher),
            Kind.UNSUPPORTED to arrayOf(lock, nothing, mounted, oldSwitcher, installd),
            Kind.NO_ROOT to arrayOf(lock, nothing, mounted, oldSwitcher, installd, root),
            Kind.RESTORE to arrayOf(lock, nothing, oldSwitcher, installd, root, unfinished),
        )
        for ((kind, bad) in ladder) {
            val s = decide(report(*bad))
            assertEquals(bad.joinToString { "${it.id}/${it.reason}" }, kind, s.kind)
        }
        // A running setup or switch comes before root, an unfinished session before the job.
        assertEquals(Kind.SETTING_UP, decide(report(root, lock), job = HomeJob(HomeJob.Kind.SETUP, n6, 62)).kind)
        assertEquals(Kind.SWITCHING, decide(report(), job = HomeJob(HomeJob.Kind.SWITCH, n6)).kind)
        assertEquals(Kind.RESTORE, decide(report(unfinished), job = HomeJob(HomeJob.Kind.SETUP, n6, 1)).kind)
        assertEquals(Kind.RESTORING, decide(report(unfinished), job = HomeJob(HomeJob.Kind.RESTORE)).kind)
        // Back from a session: after the problems, before Ready.
        assertEquals(Kind.FIX, decide(report(lock), last = last()).kind)
        assertEquals(Kind.WELCOME_BACK, decide(report(), last = last()).kind)
    }

    @Test
    fun eachStateHasItsButton() {
        val ready = decide(report())
        assertEquals(FixAction.SWITCH, ready.primary)
        assertEquals("Switch to ColorOS 17", ready.primaryLabel)
        assertEquals(n6, ready.image)
        assertTrue(ready.primaryEnabled)

        val fix = decide(report(lock, battery))
        assertEquals(FixAction.OPEN_LOCK_SETTINGS, fix.primary)
        assertEquals("Turn off your screen lock", fix.problem!!.title)
        assertEquals(lock, fix.finding)
        // Still names the system that is set up (its row on Home).
        assertEquals(n6, fix.image)

        val restore = decide(report(unfinished))
        assertEquals(FixAction.RESTORE, restore.primary)
        assertEquals("Restore now", restore.primaryLabel)

        val update = decide(report(oldVersion))
        assertEquals(FixAction.UPDATE, update.primary)
        assertEquals("Finish updating ColorOS 17", update.problem!!.title)

        val nothingYet = decide(report(nothing, image = null))
        assertEquals(FixAction.CHOOSE_SYSTEM, nothingYet.primary)
        assertNull(nothingYet.problem)
        // A downloaded file was chosen already: set that system up.
        val picked = HomeState.decide(HomeInput(report(nothing, image = null), picked = Images.PIXEL_YOGI))
        assertEquals(Kind.NOTHING_SET_UP, picked.kind)
        assertEquals(FixAction.SET_UP, picked.primary)
        assertEquals("Set up Pixel 11 Fold", picked.primaryLabel)
        assertEquals(Images.PIXEL_YOGI, picked.image)

        // A restart or a battery to charge has nothing to tap.
        assertNull(decide(report(mounted)).primary)
        assertNull(decide(report(battery)).primary)

        val setup = decide(report(), job = HomeJob(HomeJob.Kind.SETUP, Images.PIXEL_YOGI, 62))
        assertEquals(FixAction.SHOW_PROGRESS, setup.primary)
        assertEquals(62, setup.percent)
        assertEquals(Images.PIXEL_YOGI, setup.image)
        assertNull(decide(report(), job = HomeJob(HomeJob.Kind.SWITCH, n6)).primary)
    }

    @Test
    fun beforeTheFirstCheck() {
        val checking = decide(null, checking = true)
        assertEquals(Kind.CHECKING, checking.kind)
        assertEquals(FixAction.CHOOSE_SYSTEM, checking.primary)
        assertFalse(checking.primaryEnabled)
        // The check stopped at root: allow root (no root app known here: try again).
        val noRoot = decide(null, failure = SwitchGates.rootFinding(SuProbeResult(SuState.DENIED, null, null, "")))
        assertEquals(Kind.NO_ROOT, noRoot.kind)
        assertEquals("Allow root access", noRoot.problem!!.title)
        assertEquals(FixAction.TRY_AGAIN, noRoot.primary)
        val other = decide(null, failure = block(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_NOT_READ))
        assertEquals(Kind.CHECK_FAILED, other.kind)
        assertEquals(FixAction.TRY_AGAIN, other.primary)
    }

    @Test
    fun aNewCheckRunningKeepsTheStateButHoldsTheJobs() {
        val s = decide(report(), checking = true)
        assertEquals(Kind.READY, s.kind)
        assertFalse(s.primaryEnabled)
        assertTrue(s.checking)
        assertFalse(decide(report()).checking)
        // Opening lock settings needs no root: still allowed.
        assertTrue(decide(report(lock), checking = true).primaryEnabled)
        assertFalse(decide(report(unfinished), checking = true).primaryEnabled)
    }

    @Test
    fun welcomeBackOnceAfterTheLogsAreRead() {
        assertEquals(Kind.WELCOME_BACK, decide(report(), last = last()).kind)
        assertEquals(FixAction.SWITCH, decide(report(), last = last()).primary)
        // Seen, not read yet, or the phone has not restarted: just Ready (the "Last time" row).
        assertEquals(Kind.READY, decide(report(), last = last(seen = true)).kind)
        assertEquals(Kind.READY, decide(report(), last = last(outcome = null)).kind)
        assertEquals(Kind.READY, decide(report(), last = last(over = false)).kind)
        assertEquals(OutcomeKind.USER_RETURN, decide(report(), last = last(seen = true)).last!!.outcome)
    }

    @Test
    fun theStageAloneCanAskForRestore() {
        // The check's stage read says the last session never returned, before any gate report.
        val st = StageFixtures.status(
            StageFixtures.prepared(Profiles.F8U, n6, PackageSets.N6_F8U, extra = mapOf("stage.session" to "boot=new\nactive\nboot_id=old\n")),
        )
        assertTrue(st.unfinishedSession)
        val s = decide(null, status = st)
        assertEquals(Kind.RESTORE, s.kind)
        assertEquals(FixAction.RESTORE, s.primary)
    }

    /** The tiles as Home would keep them (their values are the app's text). */
    private val tiles = listOf(
        HomeCheck(SwitchGates.ID_ROOT, Level.OK, "KernelSU allowed"),
        HomeCheck(SwitchGates.ID_SPACE, Level.OK, "54 GB free"),
        HomeCheck(SwitchGates.ID_BATTERY, Level.OK, "78% · 31 °C"),
        HomeCheck(SwitchGates.ID_SCREEN_LOCK, Level.BLOCK, "On"),
    )

    @Test
    fun aColdStartShowsTheLastHomeButNeverActsOnIt() {
        // Kept from the last finished check: ready, and the lock to fix.
        val ready = decide(report()).snapshot(tiles, 1_792_000_000_000)!!
        val fix = decide(report(lock)).snapshot(tiles, 1_792_000_000_000)!!

        // Cold start, the first check runs: the kept Home instead of "Checking your phone…", button off.
        val s = decide(null, checking = true, cached = ready)
        assertEquals(Kind.READY, s.kind)
        assertEquals(ready, s.cached)
        assertEquals(n6, s.image)
        assertEquals(FixAction.SWITCH, s.primary)
        assertEquals(decide(report()).primaryLabel, s.primaryLabel)
        assertFalse(s.primaryEnabled)
        assertTrue(s.checking)
        // Off even for an action that needs no root (a fresh FIX allows it), and no Details from what was kept.
        val f = decide(null, checking = true, cached = fix)
        assertEquals(Kind.FIX, f.kind)
        assertEquals(FixAction.OPEN_LOCK_SETTINGS, f.primary)
        assertEquals("Turn off your screen lock", f.problem!!.title)
        assertFalse(f.primaryEnabled)
        assertNull(f.finding)
        // Before the check even started: still read-only.
        assertFalse(decide(null, cached = ready).primaryEnabled)

        // The check ended: it decides, and the kept Home is gone.
        val fresh = decide(report(lock), cached = ready)
        assertEquals(Kind.FIX, fresh.kind)
        assertNull(fresh.cached)
        assertTrue(fresh.primaryEnabled)
        assertTrue(decide(report(), cached = fix).primaryEnabled)
        // A stopped check, a job, or an unfinished session wins over it.
        val denied = decide(null, failure = SwitchGates.rootFinding(SuProbeResult(SuState.DENIED, null, null, "")), cached = ready)
        assertEquals(Kind.NO_ROOT, denied.kind)
        assertNull(denied.cached)
        assertEquals(Kind.SETTING_UP, decide(null, checking = true, job = HomeJob(HomeJob.Kind.SETUP, n6, 3), cached = ready).kind)
        val st = StageFixtures.status(
            StageFixtures.prepared(Profiles.F8U, n6, PackageSets.N6_F8U, extra = mapOf("stage.session" to "boot=new\nactive\nboot_id=old\n")),
        )
        assertEquals(Kind.RESTORE, decide(null, checking = true, status = st, cached = ready).kind)
        // Back from a session is read again from the last session, not from what was kept.
        assertEquals(Kind.WELCOME_BACK, decide(null, checking = true, last = last(), cached = ready).kind)
        val welcome = decide(report(), last = last()).snapshot(tiles, 0)!!
        assertEquals(Kind.WELCOME_BACK, welcome.kind)
        assertEquals(Kind.READY, decide(null, checking = true, last = last(seen = true), cached = welcome).kind)
        assertFalse(decide(null, checking = true, last = last(), cached = welcome).primaryEnabled)
    }

    @Test
    fun onlyASettledHomeIsKept() {
        // From a finished check with no job: kept, with its tiles.
        val ready = decide(report()).snapshot(tiles, 7)!!
        assertEquals(Kind.READY, ready.kind)
        assertEquals(n6.id, ready.imageId)
        assertEquals(tiles, ready.checks)
        assertEquals(7L, ready.wallMs)
        assertEquals(Kind.NOTHING_SET_UP, decide(report(nothing, image = null)).snapshot(tiles, 0)!!.kind)
        assertEquals(Kind.RESTORE, decide(report(unfinished)).snapshot(tiles, 0)!!.kind)
        // A new check runs while the last one's result is shown: that state may be kept.
        assertTrue(decide(report(), checking = true).snapshot(tiles, 0) != null)
        // Not kept: no check yet, a failed check, root, a job, or a Home that is itself the kept one.
        assertNull(decide(null, checking = true).snapshot(tiles, 0))
        assertNull(decide(null, failure = block(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_NOT_READ)).snapshot(tiles, 0))
        assertNull(decide(report(block(SwitchGates.ID_STAGE, SwitchGates.R_STAGE_NOT_READ))).snapshot(tiles, 0))
        assertNull(decide(report(root)).snapshot(tiles, 0))
        assertNull(decide(report(), job = HomeJob(HomeJob.Kind.SETUP, n6, 50)).snapshot(tiles, 0))
        assertNull(decide(report(), job = HomeJob(HomeJob.Kind.SWITCH, n6)).snapshot(tiles, 0))
        assertNull(decide(null, checking = true, cached = ready).snapshot(tiles, 0))
        // A kept kind that is not one to show (say, an edited preference) is not shown.
        assertEquals(Kind.CHECKING, decide(null, checking = true, cached = ready.copy(kind = Kind.SWITCHING)).kind)
    }

    @Test
    fun aKeptHomeSurvivesItsTextForm() {
        val fix = decide(report(lock)).snapshot(tiles + HomeCheck("odd\tid", Level.WARN, "a\\b\nc=d"), 1_792_000_000_000)!!
        assertEquals(fix, HomeSnapshot.parse(fix.encode()))
        val nothingYet = decide(report(nothing, image = null)).snapshot(emptyList(), 0)!!
        assertNull(nothingYet.imageId)
        assertNull(nothingYet.problem)
        assertEquals(nothingYet, HomeSnapshot.parse(nothingYet.encode()))
        assertTrue(fix.sameAs(fix.copy(wallMs = 1)))
        assertFalse(fix.sameAs(nothingYet))
        // Anything else: no kept Home.
        assertNull(HomeSnapshot.parse(null))
        assertNull(HomeSnapshot.parse(""))
        assertNull(HomeSnapshot.parse("kind=READY\n"))
        assertNull(HomeSnapshot.parse(fix.encode().replace(HomeSnapshot.SCHEMA, "oneos.home/0")))
        assertNull(HomeSnapshot.parse(fix.encode().replace("kind=FIX", "kind=LATER")))
        assertNull(HomeSnapshot.parse(fix.encode() + "kind=READY\n"))
        assertNull(HomeSnapshot.parse(fix.encode() + "check=a\tOK\n"))
        assertNull(HomeSnapshot.parse(fix.encode() + "extra=1\n"))
        assertNull(HomeSnapshot.parse(fix.encode().replace("Turn off", "Turn\\x off")))
    }
}
