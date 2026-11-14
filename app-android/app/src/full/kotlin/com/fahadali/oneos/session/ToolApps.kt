package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.root.RootScript

/**
 * An app whose kernel tool (libtimer.so) stops the switch (0.5.10; owner: rather than asking users to
 * uninstall it, turn it off, and back on when they choose). Root `tool-app off` disables only an app whose
 * tool runs now and records it in the stage; `tool-app on` enables only an app that record names. The app and
 * its data stay installed. Stopping its tool may restart the phone once (the S24 panics came when that tool's
 * pipe was freed), which is why it is not turned off and on around every session.
 */
object ToolApps : BackgroundJob<ToolApps.State>(State(), "oneos-tool-apps") {
    data class State(val busy: Boolean = false, val message: String? = null, val off: List<String> = emptyList())

    /** The package a switch refusal names ("the app <pkg> runs a kernel tool ..."), or null. */
    fun fromRefusal(text: String?): String? =
        text?.let { Regex("""the app ([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+) runs""").find(it)?.groupValues?.get(1) }

    /** The apps OneOS turned off, as root's record has them (also kept in the app's settings for the screens). */
    fun turnedOff(ctx: Context): List<String> =
        SessionPrefs.p(ctx).getStringSet(KEY, emptySet()).orEmpty().sorted()

    fun refresh(ctx: Context) = run(ctx, listOf("list"))

    fun turnOff(ctx: Context, pkg: String) = run(ctx, listOf("off", pkg))

    fun turnOn(ctx: Context, pkg: String) = run(ctx, listOf("on", pkg))

    private const val KEY = "tool_apps_off"

    private fun run(ctx: Context, args: List<String>) {
        if (state.busy) return
        val app = ctx.applicationContext
        update(state.copy(busy = true, message = null))
        executor.execute {
            val r = runCatching { RootVerbs.run(app, RootScript.Verb.TOOL_APP, args, silenceMs = 60_000L) }
            val reply = r.getOrNull()
            val ok = reply?.ok == true
            val list = if (args[0] == "list" && ok) reply!!.reply.results.mapNotNull { it.removePrefix("tool_app ").takeIf { p -> p != it } }
            else {
                val now = turnedOff(app).toMutableSet()
                if (ok && args[0] == "off") now += args[1]
                if (ok && args[0] == "on") now -= args[1]
                now.toList()
            }
            SessionPrefs.p(app).edit().putStringSet(KEY, list.toSet()).apply()
            val why = reply?.problem ?: r.exceptionOrNull()?.message
            val msg = when {
                args[0] == "list" -> null
                ok && args[0] == "off" -> "${args[1]} is off. Switch again whenever you like."
                ok -> "${args[1]} is on again. OneOS will ask to turn it off before the next switch."
                else -> "Nothing was changed: ${why ?: "no answer from root"}"
            }
            update(State(busy = false, message = msg, off = list.sorted()))
        }
    }
}
