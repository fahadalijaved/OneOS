package com.fahadali.oneos.guest

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * Record full logs from now (0.5.17; owner: full session logs are off by default, "can they enable them from
 * guest app inside the OS and then it starts?"). The request is `files/oneos_full_logs` in this app's own data
 * folder, like [ReturnRequest]: the session's watcher on the host (oneos_switch.sh) checks it every second,
 * deletes it and starts the session's full log capture. It answers in [STATE] (`1` recording, `0` not), which
 * it writes at the start of every session; no state file means a OneOS too old for this, and the row is hidden.
 */
object FullLogs {
    const val STATE = "/data/oneos_bootui/full_logs"
    private const val FILE_NAME = "oneos_full_logs"

    enum class Status { UNSUPPORTED, OFF, STARTING, ON }

    fun status(context: Context): Status {
        val s = runCatching { File(STATE).takeIf { it.isFile && it.length() in 1..8 }?.readText()?.trim() }.getOrNull()
        return when {
            s == "1" -> Status.ON
            s == null -> Status.UNSUPPORTED
            File(context.filesDir, FILE_NAME).isFile -> Status.STARTING
            else -> Status.OFF
        }
    }

    /** Written to a temporary name and renamed, so the watcher never reads half of it. */
    @Throws(IOException::class)
    fun request(context: Context) {
        val dir = context.filesDir
        val tmp = File(dir, "$FILE_NAME.tmp")
        FileOutputStream(tmp).use { out ->
            out.write("full ${System.currentTimeMillis() / 1000}\n".toByteArray())
            out.fd.sync()
        }
        if (!tmp.renameTo(File(dir, FILE_NAME))) {
            tmp.delete()
            throw IOException("could not create ${File(dir, FILE_NAME)}")
        }
    }
}
