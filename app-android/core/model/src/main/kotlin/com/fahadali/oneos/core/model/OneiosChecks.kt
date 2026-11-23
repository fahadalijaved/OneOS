package com.fahadali.oneos.core.model

/**
 * The hardware checks of the iOS 27 (OneiOS) system (docs/oneios.md, "Hardware
 * checks"): OneiOS's own phone tools, which come in its runtime package
 * (`bin/bridgectl`, `gpuctl`, `displayctl`, `brightctl`, `camctl`), each run
 * as root beside a running One UI by `oneios_root.sh check <id>`. No check
 * starts a session or stops anything of One UI's.
 *
 * This file is the list (what the root script runs for each id is written
 * there; the two are compared by a test) and the reading of each tool's
 * output: pass, fail or skipped, and the one line the row shows. What each
 * tool prints is in its README in OneiOS (`runtime/bridges`, `runtime/display`,
 * `runtime/bridges/brightness`, `runtime/bridges/camera`, `docs/gpu.md`).
 */
enum class OneiosCheckOutcome(val word: String) { PASS("pass"), FAIL("fail"), SKIPPED("skipped") }

data class OneiosCheck(
    val id: String,
    val title: String,
    /** The file under the runtime's `bin/`. */
    val tool: String,
    /** Its arguments, as the root script passes them (`@BIN@` and `@OUT@` are the stage's folders). */
    val args: String,
    /** Seconds until root ends a tool that has not finished. */
    val limitSeconds: Int,
    /** What the owner sees, hears or has to do: said before the check runs. Null: nothing to notice. */
    val notice: String? = null,
    /** Not part of Run all. */
    val experimental: Boolean = false,
    /** The check writes a picture root can hand back (`checkfile <id>`). */
    val picture: Boolean = false,
) {
    val command: String get() = "$tool $args".trim()
}

data class OneiosCheckResult(val outcome: OneiosCheckOutcome, val line: String, val hint: String? = null)

object OneiosChecks {
    const val BLUETOOTH = "bt"
    const val LEVELS = "levels"

    val ALL: List<OneiosCheck> = listOf(
        OneiosCheck("cpu", "CPU layout", "bridgectl", "cpu", 15),
        OneiosCheck("gpu", "GPU", "gpuctl", "", 120),
        OneiosCheck(
            "display", "Display layer", "displayctl", "test", 30,
            "Colour bars with a moving white square cover the whole screen for 5 seconds, then One UI is back.",
        ),
        OneiosCheck("haptic", "Haptics", "bridgectl", "haptic 200 1000", 10, "The phone buzzes once."),
        OneiosCheck("haptic-pattern", "Haptics pattern", "bridgectl", "haptic-pattern", 15, "The phone buzzes: three taps, then a ramp."),
        OneiosCheck("audio", "Audio", "bridgectl", "audio @BIN@/oneios-audio", 20, "A 440 Hz tone plays for 2 seconds at the media volume."),
        OneiosCheck(
            BLUETOOTH, "Bluetooth", "bridgectl", "bt", 45,
            "Bluetooth has to be off in One UI: the check takes the controller, and One UI's Bluetooth would lose it.",
        ),
        OneiosCheck("brightness", "Brightness", "brightctl", "info", 10),
        OneiosCheck(
            LEVELS, "Brightness steps", "brightctl", "levels", 30,
            "Adaptive brightness has to be off in One UI. The screen steps from very dim to full and back for 12 seconds, then returns to where it was.",
        ),
        OneiosCheck("als", "Light sensor", "brightctl", "als 10", 25, "It reads the sensor on the back for 10 seconds: cover the back, then point it at a light."),
        OneiosCheck("camera-list", "Cameras", "camctl", "--backend ndk list", 30),
        OneiosCheck(
            "camera", "Camera", "camctl", "--backend ndk --camera wide --frames 90 --out @OUT@/camera.png capture", 45,
            "The wide camera is used for a few seconds and one picture is kept on this phone. Close One UI's Camera app first.",
            picture = true,
        ),
        OneiosCheck("camera-hal-list", "Cameras by the HAL (experimental)", "camctl", "--backend hal list", 30, experimental = true),
        OneiosCheck(
            "camera-hal", "Camera by the HAL (experimental)", "camctl",
            "-v --backend hal --camera wide --frames 90 --out @OUT@/camera-hal.png capture", 45,
            "The wide camera is opened through Samsung's camera HAL directly, which has never been tried on this phone, and one picture is kept. " +
                "Close One UI's Camera app first.",
            experimental = true, picture = true,
        ),
    )

    fun byId(id: String): OneiosCheck? = ALL.firstOrNull { it.id == id }

    /** The checks of Run all, in order. */
    val RUN_ALL: List<OneiosCheck> = ALL.filterNot { it.experimental }

    /**
     * What `oneios_root.sh check <id>` reported: the tool was not in the
     * runtime ([missing]), it was ended at the limit ([timeoutSeconds]), or it
     * ended by itself with [exit]; [output] is everything it printed.
     */
    data class Run(val missing: String? = null, val exit: Int? = null, val timeoutSeconds: Int? = null, val output: List<String> = emptyList())

    /**
     * Reads root's answer for one check: [results] are its `@@RESULT` lines
     * (`check <id> missing <tool>`, `check <id> exit <n>`, `check <id> timeout
     * <s>`), [lines] every other line; the tool's own output is the lines that
     * begin with "| ". Null when root gave no result for [id].
     */
    fun parseRun(id: String, results: List<String>, lines: List<String>): Run? {
        val output = lines.filter { it.startsWith("| ") || it == "|" }.map { it.removePrefix("|").removePrefix(" ").trimEnd('\r') }
        for (r in results) {
            val w = r.trim().split(' ')
            if (w.size < 4 || w[0] != "check" || w[1] != id) continue
            when (w[2]) {
                "missing" -> return Run(missing = w[3], output = output)
                "exit" -> w[3].toIntOrNull()?.let { return Run(exit = it, output = output) }
                "timeout" -> w[3].toIntOrNull()?.let { return Run(timeoutSeconds = it, output = output) }
            }
        }
        return null
    }

    private val CAMERAS = Regex("^back end: ([a-z]+), ([0-9]+) cameras$")
    private val FRAMES = Regex("^frames: ([0-9]+) read, ([0-9]+) missed.*$")

    /** OneiOS's `runtime/bridges/camera/README.md`, "What can go wrong, and what it means". */
    private fun cameraHint(out: List<String>, hal: Boolean): String? {
        fun has(vararg parts: String) = out.any { l -> parts.all { l.contains(it) } }
        return when {
            has("status -10013") -> "cameraserver could not ask system_server: expected in a session, not with One UI running."
            has("hal: no service") -> "The camera provider has another instance name on this build (service list | grep camera.provider)."
            has("exception -8", "camera status 2") -> "The camera is in use (One UI's Camera app, face unlock). Close it and run the check again."
            has("configureStreams", "status 1") -> "The HAL refused the stream (size, usage or session parameters). Send the full output."
            hal && has("no frame arrived") -> "The HAL's calls back into camctl are refused (dmesg | grep avc)."
            has("(black") -> "The lens is covered, or the stream is not what it says."
            else -> null
        }
    }

    /** Pass, fail or skipped for [check], and the line its row shows. */
    fun classify(check: OneiosCheck, run: Run): OneiosCheckResult {
        val out = run.output.map { it.trimEnd() }.filter { it.isNotBlank() }
        val last = out.lastOrNull().orEmpty()
        fun pass(line: String) = OneiosCheckResult(OneiosCheckOutcome.PASS, line.take(300))
        fun fail(line: String, hint: String? = null) = OneiosCheckResult(OneiosCheckOutcome.FAIL, line.take(300), hint)
        fun first(prefix: String) = out.firstOrNull { it.startsWith(prefix) }

        run.missing?.let { return OneiosCheckResult(OneiosCheckOutcome.SKIPPED, "Not in this runtime: bin/$it") }
        run.timeoutSeconds?.let { s ->
            return fail("Ended after $s s: the tool did not finish" + if (last.isEmpty()) "" else " (last line: $last)", "What it changed was put back.")
        }
        val exit = run.exit ?: return fail("No result from root")
        if (exit == 2 && check.tool != "displayctl") return fail(last.ifEmpty { "exit 2" }, "This runtime's ${check.tool} does not take this command: stage a newer runtime.")
        if (exit > 128) return fail("${check.tool} was ended by signal ${exit - 128}" + if (last.isEmpty()) "" else " (last line: $last)")

        return when (check.tool) {
            // "ok", or "failed" under the reason it printed.
            "bridgectl" -> when {
                exit == 0 && last == "ok" -> pass(
                    when (check.id) {
                        "cpu" -> listOfNotNull(first("host: "), first("plan: ")).joinToString("; ").ifEmpty { "ok" }
                        BLUETOOTH -> "ok: ${out.count { it.trimStart().startsWith("<- type") }} HCI events" + (first("address file: ")?.let { ", $it" } ?: "")
                        else -> "ok"
                    },
                )
                else -> {
                    val why = out.dropLast(1).lastOrNull()?.trim()
                    fail(
                        if (last == "failed" && why != null) "failed: $why" else last.ifEmpty { "exit $exit" },
                        if (check.id == BLUETOOTH) "Is Bluetooth off in One UI's settings? The check cannot take a controller One UI holds." else null,
                    )
                }
            }
            // Its last line is "ok" or "FAILED at: <step>: <reason>".
            "gpuctl" -> when {
                exit == 0 && last == "ok" -> pass(listOfNotNull(first("submit: ")?.substringBefore(';'), "ok").joinToString(": ").let { if (it.length > 200) "ok" else it })
                else -> fail(out.lastOrNull { it.startsWith("FAILED at:") } ?: last.ifEmpty { "exit $exit" })
            }
            "displayctl" -> when {
                exit == 0 && last == "displayctl: ok" -> pass(out.lastOrNull { it.startsWith("displayctl: ") && it.contains(" frames in ") }?.removePrefix("displayctl: ")?.let { "ok: $it" } ?: "ok")
                else -> fail(out.lastOrNull { it.startsWith("displayctl: ") && it != "displayctl: FAILED" } ?: last.ifEmpty { "exit $exit" })
            }
            "brightctl" -> {
                val ok = exit == 0 && last == "brightctl: ok"
                val failure = out.lastOrNull { it.startsWith("brightctl: failed") } ?: last.ifEmpty { "exit $exit" }
                when (check.id) {
                    "brightness" -> {
                        val panel = first("panel: ")
                        when {
                            ok && panel != null && panel != "panel: no backlight device" -> pass(panel)
                            ok -> fail(panel ?: "no panel line", "The tool found no backlight device it can write.")
                            else -> fail(failure)
                        }
                    }
                    LEVELS -> {
                        val restored = first("restored ")
                        val steps = out.count { it.startsWith("slider ") }
                        when {
                            ok && restored != null && steps > 0 -> pass("ok: $steps steps, $restored")
                            last == "brightctl: stopped" -> fail("stopped before the last step" + (restored?.let { ", $it" } ?: ""))
                            ok -> fail("no step was written")
                            else -> fail(failure)
                        }
                    }
                    else -> {
                        val readings = out.lastOrNull { it.contains(" readings in ") }
                        when {
                            ok -> pass(listOfNotNull("ok", readings, first("light sensor: ")).joinToString(": "))
                            else -> fail(failure, if (readings != null) "The sensor is there and sent nothing." else null)
                        }
                    }
                }
            }
            "camctl" -> {
                val hal = check.id.contains("hal")
                val hint = cameraHint(out, hal)
                if (check.picture) {
                    val frames = out.firstNotNullOfOrNull { FRAMES.matchEntire(it) }
                    val read = frames?.groupValues?.get(1)?.toLongOrNull() ?: 0
                    val wrote = out.any { it.startsWith("wrote ") && it.endsWith(".png") }
                    val picture = first("picture: ")
                    when {
                        exit == 0 && read > 0 && wrote && picture?.contains("(black") == true ->
                            fail("the picture is black: $picture", hint)
                        exit == 0 && read > 0 && wrote ->
                            pass(listOfNotNull("frames: $read read, ${frames!!.groupValues[2]} missed", first("fps: ")?.substringBefore(','), picture?.removePrefix("picture: ")).joinToString("; "))
                        else -> fail(out.lastOrNull { !it.startsWith("system_server:") } ?: "exit $exit", hint)
                    }
                } else {
                    val cameras = out.firstNotNullOfOrNull { CAMERAS.matchEntire(it) }
                    when {
                        exit == 0 && (cameras?.groupValues?.get(2)?.toIntOrNull() ?: 0) > 0 -> pass(cameras!!.value)
                        cameras != null -> fail(cameras.value, hint ?: "The back end answered with no camera.")
                        else -> fail(out.lastOrNull { !it.startsWith("system_server:") } ?: "exit $exit", hint)
                    }
                }
            }
            else -> if (exit == 0) pass(last.ifEmpty { "ok" }) else fail(last.ifEmpty { "exit $exit" })
        }
    }

    fun skipped(why: String) = OneiosCheckResult(OneiosCheckOutcome.SKIPPED, why)

    /** One check's log as text: its title, the verdict, the command and everything the tool printed. */
    fun log(check: OneiosCheck, result: OneiosCheckResult?, output: List<String>, maxChars: Int = 40_000): String = buildString {
        append("== ").append(check.title).append(" (").append(check.id).append("): ")
        append(result?.let { "${it.outcome.word.uppercase()}: ${it.line}" } ?: "not run").append('\n')
        result?.hint?.let { append("   ").append(it).append('\n') }
        append("$ ").append(check.command).append("   (limit ").append(check.limitSeconds).append(" s)\n")
        val text = output.joinToString("\n")
        if (text.length > maxChars) append(text, 0, maxChars).append("\n… (").append(text.length - maxChars).append(" more characters)")
        else append(text)
        if (output.isNotEmpty()) append('\n')
    }

    /** Every check's log in one text ("Share all"), under [header] (the app, the runtime, the phone). */
    fun report(header: List<String>, rows: List<Triple<OneiosCheck, OneiosCheckResult?, List<String>>>): String = buildString {
        append("OneiOS hardware checks\n")
        header.forEach { append(it).append('\n') }
        val done = rows.mapNotNull { it.second }
        append(done.count { it.outcome == OneiosCheckOutcome.PASS }).append(" passed, ")
        append(done.count { it.outcome == OneiosCheckOutcome.FAIL }).append(" failed, ")
        append(done.count { it.outcome == OneiosCheckOutcome.SKIPPED }).append(" skipped, ")
        append(rows.size - done.size).append(" not run\n\n")
        for ((c, r, o) in rows) append(log(c, r, o, 20_000)).append('\n')
    }
}
