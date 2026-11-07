package com.fahadali.oneos.session

import android.content.Context
import android.util.AtomicFile
import com.fahadali.oneos.BuildConfig
import com.fahadali.oneos.core.model.*
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/** The APK registry grants source/device trust; releases may only replace known payloads. */
object PatchChannels {
    private data class Catalog(val contributors: List<PatchSource>)
    @Volatile private var loaded: Catalog? = null

    @Synchronized private fun catalog(ctx: Context): Catalog {
        loaded?.let { return it }
        val json = ctx.assets.open("oneos/patch-sources.json").use { JSONObject(it.readBytes().toString(Charsets.UTF_8)) }
        require(json.getInt("schema") == 1)
        val array = json.getJSONArray("contributors")
        val contributors = (0 until array.length()).map { index ->
            val item = array.getJSONObject(index)
            val targets = item.getJSONArray("targets")
            PatchSource(item.getString("id"), item.getString("label"), item.getString("repository"), item.getString("tag"),
                (0 until targets.length()).map { i -> targets.getJSONObject(i).let {
                    require(Images.byId(it.getString("image"))?.rawSha256 == it.getString("imageSha256")) { "Patch target image hash differs from this app" }
                    PatchSource.Target(it.getString("profile"), it.getString("image"), it.getString("set"))
                } })
        }
        require(contributors.none { it.stable } && contributors.map { it.id }.distinct().size == contributors.size)
        require(contributors.all { it.check().isEmpty() }) { "The app's patch source registry is invalid" }
        return Catalog(contributors).also { loaded = it }
    }
    /** Stable is this app's own sets: its version, not a hand-kept copy in patch-sources.json. */
    @Suppress("UNUSED_PARAMETER") fun stableCode(ctx: Context) = BuildConfig.VERSION_CODE
    @Suppress("UNUSED_PARAMETER") fun stableVersion(ctx: Context): String = BuildConfig.VERSION_NAME
    fun setFor(profile: String, image: String): PackageSet? = Profiles.BUILT_IN.firstOrNull { it.id == profile }
        ?.choice(image)?.packageSetId?.let(PackageSets::byId)
    fun sources(ctx: Context, profile: String, image: String): List<PatchSource> {
        val set = setFor(profile, image) ?: return listOf(PatchSource.STABLE)
        return listOf(PatchSource.STABLE) + catalog(ctx).contributors.filter { it.supports(profile, image, set.id) }
    }
    private fun prefs(ctx: Context) = ctx.getSharedPreferences("patch_channels", Context.MODE_PRIVATE)
    fun selected(ctx: Context, profile: String, image: String): PatchSource {
        val choices = sources(ctx, profile, image)
        val legacy = if (profile == "f8" && prefs(ctx).getBoolean(image, false)) "that-josh-guy" else PatchSource.STABLE_ID
        val id = prefs(ctx).getString("$profile:$image", legacy)
        return choices.firstOrNull { it.id == id } ?: PatchSource.STABLE
    }
    fun select(ctx: Context, profile: String, image: String, id: String) {
        val source = sources(ctx, profile, image).first { it.id == id }
        if (!source.stable) readManifest(ctx, setFor(profile, image)!!, source, profile)
        check(prefs(ctx).edit().putString("$profile:$image", id).commit()) { "Could not save patch source" }
    }
    private fun cache(ctx: Context, set: PackageSet, source: PatchSource, profile: String) = File(ctx.filesDir, "patch-manifests/${source.id}/$profile/${set.id}.json")
    fun snapshot(ctx: Context, set: PackageSet, profile: String): PatchManifest? {
        val source = selected(ctx, profile, set.imageId)
        return if (source.stable) null else readManifest(ctx, set, source, profile)
    }
    @Synchronized private fun readManifest(ctx: Context, set: PackageSet, source: PatchSource, profile: String): PatchManifest {
        val target = cache(ctx, set, source, profile)
        var path = target
        // Migrate the initial Fold8-only build without losing its working snapshot.
        if (!path.exists() && source.id == "that-josh-guy" && profile == "f8") {
            path = File(ctx.filesDir, "patch-manifests/${source.id}/${set.id}.json")
            if (!path.exists()) path = File(ctx.filesDir, "patch-manifests/${set.id}.json")
        }
        return parse(ctx, AtomicFile(path).openRead().use { it.readBytes() }, set, source, profile, legacy = path != target)
    }
    private fun parse(ctx: Context, bytes: ByteArray, set: PackageSet, source: PatchSource, profile: String, legacy: Boolean = false): PatchManifest {
        require(bytes.size <= 131072) { "Patch manifest is too large" }
        val json = JSONObject(bytes.toString(Charsets.UTF_8))
        val entries = json.getJSONArray("files")
        val manifest = PatchManifest(json.getInt("schema"), json.getString("set"), json.getString("imageSha256"), json.getString("revision"),
            (0 until entries.length()).map { i -> entries.getJSONObject(i).let {
                PatchManifest.File(it.getString("name"), it.getString("sha256"), it.getLong("bytes"), it.getString("source"))
            } }, json.optString("profile", if (legacy) profile else ""))
        val problems = manifest.check(set, Images.byId(set.imageId)!!, setOf(PatchSource.STABLE.repository, source.repository), profile,
            base = AppAssets.list(ctx, set.id))
        require(problems.isEmpty()) { problems.joinToString("; ") }
        return manifest
    }
    /** Resolve once before staging. Neither failure nor a new manifest changes the installed guest. */
    fun refresh(ctx: Context, set: PackageSet, profile: String, sourceId: String = selected(ctx, profile, set.imageId).id): PatchManifest {
        val source = sources(ctx, profile, set.imageId).first { it.id == sourceId }
        require(!source.stable && source.supports(profile, set.imageId, set.id))
        val bytes = fetch("https://github.com/${source.repository}/releases/download/${source.tag}/$profile-${set.id}.json?check=${System.currentTimeMillis()}")
        val manifest = parse(ctx, bytes, set, source, profile)
        val target = cache(ctx, set, source, profile); target.parentFile!!.mkdirs()
        synchronized(this) {
            val atomic = AtomicFile(target)
            val output = atomic.startWrite()
            try { output.write(bytes); atomic.finishWrite(output) } catch (error: Throwable) { atomic.failWrite(output); throw error }
        }
        return manifest
    }
    fun stableRelease(): AppUpdate = AppUpdate.parse(fetch(AppUpdate.URL).toString(Charsets.UTF_8)).getOrThrow()

    private fun fetch(url: String): ByteArray {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.connectTimeout = 15000; connection.readTimeout = 20000
        return try {
            require(connection.responseCode == 200) { "Patch update check is unavailable (${connection.responseCode})" }
            connection.inputStream.use { input ->
                val output = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    require(output.size() + count <= 131072) { "Patch manifest is too large" }
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            }
        } finally { connection.disconnect() }
    }

    fun cachedHashes(ctx: Context): Set<String> = catalog(ctx).contributors.flatMap { source ->
        source.targets.flatMap { target ->
            runCatching { readManifest(ctx, PackageSets.byId(target.set)!!, source, target.profile).files.map { it.sha256 } }.getOrDefault(emptyList())
        }
    }.toSet()
}
