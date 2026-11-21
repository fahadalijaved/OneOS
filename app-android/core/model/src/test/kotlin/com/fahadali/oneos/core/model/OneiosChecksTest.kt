package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The hardware checks' reading of each tool's output: what OneiOS's bridgectl,
 * gpuctl, displayctl, brightctl and camctl print (their sources and READMEs
 * there), and what root's `check` verb reports around it.
 */
class OneiosChecksTest {
    private fun check(id: String) = OneiosChecks.byId(id)!!

    private fun ran(id: String, exit: Int, text: String) =
        OneiosChecks.classify(check(id), OneiosChecks.Run(exit = exit, output = text.trimIndent().lines()))

    private fun assertPass(r: OneiosCheckResult, part: String = "") {
        assertEquals(r.toString(), OneiosCheckOutcome.PASS, r.outcome)
        assertTrue("'${r.line}' lacks '$part'", r.line.contains(part))
    }

    private fun assertFail(r: OneiosCheckResult, part: String, hint: String? = null) {
        assertEquals(r.toString(), OneiosCheckOutcome.FAIL, r.outcome)
        assertTrue("'${r.line}' lacks '$part'", r.line.contains(part))
        if (hint != null) assertTrue("'${r.hint}' lacks '$hint'", r.hint.orEmpty().contains(hint))
    }

    @Test
    fun theListNamesEveryPartOnce() {
        assertEquals(OneiosChecks.ALL.size, OneiosChecks.ALL.map { it.id }.toSet().size)
        for (id in listOf("cpu", "gpu", "display", "haptic", "haptic-pattern", "audio", "bt", "brightness", "levels", "als", "camera-list", "camera")) {
            assertTrue(id, OneiosChecks.RUN_ALL.any { it.id == id })
        }
        // The HAL rows are there, marked experimental, and not part of Run all.
        assertTrue(check("camera-hal").experimental && check("camera-hal-list").experimental)
        assertTrue(OneiosChecks.RUN_ALL.none { it.experimental })
        // Every check has a time limit, and what the owner has to know is said for the ones that show, sound or need something.
        assertTrue(OneiosChecks.ALL.all { it.limitSeconds in 5..120 })
        // gpuctl with no argument runs all its steps (nodes, routes, probe, submit, large) from runtime 0.1.5.
        assertEquals(120, check("gpu").limitSeconds)
        for (id in listOf("display", "haptic", "haptic-pattern", "audio", "bt", "levels", "als", "camera", "camera-hal")) assertNotNull(id, check(id).notice)
        assertTrue(check("bt").notice!!.contains("Bluetooth has to be off"))
        assertTrue(check("levels").notice!!.contains("Adaptive brightness has to be off"))
        assertTrue(check("display").notice!!.contains("Colour bars"))
        assertTrue(check("camera").notice!!.contains("camera is used"))
        assertTrue(check("camera").picture && check("camera-hal").picture)
    }

    @Test
    fun rootsAnswerIsRead() {
        val lines = listOf("| host: 8 CPUs, 6 P, 2 E", "|", "| ok", "something else")
        val run = OneiosChecks.parseRun("cpu", listOf("check cpu exit 0"), lines)!!
        assertEquals(0, run.exit)
        assertEquals(listOf("host: 8 CPUs, 6 P, 2 E", "", "ok"), run.output)
        assertEquals("gpuctl", OneiosChecks.parseRun("gpu", listOf("check gpu missing gpuctl"), emptyList())!!.missing)
        assertEquals(30, OneiosChecks.parseRun("levels", listOf("check levels timeout 30"), emptyList())!!.timeoutSeconds)
        // Another check's line, or none, is no result.
        assertNull(OneiosChecks.parseRun("cpu", listOf("check gpu exit 0"), lines))
        assertNull(OneiosChecks.parseRun("cpu", listOf("check cpu exit x"), lines))
        assertNull(OneiosChecks.parseRun("cpu", emptyList(), lines))
    }

    @Test
    fun aMissingToolIsSkippedAndAHungOneFails() {
        val missing = OneiosChecks.classify(check("camera"), OneiosChecks.Run(missing = "camctl"))
        assertEquals(OneiosCheckOutcome.SKIPPED, missing.outcome)
        assertEquals("Not in this runtime: bin/camctl", missing.line)
        val hung = OneiosChecks.classify(check("levels"), OneiosChecks.Run(timeoutSeconds = 30, output = listOf("slider   5% -> wanted 3, the node was written 3")))
        assertFail(hung, "Ended after 30 s", "put back")
        assertTrue(hung.line.contains("slider   5%"))
        assertFail(OneiosChecks.classify(check("gpu"), OneiosChecks.Run()), "No result")
        assertFail(ran("gpu", 137, "/dev/kgsl-3d0            opens"), "signal 9")
    }

    @Test
    fun bridgectl() {
        assertPass(
            ran(
                "cpu", 0,
                """
                host: 8 CPUs, 6 P, 2 E
                  cpu0: E capacity 325 part 0xd80 policy 0 364800..2265600 kHz (11 steps) L1d 32768 L2 131072 L3 12582912
                plan: 8 vCPUs, 2 E then 6 P
                  vcpu0: E cluster 0 host mask 0x3 capacity 325 max 2265600 kHz
                placing this thread as vcpu7: done
                uclamp.min 1024 for the top frequency: done
                ok
                """,
            ),
            "host: 8 CPUs, 6 P, 2 E; plan: 8 vCPUs, 2 E then 6 P",
        )
        assertFail(ran("cpu", 1, "no CPUs under /sys/devices/system/cpu\nfailed"), "failed: no CPUs under /sys/devices/system/cpu")
        assertPass(ran("haptic", 0, "ok"), "ok")
        assertFail(ran("haptic", 1, "haptic: no force-feedback device named sec_vibrator_inputff\nfailed"), "failed: haptic: no force-feedback device")
        assertFail(ran("haptic-pattern", 1, "failed"), "failed")
        assertPass(ran("audio", 0, "ok"))
        // "ok" with a non-zero exit, or a zero exit without "ok", is not a pass.
        assertFail(ran("audio", 1, "ok"), "ok")
        assertFail(ran("audio", 0, ""), "exit 0")
        assertFail(ran("audio", 2, "unknown command"), "unknown command", "newer runtime")
        assertPass(
            ran(
                "bt", 0,
                """
                address file: 12:34:56:78:9a:bc
                  state 1
                  <- type 4, 6 bytes: 0e 04 01 03 0c 00
                  <- type 4, 12 bytes: 0e 0a 01 09 10 00 bc 9a 78 56 34 12
                ok
                """,
            ),
            "ok: 2 HCI events, address file: 12:34:56:78:9a:bc",
        )
        assertFail(ran("bt", 1, "the HAL did not become ready (state -1)\nfailed"), "failed: the HAL did not become ready (state -1)", "Bluetooth off")
        assertFail(ran("bt", 1, "  <- type 4, 6 bytes: 0e 04 01 03 0c 00\nsend 0, 1 events (2 expected)\nfailed"), "send 0, 1 events")
    }

    @Test
    fun gpuctl() {
        assertPass(
            ran(
                "gpu", 0,
                """
                /dev/kgsl-3d0          opens
                capset: DRM (6), 64 bytes: wire format 2, msm 1.12, context type 1, chip 0x43050a01, gpu id 750
                context 1: response buffer at pool offset 0x1000 (cache mode 1), responses from byte 0
                submit: queue 1, 256 bytes of commands at 0x100000000 run by the GPU, fence retired after 1.20 ms; GPU faults 0, async errors 0
                ok
                """,
            ),
            "ok",
        )
        assertFail(ran("gpu", 1, "/dev/kgsl-3d0          Permission denied\nFAILED at: the device nodes"), "FAILED at: the device nodes")
        assertFail(
            ran("gpu", 1, "capset: DRM (6), 64 bytes\nFAILED at: buffer import: /dev/udmabuf: No such file or directory"),
            "FAILED at: buffer import: /dev/udmabuf: No such file or directory",
        )
        // Lines after the failure (a log line) do not hide it.
        assertFail(ran("gpu", 1, "FAILED at: submit: the fence never retired\n  ERROR kgsl: timeout"), "FAILED at: submit")
        assertFail(ran("gpu", 2, "usage: gpuctl [nodes|probe|submit] [-v]"), "usage", "newer runtime")
    }

    @Test
    fun displayctl() {
        assertPass(
            ran(
                "display", 0,
                """
                oneios-display: guest frame 1320x2868, panel 1440x3120
                displayctl: helper 12345 connected; 1320x2868 pattern for 5.0 s
                displayctl: 300 frames in 5.01 s
                displayctl: the helper removed its layer and exited 0
                displayctl: ok
                """,
            ),
            "ok: 300 frames in 5.01 s",
        )
        assertFail(
            ran("display", 1, "displayctl: the helper ended before it connected (status 256)\ndisplayctl: FAILED"),
            "displayctl: the helper ended before it connected (status 256)",
        )
        assertFail(ran("display", 1, "displayctl: the helper did not connect\ndisplayctl: FAILED"), "the helper did not connect")
        // A set-up error is exit 2 with one line, and is its own reason (not "a newer runtime").
        val setup = ran("display", 2, "displayctl: /data/local/tmp/oneios/runtime/bin/oneios-display: No such file or directory")
        assertFail(setup, "oneios-display: No such file or directory")
        assertNull(setup.hint)
    }

    @Test
    fun brightctl() {
        val info = """
            panel: /sys/class/backlight/panel/brightness  max_brightness 510, slider range 1..255, One UI's value 97
            light sensor: /dev/input/event9
            brightctl: ok
        """
        assertPass(ran("brightness", 0, info), "panel: /sys/class/backlight/panel/brightness  max_brightness 510")
        // The tool says ok when it found only the sensor: the brightness row still fails.
        assertFail(ran("brightness", 0, "panel: no backlight device\nlight sensor: /dev/input/event9\nbrightctl: ok"), "panel: no backlight device")
        assertFail(ran("brightness", 1, "brightctl: failed: no backlight device and no light sensor"), "brightctl: failed: no backlight device and no light sensor")
        assertPass(
            ran(
                "levels", 0,
                """
                slider   5% -> wanted 1, the node was written 1
                slider  25% -> wanted 16, the node was written 16
                slider 100% -> wanted 255, the node was written 255
                restored 97
                brightctl: ok
                """,
            ),
            "ok: 3 steps, restored 97",
        )
        assertFail(ran("levels", 0, "slider   5% -> wanted 1, the node was written 1\nrestored 97\nbrightctl: stopped"), "stopped before the last step, restored 97")
        assertFail(ran("levels", 1, "brightctl: failed: no writable backlight device"), "no writable backlight device")
        assertPass(
            ran(
                "als", 0,
                """
                light sensor: /dev/input/event9
                 12345.678  clear 12       ir 3        uv 1        -> 12.000 lux
                7 readings in 10 s
                brightctl: ok
                """,
            ),
            "7 readings in 10 s",
        )
        assertFail(
            ran("als", 1, "0 readings in 10 s\nbrightctl: failed: the sensor sent nothing (is its enable file writable?)"),
            "the sensor sent nothing", "sent nothing",
        )
        assertFail(ran("als", 1, "brightctl: failed: no light sensor (no input device named als_rear)"), "no input device named als_rear")
        assertFail(ran("als", 2, "usage: brightctl info | levels [--ms N] [PERCENT...] | als [SECONDS]"), "usage")
    }

    @Test
    fun camctl() {
        assertPass(
            ran(
                "camera-list", 0,
                """
                system_server: running (One UI's framework is up)
                back end: ndk, 4 cameras
                 0  id 0    wide      back   6.30 mm (35 mm equivalent  24)  sensor 4000x3000  turned  90
                      YUV sizes: 1920x1080 1280x720 (30 in all)
                      fps ranges: 15-30 30-30
                """,
            ),
            "back end: ndk, 4 cameras",
        )
        assertFail(ran("camera-list", 0, "system_server: running (One UI's framework is up)\nback end: ndk, 0 cameras"), "0 cameras", "no camera")
        assertFail(
            ran("camera-hal-list", 1, "system_server: running\nhal: no service android.hardware.camera.provider.ICameraProvider/internal/0\nhal: no camera list: No such device"),
            "no camera list", "another instance name",
        )
        val good = ran(
            "camera", 0,
            """
            system_server: running (One UI's framework is up)
            back end: ndk, 4 cameras
            camera: id 0 (wide), asked 1280x720 at 30 fps, got 1280x720 at 30 fps
            frames: 90 read, 0 missed by the reader; first frame 412 ms after the start
            fps: 30.00 by the sensor's time, 29.87 read (wall clock)
            picture: 1280x720 NV12, sequence 90, mean luma 97.3
            wrote /data/local/tmp/oneios/checks/camera.png
            """,
        )
        assertPass(good, "frames: 90 read, 0 missed; fps: 30.00 by the sensor's time; 1280x720 NV12, sequence 90, mean luma 97.3")
        // The README's table of what can go wrong.
        assertFail(
            ran("camera", 1, "back end: ndk, 4 cameras\nndk: openCamera failed for 0: status -10013\nndk: camera 0 did not start: Permission denied"),
            "did not start", "cameraserver could not ask system_server",
        )
        assertFail(
            ran("camera-hal", 1, "back end: hal, 9 cameras\nhal: open: exception -8, camera status 2\nhal: camera 0 did not start: Device or resource busy"),
            "did not start", "in use",
        )
        assertFail(
            ran("camera-hal", 1, "back end: hal, 9 cameras\nhal: configureStreams failed: exception -8, status 1\nhal: camera 0 did not start: Invalid argument"),
            "did not start", "refused the stream",
        )
        assertFail(ran("camera-hal", 1, "back end: hal, 9 cameras\ncamera: id 0 (wide), asked 1280x720\nno frame arrived"), "no frame arrived", "calls back into camctl")
        assertNull(ran("camera", 1, "back end: ndk, 4 cameras\nno frame arrived").hint)
        assertFail(
            ran(
                "camera", 0,
                """
                frames: 90 read, 0 missed by the reader; first frame 400 ms after the start
                fps: 30.00 by the sensor's time
                picture: 1280x720 NV12, sequence 90, mean luma 0.4 (black: is the lens covered?)
                wrote /data/local/tmp/oneios/checks/camera.png
                """,
            ),
            "the picture is black", "lens is covered",
        )
        // Frames without a written picture, or an exit code that is not 0, is not a pass.
        assertFail(ran("camera", 1, "frames: 90 read, 0 missed by the reader; first frame 400 ms after the start\n/x.png: Read-only file system"), "Read-only file system")
        assertFail(ran("camera", 0, "frames: 0 read, 0 missed by the reader"), "frames: 0 read")
        assertFail(ran("camera", 1, "no camera 'wide' (camctl list shows them)"), "no camera 'wide'")
    }

    @Test
    fun theLogsAreOneText() {
        val cpu = check("cpu")
        val r = OneiosCheckResult(OneiosCheckOutcome.PASS, "host: 8 CPUs")
        val log = OneiosChecks.log(cpu, r, listOf("host: 8 CPUs, 6 P, 2 E", "ok"))
        assertTrue(log.startsWith("== CPU layout (cpu): PASS: host: 8 CPUs\n$ bridgectl cpu   (limit 15 s)\nhost: 8 CPUs, 6 P, 2 E\nok\n"))
        assertTrue(OneiosChecks.log(cpu, null, emptyList()).contains("not run"))
        assertTrue(OneiosChecks.log(cpu, r, listOf("x".repeat(500)), maxChars = 100).contains("(400 more characters)"))
        val all = OneiosChecks.report(
            listOf("OneOS 0.4.75, OneiOS runtime 0.1.0"),
            OneiosChecks.ALL.map { c ->
                when (c.id) {
                    "cpu" -> Triple(c, r, listOf("ok"))
                    "gpu" -> Triple(c, OneiosCheckResult(OneiosCheckOutcome.FAIL, "FAILED at: the device nodes", null), listOf("FAILED at: the device nodes"))
                    "bt" -> Triple(c, OneiosChecks.skipped("Bluetooth is on"), emptyList())
                    else -> Triple(c, null, emptyList())
                }
            },
        )
        assertTrue(all.startsWith("OneiOS hardware checks\nOneOS 0.4.75, OneiOS runtime 0.1.0\n1 passed, 1 failed, 1 skipped, ${OneiosChecks.ALL.size - 3} not run\n"))
        for (c in OneiosChecks.ALL) assertTrue(c.id, all.contains("== ${c.title} (${c.id}): "))
        assertTrue(all.contains("FAIL: FAILED at: the device nodes") && all.contains("SKIPPED: Bluetooth is on"))
    }
}
