package com.fahadali.oneos.shared

import android.app.Activity
import android.net.Uri
import androidx.appcompat.app.AlertDialog
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URI
import java.security.MessageDigest
import java.util.concurrent.Executors

/** Fetches module-provided update metadata and ZIPs. Installation is always the existing verified importer. */
object ModuleUpdates {
    private val io = Executors.newCachedThreadPool()
    private const val LIMIT = 512L * 1024 * 1024
    private fun connection(url: String): HttpURLConnection {
        var next = url
        repeat(6) {
            val uri = URI(next)
            require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null) { "Module updates require an HTTPS URL" }
            val c = uri.toURL().openConnection() as HttpURLConnection
            c.connectTimeout = 15000; c.readTimeout = 30000; c.instanceFollowRedirects = false
            c.setRequestProperty("User-Agent", "OneOS-GuestModules/1")
            if (c.responseCode in 300..399) {
                val location = c.getHeaderField("Location") ?: error("Invalid update redirect")
                next = uri.resolve(location).toString(); c.disconnect()
            } else { check(c.responseCode == 200) { "Update server returned HTTP ${c.responseCode}" }; return c }
        }
        error("Too many update redirects")
    }
    private fun download(url: String, target: File, limit: Long) {
        val c = connection(url)
        try {
            require(c.contentLengthLong <= limit) { "Download is too large" }
            c.inputStream.use { input -> target.outputStream().use { out ->
                val buffer = ByteArray(65536); var total = 0L
                while (true) { val n = input.read(buffer); if (n < 0) break; total += n; require(total <= limit) { "Download is too large" }; out.write(buffer,0,n) }
            } }
        } finally { c.disconnect() }
    }
    fun copyDocument(activity: Activity, uri: Uri): File {
        val target = File.createTempFile("guest-module-", ".zip", activity.cacheDir)
        try {
            activity.contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "Cannot read this ZIP" }
                target.outputStream().use { out -> val b = ByteArray(65536); var total = 0L
                    while (true) { val n = input.read(b); if (n < 0) break; total += n; require(total <= LIMIT) { "Module ZIP exceeds 512 MiB" }; out.write(b,0,n) }
                }
            }
            return target
        } catch (t: Throwable) { target.delete(); throw t }
    }
    fun check(activity: Activity, name: String, id: String, installedCode: Long, url: String, done: (File?) -> Unit) {
        fun finish(file: File? = null) { if (!activity.isDestroyed) done(file) else file?.delete() }
        fun failure(t: Throwable) { activity.runOnUiThread { if (!activity.isDestroyed) {
            AlertDialog.Builder(activity).setTitle("Module update").setMessage(t.message ?: "Update failed").setPositiveButton(android.R.string.ok,null).show()
        }; finish() } }
        io.execute {
            try {
                val metadata = File.createTempFile("module-update-", ".json", activity.cacheDir)
                val json = try { download(url,metadata,64*1024); JSONObject(metadata.readText()) } finally { metadata.delete() }
                val code = json.getLong("versionCode")
                if (code <= installedCode) { activity.runOnUiThread { if (!activity.isDestroyed)
                    AlertDialog.Builder(activity).setTitle(name).setMessage("This module is up to date.").setPositiveButton(android.R.string.ok,null).show(); finish() }; return@execute }
                val zipUrl = json.getString("zipUrl")
                require(URI(zipUrl).scheme == "https" && !URI(zipUrl).host.isNullOrBlank()) { "Module updates require an HTTPS ZIP URL" }
                val changelog = json.optString("changelog").takeIf { runCatching { URI(it).scheme == "https" && !URI(it).host.isNullOrBlank() }.getOrDefault(false) }.orEmpty()
                val sha = json.optString("sha256").lowercase()
                require(sha.isEmpty() || sha.matches(Regex("[a-f0-9]{64}"))) { "Invalid update SHA-256" }
                activity.runOnUiThread {
                    if (activity.isDestroyed) return@runOnUiThread
                    var accepted = false
                    AlertDialog.Builder(activity).setTitle("Update $name?")
                        .setMessage("${json.optString("version", code.toString())}\n\nThe update will be downloaded from ${URI(zipUrl).host} and staged for the next guest restart.")
                        .setNeutralButton(if (changelog.isNotBlank()) "Changelog" else "Details") { _,_ ->
                            if (changelog.isNotBlank()) runCatching { activity.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, Uri.parse(changelog))) }
                                .onFailure { android.widget.Toast.makeText(activity,"No browser available to open the changelog",android.widget.Toast.LENGTH_LONG).show() }
                            finish()
                        }.setNegativeButton(android.R.string.cancel,null)
                        .setPositiveButton("Download update") { _,_ ->
                            accepted = true
                            io.execute {
                                val zip = File.createTempFile("guest-module-", ".zip", activity.cacheDir)
                                try {
                                    download(zipUrl,zip,LIMIT)
                                    if (sha.isNotEmpty()) {
                                        val md=MessageDigest.getInstance("SHA-256"); zip.inputStream().use { input -> val b=ByteArray(65536); while(true){ val n=input.read(b);if(n<0)break;md.update(b,0,n) } }
                                        check(md.digest().joinToString("") { "%02x".format(it) } == sha) { "Update SHA-256 mismatch" }
                                    }
                                    java.util.zip.ZipFile(zip).use { archive ->
                                        val prop=archive.getEntry("module.prop") ?: error("Missing module.prop")
                                        require(prop.size in 1..16384) { "Invalid update module.prop" }
                                        val p=java.util.Properties(); archive.getInputStream(prop).use(p::load)
                                        check(p.getProperty("id")?.trim() == id) { "Update belongs to a different module" }
                                        check(p.getProperty("versionCode")?.trim()?.toLongOrNull() == code) { "Update version does not match metadata" }
                                    }
                                    activity.runOnUiThread { finish(zip) }
                                } catch(t:Throwable) { zip.delete(); failure(t) }
                            }
                        }.setOnDismissListener { if (!accepted) finish() }.show()
                }
            } catch(t:Throwable) { failure(t) }
        }
    }
}
