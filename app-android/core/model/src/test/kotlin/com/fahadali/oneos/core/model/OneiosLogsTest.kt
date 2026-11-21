package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The reading of an xnuhost session log. The lines are xnuhost's own
 * (`runtime/xnuhost/src` in OneiOS: `xh_log`, `xh_log_raw`, `xh_log_signal`,
 * main.c's `stopping:` and `exit`) and the iOS kernel's console as OneiOS's
 * boots on the PC logged it (its `logs/fb-boot.log`, `logs/keystore-boot*.log`),
 * shortened; and `return.log` is what `oneios_return.sh` and the watcher write.
 */
class OneiosLogsTest {
    private fun log(text: String) = text.trimIndent().lines()

    private val start = """
        [286239.524] xnuhost I xnuhost: session ABI 1, mode takeover, pid 4146179
        [286239.549] xnuhost I host: page 4096, user VA 47 bits, counter 62500000 Hz, PAC yes, keys shared across fork and threads
        [286239.577] xnuhost I tasks: factory pid 4146187, stub region 0x7e00000000, stub 3272 bytes, filter 0 instructions
        [286239.901] xnuhost I placed: entry 0x2003dcc488, boot_args 0x2005924000, device tree 17032 bytes, 89 MiB of the window used; boot-args "debug=0x14e serial=3 -v -no_slto_panic ml-timeout-lock-panic-scale=40"
        [286239.909] xnuhost I cpu0: entering the kernel at 0x2003dcc488
        [286240.068] guest     Darwin Kernel Version 25.5.0: Wed Nov 11 04:04:41 IST 2026; akshay:ios-obj/DEVELOPMENT_ARM64_BCM2837
        [286241.714] guest     pmap_startup() init/release time: 1542521 microsec
        [286719.931] guest     debug_log_init: Error!! gPanicBase is still not initialized
    """

    private val toLaunchd = """
        [286727.194] guest     BSD root: disk8s1, major 1, minor 12
        [286727.203] guest     apfs_vfsop_mountroot:3156: apfs: mountroot called!
        [286727.938] guest     load_init_program: attempting to load /usr/appleinternal/sbin/launchd.development
        [286728.026] guest     load_init_program: attempting to load /sbin/launchd
        [287612.623] guest     com.apple.xpc.launchd|2026-11-10 15:05:22.422484 <Notice>: hello, launchd UUID: CA54230D-4005-3131-8DC3-CCB7E7EF18E6
        [287613.277] guest     com.apple.xpc.launchd|2026-11-10 15:05:23.202667 (fsck) <Notice>: Doing boot task
    """

    private val cpus = """
        [287167.934] xnuhost I cpu0: started, 40010 interrupts (96084 timer, 8620 IPI acknowledged, 518 re-raised), 20319 device accesses, 2095093 emulated instructions, 391320 task traps
        [287167.935] xnuhost I cpu1: started, 35650 interrupts (88048 timer, 8412 IPI acknowledged, 232 re-raised), 17874 device accesses, 559250 emulated instructions, 354714 task traps
    """

    @Test
    fun aBootThatPanicsAfterSpringBoard() {
        val s = OneiosLogs.summarize(
            log(start) + log(toLaunchd) + log(
                """
                [286981.700] guest     oneios-display: framebuffer opened by backboardd[53], type 0: status 0, client IOMobileFramebufferUserClient
                [286981.831] guest     [backboardd: killed] exiting with signal 9, force exiting the process
                [286981.838] guest     sheng-exit: backboardd[53] status 0x9 reason ns 19 code 0x1: (no description)
                [286982.302] guest     Process[53] crashed: backboardd. Too many corpses being created.
                [286742.807] guest     sheng-exit: chronod[86] status 0x6 reason ns 2 code 0x6: (no description)
                [288183.351] guest     [audiomxd: killed] exiting with signal 9, force exiting the process
                [288183.451] guest     Text page corruption detected for pid 96
                [288183.453] guest     Process[96] crashed: audiomxd. Too many corpses being created.
                [288185.375] guest     Process[120] crashed: SpringBoard. Too many corpses being created.
                [288194.264] guest     SpringBoard[124] triggered unnest of range 0x1e9c00000->0x1ebe00000 of DYLD shared region in VM map 0x1f562c5cb686e731.
                [288205.541] guest     sheng-exit: SpringBoard[124] status 0x5 reason ns 2 code 0x5: (no description)
                [288205.543] guest     Process[124] crashed: SpringBoard. Too many corpses being created.
                [288206.000] guest     sheng-exit: SpringBoard[130] status 0x5 reason ns 2 code 0x5: (no description)
                [288192.000] xnuhost E tasks: pid 152686: order 1 (va 0x191e49000, size 0x1000, prot 5) took long: answered after 1 s
                [287167.735] guest     panic(cpu 1 caller 0xfffffff00ad8d2c4): Console I/O from interrupt-disabled context @serial_console.c:175
                [287167.737] guest       frame 0xfffffff00b4aa0cc
                [287167.934] xnuhost I stopping: the guest halted on cpu1 (reason 2, code 0)
                """,
            ) + log(cpus) + "[287168.353] xnuhost I exit 4",
        )
        assertEquals(OneiosBootStage.SPRINGBOARD, s.stage)
        assertTrue(s.stages.containsAll(listOf(OneiosBootStage.HOST, OneiosBootStage.KERNEL_ENTERED, OneiosBootStage.KERNEL, OneiosBootStage.ROOT,
            OneiosBootStage.INIT, OneiosBootStage.LAUNCHD, OneiosBootStage.BACKBOARDD)))
        assertFalse(OneiosBootStage.READY in s.stages)
        assertEquals("Console I/O from interrupt-disabled context @serial_console.c:175", s.panic)
        assertEquals(1, s.panics)
        assertEquals(OneiosEndKind.PANIC, s.end.kind)
        assertEquals(4, s.end.exitCode)
        assertEquals("exit 4 · kernel panic", s.end.short)
        assertTrue(s.end.text, s.end.text.contains("Kernel panic: Console I/O") && s.end.text.contains("xnuhost exit 4 (kernel panic or kernel fault)"))
        // Each death once: three lines of one backboardd are one death; SpringBoard's three pids are three, two with a signal.
        val deaths = s.deaths.associateBy { it.name }
        assertEquals(setOf("SpringBoard", "backboardd", "chronod", "audiomxd"), deaths.keys)
        assertEquals(OneiosLogs.Death("SpringBoard", 3, mapOf(5 to 2)), deaths["SpringBoard"])
        assertEquals(OneiosLogs.Death("backboardd", 1, mapOf(9 to 1)), deaths["backboardd"])
        assertEquals(OneiosLogs.Death("chronod", 1, mapOf(6 to 1)), deaths["chronod"])
        assertEquals(OneiosLogs.Death("audiomxd", 1, mapOf(9 to 1)), deaths["audiomxd"])
        assertEquals("SpringBoard ×3 (SIGTRAP ×2)", deaths.getValue("SpringBoard").text)
        assertEquals("backboardd ×1 (SIGKILL)", deaths.getValue("backboardd").text)
        assertEquals("SpringBoard", s.deaths.first().name)
        assertEquals(1, s.errors)
        val text = OneiosLogs.summaryLines(s).joinToString("\n")
        assertTrue(text, text.contains("Boot got to: SpringBoard (8 of 9)"))
        assertTrue(text, text.contains("Processes that died: SpringBoard ×3 (SIGTRAP ×2), "))
        assertTrue(text, text.contains("Ended: Kernel panic"))
    }

    @Test
    fun anEarlyPanicStopsAtTheKernel() {
        val s = OneiosLogs.summarize(
            log(start) + log(
                """
                [257833.321] guest     Security policy loaded: Guarded vnode policy (vnguard)
                [257833.321] guest     panic(cpu 0 caller 0xfffffff0078c62dc): image4 interface not available @kern_trustcache.c:592
                [257833.322] guest       frame 0xfffffff007bf8ed0
                [257833.383] xnuhost I stopping: the guest halted on cpu0 (reason 2, code 0)
                [257833.541] xnuhost I exit 4
                exit 4
                """,
            ),
        )
        assertEquals(OneiosBootStage.KERNEL, s.stage)
        assertEquals("image4 interface not available @kern_trustcache.c:592", s.panic)
        assertTrue(s.deaths.isEmpty())
        assertTrue(OneiosLogs.summaryLines(s).any { it == "Processes that died: none reported" })
    }

    @Test
    fun aReadySessionEndedByTheReturnsSigterm() {
        val body = log(start) + log(toLaunchd) + log(
            """
            [286240.062] xnuhost I display: a helper connected
            [288300.000] guest     backboardd[61] triggered unnest of range 0x1e9c00000->0x1ebe00000 of DYLD shared region in VM map 0x1f562c5cb6794fa1.
            [288301.000] xnuhost I guest ready: first frame
            [288400.000] xnuhost I stopping: signal 15 (reason 0, code 0)
            """,
        ) + log(cpus) + "[288400.200] xnuhost I exit 0"
        val notes = OneiosLogs.returns(
            log(
                """
                2026-11-11 10:15:02 watcher: return asked (keys: Volume Up + Volume Down down for 3 s at 2026-11-11 10:15:01); returning to One UI
                10:15:02 === Return to One UI (watcher), session state 'running', boot 1b2c ===
                10:15:02 SIGTERM to xnuhost 4242 (20 s to end its tasks and flush the guest's data)
                10:15:40 One UI restored in place (Enforcing).
                """,
            ),
        )
        assertEquals(1, notes.size)
        assertTrue(notes[0].keys)
        val note = OneiosLogs.returnFor(notes, "2026-11-11", 10 * 3600 + 15 * 60 + 3, newest = false)
        assertNotNull(note)
        val s = OneiosLogs.summarize(body, returned = note)
        assertEquals(OneiosBootStage.READY, s.stage)
        assertEquals(OneiosEndKind.STOP_SIGNAL, s.end.kind)
        assertEquals(15, s.end.signal)
        assertEquals(0, s.end.exitCode)
        assertNull(s.panic)
        assertTrue(s.end.text, s.end.text.contains("Stopped by SIGTERM") && s.end.text.contains("xnuhost exit 0"))
        assertTrue(s.end.text, s.end.text.contains("Return: the watcher: return asked (keys: Volume Up + Volume Down down for 3 s at 2026-11-11 10:15:01); One UI restored in place (Enforcing)."))
        // SpringBoard was never named: not seen on the way is said only of stages before the furthest.
        assertFalse(OneiosBootStage.SPRINGBOARD in s.stages)
        assertTrue(OneiosLogs.summaryLines(s).any { it == "Not seen on the way: SpringBoard" })
    }

    @Test
    fun howASessionEnds() {
        fun end(text: String) = OneiosLogs.summarize(log(start) + log(text)).end
        // The guest shut down, or asked to return.
        end("[1.000] xnuhost I stopping: PSCI SYSTEM_OFF (reason 0, code 0)\n[1.100] xnuhost I exit 0").let {
            assertEquals(OneiosEndKind.GUEST_OFF, it.kind); assertEquals("exit 0 · the guest shut down", it.short)
        }
        end("[1.000] xnuhost I stopping: the guest halted on cpu2 (reason 3, code 0)\n[1.100] xnuhost I exit 0").let {
            assertEquals(OneiosEndKind.GUEST_RETURN, it.kind)
        }
        // A restart that could not be done: exit 3.
        end(
            """
            [1.000] xnuhost I stopping: PSCI SYSTEM_RESET (reason 1, code 0)
            [1.050] xnuhost E the guest restarted 8 times without getting ready: not starting it again
            [1.100] xnuhost I exit 3
            """,
        ).let {
            assertEquals(OneiosEndKind.RESTART_FAILED, it.kind); assertEquals(3, it.exitCode)
            assertTrue(it.text, it.text.contains("kept restarting without getting ready"))
        }
        // A kernel fault the kernel did not take: lines from signal context, then the stop.
        end(
            """
            xnuhost !! kernel fault with no exception upcall: signal, address 0x000000000000000b 0x0000000000000010
            xnuhost !!   pc, sp 0x0000002003dcc488 0x0000002005924000
            [2.000] xnuhost I stopping: kernel fault (reason 2, code 0)
            [2.100] xnuhost I exit 4
            """,
        ).let { assertEquals(OneiosEndKind.KERNEL_FAULT, it.kind); assertEquals("exit 4 · kernel fault", it.short) }
        // A fault in xnuhost's own code: it re-raises the signal, so there is no exit line.
        end(
            """
            xnuhost !! fault inside a host call: signal, address 0x000000000000000b 0x0000000000000000
            xnuhost !!   pc, sp 0x00000055aa001234 0x0000007fff000000
            xnuhost !!   x30, esr 0x00000055aa001200 0x0000000092000046
            """,
        ).let {
            assertEquals(OneiosEndKind.HOST_FAULT, it.kind); assertEquals(11, it.signal); assertNull(it.exitCode)
            assertTrue(it.text, it.text.contains("xnuhost crashed: SIGSEGV, a fault inside a host call"))
        }
        // Another stop of xnuhost's own is named as it is, not as a panic.
        end("[1.000] xnuhost I stopping: the task factory is gone (reason 2, code 0)\n[1.100] xnuhost I exit 4").let {
            assertEquals(OneiosEndKind.HOST_STOP, it.kind); assertTrue(it.text.contains("xnuhost stopped: the task factory is gone"))
        }
        // SIGTERM, then killed before it finished stopping.
        end("[1.000] xnuhost I stopping: signal 15 (reason 0, code 0)").let {
            assertEquals(OneiosEndKind.STOP_SIGNAL, it.kind); assertTrue(it.text, it.text.contains("no exit line after it"))
        }
        // No end at all: killed, a restart of the phone, or still running.
        end("[1.000] guest     tx_flush:1185: disk6 tx xid 74 took 2257291 us to flush").let {
            assertEquals(OneiosEndKind.UNKNOWN, it.kind); assertEquals("no end line", it.short)
        }
        // Setup: xnuhost never entered the kernel (exit 2 has no line of its own).
        OneiosLogs.summarize(
            log(
                """
                [5.000] xnuhost I xnuhost: session ABI 1, mode takeover, pid 77
                [5.100] xnuhost E cannot read the kernel collection /data/image/overlay/kernel.kc: No such file or directory
                """,
            ),
        ).let {
            assertEquals(OneiosBootStage.HOST, it.stage)
            assertEquals(OneiosEndKind.SETUP, it.end.kind)
            assertTrue(it.end.text, it.end.text.contains("cannot read the kernel collection"))
        }
    }

    @Test
    fun aGuestRestartInPlaceStartsANewBoot() {
        val s = OneiosLogs.summarize(
            log(start) + log(toLaunchd) + log(
                """
                [100.000] guest     sheng-exit: mobileassetd[40] status 0x9 reason ns 2 code 0x9: (no description)
                [101.000] xnuhost I stopping: PSCI SYSTEM_RESET (reason 1, code 0)
                [101.500] xnuhost I the guest asked for a restart: starting again (1)
                """,
            ) + log(start) + log(
                """
                [150.000] guest     sheng-exit: mobileassetd[40] status 0x9 reason ns 2 code 0x9: (no description)
                [160.000] xnuhost I stopping: signal 15 (reason 0, code 0)
                [160.100] xnuhost I exit 0
                """,
            ),
        )
        assertEquals(1, s.restarts)
        assertEquals(OneiosBootStage.LAUNCHD, s.stage)
        assertEquals(OneiosBootStage.KERNEL, s.lastBootStage)
        // The same pid in the next boot is another process.
        assertEquals(2, s.deaths.single().count)
        // The end is the last boot's.
        assertEquals(OneiosEndKind.STOP_SIGNAL, s.end.kind)
        assertTrue(OneiosLogs.summaryLines(s).first().contains("the last boot got to kernel start"))
    }

    @Test
    fun onlyTheEndOfALogSaysSo() {
        val s = OneiosLogs.summarize(log("[9.000] guest     x\n[9.100] xnuhost I stopping: signal 15 (reason 0, code 0)\n[9.200] xnuhost I exit 0"), complete = false)
        assertNull(s.stage)
        assertTrue(OneiosLogs.summaryLines(s).last().contains("Only the end of the log has been read"))
        assertEquals("exit 0 · stopped by SIGTERM", OneiosLogs.endLine(log("[9.100] xnuhost I stopping: signal 15 (reason 0, code 0)\n[9.200] xnuhost I exit 0")))
        // With no end line the row shows the log's last line, without its time.
        assertEquals("guest     tx_flush:1185: disk6 tx xid 74", OneiosLogs.endLine(listOf("[287165.221] guest     tx_flush:1185: disk6 tx xid 74", "")))
        assertEquals("empty", OneiosLogs.endLine(emptyList()))
    }

    @Test
    fun theFilterChips() {
        val lines = log(start) + log(
            """
            [288192.000] xnuhost E tasks: pid 152686: order 1 (va 0x191e49000, size 0x1000, prot 5) took long: answered after 1 s
            xnuhost !! kernel fault with no exception upcall: signal, address 0x000000000000000b 0x0000000000000010
            [287167.735] guest     panic(cpu 1 caller 0xfffffff00ad8d2c4): Console I/O from interrupt-disabled context @serial_console.c:175
            === oneios_switch.sh --inner ===
            """,
        )
        fun shown(vararg f: OneiosLogFilter, query: String = "") = lines.filter { OneiosLogs.shown(it, f.toSet(), query) }
        assertEquals(lines, shown())
        assertEquals(1, shown(OneiosLogFilter.ERRORS).size)
        assertEquals(1, shown(OneiosLogFilter.SIGNAL).size)
        // The word panic, not the boot arguments' -no_slto_panic or the console's gPanicBase.
        assertEquals(listOf(lines[lines.size - 2]), shown(OneiosLogFilter.PANIC))
        assertEquals(4, shown(OneiosLogFilter.GUEST).size)
        // Chips add up; the search narrows.
        assertEquals(2, shown(OneiosLogFilter.ERRORS, OneiosLogFilter.SIGNAL).size)
        assertEquals(1, shown(OneiosLogFilter.GUEST, query = "darwin kernel").size)
        assertEquals(OneiosLogs.Source.OTHER, OneiosLogs.source(lines.last()))
        assertEquals(OneiosLogs.Source.HOST_INFO, OneiosLogs.source("[     5.001] xnuhost I host: page 4096"))
        assertEquals("xnuhost I host: page 4096", OneiosLogs.body("[     5.001] xnuhost I host: page 4096"))
    }

    @Test
    fun whatRootPrintsForTheList() {
        val l = OneiosLogs.parseList(
            listOf("session none", "log session 138976 1794357280", "log xnuhost-1794300000 80565 1794300100", "log xnuhost-1794350000 10 1794350100",
                "log return 3 1794357290", "log bogus 1 1", "log ../x 1 1", "log switch x 1"),
            listOf("| session [287168.353] xnuhost I exit 4", "| xnuhost-1794300000 [1.000] guest     a b", "| return a", "| return", "| other x", "noise"),
        )
        assertFalse(l.sessionOpen)
        assertEquals(listOf("session", "xnuhost-1794350000", "xnuhost-1794300000", "return"), l.files.map { it.id })
        assertEquals(listOf("[287168.353] xnuhost I exit 4"), l.files[0].tail)
        assertEquals(listOf("[1.000] guest     a b"), l.sessions[2].tail)
        assertEquals(listOf("a", ""), l.others.single().tail)
        assertEquals(138976L, l.files[0].bytes)
        assertTrue(OneiosLogs.parseList(listOf("session open"), emptyList()).sessionOpen)
        // Six earlier logs: the five newest.
        val many = OneiosLogs.parseList((1..7).map { "log xnuhost-170000000$it 1 1" }, emptyList())
        assertEquals((7 downTo 3).map { "xnuhost-170000000$it" }, many.files.map { it.id })
        for (id in listOf("session", "switch", "return", "display", "feeder", "xnuhost-1794300000")) assertTrue(id, OneiosLogs.validId(id))
        for (id in listOf("", "xnuhost-", "xnuhost-1a", "xnuhost.log", "../return", "control", "checks")) assertFalse(id, OneiosLogs.validId(id))
        assertEquals("session/xnuhost.log", OneiosLogs.path("session"))
        assertEquals("logs/xnuhost-5.log", OneiosLogs.path("xnuhost-5"))
        assertEquals("control/watchdog_feeder.log", OneiosLogs.path("feeder"))
    }

    @Test
    fun whatRootPrintsForAChunk() {
        val c = OneiosLogs.parseChunk("session", listOf("chunk session 138976 138765 138976"), listOf("| [1.000] guest     a", "| ", "|", "| | piped", "@@OK logfile session"))!!
        assertEquals(138765L, c.start)
        assertEquals(138976L, c.end)
        assertFalse(c.first)
        assertEquals(listOf("[1.000] guest     a", "", "", "| piped"), c.lines)
        assertTrue(OneiosLogs.parseChunk("return", listOf("chunk return 3 0 3"), listOf("| a"))!!.first)
        assertNull(OneiosLogs.parseChunk("session", listOf("chunk return 3 0 3"), emptyList()))
        assertNull(OneiosLogs.parseChunk("session", listOf("chunk session 10 8 4"), emptyList()))
        assertNull(OneiosLogs.parseChunk("session", listOf("chunk session 9999999 0 9999999"), emptyList()))
    }

    @Test
    fun theReturnsOfReturnLog() {
        val notes = OneiosLogs.returns(
            log(
                """
                2026-11-10 23:59:30 watcher: xnuhost 4242 ended (last log lines: [1.0] xnuhost I exit 4|); returning to One UI
                23:59:30 === Return to One UI (watcher), session state 'running', boot 1b2c ===
                23:59:58 One UI restored in place (Enforcing).
                08:00:00 === Return to One UI (app), session state 'running', boot 1b2c ===
                08:00:05 FAILSAFE: surfaceflinger did not come back - rebooting into One UI instead
                2026-11-11 09:00:00 watcher: the guest did not report ready within 600s; returning to One UI
                09:00:00 === Return to One UI (watcher), session state 'running', boot 77aa ===
                2026-11-11 09:30:00 keys: the watcher did not start the return within 5 s of 'keys: Volume Up + Volume Down down for 3 s'; starting it from the key reader
                09:30:00 === Return to One UI (keys-direct), session state 'running', boot 77aa ===
                09:30:20 One UI restored in place (Enforcing).
                09:40:00 === Return to One UI (app), session state 'returned', boot 77aa ===
                09:40:00 no open session (state 'returned'): nothing to return from
                09:41:00 === Return to One UI (manual), session state 'returning', boot 77aa ===
                09:41:00 another return is already running (pid 812); leaving it to it
                """,
            ),
        )
        // A return that found no open session, or another at work, is not one.
        assertEquals(listOf("watcher", "app", "watcher", "keys-direct"), notes.map { it.who })
        assertEquals("2026-11-10", notes[0].date)
        assertTrue(notes[0].why!!.startsWith("xnuhost 4242 ended"))
        assertEquals("One UI restored in place (Enforcing).", notes[0].result)
        assertNull(notes[1].date)
        assertEquals("Back to One UI in the app; FAILSAFE: surfaceflinger did not come back - rebooting into One UI instead", notes[1].text)
        assertEquals("the guest did not report ready within 600s", notes[2].why)
        assertNull(notes[2].result)
        assertTrue(notes[3].keys)
        // By the time of the log's last line, within two minutes, across midnight too; a dated return only on its day.
        assertEquals(notes[1], OneiosLogs.returnFor(notes, "2026-11-11", 8 * 3600 + 1, newest = false))
        assertEquals(notes[0], OneiosLogs.returnFor(notes, "2026-11-11", 5, newest = false))
        assertNull(OneiosLogs.returnFor(notes, "2026-11-12", 9 * 3600, newest = false))
        assertEquals(notes[2], OneiosLogs.returnFor(notes, "2026-11-11", 9 * 3600 - 60, newest = false))
        assertNull(OneiosLogs.returnFor(notes, "2026-11-11", 12 * 3600, newest = false))
        // The newest log of a guest that had gone quiet: the last return.
        assertEquals(notes[3], OneiosLogs.returnFor(notes, "2026-11-11", 12 * 3600, newest = true))
        assertTrue(OneiosLogs.returns(emptyList()).isEmpty())
    }
}
