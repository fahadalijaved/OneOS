package com.fahadali.oneos.session

import android.content.Context
import com.fahadali.oneos.core.model.Debloat
import com.fahadali.oneos.core.root.RootScript
import com.fahadali.oneos.core.root.RootShell

/**
 * Debloater (0.5.32): the apps ticked on each system's Debloat screen ([Debloat]), kept per system in the
 * app-private prefs `oneos_debloat`, and sent to root's `debloat` verb right before every start of that
 * system ([beforeLaunch]), so the list root holds is always the screen's. guest_prepare.sh then hides those
 * apps' folders for the session; nothing changes in the image, and an empty list (Restore all) shows every
 * app again at the next start.
 */
object Debloater {
    private const val PREFS = "oneos_debloat"

    @Volatile private var cache: List<Debloat.App>? = null

    private fun prefs(ctx: Context) = ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun key(image: String) = "hidden:$image"

    /** Every system's apps from the asset (read once). */
    fun all(ctx: Context): List<Debloat.App> = cache ?: runCatching {
        ctx.applicationContext.assets.open(Debloat.ASSET).bufferedReader().use { Debloat.parse(it.readText()) }
    }.getOrDefault(emptyList()).also { cache = it }

    /** [image]'s apps, Safe first. */
    fun apps(ctx: Context, image: String): List<Debloat.App> = Debloat.forImage(all(ctx), image)

    /** The packages ticked for [image] that its list still offers. */
    fun hidden(ctx: Context, image: String): Set<String> {
        val offered = apps(ctx, image).mapTo(HashSet()) { it.pkg }
        return prefs(ctx).getStringSet(key(image), emptySet())!!.filterTo(HashSet()) { it in offered }
    }

    fun setHidden(ctx: Context, image: String, pkgs: Set<String>) {
        prefs(ctx).edit().apply { if (pkgs.isEmpty()) remove(key(image)) else putStringSet(key(image), pkgs.toSet()) }.apply()
    }

    fun toggle(ctx: Context, image: String, pkg: String, on: Boolean) =
        setHidden(ctx, image, hidden(ctx, image).let { if (on) it + pkg else it - pkg })

    /**
     * Before a start of [image] (LaunchJob): root's list becomes the ticked apps' folders. Returns how many apps
     * the start hides, or null when root refused (the reason is logged; the start goes on with the list root had).
     */
    fun beforeLaunch(ctx: Context, image: String): Int? {
        val app = ctx.applicationContext
        val apps = apps(app, image).let { list -> val h = hidden(app, image); list.filter { it.pkg in h } }
        val bytes = Debloat.listText(apps).toByteArray()
        val reply = runCatching {
            RootVerbs.run(
                app, RootScript.Verb.DEBLOAT, listOf(bytes.size.toString()),
                feed = RootShell.Feed { it.write(bytes) }, silenceMs = 60_000L, totalMs = 2 * 60_000L,
            )
        }.getOrNull()
        if (reply?.ok != true) {
            android.util.Log.w("OneOS", "debloat list not written: ${reply?.problem ?: "no answer"}")
            return null
        }
        return apps.size
    }
}
