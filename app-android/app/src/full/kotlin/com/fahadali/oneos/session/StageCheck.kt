package com.fahadali.oneos.session

import android.content.Context
import android.os.SystemClock
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.ApkSeries
import com.fahadali.oneos.core.model.ClassPath
import com.fahadali.oneos.core.model.DeviceFacts
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.GateInput
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.GateReport
import com.fahadali.oneos.core.model.ImageFileCheck
import com.fahadali.oneos.core.model.InstalldDerivation
import com.fahadali.oneos.core.model.JarsListing
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.ProbeResult
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SuProbeResult
import com.fahadali.oneos.core.model.SuState
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.core.root.StageStatus
import com.fahadali.oneos.core.root.SuProbe
import com.fahadali.oneos.core.safety.HostInstalldTable
import com.fahadali.oneos.probe.CarrierProps
import com.fahadali.oneos.probe.ProbeSession
import java.io.File

/**
 * The read-only check behind the Image, Prepare and Switch screens: `su -c id`,
 * the stage check (assets/root/status.list) and, unless [Mode.STAGE_ONLY],
 * One UI's installd interface (assets/root/installd.list), then the facts an
 * app can read and the gates (SwitchGates). Root only reads here.
 */
object StageCheck : BackgroundJob<StageCheck.State>(State(), "oneos-check") {
    enum class Mode { STAGE_ONLY, FULL }

    enum class Phase { IDLE, RUNNING, DONE, FAILED }

    data class Result(
        val facts: DeviceFacts,
        val su: SuProbeResult,
        val status: StageStatus,
        /** Null for [Mode.STAGE_ONLY]. */
        val installd: InstalldDerivation?,
        val oldSwitcher: Boolean?,
        /** `elapsedRealtime` of the check. */
        val at: Long,
    ) {
        val ageMs: Long get() = SystemClock.elapsedRealtime() - at
    }

    data class State(
        val phase: Phase = Phase.IDLE,
        val step: String? = null,
        val message: String? = null,
        val result: Result? = null,
        /**
         * Why the last check stopped before the gates, as a gate finding (root:
         * [SwitchGates.rootFinding]; else the stage could not be read), for
         * Home's plain message; null after a check that finished.
         */
        val failure: Finding? = null,
        /** `elapsedRealtime` the last check finished or failed at (Readiness waits a little before trying again). */
        val endedAt: Long = 0,
    ) {
        val busy: Boolean get() = phase == Phase.RUNNING
    }

    /** `su -c id` did not answer uid 0: the check stops there. */
    class RootRefused(val su: SuProbeResult, message: String) : IllegalStateException(message)

    /** A check is good for this long; Switch asks for a new one after it. */
    const val FRESH_MS = 10 * 60 * 1000L

    /**
     * A check another job ran itself (Prepare before it writes and after it
     * verifies, Switch before root is asked): the screens and Home show it
     * instead of an older one. Ignored while a check of this job's own runs.
     */
    fun publish(r: Result) {
        if (state.busy) return
        update(State(Phase.DONE, result = r, endedAt = SystemClock.elapsedRealtime()))
    }

    private val status = ReadOnlyRun(ReadOnlyRun.STATUS_LIST, "root-lists")
    private val installd = ReadOnlyRun(ReadOnlyRun.INSTALLD_LIST, "root-lists")

    fun start(ctx: Context, mode: Mode) {
        if (state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy) return
        val app = ctx.applicationContext
        val keep = state.result
        update(State(Phase.RUNNING, step = "Checking root…", result = keep))
        executor.execute {
            val r = runCatching { runBlocking(app, mode) { update(state.copy(step = it)) } }
            val now = SystemClock.elapsedRealtime()
            r.fold(
                onSuccess = { update(State(Phase.DONE, result = it, endedAt = now)) },
                onFailure = { e ->
                    val failure = when (e) {
                        is RootRefused -> SwitchGates.rootFinding(e.su)
                        else -> Finding(
                            SwitchGates.ID_STAGE, Level.BLOCK, "Stage not checked", e.message ?: e.javaClass.simpleName, SwitchGates.R_STAGE_NOT_READ,
                        )
                    }
                    // A root that stopped answering makes the older result stale for Home: drop it then.
                    update(State(Phase.FAILED, message = e.message ?: e.javaClass.simpleName, result = keep.takeIf { e !is RootRefused }, failure = failure, endedAt = now))
                },
            )
        }
    }

    fun cancel() {
        status.cancel()
        installd.cancel()
    }

    /** The whole check, on the calling thread (Prepare and Switch run it again right before root writes). */
    fun runBlocking(app: Context, mode: Mode, progress: (String) -> Unit = {}): Result {
        val su = SuProbe.runId()
        if (su.state != SuState.GRANTED || su.uid != 0) throw RootRefused(su, ProbeSession.suText(app, su))
        progress("Reading the stage folder…")
        val st = readStatus(app)
        val derivation = if (mode == Mode.FULL) {
            progress("Reading One UI's installd interface…")
            readInstalld(app)
        } else {
            null
        }
        progress("Reading this phone…")
        val facts = facts(app, su, st)
        return Result(facts, su, st, derivation, RootProbe(app).oldSwitcherInstalled(), SystemClock.elapsedRealtime())
    }

    fun readStatus(app: Context): StageStatus {
        val dir = File(app.cacheDir, "stage-check").apply {
            deleteRecursively()
            mkdirs()
        }
        try {
            val out = status.run(app, status.fileSink(dir))
            if (out.stopped) throw IllegalStateException("the stage check stopped: ${out.end.error ?: if (out.end.killed) "no answer in time" else "stopped"}")
            return StageStatus.parse(out.statuses) { path -> File(dir, path).takeIf { it.isFile }?.readText() }
        } finally {
            dir.deleteRecursively()
        }
    }

    private fun readInstalld(app: Context): InstalldDerivation {
        val dir = File(app.cacheDir, "installd-check").apply {
            deleteRecursively()
            mkdirs()
        }
        try {
            val out = installd.run(app, installd.fileSink(dir))
            if (out.stopped) return InstalldDerivation.failed("the installd read stopped")
            return derive(dir, out.stream.results)
        } finally {
            dir.deleteRecursively()
        }
    }

    /** As ProbeSession derives it: the captured dex in system_server's class-loader order. */
    private fun derive(capture: File, results: List<ProbeResult>): InstalldDerivation {
        val dex = results.firstOrNull { it.id == "installd.dex" }
        if (dex == null || dex.files.isEmpty()) return InstalldDerivation.failed("no dex captured (${dex?.status?.label ?: "not run"})")
        return runCatching {
            val cp = File(capture, "installd/classpath.txt").takeIf { it.isFile }?.readText().orEmpty()
            val jars = File(capture, "installd/jars.txt").takeIf { it.isFile }?.readText().orEmpty()
            HostInstalldTable.derive(
                HostInstalldTable.inputsFrom(capture, dex.files, ClassPath.order(cp)),
                JarsListing.parse(jars).associate { it.path to it.sha256 },
            )
        }.getOrElse { InstalldDerivation.failed("${it.javaClass.simpleName}: ${it.message}", dex.files.map { f -> f.path }) }
    }

    /** FactProbe's facts, with the carrier props (the app's own read, else root's from the stage check) and the su result. */
    fun facts(app: Context, su: SuProbeResult, st: StageStatus?): DeviceFacts =
        CarrierProps.withCarrier(FactProbe(app).collect(RootProbe(app).signals(su)), st?.carrier)

    /**
     * The gates for [phase] from [r], with a fresh screen-lock read and the
     * app's own files. PREPARE is for the picked .gz or, [onPhone], the stage's
     * system.raw (root hashes it in Prepare, keep-raw, and moves it to the attic
     * when it is not that image); SWITCH for the staged image. The report names
     * the image and its set ([GateReport.image], [GateReport.set]).
     */
    fun gates(
        app: Context,
        r: Result,
        phase: GatePhase,
        imageFile: ImageFileCheck? = null,
        onPhone: Boolean = false,
        /** Bytes root frees first: a kept stage's old system.raw, replaced or used as it is. */
        reclaimBytes: Long = 0,
        screenLock: Boolean? = FactProbe.screenLockSet(app),
        facts: DeviceFacts = r.facts,
    ): GateReport {
        val profile = Profiles.resolve(facts).profile
        val st = r.status
        val launch = SessionPrefs.lastLaunch(app)
        val input = GateInput(
            facts = facts,
            screenLockSet = screenLock,
            allowScreenLock = SessionPrefs.allowScreenLock(app),
            oldSwitcherInstalled = r.oldSwitcher,
            installd = r.installd,
            stage = st.stageState(profile),
            imageFile = imageFile.takeIf { !onPhone },
            onPhone = if (onPhone) st.stagedRaw else null,
            expectedInstalld = runCatching { AppAssets.hostInstalldTxt(app) }.getOrNull(),
            reclaimBytes = reclaimBytes,
            appVersionCode = BuildConfig.VERSION_CODE,
            uncollectedLogs = launch != null && !launch.logsCollected && launch.rebootedSince(),
            series = ApkSeries.byId(BuildConfig.SERIES),
        )
        return SwitchGates.evaluate(phase, input)
    }
}
