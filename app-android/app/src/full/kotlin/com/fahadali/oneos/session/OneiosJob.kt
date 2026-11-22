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
import com.fahadali.oneos.core.model.OneiosKb
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosManifest
import com.fahadali.oneos.core.model.OneiosManifests
import com.fahadali.oneos.core.model.OneiosPackage
import com.fahadali.oneos.core.model.OneiosRelease
import com.fahadali.oneos.core.model.OneiosReleases
import com.fahadali.oneos.core.model.OneiosStaged
import com.fahadali.oneos.core.model.OneiosSystem
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.TarReader
import com.fahadali.oneos.core.model.Units
import com.fahadali.oneos.core.root.OneiosFlow
import com.fahadali.oneos.core.root.OneiosImport
import com.fahadali.oneos.core.root.OneiosMakeImage
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
        /** When [message] began ([SystemClock.elapsedRealtime]): the screens count the seconds of a step that runs. */
        val since: Long = 0,
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
        OldStagesJob.state.busy || RemoveJob.state.busy || OneiosChecksJob.state.busy || OneiosToolJob.state.busy

    fun canStart(): Boolean = !state.busy && !othersBusy()

    fun cancel() {
        cancelled = true
        shells.forEach { it.cancel() }
        runCatching { connection?.disconnect() }
    }

    // --- Root ---------------------------------------------------------------------

    private class Reply(val reply: RootReply, val end: RootShell.End, val answered: Boolean = true) {
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
        onLine: ((RootReply) -> Unit)? = null,
        /** The limit until root prints its first line (su waits for the root manager's grant); null: [silenceMs]. */
        firstLineMs: Long? = null,
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
        var answered = false
        val end = try {
            if (cancelled) sh.cancel()
            sh.run(input, { line -> answered = true; reply.accept(line); onLine?.invoke(reply) }, { if (!answered && firstLineMs != null) firstLineMs else silenceMs }, totalMs)
        } finally {
            shells -= sh
        }
        return Reply(reply, end, answered)
    }

    private fun must(r: Reply): Reply {
        if (cancelled) throw Failed("stopped")
        if (!r.ok) throw Failed(r.problem)
        return r
    }

    /**
     * Root's `status`. With [partial], what it has said of the stage is passed on as soon as only its preflight is
     * left ([OneiosStatus.partial]), once: the screens show the stage while the last check still runs.
     */
    private fun readStatus(app: Context, partial: ((OneiosStatus) -> Unit)? = null): OneiosStatus {
        // A check says each step as it comes (the screens count its seconds): root's grant, the stage, the last check.
        val shown = partial != null
        if (shown) say("Asking root for access…")
        var first = true
        var sent = false
        val hook: (RootReply) -> Unit = { r ->
            if (shown && first) {
                first = false
                say("Root answered. Reading what is on this phone…")
            }
            if (partial != null && !sent) OneiosStatus.partial(r.results)?.let {
                sent = true
                partial(it)
                say("Checking the staged files and the phone…")
            }
        }
        // Root prints its first line at once; nothing within ROOT_FIRST_LINE_MS is su waiting for a grant that does
        // not come (before 2026-11-22 the page said "Checking…" for the whole 3 minutes of the silence limit).
        val r = root(app, OneiosRoot.Verb.STATUS, silenceMs = 120_000, onLine = hook, firstLineMs = ROOT_FIRST_LINE_MS)
        if (!r.ok && !r.answered && !cancelled) throw Failed(if (r.end.killed) ROOT_SILENT else "$ROOT_REFUSED (${r.problem})")
        val st = OneiosStatus.parse(must(r).reply.results)
        statusAt = SystemClock.elapsedRealtime()
        return st
    }

    /** The step in words now, its seconds counted from here. */
    private fun say(message: String) = update(state.copy(message = message, since = SystemClock.elapsedRealtime()))

    private const val ROOT_FIRST_LINE_MS = 20_000L
    internal const val ROOT_SILENT = "Root did not answer within 20 s. Open your root manager (KernelSU, Magisk or APatch), " +
        "allow root for OneOS, then Check again. OneOS signed with a new key counts as a new app there."
    internal const val ROOT_REFUSED = "Root was refused. Allow root for OneOS in your root manager (KernelSU, Magisk or APatch), then Check again"

    /** When root last answered a whole `status` ([SystemClock.elapsedRealtime]); 0 = never in this process. */
    @Volatile private var statusAt = 0L

    private fun offered(app: Context): Boolean =
        runCatching { OneiosSystem.offeredOn(Profiles.resolve(FactProbe(app).collect(RootProbe(app).signals())).profile) }.getOrDefault(false)

    // --- What the app checked at staging (shown beside root's status) ----------------

    private const val PREFS = "oneios"
    private const val KEY_KERNEL_CHECK = "kernel_check"

    /** The last kernel check's answer, for the iOS page's kernel row; null = never checked. */
    fun kernelCheckLine(ctx: Context): String? =
        ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_KERNEL_CHECK, null)

    private fun record(app: Context, kind: OneiosKind): OneiosStaged? =
        OneiosStaged.decode(app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(kind.word, null))

    /** The staged runtime's kernel path (`runtime.json`'s `kernel.path`); null when nothing recorded. */
    fun stagedKernelPath(ctx: Context): String? =
        OneiosStaged.decode(ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(OneiosKind.RUNTIME.word, null))?.kernelPath

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
        update(state.copy(phase = phase, job = kind, last = null, failure = null, message = first, since = SystemClock.elapsedRealtime(), failed = false, done = 0, total = 0, file = null, bytesPerSecond = 0, etaSeconds = null))
        // Before the work, from the screen the user tapped: Android only lets a visible app start it.
        if (state.copying) OneiosService.start(app)
        val before = state.status
        executor.execute {
            val result = runCatching { work(app) }
            val offered = state.offered ?: offered(app)
            // A check shows the stage as soon as root has said it, and the last check as it runs (OneiosStatus.partial).
            val partial: ((OneiosStatus) -> Unit)? = if (kind == OneiosFlow.Job.CHECK) { st -> update(state.copy(status = st, offered = offered)) } else null
            val read = runCatching { cancelled = false; readStatus(app, partial) }
            // (Not a partial answer: a status that failed keeps the one from before the job.)
            val status = read.getOrNull() ?: before
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

    /**
     * [refresh], unless root answered a whole status less than [maxAgeMs] ago and the screen shows it: a screen that
     * comes back (from the picker, Make iOS image, the logs) does not ask root again for what it just said. Every job
     * reads the status again when it ends, and Check again always asks.
     */
    fun refreshIfStale(ctx: Context, maxAgeMs: Long = 30_000) {
        val s = state
        if (s.status != null && !s.failed && statusAt != 0L && SystemClock.elapsedRealtime() - statusAt < maxAgeMs) return
        refresh(ctx)
    }

    /** The runtime package of OneiOS's latest release, or of [tag]. */
    fun downloadRuntime(ctx: Context, tag: String?) = job(ctx, Phase.DOWNLOADING, OneiosFlow.Job.DOWNLOAD_RUNTIME, "Looking for the OneiOS runtime…") { app ->
        stageRelease(app, tag, unless = null).second
    }

    /**
     * Make iOS image's runtime step ([OneiosMakeImage.Io.latestRuntime]): the latest release's runtime downloaded and
     * staged as [downloadRuntime] does, unless its version is [unless] (the staged one: then nothing is downloaded).
     * Runs on the caller's thread, [OneiosToolJob]'s flow, while no other job can start; meanwhile this job's state
     * is a download like [downloadRuntime]'s (Set up iOS 27 and the flow's screen show its bytes, Stop cancels it), and
     * afterwards it holds root's new status, as after any job.
     */
    internal fun stageLatestForMakeImage(app: Context, unless: String?): OneiosMakeImage.Runtime {
        if (state.busy) return OneiosMakeImage.Runtime.Failed("another iOS job runs")
        cancelled = false
        meter.reset()
        update(state.copy(phase = Phase.DOWNLOADING, job = OneiosFlow.Job.DOWNLOAD_RUNTIME, last = null, failure = null, message = "Looking for the OneiOS runtime…",
            failed = false, done = 0, total = 0, file = null, bytesPerSecond = 0, etaSeconds = null))
        val result = runCatching { stageRelease(app, null, unless) }
        val why = result.exceptionOrNull()?.let { it.message ?: it.javaClass.simpleName }
        val offered = state.offered ?: offered(app)
        val status = runCatching { cancelled = false; readStatus(app) }.getOrNull() ?: state.status
        val (release, line) = result.getOrNull() ?: (null to null)
        update(
            State(
                Phase.IDLE, status, offered, why ?: line ?: "OneiOS runtime ${release?.version} is the newest; it is staged already.", failed = why != null,
                last = OneiosFlow.Job.DOWNLOAD_RUNTIME, failure = why,
                runtimeRecord = record(app, OneiosKind.RUNTIME), imageRecord = record(app, OneiosKind.IMAGE),
            ),
        )
        return when {
            why != null || release == null -> OneiosMakeImage.Runtime.Failed(why ?: "no runtime in the release")
            line == null -> OneiosMakeImage.Runtime.Same(release.version)
            else -> OneiosMakeImage.Runtime.Staged(release.version)
        }
    }

    /** Root's status that another flow read (Make iOS image's last one): the iOS screens show it, when no job runs. */
    internal fun statusRead(app: Context, st: OneiosStatus) {
        statusAt = SystemClock.elapsedRealtime()
        if (!state.busy) update(state.copy(status = st, runtimeRecord = record(app, OneiosKind.RUNTIME), imageRecord = record(app, OneiosKind.IMAGE)))
    }

    /**
     * The runtime package of OneiOS's latest release (or of [tag]) downloaded and staged: the release, and the line
     * for the screen; that line is null when the release's version is [unless] (nothing was downloaded).
     */
    private fun stageRelease(app: Context, tag: String?, unless: String?): Pair<OneiosRelease, String?> {
        val t = tag?.trim()?.takeIf { it.isNotEmpty() }
        if (t != null && !OneiosReleases.validTag(t)) throw Failed("'$t' is not a release tag")
        val api = http(OneiosReleases.apiUrl(t), accept = "application/vnd.github+json")
        if (api.first == 404) throw Failed(OneiosReleases.noRelease(t))
        if (api.first != 200) throw Failed("GitHub answered ${api.first} for the release")
        val release = OneiosReleases.parse(api.second.toString(Charsets.UTF_8)).getOrElse { throw Failed(it.message ?: "no runtime in the release") }
        if (unless != null && release.version == unless) return release to null
        val shaAnswer = http(release.sha256Url)
        if (shaAnswer.first != 200) throw Failed("${release.assetName}.sha256 could not be downloaded (${shaAnswer.first})")
        val sha = OneiosReleases.parseSha256(shaAnswer.second.toString(Charsets.UTF_8), release.assetName)
            ?: throw Failed("${release.assetName}.sha256 does not hold its SHA-256")
        val dir = File(app.cacheDir, "oneios").apply { mkdirs() }
        dir.listFiles()?.forEach { it.delete() }
        val file = File(dir, release.assetName)
        return try {
            download(release.assetUrl, file, release.assetBytes, sha)
            meter.reset()
            val m = stage(app, OneiosKind.RUNTIME) { file.inputStream() }
            remember(app, m)
            release to (runtimeLine(m) + " (release ${release.tag})")
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
     * The switch. [ticked] is the experimental tick and [notThisPhoneTicked] the not-this-phone
     * warning's (OneiosSwitchConfirm's boxes); the gate and root's own preflight both have to pass,
     * and a refusal changes nothing. When it works One UI's framework stops, and this app with it.
     */
    // --- Kernel updates (docs/oneios.md, "Kernel updates") ------------------------------

    /** The app's kb/kb.json: what Apple build the prelink inputs pair, their hashes and the kernelcache's pin. */
    internal fun kbInputs(app: Context): OneiosKb {
        val text = app.assets.open("kb/kb.json").use { it.readBytes().toString(Charsets.UTF_8) }
        return OneiosKb.parse(text).getOrElse { throw Failed("the app's kernel-build inputs are not valid: ${it.message}") }
    }

    /**
     * The newest release's runtime kernel against the staged one. Read only:
     * downloads the new runtime package to the cache, reads its runtime.json
     * (no staging), compares its `kernel` with the staged one.
     */
    fun checkKernel(ctx: Context) = job(ctx, Phase.CHECKING, OneiosFlow.Job.CHECK, "Looking for a newer OneiOS kernel…") { app ->
        val line = try {
            checkKernelNow(app)
        } catch (e: Failed) {
            if (cancelled) throw e
            e.message ?: "the kernel check failed"
        }
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY_KERNEL_CHECK, line).apply()
        line
    }

    private fun checkKernelNow(app: Context): String {
        val api = http(OneiosReleases.apiUrl(null), accept = "application/vnd.github+json")
        if (api.first != 200) throw Failed("GitHub answered ${api.first} for the latest release")
        val release = OneiosReleases.parse(api.second.toString(Charsets.UTF_8)).getOrElse { throw Failed(it.message ?: "no runtime in the release") }
        val shaAnswer = http(release.sha256Url)
        if (shaAnswer.first != 200) throw Failed("${release.assetName}.sha256 could not be downloaded (${shaAnswer.first})")
        val sha = OneiosReleases.parseSha256(shaAnswer.second.toString(Charsets.UTF_8), release.assetName)
            ?: throw Failed("${release.assetName}.sha256 does not hold its SHA-256")
        val dir = File(app.cacheDir, "oneios-kernel").apply { mkdirs() }
        dir.listFiles()?.forEach { it.delete() }
        val file = File(dir, release.assetName)
        return try {
            download(release.assetUrl, file, release.assetBytes, sha)
            val latest = tar(file.inputStream()).use { z ->
                val reader = TarReader(z)
                val found = OneiosPackage.manifestFirst(reader, OneiosKind.RUNTIME)
                    ?: throw Failed("${release.assetName} holds no runtime.json")
                OneiosManifests.parse(OneiosKind.RUNTIME, found.text).getOrElse { throw Failed(it.message ?: "runtime.json is not valid") }
            }.kernel
            val staged = readStatus(app)
            OneiosManifests.kernelUpdate(staged.runtimeKernel?.buildId, latest)
                ?: "The staged kernel ${staged.runtimeKernel?.buildId ?: "is unknown"} is current (release ${release.tag})."
        } finally {
            file.delete()
        }
    }

    /**
     * The app's kb/ files (everything Update the kernel stages but Apple's kernelcache), by name, as its assets
     * hold them. [OneiosKernelUpdate] checks each against kb.json before root gets it; root checks it again.
     */
    internal fun kbAssets(app: Context): Map<String, ByteArray> =
        OneiosKbFiles.NAMES.filter { it != "kernelcache.macho" }.associateWith { name -> app.assets.open("kb/$name").use { it.readBytes() } }

    /**
     * Optional, with no download: Apple's decoded kernelcache from a file a PC wrote (OneiOS's image build leaves
     * `kernelcache.macho`), checked against the profile's pin, into the stage. Update the kernel fetches it from
     * Apple itself, so this is only for a phone without a network.
     */
    fun importKernelcache(ctx: Context, uri: Uri) =
        job(ctx, Phase.STAGING, OneiosFlow.Job.STAGE_KB, "Reading the kernelcache…") { app ->
            importKernelcache(app, kbInputs(app), uri)
            "Apple's kernelcache is staged: it pairs only with the ${kbInputs(app).build} prelink inputs."
        }

    private fun importKernelcache(app: Context, kb: OneiosKb, uri: Uri): String {
        val dir = File(app.cacheDir, "oneios-kernel").apply { mkdirs() }
        val file = File(dir, "kernelcache.macho")
        try {
            app.contentResolver.openInputStream(uri)?.use { input ->
                file.outputStream().use { output ->
                    val digest = java.security.MessageDigest.getInstance("SHA-256")
                    val buf = ByteArray(1 shl 20)
                    var total = 0L
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        output.write(buf, 0, n)
                        digest.update(buf, 0, n)
                        total += n
                        bytes(total, total, force = false)
                    }
                    val sha = digest.digest().joinToString("") { "%02x".format(it) }
                    if (!sha.equals(kb.kernelcacheSha256, ignoreCase = true)) {
                        throw Failed("this kernelcache is not the ${kb.build} one the profile pins (SHA-256 differs): " +
                            "import the kernelcache.macho your PC wrote when it built the image set.")
                    }
                    step("Staging kernelcache.macho…")
                    must(root(app, OneiosRoot.Verb.KBINPUT, listOf("kernelcache.macho", total.toString(), sha),
                        RootShell.Feed { o -> file.inputStream().use { it.copyTo(o) } }))
                    return sha
                }
            } ?: throw Failed("the picked file cannot be opened")
        } finally {
            file.delete()
        }
    }

    /**
     * Activates the kernel the phone built (`tool work`, prelink): [kcSha256]
     * is the collection's SHA-256 as the tool reported it. Checks first (the
     * image set's build, the staged kernelcache, the staged runtime's kernel),
     * then the old set aside, the new files in with fresh hashes, lists,
     * manifest and configs, and a receipt where the session logs live. Refuses
     * during a session; the kept set is the fallback (`restoreKernel`).
     */
    fun activateKernel(ctx: Context, kcSha256: String) =
        job(ctx, Phase.STAGING, OneiosFlow.Job.FINISH_KERNEL, "Activating the phone-built kernel…") { app ->
            val st = readStatus(app)
            val kb = kbInputs(app)
            OneiosManifests.kernelProblem(st.image?.build, kb, st.kb.kernelcacheSha256, st.runtimeKernel != null)?.let { throw Failed(it) }
            val bid = st.runtimeKernel?.buildId ?: throw Failed("the staged runtime carries no kernel")
            must(root(app, OneiosRoot.Verb.FINISH, listOf("kernel", kcSha256.lowercase(java.util.Locale.ROOT), bid)))
            "kernel.kc $bid is activated for the next session; the previous set is kept as the fallback."
        }

    /** Back to the kept kernel set after a kernel update, with its own receipt. */
    fun restoreKernel(ctx: Context) =
        job(ctx, Phase.STAGING, OneiosFlow.Job.RESTORE_KERNEL, "Restoring the kept kernel set…") { app ->
            must(root(app, OneiosRoot.Verb.RESTORE, listOf("kernel")))
            "The kept kernel set is the image's again."
        }

    fun switch(ctx: Context, ticked: Boolean, notThisPhoneTicked: Boolean = false) = job(ctx, Phase.SWITCHING, OneiosFlow.Job.SWITCH, "Checking before the switch…") { app ->
        val profile = Profiles.resolve(FactProbe(app).collect(RootProbe(app).signals())).profile
        val gate = OneiosSystem.gate(profile, ticked, notThisPhoneTicked)
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
