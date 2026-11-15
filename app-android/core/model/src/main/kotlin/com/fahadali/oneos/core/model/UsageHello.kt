package com.fahadali.oneos.core.model

import java.time.Instant
import java.time.ZoneOffset
import java.util.UUID

/**
 * The anonymous daily usage check-in (reports/worker.js, POST /v1/hello): which parts are pure
 * and tested here, the sender and its preferences are `report/UsageCheckIn.kt`. The limits are
 * the worker's own (install 32 hex, a model of 1-40 characters, at most 8 system ids, switches
 * 0..500), so the service never refuses what this builds.
 */
object UsageHello {
    const val SCHEMA = "oneos.hello/1"
    const val MAX_SYSTEMS = 8
    const val MAX_SWITCHES = 500

    private val INSTALL = Regex("^[0-9a-f]{32}$")
    private val TOKEN = Regex("^[a-z0-9][a-z0-9._-]{0,47}$")
    private val MODEL_CHARS = Regex("[^A-Za-z0-9 ._+-]")

    fun validInstall(id: String?): Boolean = id != null && INSTALL.matches(id)

    /** A random 128-bit id as 32 lowercase hex; never derived from anything on the phone. */
    fun newInstallId(): String = UUID.randomUUID().toString().replace("-", "")

    /** The UTC day of [wallMs], `yyyy-MM-dd`. */
    fun dayOf(wallMs: Long): String = Instant.ofEpochMilli(wallMs).atZone(ZoneOffset.UTC).toLocalDate().toString()

    /** A check-in is due when it is on and none went through yet on this UTC day. */
    fun due(enabled: Boolean, lastDay: String?, nowMs: Long): Boolean = enabled && lastDay != dayOf(nowMs)

    /** The model as the worker accepts it: other characters become spaces, 40 at most, never empty. */
    fun cleanModel(model: String?): String {
        val s = (model ?: "").replace(MODEL_CHARS, " ").trim().take(40).trim()
        return if (s.isEmpty() || !s[0].isLetterOrDigit() || s[0].code > 127) "unknown" else s
    }

    /** The ids the worker accepts, once each, the first [MAX_SYSTEMS]. */
    fun cleanSystems(ids: Collection<String?>): List<String> =
        ids.filterNotNull().filter { TOKEN.matches(it) }.distinct().take(MAX_SYSTEMS)

    fun json(install: String, versionCode: Int, model: String?, profile: String?, systems: Collection<String?>, switches: Int): String {
        require(validInstall(install)) { "install id" }
        return Json.write(
            linkedMapOf(
                "schema" to SCHEMA,
                "install" to install,
                "versionCode" to versionCode.coerceIn(1, 100000),
                "model" to cleanModel(model),
                "profile" to profile?.takeIf { TOKEN.matches(it) },
                "systems" to cleanSystems(systems),
                "switches" to switches.coerceIn(0, MAX_SWITCHES),
            ),
        )
    }
}
