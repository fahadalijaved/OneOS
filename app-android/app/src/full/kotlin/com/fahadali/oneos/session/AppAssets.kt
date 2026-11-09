package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.InstalldExpected
import com.fahadali.oneos.core.model.PackageSet
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.ShaList
import com.fahadali.oneos.core.root.RootScript
import java.io.InputStream

/**
 * What the APK carries for build 2 (app/build.gradle.kts, task oneosFiles):
 * `assets/root/oneos_root.sh` (pinned in BuildConfig), the per-set lists
 * `assets/oneos/sets/<set>.sha256` and `scripts.sha256` (their hashes pinned
 * in BuildConfig too), and every file once under `assets/oneos/files/<sha256>`
 * with its size in `index.txt`. 0.4.41: the set files are not in the APK; `remote.txt`
 * names each one's Drive id and [SetDownloader] fetches the phone's set by hash. Every list is checked against its pin before
 * use; every file is hashed again while it streams to root, and root checks
 * it once more.
 */
object AppAssets {
    data class Staged(val name: String, val sha256: String, val bytes: Long, val source: String? = null)

    class Broken(message: String) : IllegalStateException(message)

    private fun read(ctx: Context, path: String): ByteArray = ctx.applicationContext.assets.open(path).use { it.readBytes() }

    /** The root script, exactly the pinned bytes. */
    fun rootScript(ctx: Context): ByteArray {
        val b = read(ctx, RootScript.ASSET)
        if (b.size.toLong() != BuildConfig.ROOT_SCRIPT_BYTES || Hashes.sha256(b) != BuildConfig.ROOT_SCRIPT_SHA256) {
            throw Broken("the root script in the app is not the pinned one")
        }
        return b
    }

    /**
     * The pin app/build.gradle.kts writes for every packed set, as
     * BuildConfig.SET_<ID>_SHA256 (0.4.12: looked up by name; the hand-written
     * list missed pixel-sultra and x9u-in-sultra, and their setups stopped at
     * "no pin for <set>").
     */
    private fun pinned(set: String): String {
        if (set == "scripts") return BuildConfig.SCRIPTS_SHA256
        if (PackageSets.byId(set) == null) throw Broken("no pin for $set")
        val field = "SET_${set.uppercase(java.util.Locale.ROOT).replace('-', '_')}_SHA256"
        return runCatching { BuildConfig::class.java.getField(field).get(null) as String }.getOrNull()
            ?: throw Broken("no pin for $set")
    }

    internal fun list(ctx: Context, id: String): Map<String, String> {
        val text = runCatching { read(ctx, "oneos/sets/$id.sha256") }
            .getOrElse { throw Broken("this OneOS download does not carry the $id set (another series' download has it)") }
        if (Hashes.sha256(text) != pinned(id)) throw Broken("the app's $id list is not the pinned one")
        val parsed = ShaList.parse(text.toString(Charsets.UTF_8))
        if (parsed.problems.isNotEmpty()) throw Broken("$id: ${parsed.problems.first()}")
        return parsed.entries
    }

    private fun sizes(ctx: Context): Map<String, Long> =
        read(ctx, "oneos/files/index.txt").toString(Charsets.UTF_8).lines().filter { it.isNotBlank() }
            .associate { it.substringBefore(' ') to (it.substringAfter(' ').toLongOrNull() ?: -1) }

    /** The session scripts and host_installd.txt, then the set's files, in staging order. */
    fun files(ctx: Context, set: PackageSet, profile: String): List<Staged> {
        val scripts = list(ctx, "scripts")
        val channel = PatchChannels.snapshot(ctx, set, profile)
        val base = list(ctx, set.id)
        val files = channel?.files?.associate { it.name to it.sha256 } ?: base
        val problems = set.check(ShaList.render(files))
        if (problems.isNotEmpty()) throw Broken(problems.first())
        if (scripts.keys != RootScript.SCRIPTS.toSet() + INSTALLD_A16) throw Broken("the app's script list is not ${RootScript.SCRIPTS}")
        val size = sizes(ctx)
        // The installd table of the set's host One UI, staged as host_installd.txt (0.4.66: Android 16 images'
        // sets carry One UI 8.5's codes).
        val installd = scripts.getValue(InstalldExpected.assetName(sdkOf(set)))
        return (RootScript.SCRIPTS.map { it to if (it == "host_installd.txt") installd else scripts.getValue(it) } +
            set.names.map { it to files.getValue(it) }).map { (n, sha) ->
            // Only a file the channel really replaced (PatchManifest.REPLACEABLE) comes from its source.
            val override = channel?.files?.firstOrNull { it.name == n && it.sha256 != base[n] }
            val b = override?.bytes ?: size[sha] ?: throw Broken("$n has no size in the app's index")
            Staged(n, sha, b, override?.source)
        }
    }

    /** Compare the stage with the selected channel snapshot, including its exact payload hashes. */
    fun expectedStageHashes(ctx: Context, set: PackageSet, profile: String): Map<String, String> =
        files(ctx, set, profile).associate { it.name to it.sha256 } + ("bin/oneos_root.sh" to BuildConfig.ROOT_SCRIPT_SHA256)

    /**
     * sha256 -> the sources of every set file the APK does not carry (0.4.41: one Drive id; empty in a packed
     * test build). 0.4.53: several per file: "gh:<tag>", a GitHub release asset, and Drive copies in other
     * folders, each with its own download limit ([SetDownloader.url]).
     */
    fun remoteIds(ctx: Context): Map<String, List<String>> =
        runCatching { read(ctx, "oneos/files/remote.txt") }.getOrNull()?.toString(Charsets.UTF_8)?.lines()
            ?.filter { it.isNotBlank() }
            ?.associate { l -> l.substringBefore(' ') to l.substringAfter(' ').split(',').map { it.trim() }.filter { it.isNotEmpty() } }
            ?: emptyMap()

    private fun packed(ctx: Context): Set<String> =
        ctx.applicationContext.assets.list("oneos/files")?.toSet() ?: emptySet()

    /** The files of [files] that are neither in the APK nor downloaded yet, with their sources. */
    fun toDownload(ctx: Context, files: List<Staged>): List<Pair<Staged, List<String>>> {
        val inApk = packed(ctx)
        val ids = remoteIds(ctx)
        return files.filter { it.sha256 !in inApk && SetDownloader.cached(ctx, it) == null }.map { f ->
            f to (f.source?.let { (listOf(it) + ids[f.sha256].orEmpty()).distinct() } ?: ids[f.sha256]?.takeIf { it.isNotEmpty() } ?: throw Broken("${f.name} is neither in the app nor on its download list"))
        }
    }

    /** Every set file hash any list in this app names: what the download cache may keep. */
    fun allSetHashes(ctx: Context): Set<String> = remoteIds(ctx).keys + PatchChannels.cachedHashes(ctx)

    /** From the APK when it carries the file, else from the downloads ([SetDownloader]). */
    fun open(ctx: Context, f: Staged): InputStream {
        if (f.sha256 in packed(ctx)) return ctx.applicationContext.assets.open("oneos/files/${f.sha256}")
        val file = SetDownloader.cached(ctx, f) ?: throw Broken("${f.name} is not downloaded")
        return file.inputStream()
    }

    /** One UI 8.5's installd table: an app asset beside the scripts, staged as host_installd.txt for SDK 36 images. */
    private const val INSTALLD_A16 = "host_installd_a16.txt"

    /** The Android version of [set]'s image (37 when the image is unknown). */
    private fun sdkOf(set: PackageSet): Int = Images.byId(set.imageId)?.sdk ?: 37

    /** The installd table the app ships for SDK [sdk] images (the installd gate's expected table). */
    fun hostInstalldTxt(ctx: Context, sdk: Int = 37): String {
        val name = InstalldExpected.assetName(sdk)
        val sha = list(ctx, "scripts")[name] ?: throw Broken("no $name in the app")
        val b = read(ctx, "oneos/files/$sha")
        if (Hashes.sha256(b) != sha) throw Broken("$name in the app is damaged")
        return b.toString(Charsets.UTF_8)
    }
}
