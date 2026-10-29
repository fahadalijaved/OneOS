package com.fahadali.oneos.core.root

import java.io.File
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipOutputStream

/**
 * The short log a report sends by default (0.4.29, owner: "the important
 * ones are in the beginning only ... unless the user specifies that this was
 * not working, then we get the bigger log"). From a session's log bundle it
 * keeps every file whole except the logcat capture (capture/, nearly all of
 * the bundle's size), whose lines are kept only in two windows:
 *
 * - the start: [BEFORE_START] before the session's header in auto_return.log
 *   to [AFTER_START] after it (the switch, which takes 0.5 to 1 min, and the
 *   other system's first minutes, where its boot failures were: the package
 *   scan, surfaceflinger, the watchdog);
 * - the end: [BEFORE_END] before the watcher's return line (or the last
 *   logged line when there is none: a force restart), where a later crash
 *   shows.
 *
 * Both stop [AFTER_END] after that moment: what follows is One UI starting
 * again (S25 Ultra 26ea59af: 300,000 lines, half the bundle), and the
 * return's own log (stage/, kept whole) says how that went.
 *
 * Logcat's own `--------- beginning of` lines are kept. The times are the
 * phone's local ones on both sides (logcat, the session header, the watcher's
 * `date` lines), so no time zone is needed. trim.txt in the short zip says
 * what was kept; report.json still lists the whole files.
 */
object LogTrim {
    const val BEFORE_START = 30L
    const val AFTER_START = 5 * 60L
    const val BEFORE_END = 2 * 60L
    const val AFTER_END = 30L
    const val TRIM_NOTE = "trim.txt"

    data class Window(val from: LocalDateTime, val to: LocalDateTime) {
        operator fun contains(t: LocalDateTime): Boolean = !t.isBefore(from) && !t.isAfter(to)
    }

    private val HEADER = Regex("""^=== OneOS session (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})""")
    private val CLOCK = Regex("""\b(\d{2}):(\d{2}):(\d{2})\b""")
    private val RETURN_LINE = Regex("""returning to One UI|Volume Up \+ Volume Down held|Back to One UI asked|guest requested""")
    private val LOGCAT_TIME = Regex("""^(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})""")

    /** The capture files (logcat, rotated): the only ones cut. */
    fun isCapture(path: String): Boolean = path.substringAfter('/').startsWith("capture/")

    /**
     * The two windows from the last session of [autoReturn]; [lastLogged]: the
     * newest logcat time in the capture, the end when no return was logged.
     * Null when the log has no session header (keep everything then).
     */
    fun windows(autoReturn: String, lastLogged: LocalDateTime?): List<Window>? {
        val block = ReturnOutcomes.lastBlock(autoReturn, "=== OneOS session ")
        val head = block.firstOrNull()?.let(HEADER::find) ?: return null
        val start = LocalDateTime.of(LocalDate.parse(head.groupValues[1]), LocalTime.parse(head.groupValues[2]))
        // Each line's clock time, on the header's day or later (midnight).
        var day = start.toLocalDate()
        var prev = start.toLocalTime()
        var returnAt: LocalDateTime? = null
        for (l in block.drop(1)) {
            val m = CLOCK.find(l) ?: continue
            val t = LocalTime.of(m.groupValues[1].toInt(), m.groupValues[2].toInt(), m.groupValues[3].toInt())
            if (t.toSecondOfDay() < prev.toSecondOfDay() - 3600) day = day.plusDays(1)
            prev = t
            if (returnAt == null && RETURN_LINE.containsMatchIn(l)) returnAt = LocalDateTime.of(day, t)
        }
        val endAt = returnAt ?: lastLogged ?: return listOf(Window(start.minusSeconds(BEFORE_START), start.plusSeconds(AFTER_START)))
        val stop = endAt.plusSeconds(AFTER_END)
        return listOf(
            Window(start.minusSeconds(BEFORE_START), minOf(start.plusSeconds(AFTER_START), stop)),
            Window(endAt.minusSeconds(BEFORE_END), stop),
        )
    }

    /** A logcat line's time, in the year of [near] (logcat prints no year; December/January is handled). */
    fun lineTime(line: String, near: LocalDateTime): LocalDateTime? {
        val m = LOGCAT_TIME.find(line) ?: return null
        val (mo, d, h, mi, s) = m.destructured
        val t = runCatching { LocalDateTime.of(near.year, mo.toInt(), d.toInt(), h.toInt(), mi.toInt(), s.toInt()) }.getOrNull() ?: return null
        return when {
            t.isAfter(near.plusMonths(6)) -> t.minusYears(1)
            t.isBefore(near.minusMonths(6)) -> t.plusYears(1)
            else -> t
        }
    }

    fun keep(line: String, windows: List<Window>, near: LocalDateTime): Boolean {
        if (line.startsWith("--------- ")) return true
        val t = lineTime(line, near) ?: return false
        return windows.any { t in it }
    }

    /**
     * The short zip of [full] (a log bundle) at [out]: what [keep] keeps of
     * the capture, everything else whole. Returns false (and writes nothing)
     * when the bundle has no session header to cut by: send the whole one.
     */
    fun shorten(full: File, out: File): Boolean {
        ZipFile(full).use { z ->
            val entries = z.entries().toList().filter { !it.isDirectory }
            val auto = entries.firstOrNull { it.name.endsWith("_auto_return.log") }?.let { e -> z.getInputStream(e).bufferedReader().readText() } ?: return false
            val capture = entries.filter { isCapture(it.name) }
            // The newest line in the capture: the end when no return was logged.
            val header = HEADER.find(ReturnOutcomes.lastBlock(auto, "=== OneOS session ").firstOrNull().orEmpty()) ?: return false
            val near = LocalDateTime.of(LocalDate.parse(header.groupValues[1]), LocalTime.parse(header.groupValues[2]))
            var newest: LocalDateTime? = null
            for (e in capture) {
                z.getInputStream(e).bufferedReader().useLines { lines ->
                    lines.forEach { l -> lineTime(l, near)?.let { t -> if (newest == null || t.isAfter(newest)) newest = t } }
                }
            }
            val windows = windows(auto, newest) ?: return false
            out.delete()
            val note = StringBuilder("Short log: the capture/ files keep only the lines in these windows (phone time); every other file is whole.\n")
            windows.forEach { note.append("  ${it.from} to ${it.to}\n") }
            ZipOutputStream(out.outputStream().buffered(1 shl 16)).use { zo ->
                val top = entries.first().name.substringBefore('/')
                for (e in entries) {
                    zo.putNextEntry(ZipEntry(e.name))
                    if (isCapture(e.name)) {
                        var kept = 0
                        var all = 0
                        val w = zo.bufferedWriter()
                        z.getInputStream(e).bufferedReader().useLines { lines ->
                            lines.forEach { l ->
                                all++
                                if (keep(l, windows, near)) {
                                    kept++
                                    w.write(l)
                                    w.write("\n")
                                }
                            }
                        }
                        w.flush()
                        note.append("${e.name.substringAfter('/')}: $kept of $all lines\n")
                    } else {
                        z.getInputStream(e).use { it.copyTo(zo) }
                    }
                    zo.closeEntry()
                }
                zo.putNextEntry(ZipEntry("$top/$TRIM_NOTE"))
                zo.write(note.toString().toByteArray())
                zo.closeEntry()
            }
            return true
        }
    }
}
