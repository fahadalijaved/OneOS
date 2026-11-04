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
    class Failed(message: String) : IOException(message)

    /** A public file of the shared Drive folder, without the virus-scan page large files get. */
    fun url(driveId: String): String = "https://drive.usercontent.google.com/download?id=$driveId&export=download&confirm=t"

    fun dir(ctx: Context): File = File(ctx.applicationContext.filesDir, "oneos-files").apply { mkdirs() }

    /** The downloaded file when it is complete (size checked; its hash was checked when it was kept). */
    fun cached(ctx: Context, f: AppAssets.Staged): File? =
        File(dir(ctx), f.sha256).takeIf { it.isFile && it.length() == f.bytes }

    /**
     * Downloads [f] unless it is already here. [progress] gets the bytes of this file
     * done so far. Runs on the caller's thread; [cancelled] is checked between reads.
     */
    fun fetch(
        ctx: Context, f: AppAssets.Staged, driveId: String, cancelled: () -> Boolean,
        connections: MutableSet<HttpURLConnection>? = null, progress: (Long) -> Unit,
    ) {
        if (cached(ctx, f) != null) { progress(f.bytes); return }
        val part = File(dir(ctx), "${f.sha256}.part")
        if (part.length() > f.bytes) part.delete()
        var last: Exception? = null
        repeat(4) { attempt ->
            if (cancelled()) throw Failed("stopped")
            try {
                download(part, url(driveId), f.bytes, f.name, cancelled, connections, progress)
                verify(part, f.bytes, f.sha256, f.name)
                if (!part.renameTo(File(dir(ctx), f.sha256))) throw Failed("could not keep ${f.name}")
                return
            } catch (e: Failed) {
                throw e
            } catch (e: IOException) {
                if (cancelled()) throw Failed("stopped")
                last = e
                try { Thread.sleep(2_000L * (attempt + 1)) } catch (ie: InterruptedException) { throw Failed("stopped") }
            }
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
            if (type.startsWith("text/html")) throw Failed("the server did not hand out $name (HTTP $code): try again later")
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
