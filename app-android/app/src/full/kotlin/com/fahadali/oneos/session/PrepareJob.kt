package com.fahadali.oneos.session

import android.content.Context
import android.net.Uri
import android.os.SystemClock
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.Finding
import com.fahadali.oneos.core.model.GatePhase
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.ImageIdentifier
import com.fahadali.oneos.core.model.ImageRef
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.InstalldTableFormat
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.Plain
import com.fahadali.oneos.core.model.PlainMessage
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SessionEnv
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootShell
import com.fahadali.oneos.core.root.SetupPlan
import java.io.BufferedInputStream
import java.io.FilterInputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.security.MessageDigest
import java.util.zip.GZIPInputStream

/**
 * Prepare, "Set up" on the new screens (build 2, AA1/AA11/AA12): checks
 * again, publishes that check (so Switch and Home show it, not an older one),
 * picks what to do with the stage when the caller did not ([SetupPlan]: keep
 * the same system's apps and data, set another one aside, reuse the system
 * already installed when root vouches for it), hashes the picked .gz itself
 * when Check file has not ("Check the download"; the identity gate still
 * refuses anything but the verified image), then the root script's verbs in
 * order: begin (stage adopted, moved aside or new), the image (the picked
 * .gz unpacked on the fly into `receive system.raw`, or `keep-raw` for the
 * image already on this phone), every session script and file of the
 * image's set on this phone, the installd table, session.env, finish (files
 * list, attic, marker), and a fresh read of the stage, published too. The
 * image is the one the gates identified (a phone may take more than one,
 * 0.3.3) and decides the set; begin and finish name both, and root refuses a
 * set that is not that image's. Root checks each file's size and SHA-256
 * itself; the app hashes every byte it sends as well. Stopping at any point
 * leaves a stage without a marker, which Switch refuses.
 */
object PrepareJob : BackgroundJob<PrepareJob.State>(State(), "oneos-prepare") {
    enum class Phase { IDLE, RUNNING, DONE, FAILED, STOPPED }

    /** The three steps the Setting up screen shows (four with an in-app download, later). */
    enum class UserStep { CHECK_DOWNLOAD, INSTALL, FINISH }

    enum class Step(val label: String, val userStep: UserStep) {
        CHECK("Check this phone and the stage", UserStep.CHECK_DOWNLOAD),
        HASH("Check the download", UserStep.CHECK_DOWNLOAD),
        DOWNLOAD("Download this system's OneOS files", UserStep.CHECK_DOWNLOAD),
        BEGIN("Stage folder", UserStep.INSTALL),
        IMAGE("System image", UserStep.INSTALL),
        FILES("OneOS files and session scripts", UserStep.FINISH),
        TABLE("installd table", UserStep.FINISH),
        ENV("Session settings", UserStep.FINISH),
        FINISH("Finish", UserStep.FINISH),
        VERIFY("Check the prepared stage", UserStep.FINISH),
    }

    /**
     * What to do with the stage and where the image comes from. Null fields
     * are decided by [SetupPlan] from the stage and the image (Home, the new
     * screens); the old Prepare screen still passes both.
     */
    data class Plan(val mode: RootScript.BeginMode? = null, val source: SessionPrefs.Source? = null) {
        companion object {
            val AUTO = Plan()
        }
    }

    data class State(
        val phase: Phase = Phase.IDLE,
        val step: Step? = null,
        val done: Set<Step> = emptySet(),
        val detail: String? = null,
        val message: String? = null,
        val infos: List<String> = emptyList(),
        /** The system being set up, once known. */
        val image: ImageRef? = null,
        /** What the job decided ([SetupPlan]), once known. */
        val plan: SetupPlan? = null,
        /** The source selected after resolving the plan; presentation only. */
        val source: SessionPrefs.Source? = null,
        /** Bytes hashed, unpacked and sent so far, of [bytesTotal] (0 = not known yet). */
        val bytesDone: Long = 0,
        val bytesTotal: Long = 0,
        /** Seconds left (moving average of the byte rate); null = still estimating (the first 30 s). */
        val etaSeconds: Int? = null,
        /** The current step's own progress (0.4.41): bytes of this step done, of [stepTotal] (0 = not measured). */
        val stepDone: Long = 0,
        val stepTotal: Long = 0,
        /** The gate that refused before anything was written, for Details. */
        val finding: Finding? = null,
        /** Why it failed or stopped, in plain words. */
        val plain: PlainMessage? = null,
    ) {
        val busy: Boolean get() = phase == Phase.RUNNING
        val userStep: UserStep? get() = step?.userStep
        val percent: Int? get() = if (bytesTotal > 0) (bytesDone * 100 / bytesTotal).toInt().coerceIn(0, 100) else null
        /** The current step's own share done, 0..1, or null when the step does not measure bytes. */
        val stepFraction: Float? get() = if (stepTotal > 0) (stepDone.toDouble() / stepTotal).toFloat().coerceIn(0f, 1f) else null
    }

    @Volatile private var cancelled = false

    fun start(ctx: Context, plan: Plan = Plan.AUTO) {
        if (state.busy || StageCheck.state.busy || LaunchJob.state.busy || LogJob.state.busy) return
        val app = ctx.applicationContext
        cancelled = false
        Rate.reset()
        update(State(Phase.RUNNING, Step.CHECK, detail = "Checking root…"))
        lastBytesUpdateMs = 0L
        PrepareService.start(app)
        executor.execute {
            try {
                run(app, plan)
            } catch (e: Stop) {
                val stopped = cancelled
                update(
                    state.copy(
                        phase = if (stopped) Phase.STOPPED else Phase.FAILED, message = e.message, finding = e.finding,
                        plain = e.plain ?: Plain.setupFailed(e.message.orEmpty(), stopped, state.image),
                    ),
                )
                republishStage(app)
            } catch (e: Throwable) {
                val msg = "${e.javaClass.simpleName}: ${e.message.orEmpty()}".take(500)
                update(state.copy(phase = Phase.FAILED, message = msg, plain = Plain.setupFailed(msg, cancelled, state.image)))
                republishStage(app)
            }
        }
    }

    /**
     * After a failed or stopped setup, Home must not keep showing the check
     * published before it (e.g. "ready" with Switch): read the stage again.
     */
    private fun republishStage(app: Context) {
        val prev = StageCheck.state.result ?: return
        runCatching { StageCheck.readStatus(app) }.onSuccess {
            StageCheck.publish(prev.copy(status = it, at = SystemClock.elapsedRealtime()))
        }
    }

    fun cancel() {
        cancelled = true
        StageCheck.cancel()
        RootVerbs.cancel()
    }

    private class Stop(message: String, val finding: Finding? = null, val plain: PlainMessage? = null) : Exception(message)

    private const val STOPPED = "Stopped. The stage is not prepared: prepare again before switching."

    private fun step(s: Step, detail: String? = null) {
        if (cancelled) throw Stop(STOPPED)
        update(state.copy(step = s, done = state.done + (state.step?.takeIf { it != s }?.let { setOf(it) } ?: emptySet()), detail = detail,
            stepDone = 0, stepTotal = 0))
    }

    private fun detail(d: String) = update(state.copy(detail = d))

    /** Bytes per second, a moving average; the ETA shows after [ESTIMATE_MS] of byte flow. */
    private object Rate {
        private const val ESTIMATE_MS = 30_000L
        private var startMs = 0L
        private var lastMs = 0L
        private var lastBytes = 0L
        private var bps = 0.0

        fun reset() {
            startMs = 0
            lastMs = 0
            lastBytes = 0
            bps = 0.0
        }

        fun eta(done: Long, total: Long): Int? {
            val now = SystemClock.elapsedRealtime()
            if (startMs == 0L) {
                startMs = now
                lastMs = now
                lastBytes = done
                return null
            }
            val dt = now - lastMs
            if (dt >= 1000) {
                val sample = (done - lastBytes) * 1000.0 / dt
                bps = if (bps == 0.0) sample else bps * 0.8 + sample * 0.2
                lastMs = now
                lastBytes = done
            }
            if (now - startMs < ESTIMATE_MS || bps <= 0.0) return null
            return ((total - done).coerceAtLeast(0) / bps).toInt()
        }
    }

    /** When the screen last got a byte count: at most [UPDATE_MS] apart (0.4.41). */
    @Volatile private var lastBytesUpdateMs = 0L
    private const val UPDATE_MS = 250L

    /**
     * [base] bytes of the steps before this one plus [n] of this one. The screen hears of it at
     * most every [UPDATE_MS], or when [force]: one update per network chunk kept a CPU core busy
     * redrawing the setup screen and slowed the 0.4.41 download to a sixth of the phone's speed.
     */
    private fun bytes(base: Long, n: Long, stepDone: Long = state.stepDone, force: Boolean = false, detail: (() -> String)? = null) {
        val done = base + n
        val eta = Rate.eta(done, state.bytesTotal)
        val now = SystemClock.elapsedRealtime()
        if (!force && now - lastBytesUpdateMs < UPDATE_MS) return
        lastBytesUpdateMs = now
        update(state.copy(bytesDone = done, etaSeconds = eta, stepDone = stepDone, detail = detail?.invoke() ?: state.detail))
    }

    private fun verb(
        app: Context,
        s: Step,
        verb: RootScript.Verb,
        args: List<String>,
        feed: RootShell.Feed? = null,
        silenceMs: Long = 120_000,
        totalMs: Long = 30 * 60_000L,
    ): RootVerbs.Reply {
        val r = RootVerbs.run(app, verb, args, feed, silenceMs, totalMs) { detail(stepText(it)) }
        if (cancelled) throw Stop(STOPPED)
        if (!r.ok) throw Stop("${s.label}: ${r.problem}")
        if (r.reply.infos.isNotEmpty() || r.reply.results.isNotEmpty()) update(state.copy(infos = state.infos + r.reply.infos + r.reply.results))
        return r
    }

    private fun stepText(s: String): String = when {
        s.startsWith("verify system.raw") -> "Making sure it installed correctly…"
        s.startsWith("verify ") -> "Root is checking ${s.removePrefix("verify ")}…"
        s.startsWith("receive ") -> "Writing ${s.removePrefix("receive ").substringBefore(' ')}…"
        s.startsWith("aside ") -> "Moving the old stage aside…"
        s.startsWith("rename ${RootScript.LEGACY_STAGE} ") -> "Renaming the stage to its OneOS name…"
        s == "attic" -> "Moving leftovers to the attic…"
        else -> s
    }

    private fun run(app: Context, plan: Plan) {
        // 1. Everything again, right before the first write; Switch and Home show this check from now on.
        step(Step.CHECK)
        val check = StageCheck.runBlocking(app, StageCheck.Mode.FULL) { detail(it) }
        StageCheck.publish(check)
        val profile = Profiles.resolve(check.facts).profile ?: throw Stop("No OneOS profile for this phone.")
        val st = check.status
        var picked = SessionPrefs.picked(app)

        // A reuse update targets the installed image, even if an older download
        // selection names a different OS. Fresh prepare gates below decide it again.
        val stagedCandidate = st.staged(profile)?.first
            ?: st.marker?.takeIf { st.ours && it.profileId == profile.id }?.let { m -> Images.byId(m.imageId)?.takeIf { profile.choice(it.id) != null } }
            ?: st.pendingUpdate?.takeIf { st.partial && it.profileId == profile.id }
                ?.let { m -> Images.byId(m.imageId)?.takeIf { profile.choice(it.id) != null } }
            // An interrupted setup has no marker, but root can identify its raw image.
            ?: profile.images().firstOrNull { st.partial && st.rawVerifiedSha256 == it.rawSha256 }
        val candidate = if (plan.source == SessionPrefs.Source.ON_PHONE) stagedCandidate else
            picked?.let { ImageIdentifier.identify(it.check, profile).image?.takeIf { i -> profile.choice(i.id) != null } } ?: stagedCandidate
        update(state.copy(image = candidate))
        val auto = candidate?.let { SetupPlan.decide(st, it, profile, BuildConfig.VERSION_CODE, hasDownload = picked != null) }
        update(state.copy(plan = auto))
        val mode = plan.mode ?: auto?.mode ?: st.beginModes(null).firstOrNull() ?: throw Stop("The stage path is not a folder. Remove it, then try again.")
        val source = plan.source ?: when (auto?.source) {
            SetupPlan.Source.ON_PHONE -> SessionPrefs.Source.ON_PHONE
            else -> SessionPrefs.Source.GZ
        }
        if (mode !in st.beginModes(null)) throw Stop("The stage changed since the last check. Check again and choose what to do with it.")
        update(state.copy(source = source))
        val onPhone = source == SessionPrefs.Source.ON_PHONE
        if (onPhone && mode != RootScript.BeginMode.KEEP) throw Stop("The image already on this phone can only be used when the stage is kept.")

        // Sizes for the progress: the hash (when needed), the image, the files.
        val hashNeeded = !onPhone && picked != null && picked.sha256 == null
        val gzBytes = candidate?.gzBytes ?: picked?.bytes ?: 0L
        val set0 = candidate?.let { i -> profile.choice(i.id)?.packageSetId?.let { PackageSets.byId(it) } }
        update(state.copy(bytesTotal = (if (hashNeeded) gzBytes else 0L) + (if (onPhone) 0L else gzBytes) + (set0?.approxBytes ?: 0L)))

        // 2. "Check the download": the picked .gz hashed here when Check file did not, so the identity gate can pass.
        var base = 0L
        if (hashNeeded) {
            val p = picked
            step(Step.HASH, "Checking the download…")
            update(state.copy(stepTotal = gzBytes))
            val (sha, n) = try {
                ImageHash.of(app, p.uri, { cancelled }) { read -> bytes(0, read, stepDone = read) }
            } catch (e: InterruptedException) {
                throw Stop(STOPPED)
            } catch (e: java.io.IOException) {
                throw Stop("Could not read the file: IOException: ${e.message}")
            }
            SessionPrefs.setChecked(app, p.uri, sha, n)
            picked = SessionPrefs.picked(app)
            base = n
        }

        val reclaim = if (mode == RootScript.BeginMode.KEEP) st.rawSize ?: 0 else 0
        val report = StageCheck.gates(app, check, GatePhase.PREPARE, picked?.check, onPhone, reclaim)
        report.gates.firstOrNull { it.level == Level.BLOCK }?.let {
            throw Stop("${it.finding.title}. ${it.finding.detail}", it.finding, Plain.of(it.finding, report, check.facts))
        }
        // The image the gates identified decides the set (never another set with it).
        val image = report.image ?: throw Stop("No image for ${profile.label}.")
        update(state.copy(image = image))
        // Guest data stays with the image that made it, and with its own system: never kept for
        // another one (root refuses too). The modes for the image itself, now that it is known.
        if (mode !in st.beginModes(image.id)) {
            val other = st.otherImageData(image.id)
            throw Stop(
                if (other != null) {
                    "The data in the stage is from ${Images.shortName(other)}, not ${image.shortName}: move the stage aside."
                } else {
                    "The data in the stage is another system's, not ${image.shortName}'s: move the stage aside."
                },
            )
        }
        val set = report.set?.takeIf { it.imageId == image.id && profile.choice(image.id)?.packageSetId == it.id }
            ?: throw Stop("No file set for the ${image.shortName} image on the ${profile.label}.")
        val derivation = check.installd ?: throw Stop("installd table not derived")
        if (!PatchChannels.selected(app, profile.id, image.id).stable) {
            detail("Checking experimental patch updates…")
            PatchChannels.refresh(app, set, profile.id)
        }
        val files = AppAssets.files(app, set, profile.id)
        val code = BuildConfig.VERSION_CODE.toString()
        val filesBytes = files.sumOf { it.bytes }
        update(state.copy(bytesTotal = base + (if (onPhone) 0L else image.gzBytes) + filesBytes))

        // 2b. (0.4.41) The set's files this app does not carry, downloaded by hash before the
        // stage is touched: a failed or stopped download leaves the phone as it was.
        val downloads = AppAssets.toDownload(app, files)
        if (downloads.isNotEmpty()) {
            step(Step.DOWNLOAD)
            val need = downloads.sumOf { it.first.bytes }
            update(state.copy(bytesTotal = state.bytesTotal + need, stepTotal = need))
            val free = SetDownloader.dir(app).usableSpace
            if (free < need + 256L * 1024 * 1024) {
                throw Stop("Not enough free space for this system's OneOS files: ${Units.bytes(need)} to download, ${Units.bytes(free)} free.")
            }
            // (0.4.42) Three at a time: Drive took 16-80 s to start some files (one at a time, the
            // screen sat still that long); the others keep coming meanwhile.
            val partial = java.util.concurrent.atomic.AtomicLongArray(downloads.size)
            val finished = java.util.concurrent.atomic.AtomicInteger(0)
            val lastByteAt = java.util.concurrent.atomic.AtomicLong(SystemClock.elapsedRealtime())
            val abort = java.util.concurrent.atomic.AtomicBoolean(false)
            // The first failure that was not caused by the abort itself (0.4.42 review: a sibling's
            // "stopped" was reported instead of Drive's quota page or a damaged file).
            val firstFailure = java.util.concurrent.atomic.AtomicReference<Throwable?>(null)
            val connections: MutableSet<java.net.HttpURLConnection> = java.util.concurrent.ConcurrentHashMap.newKeySet()
            val started = SystemClock.elapsedRealtime()
            val pool = java.util.concurrent.Executors.newFixedThreadPool(minOf(3, downloads.size)) { r -> Thread(r, "oneos-download") }
            val stepBase = base
            try {
                val futures = downloads.mapIndexed { i, (f, ids) ->
                    pool.submit {
                        try {
                            SetDownloader.fetch(app, f, ids, { cancelled || abort.get() }, connections) { n ->
                                partial.set(i, n)
                                lastByteAt.set(SystemClock.elapsedRealtime())
                            }
                        } catch (e: Throwable) {
                            if (!abort.get() && !cancelled) firstFailure.compareAndSet(null, e)
                            abort.set(true)
                            throw e
                        }
                        partial.set(i, f.bytes)
                        finished.incrementAndGet()
                    }
                }
                while (futures.any { !it.isDone }) {
                    try { Thread.sleep(250) } catch (e: InterruptedException) { abort.set(true); throw Stop(STOPPED) }
                    if (cancelled) { abort.set(true); throw Stop(STOPPED) }
                    // A failed file ends the step at once (the others stop at their next read).
                    if (abort.get()) break
                    var got = 0L
                    for (i in 0 until partial.length()) got += partial.get(i)
                    val now = SystemClock.elapsedRealtime()
                    val idle = (now - lastByteAt.get()) / 1000
                    val secs = (now - started) / 1000.0
                    val rate = if (secs >= 2 && idle < 3) " · ${Units.bytes((got / secs).toLong())}/s" else ""
                    val waiting = if (idle >= 3) " · waiting for Google Drive ${idle} s" else ""
                    bytes(stepBase, got, stepDone = got, force = true) {
                        "${finished.get()} of ${downloads.size} files · ${Units.bytes(got)} of ${Units.bytes(need)}$rate$waiting"
                    }
                }
                firstFailure.get()?.let { throw Stop("Downloading this system's OneOS files: ${it.message ?: it}") }
                if (abort.get() || cancelled) throw Stop(STOPPED)
            } finally {
                // Stopped or failed: close the live connections so blocked reads end now, and wait for
                // the threads, so a setup started again never shares a .part with one of them.
                abort.set(true)
                pool.shutdownNow()
                connections.forEach { runCatching { it.disconnect() } }
                if (!pool.awaitTermination(15, java.util.concurrent.TimeUnit.SECONDS)) {
                    android.util.Log.w("OneOS", "download threads still running after a stop")
                }
            }
            base += need
        }

        // 3. begin.
        step(Step.BEGIN, "Making the stage OneOS's…")
        verb(app, Step.BEGIN, RootScript.Verb.BEGIN, listOf(mode.word, profile.id, image.id, set.id, code))

        // 4. The image.
        if (onPhone) {
            step(Step.IMAGE, "Making sure it installed correctly…")
            verb(app, Step.IMAGE, RootScript.Verb.KEEP_RAW, listOf(image.rawBytes.toString(), image.rawSha256), silenceMs = 15 * 60_000L)
        } else {
            val uri = picked?.uri ?: throw Stop("Pick the image first.")
            step(Step.IMAGE, "Unpacking the download…")
            update(state.copy(stepTotal = image.gzBytes))
            val imageBase = base
            val feed = ImageFeed(app, uri, image) { gz ->
                // In Double: gz * rawBytes passes Long's range after about 1.2 GB of
                // a large image's .gz, and the label showed wrong sizes and "?" (2026-10-25).
                bytes(imageBase, gz, stepDone = gz) {
                    "${Units.bytes((gz.toDouble() / image.gzBytes * image.rawBytes).toLong())} of ${Units.bytes(image.rawBytes)}"
                }
            }
            verb(
                app, Step.IMAGE, RootScript.Verb.RECEIVE, listOf(RootScript.RAW_NAME, image.rawBytes.toString(), image.rawSha256), feed,
                silenceMs = 15 * 60_000L, totalMs = 3 * 60 * 60_000L,
            )
            feed.problem()?.let { throw Stop("The image: $it") }
            base += image.gzBytes
        }

        // 5. Scripts and files, each hashed while it streams. (0.4.42) Root first keeps the ones the
        // stage already holds byte for byte (keep-files: one call with the whole list instead of a
        // root call and a full copy per file; finish hashes all of them again).
        step(Step.FILES, "Checking what the stage already has…")
        update(state.copy(stepTotal = filesBytes))
        val keptNames: Set<String> = if (mode == RootScript.BeginMode.KEEP) {
            val list = files.joinToString("") { "${it.sha256}  ${it.name}\n" }.toByteArray()
            val r = verb(app, Step.FILES, RootScript.Verb.KEEP_FILES, listOf(list.size.toString()), RootShell.Feed { it.write(list) })
            r.reply.results.filter { it.startsWith("kept ") }.map { it.removePrefix("kept ") }.toSet()
        } else {
            emptySet()
        }
        val toSend = files.filter { it.name !in keptNames }
        var sentFiles = files.filter { it.name in keptNames }.sumOf { it.bytes }
        base += sentFiles
        bytes(base, 0, stepDone = sentFiles, force = true) {
            if (toSend.isEmpty()) "All ${files.size} files already in place" else "${keptNames.size} of ${files.size} already in place"
        }
        for ((i, f) in toSend.withIndex()) {
            val fileBase = base
            val stepBase = sentFiles
            // "File 3 of 9 · 120 MB of 600 MB": files sent of those that changed, bytes of the whole set.
            fun line(n: Long) = "File ${i + 1} of ${toSend.size} · ${Units.bytes(stepBase + n)} of ${Units.bytes(filesBytes)}"
            bytes(fileBase, 0, stepDone = stepBase, force = true) { line(0) }
            val md = MessageDigest.getInstance("SHA-256")
            var sent = 0L
            verb(app, Step.FILES, RootScript.Verb.RECEIVE, listOf(f.name, f.bytes.toString(), f.sha256), RootShell.Feed { out ->
                AppAssets.open(app, f).use { input ->
                    sent = copy(input, out, md) { n -> bytes(fileBase, n, stepDone = stepBase + n) { line(n) } }
                }
            })
            if (sent != f.bytes || Hashes.hex(md.digest()) != f.sha256) throw Stop("${f.name} in the app is damaged")
            base += f.bytes
            sentFiles += f.bytes
            bytes(base, 0, stepDone = sentFiles, force = true) { line(f.bytes) }
        }

        // 6. installd table, 7. session.env.
        step(Step.TABLE)
        val table = InstalldTableFormat.write(
            check.facts.fingerprint, derivation.sourceJar ?: throw Stop("installd: no source jar"),
            derivation.sourceSha256 ?: throw Stop("installd: no source jar hash"), derivation.methods,
        ).toByteArray()
        verb(app, Step.TABLE, RootScript.Verb.TABLE, listOf(table.size.toString()), RootShell.Feed { it.write(table) })
        step(Step.ENV)
        val env = SessionEnv.generate(profile).toByteArray()
        verb(app, Step.ENV, RootScript.Verb.ENV, listOf(env.size.toString()), RootShell.Feed { it.write(env) })

        // 8. finish: files.sha256, attic, marker.
        step(Step.FINISH)
        verb(app, Step.FINISH, RootScript.Verb.FINISH, listOf(profile.id, image.id, set.id, code), silenceMs = 5 * 60_000L)

        // 9. What Switch will see, published so Switch and Home do not show the check from before.
        step(Step.VERIFY, "Reading the stage again…")
        val after = StageCheck.readStatus(app)
        StageCheck.publish(check.copy(status = after, oldSwitcher = RootProbe(app).oldSwitcherInstalled(), at = SystemClock.elapsedRealtime()))
        val problems = after.verify(profile, image, set)
        if (problems.isNotEmpty()) throw Stop("The prepared stage does not check out: ${problems.first()}")
        // Downloads no list of this app names any more (a set before an update) go.
        runCatching { SetDownloader.prune(app, AppAssets.allSetHashes(app)) }
        update(
            state.copy(
                phase = Phase.DONE, step = null, done = Step.entries.toSet(), detail = null, bytesDone = state.bytesTotal, etaSeconds = 0,
                message = "Prepared ${image.shortName} for the ${profile.label}. Next: switch to ${Images.systemName(image)}.",
            ),
        )
    }

    private fun copy(input: InputStream, out: OutputStream, md: MessageDigest, progress: (Long) -> Unit = {}): Long {
        val buf = ByteArray(1 shl 16)
        var n = 0L
        while (true) {
            val r = input.read(buf)
            if (r < 0) break
            md.update(buf, 0, r)
            out.write(buf, 0, r)
            n += r
            progress(n)
        }
        out.flush()
        return n
    }

    /**
     * The picked .gz, unpacked on the fly into root's stdin: SHA-256 and size
     * of the .gz and of the unpacked bytes, the ext4 magic at byte 1080, and
     * GZIPInputStream's own CRC and ISIZE check at the end. Anything wrong
     * stops the stream (RootShell then kills su, so root never keeps a short
     * image; its own size and hash checks refuse it anyway).
     */
    private class ImageFeed(
        private val app: Context,
        private val uri: Uri,
        private val image: ImageRef,
        private val progress: (Long) -> Unit,
    ) : RootShell.Feed {
        private val gzMd = MessageDigest.getInstance("SHA-256")
        private val rawMd = MessageDigest.getInstance("SHA-256")
        var gzBytes = 0L
        var rawBytes = 0L

        override fun write(out: OutputStream) {
            val src = app.contentResolver.openInputStream(uri) ?: throw IOException("cannot open the picked file")
            src.use {
                var lastReport = 0L
                val counting = object : FilterInputStream(BufferedInputStream(src, 1 shl 20)) {
                    override fun read(b: ByteArray, off: Int, len: Int): Int {
                        val n = super.read(b, off, len)
                        if (n > 0) {
                            gzMd.update(b, off, n)
                            gzBytes += n
                            if (gzBytes - lastReport > 64L * 1024 * 1024) {
                                lastReport = gzBytes
                                progress(gzBytes)
                            }
                        }
                        return n
                    }

                    override fun read(): Int {
                        val b = ByteArray(1)
                        return if (read(b, 0, 1) < 0) -1 else b[0].toInt() and 0xff
                    }
                }
                val gz = GZIPInputStream(counting, 1 shl 16)
                val buf = ByteArray(1 shl 18)
                val head = ByteArray(2)
                while (true) {
                    if (cancelled) throw IOException("stopped")
                    val n = gz.read(buf)
                    if (n < 0) break
                    // ext4 superblock magic 0xEF53, little endian at byte 1080.
                    for (k in 0 until n) {
                        val at = rawBytes + k
                        if (at == Images.EXT4_MAGIC_OFFSET) head[0] = buf[k]
                        if (at == Images.EXT4_MAGIC_OFFSET + 1) {
                            head[1] = buf[k]
                            val magic = (head[0].toInt() and 0xff) or ((head[1].toInt() and 0xff) shl 8)
                            if (magic != Images.EXT4_MAGIC) throw IOException("not an ext4 image")
                        }
                        if (at > Images.EXT4_MAGIC_OFFSET + 1) break
                    }
                    rawMd.update(buf, 0, n)
                    rawBytes += n
                    if (rawBytes > image.rawBytes) throw IOException("the image unpacks to more than ${image.rawBytes} bytes")
                    out.write(buf, 0, n)
                }
                // Whatever follows the gzip stream counts for the file's hash too.
                do {
                    val k = counting.read(buf, 0, buf.size)
                } while (k >= 0)
                out.flush()
                progress(gzBytes)
            }
        }

        fun problem(): String? = when {
            gzBytes != image.gzBytes -> "the .gz has $gzBytes bytes, not ${image.gzBytes}"
            Hashes.hex(gzMd.digest()) != image.gzSha256 -> "the .gz SHA-256 differs"
            rawBytes != image.rawBytes -> "unpacked to $rawBytes bytes, not ${image.rawBytes}"
            Hashes.hex(rawMd.digest()) != image.rawSha256 -> "the unpacked SHA-256 differs"
            else -> null
        }
    }
}
