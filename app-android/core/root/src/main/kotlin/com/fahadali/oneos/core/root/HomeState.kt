package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.DeviceFacts
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.FixAction
import com.fahadali.oneos.core.model.GateReport
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.PlainFacts
import com.fahadali.oneos.core.model.PlainMessage
import com.fahadali.oneos.core.model.RootKind
import com.fahadali.oneos.core.model.SwitchGates

/** The last launch as Home tells it (the app's launch record plus how it ended, once the logs were read). */
data class LastSession(
    val sessionId: String,
    val imageId: String,
    val dryRun: Boolean,
    /** Wall clock of the launch. */
    val wallMs: Long,
    /** The phone restarted since the launch: the session is over. */
    val over: Boolean,
    /** How it ended; null until the logs are read. */
    val outcome: OutcomeKind? = null,
    /** Seconds into the session when it ended, when the logs say. */
    val afterSeconds: Int? = null,
    /** "Welcome back" was shown (and dismissed) for this session. */
    val seen: Boolean = false,
) {
    val image: ImageRef? get() = Images.byId(imageId)

    /** Home says "Welcome back" for it (once): the phone restarted since, the logs told how it ended, and it was not seen yet. */
    val welcomeDue: Boolean get() = over && outcome != null && !seen
}

/** A job that runs now (one at a time). */
data class HomeJob(val kind: Kind, val image: ImageRef? = null, val percent: Int? = null) {
    enum class Kind { SETUP, SWITCH, RESTORE }
}

data class HomeInput(
    /** The SWITCH gates of the last check; null = no check finished yet. */
    val report: GateReport?,
    /** The stage as the last check read it. */
    val status: StageStatus? = null,
    /** The automatic check runs now. */
    val checking: Boolean = false,
    /** The check stopped before the gates (root: [SwitchGates.rootFinding]; else the stage was not read). */
    val checkFailure: Finding? = null,
    val job: HomeJob? = null,
    val last: LastSession? = null,
    val facts: DeviceFacts? = null,
    val appVersionCode: Int? = null,
    /** A downloaded file the user chose, identified (by its size) as a system this phone takes; null = none. */
    val picked: ImageRef? = null,
    /**
     * The Home of the last finished check, kept across app starts
     * ([HomeState.snapshot]); the app passes it only on a cold start, until
     * that start's first check ends. Null = none.
     */
    val cached: HomeSnapshot? = null,
)

/**
 * Home: one status and one button (the UX redesign, section 2.2), decided
 * from the last check, the running job and the last session, worst first:
 * an unfinished session, a running job, root, an unsupported phone or One UI
 * update, the old switcher, a restart, nothing set up, an update or repair,
 * the screen lock / battery / space, back from a session, ready. Pure: the
 * app passes what it read; the same gates still run in the jobs and in root.
 *
 * A cold start shows the last known Home ([HomeInput.cached]) instead of
 * [Kind.CHECKING] while its first check runs, read-only: its button is off
 * whatever it does, and nothing is decided from it. A job, a stopped check or
 * the check's result always wins over it.
 */
data class HomeState(
    val kind: Kind,
    /** The system set up (or being set up); null = none known. */
    val image: ImageRef?,
    /** The problem's plain message ([Kind.RESTORE], [Kind.NO_ROOT] … [Kind.FIX]). */
    val problem: PlainMessage? = null,
    /** The finding behind [problem], for Details. */
    val finding: Finding? = null,
    /** The footer button; null = none. */
    val primary: FixAction? = null,
    val primaryLabel: String? = null,
    val primaryEnabled: Boolean = true,
    val last: LastSession? = null,
    val percent: Int? = null,
    /** A check (or the log read) runs now: Home shows that it is checking. */
    val checking: Boolean = false,
    /** Non-null: this is the kept Home of an earlier check ([HomeInput.cached]), shown read-only until the new check ends. */
    val cached: HomeSnapshot? = null,
    /** Decided from a finished check with no job running: Home may keep it for the next cold start ([snapshot]). */
    val settled: Boolean = false,
) {
    /**
     * What to keep of this Home for the next cold start, with the check tiles
     * as Home showed them; null when it is not one to keep: a job, a check
     * that did not finish (or failed), root not allowed, or a Home that is
     * itself the kept one.
     */
    fun snapshot(checks: List<HomeCheck>, wallMs: Long): HomeSnapshot? =
        if (settled && cached == null && kind in KEPT) HomeSnapshot(kind, image?.id, problem, primary, primaryLabel, checks, wallMs) else null

    /** In the order Home picks them (the first that applies wins). */
    enum class Kind {
        /** No check has finished yet. */
        CHECKING,

        /** The last session never returned: One UI's settings need restoring (G). */
        RESTORE,
        RESTORING,
        SETTING_UP,
        SWITCHING,
        NO_ROOT,
        CHECK_FAILED,

        /** The phone, its Android, its form or its One UI (installd) is not one this build switches on. */
        UNSUPPORTED,
        OLD_SWITCHER,
        RESTART,

        /** Nothing set up yet (B). */
        NOTHING_SET_UP,

        /** Finish updating, repair or set up again (H). */
        UPDATE,

        /** The screen lock, battery, space or another check (D). */
        FIX,

        /** Back from a session, shown once (F). */
        WELCOME_BACK,

        /** Ready to switch (C). */
        READY,
    }

    companion object {
        private val UNSUPPORTED_GATES = setOf(SwitchGates.ID_PROFILE, SwitchGates.ID_ANDROID, SwitchGates.ID_FORM, SwitchGates.ID_INSTALLD)
        private val UPDATE_REASONS = setOf(
            SwitchGates.R_IMAGE_OTHER_PHONE, SwitchGates.R_IMAGE_OTHER_VERSION, SwitchGates.R_IMAGE_OTHER_SET, SwitchGates.R_IMAGE_FILES_CHANGED,
        )

        /**
         * The kinds a cold start may show from the last check: settled states,
         * not a job, a failed check or root (those are about this start).
         */
        val KEPT = setOf(
            Kind.RESTORE, Kind.UNSUPPORTED, Kind.OLD_SWITCHER, Kind.RESTART, Kind.NOTHING_SET_UP, Kind.UPDATE, Kind.FIX,
            Kind.WELCOME_BACK, Kind.READY,
        )

        /** Actions that start a job: off while the check (or another job) runs, since only one runs at a time. */
        private val STARTS_JOB = setOf(FixAction.SWITCH, FixAction.UPDATE, FixAction.REPAIR, FixAction.RESTORE, FixAction.TRY_AGAIN, FixAction.SET_UP)

        fun decide(i: HomeInput): HomeState {
            val r = i.report
            val staged = r?.image ?: i.status?.staged(r?.profile)?.first
            val image = i.job?.image ?: staged
            val busy = i.checking || i.job != null
            val settled = r != null && i.job == null

            fun state(kind: Kind, f: Finding? = null, plain: PlainMessage? = f?.let { plainOf(it, i) }, primary: FixAction? = plain?.action, label: String? = plain?.actionLabel) =
                HomeState(
                    kind, image, plain, f,
                    primary = primary?.takeIf { it != FixAction.NONE && it != FixAction.ACKNOWLEDGE },
                    primaryLabel = label,
                    primaryEnabled = !(busy && primary in STARTS_JOB),
                    last = i.last,
                    percent = i.job?.percent,
                    checking = i.checking,
                    settled = settled,
                )

            if (i.job?.kind == HomeJob.Kind.RESTORE) return state(Kind.RESTORING, primary = null)
            // 1. A session that never returned: Restore, whatever else is wrong.
            val stageGate = r?.find(SwitchGates.ID_STAGE)?.finding
            if (stageGate?.reason == SwitchGates.R_STAGE_UNFINISHED) return state(Kind.RESTORE, stageGate)
            if (i.status?.unfinishedSession == true) {
                val f = Finding(SwitchGates.ID_STAGE, Level.BLOCK, "The last session did not end", "", SwitchGates.R_STAGE_UNFINISHED)
                return state(Kind.RESTORE, f)
            }
            // 2. A job.
            when (i.job?.kind) {
                HomeJob.Kind.SETUP -> return state(Kind.SETTING_UP, primary = FixAction.SHOW_PROGRESS, label = Plain.defaultLabel(FixAction.SHOW_PROGRESS))
                HomeJob.Kind.SWITCH -> return state(Kind.SWITCHING, primary = null)
                else -> Unit
            }
            if (r == null) {
                val fail = i.checkFailure
                val kept = i.cached?.takeIf { fail == null && it.kind in KEPT }
                return when {
                    // A cold start: the last known Home, read-only, instead of "Checking your phone…".
                    kept != null -> fromCache(kept, i)
                    fail == null -> state(Kind.CHECKING, primary = FixAction.CHOOSE_SYSTEM, label = Plain.defaultLabel(FixAction.CHOOSE_SYSTEM))
                        .copy(primaryEnabled = false)
                    fail.id == SwitchGates.ID_ROOT -> state(Kind.NO_ROOT, fail)
                    else -> state(Kind.CHECK_FAILED, fail)
                }
            }
            fun block(id: String): Finding? = r.find(id)?.finding?.takeIf { it.level == Level.BLOCK }

            // 3. Root.
            block(SwitchGates.ID_ROOT)?.let { return state(Kind.NO_ROOT, it) }
            // 4. Not a phone, Android, form or One UI this build switches on (or no system for it in this build).
            UNSUPPORTED_GATES.firstNotNullOfOrNull { id -> r.gates.firstOrNull { it.id == id && it.level == Level.BLOCK }?.finding }
                ?.let { return state(Kind.UNSUPPORTED, it) }
            block(SwitchGates.ID_IMAGE)?.takeIf { it.reason == SwitchGates.R_IMAGE_NOT_IN_BUILD || it.reason == SwitchGates.R_IMAGE_OTHER_SERIES }
                ?.let { return state(Kind.UNSUPPORTED, it) }
            // 5. The old switcher.
            block(SwitchGates.ID_OLD_SWITCHER)?.let { return state(Kind.OLD_SWITCHER, it) }
            // 6. Something of the last session is still in place, or the stage could not be read.
            stageGate?.takeIf { it.level == Level.BLOCK }?.let {
                return state(if (it.reason == SwitchGates.R_STAGE_NOT_READ) Kind.CHECK_FAILED else Kind.RESTART, it)
            }
            val imageGate = block(SwitchGates.ID_IMAGE)
            // 7. Nothing set up: choose a system, or set up the one whose file was chosen.
            if (imageGate?.reason == SwitchGates.R_IMAGE_NOTHING) {
                val picked = i.picked
                return if (picked != null) {
                    state(Kind.NOTHING_SET_UP, primary = FixAction.SET_UP, label = "Set up ${picked.name}", plain = null).copy(finding = imageGate, image = picked)
                } else {
                    state(Kind.NOTHING_SET_UP, primary = FixAction.CHOOSE_SYSTEM, label = Plain.defaultLabel(FixAction.CHOOSE_SYSTEM), plain = null)
                        .copy(finding = imageGate)
                }
            }
            // 8. Update, repair or set up again.
            if (imageGate != null && imageGate.reason in UPDATE_REASONS) return state(Kind.UPDATE, imageGate)
            imageGate?.let { return state(Kind.CHECK_FAILED, it) }
            // 9. Screen lock, battery, space, or any other check that stops the switch.
            r.report.sorted.firstOrNull { it.level == Level.BLOCK }?.let { return state(Kind.FIX, it) }
            // 10. Back from a session, once.
            if (i.last?.welcomeDue == true) {
                return state(Kind.WELCOME_BACK, primary = FixAction.SWITCH, label = switchLabel(image))
            }
            // 11. Ready.
            return state(Kind.READY, primary = FixAction.SWITCH, label = switchLabel(image))
        }

        private fun switchLabel(image: ImageRef?) = "Switch to ${Images.systemName(image)}"

        /**
         * The kept Home, with nothing to tap that acts: the button is off, and
         * there is no finding behind it (Details needs the new check). Back
         * from a session or not is read again from the last session itself.
         */
        private fun fromCache(c: HomeSnapshot, i: HomeInput): HomeState {
            val kind = when (c.kind) {
                Kind.READY, Kind.WELCOME_BACK -> if (i.last?.welcomeDue == true) Kind.WELCOME_BACK else Kind.READY
                else -> c.kind
            }
            return HomeState(
                kind, c.image, c.problem, null,
                primary = c.primary,
                primaryLabel = c.primaryLabel,
                primaryEnabled = false,
                last = i.last,
                checking = i.checking,
                cached = c,
            )
        }

        private fun plainOf(f: Finding, i: HomeInput): PlainMessage {
            val r = i.report ?: return Plain.of(
                f, null, null,
                PlainFacts(rootApp = i.facts?.rootKind?.takeIf { it != RootKind.NONE && it != RootKind.OTHER }?.label),
            )
            val reusable = r.image?.let { img -> i.status?.let { SetupPlan.reusesInstalled(it, img, r.profile, i.appVersionCode) } } ?: true
            return Plain.of(f, r, i.facts, reusable)
        }
    }
}
