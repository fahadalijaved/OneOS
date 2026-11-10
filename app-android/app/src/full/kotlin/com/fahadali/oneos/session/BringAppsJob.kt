package com.fahadali.oneos.session

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.os.SystemClock
import com.fahadali.oneos.core.model.BringApps
import com.fahadali.oneos.core.model.StageMarker
import com.fahadali.oneos.core.model.SuState
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootShell
import com.fahadali.oneos.core.root.SuProbe
import com.fahadali.oneos.probe.ProbeSession

/**
 * Bring apps (0.4.75, owner: "a way to select our 3rd party apps we want to
 * bring over with us to guest OS with its data ... so we dont have to keep
 * logging in"). Lists the user apps One UI has that may be brought (the package
 * manager, no root: the launcher apps that are not One UI's own, [BringApps]),
 * keeps the owner's ticks per system, and brings the ticked ones with the root
 * verb `bring-collect`, which copies each one's APKs and its One UI /data into
 * the stage so the guest starts it signed in. `bring-clear` removes the copies.
 *
 * Build 104: a tick is used up when its app is brought, and a bring adds to
 * what the stage holds (it replaces only the copies of the apps it brings).
 * The ticked apps are brought when the system is booted ([beforeLaunch], "the
 * loading / shifting to OneOS guest should say bringing over your apps too
 * before shutting down"), or right away with Bring now. The read-only verb
 * `bring-status` tells what became of each copy in the guest and whether One
 * UI's app or data is newer than it ("apps whose data or app itself has been
 * updated should be reminded to toggle again ... so newer data is picked").
 *
 * Build 109 (owner: "if 2 apps are already present and selected, when i
 * select a 3rd one why it starts to add the previous 2 again too ... it should
 * ask me if i want to recheck data of old apps"): a ticked app the system has
 * installed already ([BringApps.split]) is brought again only from Bring now,
 * where the screen asks first ([collect] with the apps to leave out); a boot
 * never copies it again, and keeps its tick.
 *
 * One way, host -> guest: One UI's data is only read. The guest installs and
 * restores the copies once its own UI is up. Bringing needs a prepared stage
 * whose root script is this build's (the launcher refuses otherwise: [State.stale]).
 */
object BringAppsJob : BackgroundJob<BringAppsJob.State>(State(), "oneos-bring-apps") {
    enum class Phase { IDLE, LOADING, COLLECTING, CLEARING, DONE, FAILED }

    data class Candidate(val pkg: String, val label: String, val version: String)

    data class State(
        val phase: Phase = Phase.IDLE,
        /** The user apps that may be brought, by label; null before the first load. */
        val candidates: List<Candidate>? = null,
        /** The packages ticked for [imageId] and not brought yet (kept in prefs). */
        val selected: Set<String> = emptySet(),
        /** Every app the stage holds a copy or a mark of (root's answer when [copies] is read, else what prefs remember). */
        val brought: Set<String> = emptySet(),
        /** KiB the last Bring copied. */
        val broughtKib: Long = 0,
        val message: String? = null,
        val failed: Boolean = false,
        /** The stage [brought] belongs to ([stageKey]); null while none is set up or known. */
        val stageKey: String? = null,
        /** The system the ticks belong to: the page's, else the one set up now. */
        val imageId: String? = null,
        /** What became of each copy and what is newer on One UI (`bring-status`); null while not read. */
        val copies: List<BringApps.Copy>? = null,
        /** The last lines of the guest's own account of installing them. */
        val log: List<String> = emptyList(),
        /** The stage's root script is another build's: the system has to be updated before anything can be brought. */
        val stale: Boolean = false,
        /** How many apps the running Bring copies, and the one it is at. */
        val working: Int = 0,
        val current: String? = null,
        /** Asked for in the last Bring but not copied, and what root said about them. */
        val skipped: Set<String> = emptySet(),
        val notes: List<String> = emptyList(),
    ) {
        val busy: Boolean get() = phase == Phase.LOADING || phase == Phase.COLLECTING || phase == Phase.CLEARING
    }

    private const val PREFS = "oneos_bring"

    /** Up to build 103: one set of ticks for every system, never used up. Dropped, so an old tick brings nothing again. */
    private const val KEY_SELECTED_OLD = "selected"
    private const val KEY_TICKS = "ticks"
    private const val KEY_BROUGHT = "brought"

    /** The launcher's refusal when the stage's root script is not this build's (RootScript.TEMPLATE). */
    private const val STALE = "prepare again"

    private val gate = Any()

    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    /** Every change of the state goes through here: the screen, this job's thread and a boot all write it. */
    private inline fun change(f: (State) -> State?): Boolean = synchronized(gate) {
        val next = f(state) ?: return false
        update(next)
        true
    }

    private fun claim(phase: Phase, working: Int = 0): Boolean =
        change { if (it.busy) null else it.copy(phase = phase, message = null, failed = false, working = working, current = null) }

    /**
     * Names one stage: its system and the moment it was set up. The brought set
     * is kept per stage, so apps brought into one system never show on another
     * system's page, or on a fresh setup of the same one (11-10).
     */
    fun stageKey(marker: StageMarker?): String? = marker?.let { "${it.imageId}:${it.createdEpoch}" }

    private fun broughtKey(stage: String) = "$KEY_BROUGHT:$stage"

    private fun broughtIn(ctx: Context, stage: String?): Set<String> =
        stage?.let { prefs(ctx).getStringSet(broughtKey(it), emptySet())!!.toSet() } ?: emptySet()

    private fun ticksKey(image: String?) = "$KEY_TICKS:${image ?: "-"}"

    private fun ticksOf(ctx: Context, image: String?): Set<String> =
        prefs(ctx).getStringSet(ticksKey(image), emptySet())!!.filter(BringApps.PACKAGE::matches).toSet()

    private fun saveTicks(ctx: Context, image: String?, ticks: Set<String>) {
        prefs(ctx).edit().putStringSet(ticksKey(image), ticks).remove(KEY_SELECTED_OLD).apply()
    }

    /** The ticks the list can show: the apps still installed (all of them while the list is not read). */
    private fun shown(ticks: Set<String>, candidates: List<Candidate>?): Set<String> =
        if (candidates == null) ticks else ticks.intersect(candidates.map { it.pkg }.toSet())

    /**
     * Which system's page the screen is ([imageId]; null from anywhere else:
     * the one set up now) and its stage ([marker]; null: none set up, or not
     * this page's system). Another one shows its own ticks and brought apps.
     * True when that made it ask root what the stage holds ([refresh]).
     */
    fun page(ctx: Context, imageId: String?, marker: StageMarker?): Boolean {
        val app = ctx.applicationContext
        val key = stageKey(marker)
        val image = imageId ?: marker?.imageId
        val changed = change { st ->
            if ((key == st.stageKey && image == st.imageId) || st.phase == Phase.COLLECTING || st.phase == Phase.CLEARING) return@change null
            st.copy(
                phase = if (st.phase == Phase.LOADING) Phase.LOADING else Phase.IDLE,
                stageKey = key, imageId = image, selected = shown(ticksOf(app, image), st.candidates),
                brought = broughtIn(app, key), broughtKib = 0, message = null, failed = false,
                copies = null, log = emptyList(), stale = false, skipped = emptySet(), notes = emptyList(),
            )
        }
        if (changed && key != null) refresh(app)
        return changed && key != null
    }

    /**
     * An update that kept the stage kept its brought apps too, but the marker's
     * date is new: carry the list over to it (PrepareJob, keep mode only).
     */
    fun carry(ctx: Context, from: StageMarker?, to: StageMarker?) {
        if (from == null || to == null || from.imageId != to.imageId) return
        val a = broughtKey(stageKey(from)!!)
        val b = broughtKey(stageKey(to)!!)
        val p = prefs(ctx)
        val set = p.getStringSet(a, null)?.toSet() ?: return
        if (a != b) p.edit().putStringSet(b, set).remove(a).apply()
    }

    private fun othersBusy() =
        StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || OldStagesJob.state.busy

    /** Reads the installable candidates (no root) and the kept ticks. */
    fun load(ctx: Context) {
        val app = ctx.applicationContext
        if (!claim(Phase.LOADING)) return
        executor.execute {
            val r = runCatching { candidates(app) }
            change { st ->
                r.fold(
                    // Ticks for apps no longer installed are not shown (and a bring skips them).
                    { list -> st.copy(phase = Phase.IDLE, candidates = list, selected = shown(ticksOf(app, st.imageId), list)) },
                    { st.copy(phase = Phase.FAILED, message = it.message ?: it.javaClass.simpleName, failed = true) },
                )
            }
        }
    }

    /**
     * Reads what the stage holds, what became of it in the guest and what is
     * newer on One UI (root `bring-status`; read only, nothing is asked on screen).
     */
    fun refresh(ctx: Context) {
        val app = ctx.applicationContext
        val key = state.stageKey ?: return
        executor.execute {
            // Not while the stage is being rewritten or started; a bring reads it itself when it ends.
            if (state.stageKey != key || PrepareJob.state.busy || LaunchJob.state.busy || OldStagesJob.state.busy) return@execute
            val read = readStatus(app)
            change { st -> if (st.stageKey != key || st.phase == Phase.COLLECTING || st.phase == Phase.CLEARING) null else st.with(app, read) }
        }
    }

    /** Ticks or unticks one app; kept in prefs for this system until it is brought. */
    fun toggle(ctx: Context, pkg: String, on: Boolean) = retick(ctx) { if (on) it + pkg else it - pkg }

    /** Select all: every app in the list, or none. */
    fun setAll(ctx: Context, on: Boolean) {
        val all = state.candidates?.map { it.pkg }?.toSet() ?: return
        retick(ctx) { if (on) all else emptySet() }
    }

    /** Ticks these as well (the brought apps that are newer on One UI). */
    fun tick(ctx: Context, pkgs: Collection<String>) = retick(ctx) { it + pkgs }

    private fun retick(ctx: Context, f: (Set<String>) -> Set<String>) {
        val app = ctx.applicationContext
        change { st ->
            if (st.phase == Phase.COLLECTING || st.phase == Phase.CLEARING) return@change null
            val sel = f(st.selected).filter(BringApps.PACKAGE::matches).toSet()
            saveTicks(app, st.imageId, sel)
            st.copy(selected = sel)
        }
    }

    /**
     * Bring now: copies the ticked apps' APKs and data into the stage (root
     * `bring-collect`). [only]: the owner's answer was to bring just these of
     * the ticked ones; the other ticks (apps the system has already) are
     * dropped with it, so nothing asks about them again.
     */
    fun collect(ctx: Context, only: Collection<String>? = null) {
        if (othersBusy() || state.busy) return
        val app = ctx.applicationContext
        if (only != null) retick(app) { it.intersect(only.toSet()) }
        val before = state
        val chosen = before.selected.toList().sorted()
        if (chosen.isEmpty()) {
            change { if (it.busy) null else it.copy(phase = Phase.FAILED, message = "Tick at least one app first.", failed = true) }
            return
        }
        if (!claim(Phase.COLLECTING, chosen.size)) return
        executor.execute {
            val out = bring(app, before.stageKey, before.imageId, chosen) { pkg -> change { it.copy(current = pkg) } }
            val read = readStatus(app)
            change { ended(app, it, chosen, out).with(app, read) }
        }
    }

    /**
     * A boot (LaunchJob's thread, before One UI is asked to stop; a real boot,
     * not a test run): the apps ticked for this system that it does not have
     * yet, and the copies it has not installed yet that are newer on One UI
     * ([BringApps.atBoot]), are brought now, so the system starts with the
     * newest. A ticked app it has installed already is not copied again here
     * (build 109): that is Bring now's, which asks first. [onDetail] gets
     * the boot screen's status while they are copied (how many, and the one it
     * is at). [onApps] gets the screen's own line about the brought apps, which
     * stays until One UI closes: how many come along at this boot and how many
     * [system] has already (build 108: up to 107 a boot with nothing left to
     * copy said nothing, and the owner, whose two apps were brought on the Apps
     * screen, never saw a word of it). No app ticked and none ever brought:
     * neither is called. A Bring started on the Apps screen is waited for.
     * Never stops the boot: what went wrong is kept for the Apps screen.
     */
    fun beforeLaunch(
        app: Context, marker: StageMarker?, system: String, cancelled: () -> Boolean,
        onApps: (String?) -> Unit, onDetail: (String) -> Unit,
    ) {
        val key = stageKey(marker) ?: return
        val image = marker?.imageId ?: return
        runCatching {
            // Nothing ticked and nothing ever brought into this stage: root is not asked at all.
            if (ticksOf(app, image).none { installed(app, it) } && broughtIn(app, key).isEmpty()) return
            var said = false
            val until = SystemClock.elapsedRealtime() + WAIT_MS
            while (!claim(Phase.COLLECTING)) {
                if (!said) {
                    said = true
                    onDetail(DETAIL)
                }
                if (SystemClock.elapsedRealtime() > until) return
                Thread.sleep(300)
            }
            var chosen = emptyList<String>()
            var out: Outcome? = null
            try {
                // What became of the copies the stage holds (none brought yet: root is not asked).
                val known = broughtIn(app, key)
                val copies = if (known.isEmpty()) emptyList() else readStatus(app).copies
                // Read again: a Bring that was waited for used its ticks up.
                val ticks = ticksOf(app, image)
                val have = ticks.filter { installed(app, it) }.toSet()
                if (have != ticks) saveTicks(app, image, have)
                // Not the ticked apps the system has already: those keep their tick for Bring now, which asks.
                chosen = BringApps.atBoot(have, copies, known)
                if (cancelled()) return
                // Not copied now: waiting in the stage for the system to install, or installed there before.
                val rest = BringApps.bootCount(copies, chosen)
                if (chosen.isEmpty()) {
                    onApps(BringApps.bootLine(system, rest.coming, rest.there))
                    return
                }
                onDetail(BringApps.bootDetail(chosen.size))
                change { it.copy(working = chosen.size) }
                var at = 0
                val done = bring(app, key, image, chosen) { pkg ->
                    at++
                    onDetail(BringApps.bootDetail(chosen.size, at, label(app, pkg)))
                }
                out = done
                onApps(BringApps.bootLine(system, done.brought.size + rest.coming, rest.there))
            } finally {
                val o = out
                change { st ->
                    when {
                        o == null -> st.copy(phase = Phase.IDLE, working = 0, current = null)
                        // The Apps screen was last on another stage: only the job is given back.
                        st.stageKey != key -> st.copy(phase = Phase.IDLE, working = 0, current = null, selected = shown(ticksOf(app, st.imageId), st.candidates))
                        else -> ended(app, st, chosen, o).copy(copies = null)
                    }
                }
            }
        }
    }

    /** The state after a bring of [chosen] ended ([out]); the ticks and the brought set are the prefs' ([bring] wrote them). */
    private fun ended(app: Context, st: State, chosen: List<String>, out: Outcome): State {
        val base = st.copy(
            working = 0, current = null, selected = shown(ticksOf(app, st.imageId), st.candidates),
            brought = st.brought + out.brought, broughtKib = out.kib, skipped = chosen.toSet() - out.brought, notes = out.notes,
        )
        val n = out.brought.size
        val problem = out.problem
        return when {
            problem != null && STALE in problem ->
                base.copy(phase = Phase.FAILED, failed = true, stale = true, message = "Nothing was brought.")
            problem != null -> base.copy(
                phase = Phase.FAILED, failed = true,
                message = if (n > 0) "Brought $n app${s(n)}, then it stopped: $problem" else "Could not bring the apps: $problem",
            )
            else -> base.copy(
                phase = Phase.DONE, failed = false,
                message = "Brought $n app${s(n)} (${gb(out.kib)})" +
                    (if (base.skipped.isNotEmpty()) "; ${base.skipped.size} skipped" else "") +
                    (if (out.partial > 0) "; ${out.partial} may ask to sign in" else "") + ".",
            )
        }
    }

    /** What one `bring-collect` did. [problem]: why it ended early (what it copied before that still counts). */
    private class Outcome(val brought: Set<String>, val kib: Long, val partial: Int, val notes: List<String>, val problem: String?)

    /**
     * One `bring-collect` of [chosen] into the stage [key]. Blocks. The prefs
     * follow what root copied: the stage's brought set grows by it, and those
     * apps' ticks are used up (what stays ticked is what still has to come).
     */
    private fun bring(app: Context, key: String?, image: String?, chosen: List<String>, onApp: (String) -> Unit): Outcome {
        val r = runCatching {
            su(app)
            val bytes = BringApps.manifest(chosen).toByteArray()
            RootVerbs.run(
                app, RootScript.Verb.BRING_COLLECT, listOf(bytes.size.toString()),
                feed = RootShell.Feed { it.write(bytes) },
                silenceMs = 20 * 60_000L, totalMs = 90 * 60_000L,
                onStep = { step -> if (BringApps.PACKAGE.matches(step)) onApp(step) },
            )
        }
        val reply = r.getOrNull()
        // "brought <pkg> <kib>"
        val lines = reply?.reply?.results.orEmpty().map { it.split(' ') }.filter { it.size == 3 && it[0] == "brought" && BringApps.PACKAGE.matches(it[1]) }
        val brought = lines.map { it[1] }.toSet()
        if (brought.isNotEmpty()) {
            val e = prefs(app).edit()
            if (key != null) e.putStringSet(broughtKey(key), broughtIn(app, key) + brought)
            e.putStringSet(ticksKey(image), ticksOf(app, image) - brought).remove(KEY_SELECTED_OLD)
            e.apply()
        }
        val infos = reply?.reply?.infos.orEmpty()
        return Outcome(
            brought, lines.sumOf { it[2].toLongOrNull() ?: 0L },
            // Copied, with some of its data unread.
            partial = infos.count { it.contains("could not be read") },
            notes = infos.toList(),
            problem = if (reply?.ok == true) null else reply?.problem ?: r.exceptionOrNull()?.message ?: "root gave no answer",
        )
    }

    /** Removes the brought-apps copies from the stage (root `bring-clear`). */
    fun clear(ctx: Context) {
        if (othersBusy()) return
        val app = ctx.applicationContext
        val stage = state.stageKey
        if (!claim(Phase.CLEARING)) return
        executor.execute {
            val r = runCatching {
                su(app)
                RootVerbs.run(app, RootScript.Verb.BRING_CLEAR, emptyList(), silenceMs = 5 * 60_000L)
            }
            val reply = r.getOrNull()
            if (reply?.ok == true) {
                if (stage != null) prefs(app).edit().remove(broughtKey(stage)).apply()
                change {
                    it.copy(
                        phase = Phase.DONE, brought = emptySet(), broughtKib = 0, copies = emptyList(), log = emptyList(),
                        skipped = emptySet(), notes = emptyList(), message = "Removed the brought apps from the system set up now.", failed = false,
                    )
                }
            } else {
                val msg = reply?.problem ?: r.exceptionOrNull()?.message
                change {
                    it.copy(
                        phase = Phase.FAILED, failed = true, stale = it.stale || (msg != null && STALE in msg),
                        message = msg?.let { m -> "Could not remove them: $m" } ?: "Could not remove them.",
                    )
                }
            }
        }
    }

    /** What `bring-status` said. [copies] is null when it could not be asked. */
    private class Read(val copies: List<BringApps.Copy>?, val log: List<String>, val stale: Boolean)

    private fun readStatus(app: Context): Read {
        val r = runCatching {
            su(app)
            RootVerbs.run(app, RootScript.Verb.BRING_STATUS, emptyList(), silenceMs = 3 * 60_000L, totalMs = 10 * 60_000L)
        }
        val reply = r.getOrNull()
        if (reply?.ok != true) return Read(null, emptyList(), stale = reply?.problem?.contains(STALE) == true)
        return Read(
            BringApps.parseStatus(reply.reply.results),
            reply.reply.infos.filter { it.startsWith("log ") }.map { it.removePrefix("log ").trim() }.filter { it.isNotEmpty() },
            stale = false,
        )
    }

    /** The state with root's answer in it; the prefs' brought set follows it, so a boot knows whether to ask at all. */
    private fun State.with(app: Context, read: Read): State {
        val copies = read.copies ?: return copy(copies = null, stale = stale || read.stale)
        val pkgs = copies.map { it.pkg }.toSet()
        stageKey?.let { prefs(app).edit().putStringSet(broughtKey(it), pkgs).apply() }
        return copy(copies = copies, log = read.log, stale = false, brought = pkgs)
    }

    private fun su(app: Context) {
        val s = SuProbe.runId()
        check(s.state == SuState.GRANTED) { ProbeSession.suText(app, s) }
    }

    private fun installed(app: Context, pkg: String): Boolean =
        runCatching { app.packageManager.getApplicationInfo(pkg, 0) }.isSuccess

    private fun label(app: Context, pkg: String): String =
        state.candidates?.firstOrNull { it.pkg == pkg }?.label
            ?: runCatching { app.packageManager.let { pm -> pm.getApplicationInfo(pkg, 0).loadLabel(pm).toString() } }.getOrNull()?.ifBlank { null }
            ?: pkg

    private fun candidates(app: Context): List<Candidate> {
        val pm = app.packageManager
        val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val seen = mutableSetOf<String>()
        val out = mutableListOf<Candidate>()
        for (ri in pm.queryIntentActivities(intent, 0)) {
            val ai = ri.activityInfo?.applicationInfo ?: continue
            val pkg = ai.packageName
            if (!seen.add(pkg)) continue
            // Runs as a system uid (a shared-uid package): not a user app, and the guest could not install it.
            if (ai.uid < android.os.Process.FIRST_APPLICATION_UID) continue
            val system = (ai.flags and (ApplicationInfo.FLAG_SYSTEM or ApplicationInfo.FLAG_UPDATED_SYSTEM_APP)) != 0
            if (!BringApps.eligible(pkg, system, launchable = true)) continue
            val label = runCatching { ai.loadLabel(pm).toString() }.getOrDefault(pkg).ifBlank { pkg }
            val version = runCatching { pm.getPackageInfo(pkg, 0).versionName ?: "" }.getOrDefault("")
            out += Candidate(pkg, label, version)
        }
        return out.sortedBy { it.label.lowercase() }
    }

    /** The boot screen's status while a Bring started on the Apps screen is waited for. */
    private const val DETAIL = "Bringing over your apps…"

    /** How long a boot waits for a Bring started on the Apps screen. */
    private const val WAIT_MS = 90 * 60_000L

    private fun s(n: Int) = if (n == 1) "" else "s"
    private fun gb(kib: Long): String =
        if (kib >= 1_048_576) String.format(java.util.Locale.ROOT, "%.1f GB", kib / 1_048_576.0)
        else String.format(java.util.Locale.ROOT, "%.0f MB", kib / 1024.0)
}
