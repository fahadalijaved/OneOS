package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.model.Hashes
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.RandomAccessFile
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * The package set files this phone's set needs, downloaded by SHA-256 (0.4.41).
 *
 * The APK carries no set files any more, only their hashes, sizes and Drive ids
 * ([AppAssets]). Each file is fetched from the owner's shared Drive folder into
 * the app's own storage (`files/oneos-files/<sha256>`), resumed from a `.part`
 * after an interruption, and kept only when its size and SHA-256 are the ones
 * the app's pinned list names. [AppAssets.open] streams it to root from there,
 * hashing it again, and root checks it once more.
 */
object SetDownloader {
    open class Failed(message: String) : IOException(message)

    /** The server answered a page instead of the file: Drive's daily download limit for that copy (0.4.53). */
    class Refused(message: String) : Failed(message)

    /** The repository whose releases hold the set files as assets named by their SHA-256 (0.4.53). */
    const val FILES_REPO = "fahadalijaved/OneOS-files"

    /** SourceForge's folder of the set files, each named by its SHA-256 (0.4.65; the source "sf"). */
    const val SF_FILES = "https://downloads.sourceforge.net/project/oneos-mirror/files/"

    /**
     * Where [source] hands out the file [sha256]: "gh:<tag>" is that release's asset (GitHub's CDN, no daily
     * limit), "sf" SourceForge's mirror of them (no daily limit either; it redirects to a download server), anything
     * else a public file of the shared Drive folder, without the virus-scan page large files get.
     */
    fun url(source: String, sha256: String): String =
        if (source == "sf") {
            require(Regex("[0-9a-f]{64}").matches(sha256))
            SF_FILES + sha256
        }
        else if (source.startsWith("gh:")) {
            val parts = source.removePrefix("gh:").split(':')
            val repo = if (parts.size == 2) parts[0] else FILES_REPO
            val tag = parts.last()
            require(Regex("[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9][A-Za-z0-9_.-]*").matches(repo) && Regex("[a-z0-9][a-z0-9.-]{0,39}").matches(tag))
            "https://github.com/$repo/releases/download/$tag/$sha256"
        }
        else "https://drive.usercontent.google.com/download?id=$source&export=download&confirm=t"

    fun dir(ctx: Context): File = File(ctx.applicationContext.filesDir, "oneos-files").apply { mkdirs() }

    /** The downloaded file when it is complete (size checked; its hash was checked when it was kept). */
    fun cached(ctx: Context, f: AppAssets.Staged): File? =
        File(dir(ctx), f.sha256).takeIf { it.isFile && it.length() == f.bytes }

    /**
     * Downloads [f] unless it is already here, from the first of its [sources] that hands
     * it out. [progress] gets the bytes of this file done so far. Runs on the caller's
     * thread; [cancelled] is checked between reads.
     *
     * 0.4.53: Drive refuses a shared file for the rest of the day once "too many users"
     * downloaded it (0.4.51, the first public release with downloads). GitHub's release
     * assets come first; then the Drive copies, each with its own limit, starting at a
     * random one so a release's downloads spread over all of them. A source that hands
     * out a page instead of the file moves on to the next at once; one that fails
     * otherwise is tried three times. A `.part` carries over between sources: they hand
     * out the same file, and the hash decides.
     */
    fun fetch(
        ctx: Context, f: AppAssets.Staged, sources: List<String>, cancelled: () -> Boolean,
        connections: MutableSet<HttpURLConnection>? = null, progress: (Long) -> Unit,
    ) {
        if (cached(ctx, f) != null) { progress(f.bytes); return }
        if (sources.isEmpty()) throw Failed("${f.name} has no download source")
        val part = File(dir(ctx), "${f.sha256}.part")
        if (part.length() > f.bytes) part.delete()
        // 0.4.65: SourceForge right after GitHub (11-08: github.com answered 504 for hours, every phone fell on
        // the Drive copies and they ran out the same day).
        val (github, others) = sources.partition { it.startsWith("gh:") }
        val (sf, drive) = others.partition { it == "sf" }
        val start = if (drive.isEmpty()) 0 else drive.indices.random()
        val order = github + sf + drive.indices.map { drive[(start + it) % drive.size] }
        var last: Exception? = null
        var refused = 0
        for (source in order) {
            for (attempt in 1..3) {
                if (cancelled()) throw Failed("stopped")
                try {
                    download(part, url(source, f.sha256), f.bytes, f.name, cancelled, connections, progress)
                    verify(part, f.bytes, f.sha256, f.name)
                    if (!part.renameTo(File(dir(ctx), f.sha256))) throw Failed("could not keep ${f.name}")
                    return
                } catch (e: Refused) {
                    refused++
                    last = e
                    break
                } catch (e: Failed) {
                    throw e
                } catch (e: IOException) {
                    if (cancelled()) throw Failed("stopped")
                    last = e
                    try { Thread.sleep(2_000L * attempt) } catch (ie: InterruptedException) { throw Failed("stopped") }
                }
            }
        }
        if (refused == order.size) {
            throw Failed("no download server is handing out ${f.name} right now (Google Drive's daily limit, or GitHub): try again in a few hours")
        }
        throw Failed("${f.name}: ${last?.message ?: "download failed"}")
    }

    /**
     * Downloads [from] into [part], appending to what [part] already holds when the
     * server takes a Range; [bytes] is the size the file must have. Also the app's
     * own update (AppUpdater).
     */
    internal fun download(
        part: File, from: String, bytes: Long, name: String, cancelled: () -> Boolean,
        connections: MutableSet<HttpURLConnection>? = null, progress: (Long) -> Unit,
    ) {
        val have = part.length()
        if (have == bytes) return
        val c = URL(from).openConnection() as HttpURLConnection
        c.connectTimeout = 30_000
        // Drive took up to 80 s before the first byte of some files (0.4.41 on the Fold, and from the server).
        c.readTimeout = 150_000
        c.instanceFollowRedirects = true
        if (have > 0) c.setRequestProperty("Range", "bytes=$have-")
        // The caller can close it from another thread (a stop): a blocked read then ends at once.
        connections?.add(c)
        try {
            val code = c.responseCode
            val type = c.contentType.orEmpty()
            // Drive answers an HTML page instead of the file when it refuses (quota, a removed file).
            if (type.startsWith("text/html")) throw Refused("the server did not hand out $name (HTTP $code): try again later")
            // Not there, or refused for now (GitHub's 404 for a missing asset, a rate limit): the next source.
            if (code == HttpURLConnection.HTTP_NOT_FOUND || code == HttpURLConnection.HTTP_FORBIDDEN || code == 429) {
                throw Refused("the server did not hand out $name (HTTP $code)")
            }
            val append = have > 0 && code == HttpURLConnection.HTTP_PARTIAL
            if (code != HttpURLConnection.HTTP_OK && !append) throw IOException("HTTP $code")
            // A stop while Drive was still answering: never touch the file after it (0.4.42 review:
            // a late answer truncated the .part a newer run was writing).
            if (cancelled()) throw Failed("stopped")
            var done = if (append) have else 0L
            FileOutputStream(part, append).use { out ->
                c.inputStream.use { input ->
                    val buf = ByteArray(1 shl 16)
                    while (true) {
                        if (cancelled()) throw Failed("stopped")
                        val n = input.read(buf)
                        // Checked again after a read that may have blocked for a long time.
                        if (cancelled()) throw Failed("stopped")
                        if (n < 0) break
                        if (done + n > bytes) throw Failed("$name is larger than the app expects")
                        out.write(buf, 0, n)
                        done += n
                        progress(done)
                    }
                }
            }
            if (done != bytes) throw IOException("$name: $done of $bytes bytes")
        } finally {
            connections?.remove(c)
            c.disconnect()
        }
    }

    /** Deletes [part] and fails unless it is [bytes] long with SHA-256 [sha256]. */
    internal fun verify(part: File, bytes: Long, sha256: String, name: String) {
        if (part.length() != bytes) {
            part.delete()
            throw Failed("$name arrived with ${part.length()} of $bytes bytes")
        }
        val md = MessageDigest.getInstance("SHA-256")
        RandomAccessFile(part, "r").use { r ->
            val buf = ByteArray(1 shl 16)
            while (true) {
                val n = r.read(buf)
                if (n < 0) break
                md.update(buf, 0, n)
            }
        }
        if (Hashes.hex(md.digest()) != sha256) {
            part.delete()
            throw Failed("$name arrived damaged (its hash is not the app's)")
        }
    }

    /** Removes downloaded files no list in this app names (an older set's), and stray parts. */
    fun prune(ctx: Context, keep: Set<String>) {
        dir(ctx).listFiles()?.forEach { file ->
            val sha = file.name.removeSuffix(".part")
            if (sha !in keep) file.delete()
        }
    }
}
