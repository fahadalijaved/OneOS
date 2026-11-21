package com.fahadali.oneos.guest

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * ColorOS's animation level (0.5.32; owner, A36: "it's better ... add a toggle in OneOS guest app ... so user can
 * change it back n forth"). OneOS starts ColorOS at OPPO's top level, 1 (all blur and animations, as on a
 * flagship); "Lighter animations" is level 3, OPPO's mid-range level, which kept SystemUI's frames on time on the
 * A36. The request is `files/oneos_anim_level` in this app's data folder ("1" or "3"), like [FullLogs]: the
 * session's watcher on the host (oneos_switch.sh) applies it at once (ColorOS's launcher and SystemUI restart) and
 * keeps it for the next starts. It answers in [STATE], the level in effect, written at every ColorOS start; no
 * state file means another system or a OneOS too old for this, and the row is hidden.
 */
object AnimLevel {
    const val STATE = "/data/oneos_bootui/anim_level"
    private const val FILE_NAME = "oneos_anim_level"
    const val FULL = 1
    const val LIGHT = 3

    /** The level in effect, or null where this does not apply. */
    fun current(): Int? =
        runCatching { File(STATE).takeIf { it.isFile && it.length() in 1..4 }?.readText()?.trim()?.toInt() }.getOrNull()
            ?.takeIf { it in 1..4 }

    /** A request the watcher has not taken yet. */
    fun pending(context: Context): Boolean = File(context.filesDir, FILE_NAME).isFile

    /** Written to a temporary name and renamed, so the watcher never reads half of it. */
    @Throws(IOException::class)
    fun request(context: Context, level: Int) {
        require(level in 1..4)
        val dir = context.filesDir
        val tmp = File(dir, "$FILE_NAME.tmp")
        FileOutputStream(tmp).use { out ->
            out.write("$level\n".toByteArray())
            out.fd.sync()
        }
        if (!tmp.renameTo(File(dir, FILE_NAME))) {
            tmp.delete()
            throw IOException("could not create ${File(dir, FILE_NAME)}")
        }
    }
}
