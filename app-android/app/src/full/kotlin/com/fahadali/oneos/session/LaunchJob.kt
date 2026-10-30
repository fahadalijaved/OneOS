package com.fahadali.oneos.session

import android.content.Context
import android.net.Uri
import android.os.SystemClock
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.PlainMessage
import com.fahadali.oneos.core.model.ScreenLockRule
import com.fahadali.oneos.core.model.SwitchGates
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.core.root.RootScript
import java.security.MessageDigest
import java.security.SecureRandom

/** The SHA-256 of a picked file, read through the picker's grant (no root, no storage permission). */
internal object ImageHash {
    /** [cancelled] is polled between reads; [progress] gets the bytes read so far (every 32 MB). Returns (sha256, bytes). */
    fun of(app: Context, uri: Uri, cancelled: () -> Boolean, progress: (Long) -> Unit): Pair<String, Long> {
        val md = MessageDigest.getInstance("SHA-256")
        var n = 0L
        val input = app.contentResolver.openInputStream(uri) ?: throw java.io.IOException("cannot open the picked file")
        input.use {
            val buf = ByteArray(1 shl 20)
            var last = 0L
            while (true) {
                if (cancelled()) throw InterruptedException("stopped")
                val k = it.read(buf)
                if (k < 0) break
                md.update(buf, 0, k)
                n += k
                if (n - last > 32L * 1024 * 1024) {
                    last = n
                    progress(n)
                }
            }
        }
        progress(n)
        return Hashes.hex(md.digest()) to n
    }
}

/** Check file: the SHA-256 and size of the picked .gz (no root; the app reads it through the picker's grant). */
object ImageCheckJob : BackgroundJob<ImageCheckJob.State>(State(), "oneos-image") {
    data class State(
        val busy: Boolean = false,
        val uri: Uri? = null,
        val read: Long = 0,
        val total: Long? = null,
        val message: String? = null,
    )

    @Volatile private var cancelled = false

    fun start(ctx: Context, uri: Uri, total: Long?) {
        if (state.busy) return
        val app = ctx.applicationContext
        cancelled = false
        update(State(busy = true, uri = uri, total = total))
        executor.execute {
            var n = 0L
            val r = runCatching { ImageHash.of(app, uri, { cancelled }) { read -> n = read; update(state.copy(read = read)) } }
            r.fold(
                onSuccess = { (sha, bytes) ->
                    SessionPrefs.setChecked(app, uri, sha, bytes)
                    update(State(uri = uri, read = bytes, total = total, message = "Checked ${Units.bytes(bytes)}."))
                },
                onFailure = { e -> update(State(uri = uri, read = n, total = total, message = if (cancelled) "Stopped." else "Could not read the file: ${e.message}")) },
            )
        }
    }

    fun cancel() {
        cancelled = true
    }
}

/**
 * Switch and Dry run: the screen lock read again right before root is asked
 * (gate G16, no override), its own check when the last one is not fresh (or
 * else the stage read again), every Switch gate and every tick (the ones the
 * user ticked now and the ones remembered for this phone and system, owner
 * 2026-10-24); then the launch record is saved and root's `launch`
 * re-checks everything itself, writes this launch's Google services choice
 * into session.env (`ONEOS_GUEST_HIDE_GMS`, only for an image whose Google
 * services may be hidden, [com.fahadali.oneos.core.model.ImageRef.gmsHideable])
 * and Cool down when hot (`ONEOS_HEAT_CAP`, Advanced, [SessionPrefs.heatCap]),
 * leaves the app's cgroup and starts the session detached in init's mount
 * namespace. The app is expected to be killed a few seconds later, when One
 * UI's framework stops. A refusal keeps its finding (or root's reason) so
 * Home shows it in plain words ([State.plain]).
 */
object LaunchJob : BackgroundJob<LaunchJob.State>(State(), "oneos-launch") {
    enum class Phase { IDLE, RUNNING, LAUNCHED, FAILED }

    data class State(
        val phase: Phase = Phase.IDLE,
        val dryRun: Boolean = false,
        val detail: String? = null,
        val message: String? = null,
        /** The system being started, once the gates named it. */
        val image: ImageRef? = null,
        /** Why it did not start, in plain words (a gate's, root's refusal, or a tick missing). */
        val plain: PlainMessage? = null,
        /** The gate that refused, for Details. */
        val finding: Finding? = null,
    ) {
        val busy: Boolean get() = phase == Phase.RUNNING
    }

    private class Refused(message: String, val plain: PlainMessage?, val finding: Finding? = null, val image: ImageRef? = null) : Exception(message)

    /**
     * [hideGms]: hide Google services for this launch only (off by default). [edmStub]: answer Knox's
     * edmnativehelper so a camera open is not 5 s late (Advanced, off by default). [secIms]: this phone's Samsung IMS app in the
     * guest for VoLTE (Advanced; off by default). [ticked]: the ticks given now; the remembered ones count too.
     */
    fun start(ctx: Context, dryRun: Boolean, ticked: Set<String>, hideGms: Boolean, secIms: Boolean = false, edmStub: Boolean = false) {
        if (state.busy || StageCheck.state.busy || PrepareJob.state.busy || LogJob.state.busy) return
        val app = ctx.applicationContext
        update(State(Phase.RUNNING, dryRun, "Checking the screen lock…"))
        executor.execute {
            val r = runCatching { run(app, dryRun, ticked, hideGms, secIms, edmStub) }
            r.exceptionOrNull()?.let { e ->
                val refused = e as? Refused
                update(
                    state.copy(
                        phase = Phase.FAILED, detail = null, message = e.message ?: e.javaClass.simpleName,
                        plain = refused?.plain, finding = refused?.finding, image = refused?.image ?: state.image,
                    ),
                )
            }
        }
    }

    /** Back to idle after Home showed a refusal (Dismiss). */
    fun clear() {
        if (!state.busy) update(State())
    }

    private fun lockRefusal(lock: Boolean?, allowed: Boolean): Refused {
        val f = ScreenLockRule.switchGate(lock, allowed)
        return Refused(
            if (lock == true) "A screen lock is set. Set Screen lock type to None or Swipe in Settings, then come back. Advanced has a switch to do it anyway." else "Could not read whether a screen lock is set.",
            Plain.of(f, null, null), f,
        )
    }

    private fun run(app: Context, dryRun: Boolean, ticked: Set<String>, hideGms: Boolean, secIms: Boolean, edmStub: Boolean) {
        val lock = FactProbe.screenLockSet(app)
        // 0.4.32: a lock set may be the owner's choice (Advanced). Not being able to
        // read the lock state never is, so null still stops here.
        val allowLock = SessionPrefs.allowScreenLock(app)
        if (lock == null || (lock && !allowLock)) throw lockRefusal(lock, allowLock)
        // The last check when it is fresh and complete (installd read); else this job's own, published for Home.
        val last = StageCheck.state.result?.takeIf { it.ageMs <= StageCheck.FRESH_MS && it.installd != null }
        val fresh = if (last == null) {
            update(state.copy(detail = "Checking your phone…"))
            try {
                StageCheck.runBlocking(app, StageCheck.Mode.FULL) { update(state.copy(detail = it)) }
            } catch (e: StageCheck.RootRefused) {
                val f = SwitchGates.rootFinding(e.su)
                throw Refused(e.message ?: "Root refused", Plain.of(f, null, null), f)
            }
        } else {
            update(state.copy(detail = "Reading the stage again…"))
            val status = StageCheck.readStatus(app)
            val facts = StageCheck.facts(app, last.su, status)
            last.copy(facts = facts, status = status, oldSwitcher = RootProbe(app).oldSwitcherInstalled(), at = SystemClock.elapsedRealtime())
        }
        StageCheck.publish(fresh)
        val facts = fresh.facts
        val report = StageCheck.gates(app, fresh, GatePhase.SWITCH, screenLock = FactProbe.screenLockSet(app), facts = facts)
        update(state.copy(image = report.image))
        report.gates.firstOrNull { it.level == Level.BLOCK }?.let {
            throw Refused("${it.finding.title}. ${it.finding.detail}", Plain.of(it.finding, report, facts), it.finding, report.image)
        }
        val profile = report.profile ?: throw IllegalStateException("No profile.")
        val image = report.image ?: throw IllegalStateException("No image.")
        val remembered = SessionPrefs.acks(app, profile.id, image.id)
        val all = ticked + remembered
        report.toTick.firstOrNull { it.tickKey !in all }?.let {
            throw Refused("Tick every warning first.", Plain.of(it.finding, report, facts), it.finding, image)
        }
        if (!report.allows(all)) throw IllegalStateException("Tick every warning first.")
        // Asked once per phone and system: what was ticked now is remembered (the key holds the text).
        SessionPrefs.addAcks(app, profile.id, image.id, report.toTick.mapNotNull { it.tickKey }.filter { it in ticked })
        if (hideGms && !image.gmsHideable) {
            throw IllegalStateException(
                if (image.googleServices) "The ${image.shortName} image's Google services cannot be hidden: its sessions present them."
                else "The ${image.shortName} image has no Google services to hide.",
            )
        }
        val sid = ByteArray(8).also { SecureRandom().nextBytes(it) }.let(Hashes::hex)
        SessionPrefs.saveLaunch(
            app,
            SessionPrefs.Launch(sid, dryRun, profile.id, image.id, System.currentTimeMillis(), SystemClock.elapsedRealtime(), logsCollected = false),
        )
        update(state.copy(detail = "Root is checking everything again and starting the switch…"))
        val reply = RootVerbs.run(
            app, RootScript.Verb.LAUNCH,
            listOf(
                if (dryRun) "dry" else "session", BuildConfig.VERSION_CODE.toString(), sid, if (hideGms) "1" else "0",
                if (SessionPrefs.heatCap(app)) "1" else "0", if (secIms) "1" else "0", if (edmStub) "1" else "0",
            ),
            silenceMs = 5 * 60_000L,
        )
        if (!reply.ok) {
            // Nothing started: no last session to show.
            SessionPrefs.forgetLaunch(app)
            val problem = reply.problem ?: "no reason given"
            throw Refused("Root refused to switch: $problem", Plain.switchRefused(problem, image, profile), null, image)
        }
        val system = Images.systemName(image)
        update(
            State(
                Phase.LAUNCHED, dryRun, image = image,
                message = if (dryRun) {
                    "Test run started. One UI stops in a few seconds, $system is set up and checked, then the phone restarts into One UI."
                } else {
                    "Switching. The screen shows the OneOS logo, then $system starts. Hold Volume Up+Down for 3 seconds to return to One UI."
                },
            ),
        )
    }
}
