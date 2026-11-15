package com.fahadali.oneos.session

import android.content.Context
import android.net.Uri
import com.fahadali.oneos.BuildConfig
import android.os.SystemClock
import com.fahadali.oneos.core.device.FactProbe
import com.fahadali.oneos.core.model.ByteMeter
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.Level
import com.fahadali.oneos.core.model.OneiosFile
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosManifest
import com.fahadali.oneos.core.model.OneiosManifests
import com.fahadali.oneos.core.model.OneiosReleases
import com.fahadali.oneos.core.model.OneiosStaged
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.core.root.OneiosImport
import com.fahadali.oneos.core.root.OneiosRoot
import com.fahadali.oneos.core.root.OneiosStatus
import com.fahadali.oneos.core.root.RootProbe
import com.fahadali.oneos.core.root.RootReply
import com.fahadali.oneos.core.root.RootShell
import com.github.luben.zstd.ZstdInputStream
import java.io.BufferedInputStream
import java.io.File
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * Everything the app does for the iOS 27 (OneiOS) system (docs/oneios.md):
 * read what is staged, download the runtime package from OneiOS's releases,
 * import a runtime package or the iOS image set from a file the user picked,
 * switch, and remove. Each change is a verb of `oneios_root.sh` through
 * [OneiosRoot]'s launcher; the image set is never downloaded.
 *
 * A package goes to root over the road an Android system's image takes
 * ([RootShell] into the root script's `receive`), by [OneiosImport]: one pass
 * over the file when its manifest comes first, every listed file hashed by the
 * app on the way and by root once it has landed. Nothing replaces what is
 * staged until `finish`. While it runs [OneiosService] keeps the app alive and
 * the screen hears of the bytes four times a second ([ByteMeter], as setup does).
 *
 * The screens read the state through [State.flow] ([OneiosFlow]): which step is done, what to do
 * now, and a refusal in plain words. For that the state also keeps which job ran ([State.job],
 * [State.last]), its failure as root or the app said it ([State.failure]), and what the app checked
 * when it staged each package ([State.runtimeRecord], [State.imageRecord]). None of it changes a
 * root command: the verbs, their order and their arguments are the ones before the redesign.
 */
object OneiosJob : BackgroundJob<OneiosJob.State>(State(), "oneos-oneios") {
    enum class Phase { IDLE, CHECKING, DOWNLOADING, STAGING, SWITCHING, REMOVING }

    data class State(
        val phase: Phase = Phase.IDLE,
        /** What root last reported; null until the first check. */
        val status: OneiosStatus? = null,
        /** This phone takes the system ([OneiosSystem.offeredOn]); null until read. */
        val offered: Boolean? = null,
        /** The step in words while busy; afterwards the result or the reason it failed. */
        val message: String? = null,
        val failed: Boolean = false,
        val done: Long = 0,
        val total: Long = 0,
        /** The file being sent, "File 3 of 21: os.img (10.6 GB)"; null when the step has none. */
        val file: String? = null,
        /** Bytes a second, a moving average; 0 = not measured yet. */
        val bytesPerSecond: Long = 0,
        /** Seconds left; null = still estimating. */
        val etaSeconds: Int? = null,
        /** The job that runs now; null when idle. */
        val job: OneiosFlow.Job? = null,
        /** The job that ran last, and why it failed as root or the app said it (null: it worked). */
        val last: OneiosFlow.Job? = null,
        val failure: String? = null,
        /** What the app checked when it staged the runtime and the image set (size, files). */
        val runtimeRecord: OneiosStaged? = null,
        val imageRecord: OneiosStaged? = null,
    ) {
        val busy: Boolean get() = phase != Phase.IDLE

        /** A long copy runs (a download, an import): the screen stays on and [OneiosService] holds the app. */
        val copying: Boolean get() = phase == Phase.DOWNLOADING || phase == Phase.STAGING

        /** The steps, the check of each package, what to do now ([OneiosFlow]). */
        val flow: OneiosFlow.View
            get() = OneiosFlow.of(OneiosFlow.Input(status, offered, job, last, failure, runtimeRecord, imageRecord))

        /** "3.2 GB of 17.9 GB (18%) · 412 MB/s · about 2 min left", or null without a byte count. */
        val progressLine: String?
            get() = if (!busy || total <= 0) null else listOfNotNull(
                "${Units.bytes(done)} of ${Units.bytes(total)} (${(done * 100 / total).coerceIn(0, 100)}%)",
                ByteMeter.speed(bytesPerSecond),
                etaSeconds?.let(ByteMeter::left),
            ).joinToString(" · ")
    }

    private class Failed(message: String) : IOException(message)

    @Volatile private var cancelled = false

    /** The root commands that run now: one, or two while root still checks a large file and the next is sent. */
    private val shells = java.util.concurrent.ConcurrentHashMap.newKeySet<RootShell>()

    @Volatile private var connection: HttpURLConnection? = null

    private fun othersBusy() = StageCheck.state.busy || PrepareJob.state.busy || LaunchJob.state.busy || LogJob.state.busy ||
        OldStagesJob.state.busy || RemoveJob.state.busy || OneiosChecksJob.state.busy

    fun canStart(): Boolean = !state.busy && !othersBusy()

    fun cancel() {
        cancelled = true
        shells.forEach { it.cancel() }
        runCatching { connection?.disconnect() }
    }

    // --- Root ---------------------------------------------------------------------

    private class Reply(val reply: RootReply, val end: RootShell.End) {
        val ok: Boolean get() = end.exitCode == 0 && reply.ok != null && end.error == null
        val problem: String
            get() = when {
                end.error != null -> end.error!!
                end.cancelled -> "stopped"
                end.killed && reply.refused == null -> "root did not answer in time"
                else -> reply.problem(end.exitCode) ?: "no answer from root"
            }
    }

    /** The root script, exactly the pinned bytes. */
    internal fun rootScript(app: Context): ByteArray {
        val b = app.assets.open(OneiosRoot.ASSET).use { it.readBytes() }
        if (b.size.toLong() != BuildConfig.ONEIOS_ROOT_BYTES || Hashes.sha256(b) != BuildConfig.ONEIOS_ROOT_SHA256) {
            throw Failed("the OneiOS root script in the app is not the pinned one")
        }
        return b
    }

    private fun root(
        app: Context,
        verb: OneiosRoot.Verb,
        args: List<String> = emptyList(),
        data: RootShell.Feed? = null,
        silenceMs: Long = 120_000,
        totalMs: Long = 6 * 60 * 60_000L,
    ): Reply {
        val script = rootScript(app)
        val command = OneiosRoot.launcher(verb, args, BuildConfig.ONEIOS_ROOT_SHA256, BuildConfig.ONEIOS_ROOT_BYTES)
        val input = when (verb.stdin) {
            OneiosRoot.Stdin.SCRIPT -> RootShell.Feed { it.write(script) }
            OneiosRoot.Stdin.DATA -> requireNotNull(data) { "${verb.word} needs its data" }
            OneiosRoot.Stdin.NONE -> null
        }
        val sh = RootShell(command)
        shells += sh
        val reply = RootReply()
        val end = try {
            if (cancelled) sh.cancel()
            sh.run(input, { line -> reply.accept(line) }, { silenceMs }, totalMs)
        } finally {
            shells -= sh
        }
        return Reply(reply, end)
    }

    private fun must(r: Reply): Reply {
        if (cancelled) throw Failed("stopped")
        if (!r.ok) throw Failed(r.problem)
        return r
    }

    private fun readStatus(app: Context): OneiosStatus = OneiosStatus.parse(must(root(app, OneiosRoot.Verb.STATUS, silenceMs = 180_000)).reply.results)

    private fun offered(app: Context): Boolean =
        runCatching { OneiosSystem.offeredOn(Profiles.resolve(FactProbe(app).collect(RootProbe(app).signals())).profile) }.getOrDefault(false)

    // --- What the app checked at staging (shown beside root's status) ----------------

    private const val PREFS = "oneios"

    private fun record(app: Context, kind: OneiosKind): OneiosStaged? =
        OneiosStaged.decode(app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(kind.word, null))

    private fun remember(app: Context, m: OneiosManifest) =
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(m.kind.word, OneiosStaged.of(m, System.currentTimeMillis()).encode()).apply()

    private fun forget(app: Context) = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()

    /**
     * Runs [work] as the one job; afterwards reads the status again and shows [work]'s result line or
     * its failure. A check ([OneiosFlow.Job.CHECK]) whose `status` itself fails keeps that failure, so
     * the screen can say why (before, it stayed on "Checking…").
     */
    private fun job(ctx: Context, phase: Phase, kind: OneiosFlow.Job, first: String, work: (Context) -> String?) {
        if (!canStart()) return
        val app = ctx.applicationContext
        cancelled = false
        meter.reset()
        update(state.copy(phase = phase, job = kind, last = null, failure = null, message = first, failed = false, done = 0, total = 0, file = null, bytesPerSecond = 0, etaSeconds = null))
        // Before the work, from the screen the user tapped: Android only lets a visible app start it.
        if (state.copying) OneiosService.start(app)
        executor.execute {
            val result = runCatching { work(app) }
            val offered = state.offered ?: offered(app)
            val read = runCatching { cancelled = false; readStatus(app) }
            val status = read.getOrNull() ?: state.status
            fun words(e: Throwable) = e.message ?: e.javaClass.simpleName
            val why = result.exceptionOrNull()?.let(::words) ?: read.exceptionOrNull()?.takeIf { kind == OneiosFlow.Job.CHECK }?.let(::words)
            update(
                State(
                    Phase.IDLE, status, offered, why ?: result.getOrNull(), failed = why != null,
                    last = kind, failure = why,
                    runtimeRecord = record(app, OneiosKind.RUNTIME), imageRecord = record(app, OneiosKind.IMAGE),
                ),
            )
        }
    }

    // --- What the screen calls --------------------------------------------------------

    /** Read only: what is staged and whether a switch would start. */
    fun refresh(ctx: Context) = job(ctx, Phase.CHECKING, OneiosFlow.Job.CHECK, "Checking what is on this phone…") { null }

    /** The runtime package of OneiOS's latest release, or of [tag]. */
    fun downloadRuntime(ctx: Context, tag: String?) = job(ctx, Phase.DOWNLOADING, OneiosFlow.Job.DOWNLOAD_RUNTIME, "Looking for the OneiOS runtime…") { app ->
        val t = tag?.trim()?.takeIf { it.isNotEmpty() }
        if (t != null && !OneiosReleases.validTag(t)) throw Failed("'$t' is not a release tag")
        val api = http(OneiosReleases.apiUrl(t), accept = "application/vnd.github+json")
        if (api.first == 404) throw Failed(OneiosReleases.noRelease(t))
        if (api.first != 200) throw Failed("GitHub answered ${api.first} for the release")
        val release = OneiosReleases.parse(api.second.toString(Charsets.UTF_8)).getOrElse { throw Failed(it.message ?: "no runtime in the release") }
        val shaAnswer = http(release.sha256Url)
        if (shaAnswer.first != 200) throw Failed("${release.assetName}.sha256 could not be downloaded (${shaAnswer.first})")
        val sha = OneiosReleases.parseSha256(shaAnswer.second.toString(Charsets.UTF_8), release.assetName)
            ?: throw Failed("${release.assetName}.sha256 does not hold its SHA-256")
        val dir = File(app.cacheDir, "oneios").apply { mkdirs() }
        dir.listFiles()?.forEach { it.delete() }
        val file = File(dir, release.assetName)
        try {
            download(release.assetUrl, file, release.assetBytes, sha)
            meter.reset()
            val m = stage(app, OneiosKind.RUNTIME) { file.inputStream() }
            remember(app, m)
            runtimeLine(m) + " (release ${release.tag})"
        } finally {
            file.delete()
        }
    }

    /** "I have the file": a runtime package or the iOS image set, through the picker's read grant. */
    fun importFile(ctx: Context, kind: OneiosKind, uri: Uri) = job(
        ctx, Phase.STAGING, if (kind == OneiosKind.RUNTIME) OneiosFlow.Job.IMPORT_RUNTIME else OneiosFlow.Job.IMPORT_IMAGE, "Reading the file…",
    ) { app ->
        val m = stage(app, kind) {
            app.contentResolver.openInputStream(uri) ?: throw Failed("the picked file cannot be opened")
        }
        remember(app, m)
        when (kind) {
            OneiosKind.RUNTIME -> runtimeLine(m)
            OneiosKind.IMAGE -> "iOS ${m.version}${m.build?.let { " ($it)" }.orEmpty()} image set is staged: ${m.files.size} files, ${Units.bytes(m.bytes)}."
        }
    }

    /**
     * The switch. [ticked] is the experimental tick; the gate and root's own
     * preflight both have to pass, and a refusal changes nothing. When it works
     * One UI's framework stops, and this app with it.
     */
    fun switch(ctx: Context, ticked: Boolean) = job(ctx, Phase.SWITCHING, OneiosFlow.Job.SWITCH, "Checking before the switch…") { app ->
        val profile = Profiles.resolve(FactProbe(app).collect(RootProbe(app).signals())).profile
        val gate = OneiosSystem.gate(profile, ticked)
        if (gate.level != Level.OK) throw Failed(if (gate.level == Level.BLOCK) gate.detail else "Tick the box first: ${gate.title}.")
        // This build's session scripts and boot screen, before every switch: an app update reaches the stage
        // without a new import. A refusal here (no stage yet, an open session) is not the answer: root's
        // preflight below gives that, and a stage that keeps its earlier scripts switches as it did before.
        for (s in sessionFiles(app)) {
            if (cancelled) throw Failed("stopped")
            val staged = root(app, OneiosRoot.Verb.SCRIPT, listOf(s.name, s.bytes.size.toString(), s.sha256), RootShell.Feed { it.write(s.bytes) })
            if (!staged.ok) break
        }
        must(root(app, OneiosRoot.Verb.SWITCH, listOf(BuildConfig.VERSION_CODE.toString(), "1"), silenceMs = 180_000))
        "Switching to ${OneiosSystem.SHORT_NAME}…"
    }

    /** Back to One UI, for a session that is still open while this app runs (one that never stopped One UI, or is stuck). */
    fun backToOneUi(ctx: Context) = job(ctx, Phase.SWITCHING, OneiosFlow.Job.RETURN, "Returning to One UI…") { app ->
        val r = must(root(app, OneiosRoot.Verb.RETURN))
        if (r.reply.ok == "return nothing") "No iOS session is open." else "Returning to One UI. If it cannot be done in place, the phone restarts."
    }

    fun remove(ctx: Context) = job(ctx, Phase.REMOVING, OneiosFlow.Job.REMOVE, "Removing the iOS files…") { app ->
        must(root(app, OneiosRoot.Verb.REMOVE, silenceMs = 10 * 60_000L))
        forget(app)
        File(app.cacheDir, "oneios").deleteRecursively()
        "The iOS runtime, image set and data were removed from this phone."
    }

    private fun runtimeLine(m: OneiosManifest): String =
        if (m.placeholder) "OneiOS runtime ${m.version} is staged. It carries a placeholder instead of xnuhost, so it cannot start iOS yet."
        else "OneiOS runtime ${m.version} is staged."

    // --- Staging ----------------------------------------------------------------------

    private fun tar(raw: InputStream): InputStream =
        // The window both packages are packed with is at most 2^27 (OneiOS's oneos/interface.md).
        ZstdInputStream(BufferedInputStream(raw, 1 shl 20)).setContinuous(false).setLongMax(27)

    /** The bytes of a long copy, as setup counts them: the screen hears of them every 250 ms. */
    private val meter = ByteMeter(SystemClock::elapsedRealtime, updateMs = 250, estimateMs = 5000)

    /** A new step: shown at once. */
    private fun step(what: String, file: String? = null) {
        val s = state
        if (s.message == what && s.file == file) return
        update(s.copy(message = what, file = file))
    }

    /**
     * [done] of [total] bytes, called for every buffer. 0.4.76 sent the screen a
     * state for every MiB, a few hundred a second, and the screen built all its
     * rows again for each one: that was the lag during an import.
     */
    private fun bytes(done: Long, total: Long, force: Boolean = false) {
        val m = meter.tick(done, total, force) ?: return
        update(state.copy(done = m.done, total = m.total, bytesPerSecond = m.bytesPerSecond, etaSeconds = m.etaSeconds))
    }

    /**
     * The session scripts and OneOS's boot screen files this build pins: they are small, and always this app's.
     * Root stages them with every import and before every switch.
     */
    private fun sessionFiles(app: Context): List<OneiosImport.Script> {
        val boot = BuildConfig.ONEIOS_BOOT_SCREEN_SHA256.split(',').map { it.substringBefore('=') to it.substringAfter('=') }
        if (boot.map { it.first } != OneiosRoot.BOOT_SCREEN_FILES) throw Failed("the boot screen files in the app are not the pinned ones")
        val pins = listOf("oneios_switch.sh" to BuildConfig.ONEIOS_SWITCH_SHA256, "oneios_return.sh" to BuildConfig.ONEIOS_RETURN_SHA256) + boot
        return pins.map { (name, pin) ->
            val b = app.assets.open("oneios/$name").use { it.readBytes() }
            if (Hashes.sha256(b) != pin) throw Failed("$name in the app is not the pinned one")
            OneiosImport.Script(name, b, pin)
        }
    }

    private fun stage(app: Context, kind: OneiosKind, open: () -> InputStream): OneiosManifest {
        val scripts = sessionFiles(app)
        val root = object : OneiosImport.Root {
            override fun run(verb: OneiosRoot.Verb, args: List<String>, feed: RootShell.Feed?, silenceMs: Long): String? {
                val r = root(app, verb, args, feed, silenceMs)
                return if (r.ok) null else r.problem
            }

            override fun abandon() = shells.forEach { it.cancel() }
        }
        val listener = object : OneiosImport.Listener {
            override fun step(text: String) = step(text, null)

            override fun file(index: Int, count: Int, file: OneiosFile) =
                step("Staging the ${kind.label}", OneiosImport.fileLine(index, count, file))

            override fun bytes(done: Long, total: Long) = bytes(done, total, force = done >= total)

            override fun stopped(): Boolean = cancelled
        }
        try {
            return OneiosImport(kind, root, listener).run({ tar(open()) }, scripts) { manifest ->
                if (kind == OneiosKind.RUNTIME && manifest.sessionAbi != OneiosSystem.SESSION_ABI) {
                    throw Failed("This runtime speaks session ABI ${manifest.sessionAbi}; this version of OneOS speaks ${OneiosSystem.SESSION_ABI}.")
                }
                manifest.minOneosFork?.let { need ->
                    if (!OneiosManifests.versionAtLeast(BuildConfig.VERSION_NAME, need)) {
                        throw Failed("This runtime needs OneOS $need or newer; this is ${BuildConfig.VERSION_NAME}.")
                    }
                }
                bytes(0, manifest.bytes, force = true)
            }.manifest
        } catch (e: OneiosImport.Failed) {
            throw Failed(e.message ?: "the import failed")
        }
    }

    // --- Downloads (the runtime only, only from OneiOS's releases) ---------------------

    private fun open(url: String, accept: String?): HttpURLConnection {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 20_000
        c.readTimeout = 30_000
        c.instanceFollowRedirects = true
        c.setRequestProperty("User-Agent", "OneOS/${BuildConfig.VERSION_NAME}")
        if (accept != null) c.setRequestProperty("Accept", accept)
        connection = c
        return c
    }

    /** A small answer (the release JSON, the .sha256 file): its status and at most 1 MiB of it. */
    private fun http(url: String, accept: String? = null): Pair<Int, ByteArray> {
        val c = open(url, accept)
        try {
            val code = try {
                c.responseCode
            } catch (e: IOException) {
                throw Failed("No connection to GitHub (${e.message}).")
            }
            if (code != 200) return code to ByteArray(0)
            val out = java.io.ByteArrayOutputStream()
            c.inputStream.use { input ->
                val buf = ByteArray(1 shl 14)
                while (out.size() <= 1 shl 20) {
                    val n = input.read(buf)
                    if (n < 0) break
                    out.write(buf, 0, n)
                }
            }
            if (out.size() > 1 shl 20) throw Failed("the answer from GitHub is too long")
            return code to out.toByteArray()
        } finally {
            c.disconnect()
            connection = null
        }
    }

    private fun download(url: String, file: File, bytes: Long, sha256: String) {
        val c = open(url, "application/octet-stream")
        try {
            val code = try {
                c.responseCode
            } catch (e: IOException) {
                throw Failed("No connection to GitHub (${e.message}).")
            }
            if (code != 200) throw Failed("${file.name} could not be downloaded ($code)")
            val md = MessageDigest.getInstance("SHA-256")
            var n = 0L
            step("Downloading ${file.name} (${Units.bytes(bytes)})")
            meter.reset()
            c.inputStream.use { input ->
                file.outputStream().use { out ->
                    val buf = ByteArray(1 shl 16)
                    while (true) {
                        if (cancelled) throw Failed("stopped")
                        val k = input.read(buf)
                        if (k < 0) break
                        n += k
                        if (n > bytes) throw Failed("${file.name} is larger than its release says")
                        md.update(buf, 0, k)
                        out.write(buf, 0, k)
                        bytes(n, bytes)
                    }
                }
            }
            if (n != bytes || Hashes.hex(md.digest()) != sha256) {
                throw Failed("${file.name} did not arrive intact (size or SHA-256 differs). Try again.")
            }
        } catch (e: Failed) {
            throw e
        } catch (e: IOException) {
            throw Failed("The download stopped (${e.message}). Try again.")
        } finally {
            c.disconnect()
            connection = null
        }
    }
}
