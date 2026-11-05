package com.fahadali.oneos.core.model

/**
 * The app's own update (0.4.41): `update.json`, an asset of the latest GitHub
 * release, names the newest OneOS APK. The app reads it from [URL], downloads
 * [apk] (only from this repository's releases), checks [bytes] and [sha256],
 * that the APK is signed with the app's own certificate and has a higher
 * versionCode, and root installs it (`selfupdate`).
 *
 * ```
 * {"versionCode": 58, "versionName": "0.4.42", "bytes": 52428800, "sha256": "<64 hex>",
 *  "apk": "https://github.com/fahadalijaved/OneOS/releases/download/v0.4.42/OneOS-0.4.42.apk"}
 * ```
 */
data class AppUpdate(
    val versionCode: Int,
    val versionName: String,
    val apk: String,
    val bytes: Long,
    val sha256: String,
    /** One line for Home (0.4.42, optional): what the release fixes. */
    val notes: String? = null,
    /**
     * The systems (image ids) whose files this release changes (0.4.42, optional; the release script
     * compares the set lists with the release before): Home says the update is for the phone's system.
     * "*" = every system (the session scripts changed). Empty = unknown, said as an app update.
     */
    val systems: Set<String> = emptySet(),
) {
    fun newerThan(code: Int): Boolean = versionCode > code

    /** Whether this release changes the files of [imageId]'s system. */
    fun changes(imageId: String): Boolean = "*" in systems || imageId in systems

    companion object {
        const val URL = "https://github.com/fahadalijaved/OneOS/releases/latest/download/update.json"
        const val APK_PREFIX = "https://github.com/fahadalijaved/OneOS/releases/download/"

        /**
         * The team's test channel (Debug settings): an update.json in the owner's own Drive, outside
         * the shared OneOS folder, naming an APK beside it. A build is proven there before it goes to
         * GitHub. 0.4.56: its Drive id is a code the owner enters in Debug settings and appears nowhere
         * in the source (owner: the test folder was public, "anyone can use it"). [testUrl] takes the
         * id itself or a Drive link holding it; null for anything else.
         */
        fun testUrl(code: String?): String? {
            val c = code?.trim().orEmpty()
            val id = when {
                DRIVE_ID.matches(c) -> c
                else -> Regex("(?:[?&]id=|/d/)([A-Za-z0-9_-]{20,80})").find(c)?.groupValues?.get(1)
            } ?: return null
            return "https://drive.usercontent.google.com/download?id=$id&export=download&confirm=t"
        }
        private val DRIVE_ID = Regex("^[A-Za-z0-9_-]{20,80}$")
        private val DRIVE_APK = Regex("^https://drive\\.usercontent\\.google\\.com/download\\?id=[A-Za-z0-9_-]{20,80}&export=download&confirm=t$")

        /** Larger than any OneOS APK without its package set files (0.4.41 is about 60 MB). */
        const val MAX_BYTES = 256L * 1024 * 1024

        private val NAME = Regex("^[0-9]{1,3}(\\.[0-9]{1,3}){1,3}$")
        private val HEX64 = Regex("^[0-9a-f]{64}$")
        private val APK_PATH = Regex("^v[0-9.]{3,15}/OneOS-[0-9.]{3,15}\\.apk$")

        /**
         * The update [text] names, or why it is not one (a flat JSON object, these five keys).
         * [test]: the test channel's, whose APK may also be a file in the owner's Drive.
         */
        fun parse(text: String, test: Boolean = false): Result<AppUpdate> = runCatching {
            if (text.length > 4096) error("update.json is too long")
            fun raw(key: String): String =
                Regex("\"" + key + "\"\\s*:\\s*(\"[^\"\\\\]*\"|[0-9]+)").findAll(text).toList().let {
                    when (it.size) {
                        1 -> it[0].groupValues[1]
                        0 -> error("update.json has no $key")
                        else -> error("update.json names $key twice")
                    }
                }
            fun str(key: String) = raw(key).also { if (!it.startsWith('"')) error("$key is not a string") }.trim('"')
            fun optStr(key: String): String? = if (Regex("\"" + key + "\"\\s*:").containsMatchIn(text)) str(key) else null
            fun num(key: String) = raw(key).also { if (it.startsWith('"')) error("$key is not a number") }.toLongOrNull()
                ?: error("$key is out of range")
            val code = num("versionCode")
            val name = str("versionName")
            val apk = str("apk")
            val bytes = num("bytes")
            val sha = str("sha256")
            if (code !in 1..Int.MAX_VALUE.toLong()) error("versionCode $code")
            if (!NAME.matches(name)) error("versionName '$name'")
            val release = apk.startsWith(APK_PREFIX) && APK_PATH.matches(apk.removePrefix(APK_PREFIX))
            if (!release && !(test && DRIVE_APK.matches(apk))) error("the APK is not a OneOS release file: $apk")
            if (bytes !in 1..MAX_BYTES) error("APK size $bytes")
            if (!HEX64.matches(sha)) error("sha256 '$sha'")
            val notes = optStr("notes")?.trim()?.takeIf { it.isNotEmpty() }
            if (notes != null && notes.length > 140) error("notes are longer than 140 characters")
            val systems = optStr("systems")?.split(',')?.map { it.trim() }?.filter { it.isNotEmpty() }?.toSet() ?: emptySet()
            if (systems.any { it != "*" && !Regex("^[a-z0-9][a-z0-9-]{0,31}$").matches(it) }) error("systems '$systems'")
            AppUpdate(code.toInt(), name, apk, bytes, sha, notes, systems)
        }
    }
}
