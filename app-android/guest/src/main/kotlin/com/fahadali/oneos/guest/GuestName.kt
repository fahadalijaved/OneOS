package com.fahadali.oneos.guest

import android.os.Build
import java.io.File

/**
 * The name of the system this app runs in, for "You're in {system}", or null
 * when it cannot tell (the screen then names no system).
 *
 * The session writes a bounded friendly system name into its private data tree.
 * Older stages fall back to build.prop. The property area is One UI's
 * (guest_props.sh only adds the props One UI lacks), so [Build.MODEL] and
 * every `ro.product.*` the app could ask for are the Samsung phone's. The
 * guest's build.prop files are its own, though: a phone's product partition
 * names the phone (`ro.product.product.model`), which is how the host's image
 * table names such a system. Only a friendly-looking value counts (words with
 * a space, not a model code or a generic build name), and never the host
 * phone's own. Nothing here names a system: the name is the image's.
 */
internal object GuestName {
    /** The guest's own files: its root is the guest image (product and system_ext inside /system). */
    private val files = listOf(
        "/system/product/etc/build.prop",
        "/product/etc/build.prop",
        "/system/system_ext/etc/build.prop",
        "/system_ext/etc/build.prop",
        "/system/build.prop",
    )

    /** Most specific first. */
    private val keys = listOf(
        "ro.product.product.marketname",
        "ro.product.marketname",
        "ro.product.product.model",
        "ro.product.system_ext.model",
        "ro.product.system.model",
    )

    /** Build names, not system names ("mainline", "AOSP on ARM64", "Android SDK built for arm64", "generic"). */
    private val generic = Regex("""generic|mainline|aosp|gsi|sdk|emulator|android|unknown""", RegexOption.IGNORE_CASE)

    private const val MAX_FILE_BYTES = 512L * 1024

    /** A few small files, read on the main thread: the title is set once, before the first frame. */
    fun read(): String? {
        runCatching { File("/data/oneos_bootui/system_name").takeIf { it.isFile && it.length() in 1..128 }?.readText()?.trim() }
            .getOrNull()?.takeIf { it.isNotBlank() && it.none(Char::isISOControl) }?.let { return it }

        val props = files.mapNotNull { path ->
            runCatching {
                File(path).takeIf { it.isFile && it.length() in 1L..MAX_FILE_BYTES }?.let(::parse)
            }.getOrNull()
        }
        return keys.firstNotNullOfOrNull { key -> props.firstNotNullOfOrNull { p -> p[key]?.takeIf(::friendly) } }
    }

    private fun parse(f: File): Map<String, String> {
        val out = HashMap<String, String>()
        f.forEachLine { raw ->
            val line = raw.trim()
            val eq = line.indexOf('=')
            // As init reads it: the last value of a key wins.
            if (eq > 0 && !line.startsWith("#")) out[line.substring(0, eq).trim()] = line.substring(eq + 1).trim()
        }
        return out
    }

    private fun friendly(v: String): Boolean =
        v.length in 3..40 &&
            v.contains(' ') &&
            v.any { it.isLowerCase() } &&
            v.none { it.isISOControl() } &&
            !generic.containsMatchIn(v) &&
            !v.equals(Build.MODEL, ignoreCase = true) &&
            listOf(Build.MANUFACTURER, Build.BRAND).none { it.isNotBlank() && v.contains(it, ignoreCase = true) }
}
