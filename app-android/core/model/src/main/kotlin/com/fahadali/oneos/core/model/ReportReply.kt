package com.fahadali.oneos.core.model

/**
 * 0.5.16 (owner): reports only from group members. What the report service
 * (reports/worker.js) answers to /v1/signin, /v1/claim and a refused /v1/part or
 * /v1/report, read from its small JSON replies. Pure, so the JVM tests cover it.
 */
object ReportReply {
    /** What a claim answered. */
    sealed class Claim {
        /** The user has not pressed Start in Telegram yet. */
        object Waiting : Claim()

        /** The code ran out (10 minutes) or was already claimed. */
        object Expired : Claim()

        /** [username] is null when the Telegram account has none. */
        data class Done(val pass: String, val username: String?, val member: Boolean) : Claim()
    }

    enum class Refusal { SIGN_IN, JOIN }

    /** The string field [name] of a flat JSON reply (null when absent or null). */
    fun string(text: String, name: String): String? =
        Regex("\"" + Regex.escape(name) + "\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.){0,300})\"").find(text)?.groupValues?.get(1)
            ?.replace("\\\"", "\"")?.replace("\\\\", "\\")

    fun bool(text: String, name: String): Boolean? =
        Regex("\"" + Regex.escape(name) + "\"\\s*:\\s*(true|false)").find(text)?.groupValues?.get(1)?.toBooleanStrictOrNull()

    /** POST /v1/signin: the code and the t.me link; null when the reply has neither. */
    fun signin(text: String): Pair<String, String>? {
        val code = string(text, "code")?.takeIf { it.isNotEmpty() } ?: return null
        val url = string(text, "url")?.takeIf { it.startsWith("https://t.me/") } ?: return null
        return code to url
    }

    /** POST /v1/claim: null for a status the service does not use for a claim. */
    fun claim(status: Int, text: String): Claim? = when (status) {
        202 -> Claim.Waiting
        404 -> Claim.Expired
        200 -> string(text, "pass")?.takeIf { it.isNotEmpty() }?.let {
            Claim.Done(it, string(text, "username")?.takeIf { u -> u.isNotEmpty() }, bool(text, "member") ?: false)
        }
        else -> null
    }

    /** A 403 from /v1/part or /v1/report: sign in again, or join the group. */
    fun refusal(status: Int, text: String): Refusal? = when {
        status != 403 -> null
        bool(text, "join") == true -> Refusal.JOIN
        bool(text, "signin") == true -> Refusal.SIGN_IN
        else -> null
    }
}
