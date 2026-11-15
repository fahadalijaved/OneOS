package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The lines of `oneios-tool serve` as the app reads and writes them ([OneiosTool], [OneiosToolFlow]); the samples
 * are the lines of the tool's README ("serve", "An example").
 */
class OneiosToolTest {
    @Test
    fun aRequestIsOneLineOfJsonWithTheCommandsKeysAtTheTop() {
        val line = OneiosTool.request("3", "apfs-copy", linkedMapOf("image" to "/data/local/tmp/oneios/image/os.img", "src" to "/a \"b\"\n", "jobs" to 4, "resume" to true, "only" to listOf("kernelcache", "os"), "x" to null))
        assertTrue(line.endsWith("\n"))
        assertEquals(1, line.trimEnd('\n').lines().size)
        assertTrue(line.startsWith("""{"id":"3","cmd":"apfs-copy","image":"""))
        val back = JsonRead.parse(line) as Map<*, *>
        assertEquals("/a \"b\"\n", back["src"])
        assertEquals(4L, back["jobs"])
        assertEquals(true, back["resume"])
        assertEquals(listOf("kernelcache", "os"), back["only"])
        assertEquals("""{"id":"3","cmd":"cancel"}""" + "\n", OneiosTool.cancel("3"))
    }

    @Test
    fun aRequestNeedsAPlainCommandAndId() {
        for (cmd in listOf("", "Make", "a b", "x;rm", "-x")) assertTrue(cmd, runCatching { OneiosTool.request("1", cmd) }.isFailure)
        for (id in listOf("", "a b", "x".repeat(65), "1/2")) assertTrue(id, runCatching { OneiosTool.request(id, "ping") }.isFailure)
        assertTrue(runCatching { OneiosTool.request("1", "ping", mapOf("id" to "2")) }.isFailure)
    }

    @Test
    fun theReadmesLinesAreRead() {
        val hello = OneiosTool.parse("""{"ev":"hello","proto":1,"tool":"0.1.0","pid":4711,"jobs":8,"nice":10,"idle":300,"stage":"/data/local/tmp/oneios","thermal":[44,46,45,50],"battery_min":10,"cmds":["ping","health","cancel"]}""") as OneiosTool.Event.Hello
        assertEquals(1, hello.protocol)
        assertEquals("0.1.0", hello.tool)
        assertEquals(8L, hello.jobs)
        assertEquals(listOf("ping", "health", "cancel"), hello.cmds)
        val start = OneiosTool.parse("""{"ev":"start","id":"1","cmd":"apfs-copy","jobs":8,"steps":[{"step":"scan","text":"Reading the volume"},{"step":"copy","text":"Copying the files"},{"step":"place","text":"Putting the folder in place"}]}""") as OneiosTool.Event.Start
        assertEquals(listOf("scan", "copy", "place"), start.steps.map { it.first })
        val space = OneiosTool.parse("""{"ev":"space","id":"1","path":"/data/local/tmp/oneios/work","need":183500800,"free":52000000000,"reserve":268435456}""") as OneiosTool.Event.Space
        assertEquals(52000000000L, space.free)
        val p = OneiosTool.parse("""{"ev":"progress","id":"1","step":"copy","done":41943040,"total":183500800,"unit":"bytes","percent":22.9,"rate":167772160,"eta":1,"items_done":310,"items_total":2315}""") as OneiosTool.Event.Progress
        assertEquals(22.9, p.percent!!, 0.001)
        assertEquals(310L, p.itemsDone)
        val q = OneiosTool.parse("""{"ev":"queued","id":"2","cmd":"sums","ahead":1}""") as OneiosTool.Event.Queued
        assertEquals(1L, q.ahead)
        val c = OneiosTool.parse("""{"ev":"cancelled","id":"1","cmd":"apfs-copy","by":"request","removed":1,"text":"stopped; /data/local/tmp/oneios/work/CoreServices.part was removed"}""") as OneiosTool.Event.Cancelled
        assertTrue(c.ends)
        assertEquals("request", c.by)
        val ok = OneiosTool.parse("""{"ev":"ok","id":"2","cmd":"sums","seconds":9.4,"text":"12 files, 17,859,571,712 bytes: all as listed","files":12,"bytes":17859571712}""") as OneiosTool.Event.Ok
        assertEquals(12L, ok.raw["files"])
        assertEquals(9.4, ok.seconds!!, 0.001)
        val bye = OneiosTool.parse("""{"ev":"bye","why":"eof","requests":2,"cancelled":1,"threads":1,"children":0}""") as OneiosTool.Event.Bye
        assertEquals("eof", bye.why)
        assertEquals(0L, bye.children)
        val no = OneiosTool.parse("""{"ev":"refused","id":"4","cmd":"tweaks","code":"not-ported","text":"the root tweaks are not in the tool yet"}""") as OneiosTool.Event.Refused
        assertEquals("not-ported", no.code)
        assertEquals("the root tweaks are not in the tool yet", no.text)
        assertTrue(OneiosTool.parse("""{"ev":"failed","id":"4","code":"io"}""") is OneiosTool.Event.Failed)
        assertTrue(OneiosTool.parse("""{"ev":"heat","id":"4","state":"paused","why":"case","text":"the case is at 44 C"}""") is OneiosTool.Event.Heat)
        assertTrue(OneiosTool.parse("""{"ev":"row","id":"4","kind":"cpu","n":0}""") is OneiosTool.Event.Row)
        assertTrue(OneiosTool.parse("""{"ev":"error","text":"not JSON"}""") is OneiosTool.Event.Error)
    }

    @Test
    fun linesThatAreNotTheToolsAreLeftToTheCaller() {
        assertNull(OneiosTool.parse("@@OK tool work"))
        assertNull(OneiosTool.parse("@@REFUSED no OneiOS runtime is staged: oneios-tool comes with it"))
        assertNull(OneiosTool.parse("""{"id":"1","cmd":"ping"}"""))
        assertNull(OneiosTool.parse("""{"ev":"ok", broken"""))
        assertNull(OneiosTool.parse(""))
        assertTrue(OneiosTool.parse("""{"ev":"progress","done":1}""") is OneiosTool.Event.Other)
        assertTrue(OneiosTool.parse("""{"ev":"later","id":"1"}""") is OneiosTool.Event.Other)
        assertFalse(OneiosTool.parse("""{"ev":"later","id":"1"}""")!!.ends)
    }

    private fun fold(vararg lines: String): OneiosToolFlow = lines.fold(OneiosToolFlow()) { f, l -> f.with(OneiosTool.parse(l)!!) }

    @Test
    fun theMarksFollowTheToolsRule() {
        val start = """{"ev":"start","id":"1","cmd":"apfs-copy","jobs":8,"steps":[{"step":"scan","text":"Reading the volume"},{"step":"copy","text":"Copying the files"},{"step":"place","text":"Putting the folder in place"}]}"""
        var f = fold(start)
        assertEquals(listOf(OneiosTool.StepState.NEXT, OneiosTool.StepState.PENDING, OneiosTool.StepState.PENDING), f.steps.map { it.state })
        f = fold(start, """{"ev":"step","id":"1","step":"scan","n":1,"of":3,"text":"Reading the volume"}""",
            """{"ev":"space","id":"1","path":"/data/local/tmp/oneios/work","need":183500800,"free":52000000000,"reserve":268435456}""",
            """{"ev":"step","id":"1","step":"copy","n":2,"of":3,"text":"Copying the files"}""",
            """{"ev":"progress","id":"1","step":"copy","done":41943040,"total":183500800,"unit":"bytes","percent":22.9,"rate":167772160,"eta":1,"items_done":310,"items_total":2315}""")
        assertEquals(listOf(OneiosTool.StepState.DONE, OneiosTool.StepState.RUNNING, OneiosTool.StepState.NEXT), f.steps.map { it.state })
        assertEquals("place", f.next?.id)
        assertEquals(183500800L, f.spaceNeed)
        assertEquals("42 MB of 184 MB (23%) · 310 of 2315 files · 168 MB/s · less than a minute left", f.progressLine)
        assertTrue(f.running)
        val cancelled = f.with(OneiosTool.parse("""{"ev":"cancelled","id":"1","cmd":"apfs-copy","by":"request","removed":1,"text":"stopped; the .part was removed"}""")!!)
        assertEquals(listOf(OneiosTool.StepState.DONE, OneiosTool.StepState.CANCELLED, OneiosTool.StepState.PENDING), cancelled.steps.map { it.state })
        assertEquals("stopped; the .part was removed", cancelled.text)
        val refused = f.with(OneiosTool.parse("""{"ev":"refused","id":"1","cmd":"apfs-copy","code":"space","text":"not enough free space"}""")!!)
        assertEquals(OneiosTool.StepState.REFUSED, refused.steps[1].state)
        assertEquals("space", refused.code)
        val ok = f.with(OneiosTool.parse("""{"ev":"ok","id":"1","cmd":"apfs-copy","seconds":3.0,"text":"2315 files","files":2315}""")!!)
        assertTrue(ok.steps.all { it.state == OneiosTool.StepState.DONE })
        assertEquals(2315L, ok.result!!["files"])
        assertEquals(ok, ok.lost("gone"))
        assertEquals(OneiosToolFlow.End.LOST, f.lost("the tool ended (exit 9)").end)
    }

    @Test
    fun aHeatPauseIsShownUntilTheWorkGoesOn() {
        var f = fold("""{"ev":"heat","id":"1","state":"paused","why":"case","text":"the case is at 44 C: paused"}""")
        assertEquals("the case is at 44 C: paused", f.paused)
        f = f.with(OneiosTool.parse("""{"ev":"heat","id":"1","state":"resumed","why":"case"}""")!!)
        assertNull(f.paused)
    }

    @Test
    fun outputLinesAndRowsAreKeptUpToTheLimit() {
        var f = OneiosToolFlow()
        repeat(OneiosToolFlow.MAX_LINES + 10) { f = f.with(OneiosTool.Event.Line("1", "out", "l$it", emptyMap())) }
        assertEquals(OneiosToolFlow.MAX_LINES, f.lines.size)
        assertEquals("l10", f.lines.first())
        f = f.with(OneiosTool.parse("""{"ev":"row","id":"1","kind":"file","path":"bin/xnuhost","ok":true}""")!!)
        assertEquals("bin/xnuhost", f.rows.single()["path"])
    }
}
