package com.fahadali.oneos.session

import android.content.Context
import android.os.SystemClock
import com.fahadali.oneos.core.root.HomeSnapshot

/**
 * What Home does by itself (the UX redesign, step 2), one job at a time and
 * never in a loop:
 * - the read-only check (`su -c id`, the stage and installd lists, the
 *   facts) when Home opens and the last one is older than [CHECK_AGE_MS]
 *   (Switch's Check and Old stages already ran root without a dialog; the
 *   jobs and root check everything again before they write);
 * - after a return (the phone restarted since the launch and its logs are
 *   not collected), the logs: read-only, personal data removed as they
 *   arrive, kept on the phone until the user shares them (owner, 2026-10-24).
 *   Once per session per app start, so a refusal does not repeat.
 * A check that failed (root denied) is tried again only after [RETRY_MS], or
 * when the user taps Try again ([tick] with force).
 *
 * It also keeps the Home of the last finished check ([keepHome]) so that a
 * cold start shows it, read-only, while that start's first check runs
 * ([coldStartHome]; the rule is HomeState's).
 */
object Readiness {
    const val CHECK_AGE_MS = 2 * 60_000L
    const val RETRY_MS = 2 * 60_000L

    @Volatile private var logsTriedFor: String? = null

    /** The kept Home as last read or written (so an unchanged Home is not written again). */
    @Volatile private var keptHome: HomeSnapshot? = null

    /**
     * The Home kept by an earlier start, for Home to show until this start's
     * first check ends; null after that (a check finished, failed or was
     * published by a job) or when none is kept.
     */
    fun coldStartHome(ctx: Context): HomeSnapshot? {
        val check = StageCheck.state
        if (check.result != null || check.endedAt != 0L) return null
        return keptHome ?: SessionPrefs.homeSnapshot(ctx).also { keptHome = it }
    }

    /** Home decided [s] from a finished check: keep it for the next cold start (written only when it changed). */
    fun keepHome(ctx: Context, s: HomeSnapshot) {
        if (s.sameAs(keptHome)) return
        keptHome = s
        SessionPrefs.setHomeSnapshot(ctx, s)
    }

    /** Set when a fix sent the user out of the app (root manager, lock settings, app info): check again on return. */
    @Volatile private var recheckOnResume = false

    fun recheckOnResume() {
        recheckOnResume = true
    }

    /**
     * Home's onResume. A failed check (root not allowed yet: KernelSU and APatch
     * hide su until the user allows OneOS) or a fix done outside the app is
     * checked again at once, not after [RETRY_MS] or [CHECK_AGE_MS].
     */
    fun onResume(ctx: Context) {
        val again = recheckOnResume || StageCheck.state.phase == StageCheck.Phase.FAILED
        recheckOnResume = false
        tick(ctx, force = again)
    }

    fun anyBusy(): Boolean =
        StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy || OldStagesJob.state.busy

    /** Home calls it on resume and whenever a job's state changes while it is shown. [force]: Try again. */
    fun tick(ctx: Context, force: Boolean = false) {
        if (anyBusy()) return
        val app = ctx.applicationContext
        // A switch that started is followed by One UI stopping: nothing more to do in this process.
        if (LaunchJob.state.phase == LaunchJob.Phase.LAUNCHED) return
        val check = StageCheck.state
        val r = check.result
        val now = SystemClock.elapsedRealtime()
        val stale = r == null || r.installd == null || r.ageMs > CHECK_AGE_MS
        val waited = check.phase != StageCheck.Phase.FAILED || now - check.endedAt > RETRY_MS
        if (force || (stale && waited)) {
            StageCheck.start(app, StageCheck.Mode.FULL)
            return
        }
        val launch = SessionPrefs.lastLaunch(app) ?: return
        if (!launch.logsCollected && launch.endedSince() && logsTriedFor != launch.sessionId && check.phase == StageCheck.Phase.DONE) {
            logsTriedFor = launch.sessionId
            LogJob.start(app, auto = true)
        }
    }
}
