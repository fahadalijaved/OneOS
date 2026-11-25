package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * xnuhost's switches as the app reads them (docs/oneios.md, "UI (2026-11-25)"): the catalog of OneiOS's
 * `oneios-tool switches --json` and `conf show FILE --json` (OneiOS's interface: fields may be added, never renamed),
 * the Switches screen's rows (control, value, changed), the change a tap sends, and root's `conf` answer.
 */
class OneiosConfTest {
    /** The interface's shape, with a field this app does not know (added later on OneiOS's side). */
    private val catalogJson = """
        {"version":1,"switches":[
          {"name":"session-mode","where":"conf","kind":"choice","values":["hosted","takeover"],"min":null,"max":null,
           "default":"hosted","off":null,"group":"Session","title":"Session mode","help":"takeover: the Android takeover",
           "phone":"tested","warning":null,"restart":"session","since":"v0.1.20"},
          {"name":"sensors","where":"conf","kind":"choice","values":["off","auto","ssc"],"default":"auto","off":"off",
           "group":"Sensors","title":"Sensor hub","help":"motion and light","phone":"not booted","warning":null,"restart":"session"},
          {"name":"task-trim","where":"conf","kind":"bool","values":["0","1"],"default":"1","off":"0","group":"RAM",
           "title":"Task trim","help":"idle tasks drop their host mappings","phone":"not booted","restart":"session"},
          {"name":"wifi-buffers","where":"conf","kind":"bool","values":null,"default":true,"group":"Wi-Fi","title":"Wi-Fi buffers",
           "help":null,"phone":"tested","restart":"session"},
          {"name":"sensors-hz","where":"conf","kind":"int","values":null,"min":5,"max":200,"default":50,"group":"Sensors",
           "title":"Sensor rate","help":"Hz","phone":"tested","restart":"session"},
          {"name":"oneios-motion","where":"boot-arg","kind":"int","min":0,"max":15,"default":0,"group":"Kernel",
           "title":"Motion device","help":"bits","phone":"broken","warning":"panics at kernel start","restart":"kernel"},
          {"name":"decoder-codecs","where":"conf","kind":"text","default":"h264,hevc,vp9,av1","group":"Video","title":"Decoder codecs"},
          {"name":"bad name","kind":"bool"},
          {"name":"later-kind","kind":"float"}
        ]}
    """.trimIndent()

    private val showJson = """
        {"path":"/data/local/tmp/oneios/conf/xnuhost.conf","text":"pen=auto\nsensors=off\ntask-trim=1\nboot-args-add=oneios-motion=7\n",
         "set":{"pen":"auto","sensors":"off","task-trim":"1","sensors-hz":50},"boot_args_add":{"oneios-motion":"7"},
         "unknown":["pen"],"errors":[{"line":9,"message":"not KEY=VALUE"}],
         "warnings":[{"line":8,"message":"wifi is given again (first on line 7): this line's value is used"}],"exists":true,"backup":false}
    """.trimIndent()

    private val catalog = OneiosConf.parseCatalog(catalogJson).getOrThrow()
    private val show = OneiosConf.parseShow(showJson).getOrThrow()

    private fun row(name: String) = OneiosConf.groups(catalog, show).flatMap { it.rows }.single { it.switch.name == name }

    @Test
    fun theCatalogIsReadWithItsKindsAndValuesAndSkipsWhatItCannotShow() {
        assertEquals(1, catalog.version)
        assertEquals(
            listOf("session-mode", "sensors", "task-trim", "wifi-buffers", "sensors-hz", "oneios-motion", "decoder-codecs"),
            catalog.switches.map { it.name },
        )
        val motion = catalog.switches.single { it.name == "oneios-motion" }
        assertEquals(OneiosConf.Where.BOOT_ARG, motion.where)
        assertEquals(0L, motion.min)
        assertEquals(15L, motion.max)
        assertEquals("0", motion.default)
        assertEquals("broken", motion.badge)
        assertEquals("panics at kernel start", motion.warning)
        assertTrue(motion.needsKernel)
        // A boolean default as JSON's true is xnuhost.conf's 1.
        assertEquals("1", catalog.switches.single { it.name == "wifi-buffers" }.default)
        assertNull(catalog.switches.single { it.name == "session-mode" }.badge)
        assertTrue(OneiosConf.parseCatalog("[]").isFailure)
        assertTrue(OneiosConf.parseCatalog("{\"switches\":[]}").isFailure)
    }

    @Test
    fun theRowsAreGroupedAndSayTheirControlValueAndChange() {
        val groups = OneiosConf.groups(catalog, show)
        assertEquals(listOf("Session", "Sensors", "RAM", "Wi-Fi", "Kernel", "Video"), groups.map { it.name })
        assertEquals(listOf("sensors", "sensors-hz"), groups.single { it.name == "Sensors" }.rows.map { it.switch.name })
        // A choice with an off value is a toggle: on is the default, off is off.
        val sensors = row("sensors")
        assertEquals(OneiosConf.Control.TOGGLE, sensors.switch.control)
        assertEquals(false, sensors.on)
        assertTrue(sensors.changed)
        // A choice without one is a picker, at its default when the file does not name it.
        val mode = row("session-mode")
        assertEquals(OneiosConf.Control.CHOICE, mode.switch.control)
        assertEquals("hosted", mode.value)
        assertFalse(mode.changed)
        assertNull(mode.on)
        // The file's value equal to the default (written out) is not a change.
        val trim = row("task-trim")
        assertEquals(true, trim.on)
        assertFalse(trim.changed)
        assertFalse(row("sensors-hz").changed)
        assertEquals(true, row("wifi-buffers").on)
        // A boot-arg switch takes its value from boot-args-add=.
        val motion = row("oneios-motion")
        assertEquals(OneiosConf.Control.NUMBER, motion.switch.control)
        assertEquals("7", motion.value)
        assertTrue(motion.changed)
        assertEquals(OneiosConf.Control.TEXT, row("decoder-codecs").switch.control)
        assertEquals(listOf(OneiosConf.LineError(9, "not KEY=VALUE")), show.errors)
        // Added by OneiOS (aa8cfa4): warnings do not stop anything; whether the file is there and has a backup.
        assertEquals(listOf(OneiosConf.LineError(8, "wifi is given again (first on line 7): this line's value is used")), show.warnings)
        assertEquals(true, show.exists)
        assertEquals(false, show.backup)
        assertNull(OneiosConf.Show.plain("x=1\n").backup)
    }

    @Test
    fun aChangeSendsSetOrUnsetAndRefusesValuesTheCatalogDoesNotTake() {
        assertEquals(OneiosConf.Change.Unset("sensors"), OneiosConf.toggle(row("sensors"), true))
        assertEquals(OneiosConf.Change.Put("task-trim", "0"), OneiosConf.toggle(row("task-trim"), false))
        assertEquals(OneiosConf.Change.Unset("task-trim"), OneiosConf.toggle(row("task-trim"), true))
        assertEquals(OneiosConf.Change.Put("session-mode", "takeover"), OneiosConf.change(row("session-mode"), "takeover"))
        assertNull(OneiosConf.change(row("session-mode"), "other"))
        assertEquals(OneiosConf.Change.Put("sensors-hz", "100"), OneiosConf.change(row("sensors-hz"), "100"))
        assertEquals(OneiosConf.Change.Unset("sensors-hz"), OneiosConf.change(row("sensors-hz"), "50"))
        assertNull(OneiosConf.change(row("sensors-hz"), "201"))
        assertNull(OneiosConf.change(row("sensors-hz"), "4"))
        assertNull(OneiosConf.change(row("sensors-hz"), "fast"))
        assertEquals("at most 200", row("sensors-hz").switch.problem("201"))
        assertNull(OneiosConf.change(row("decoder-codecs"), "h264\nx=1"))
        assertEquals(OneiosConf.Change.Unset("oneios-motion"), OneiosConf.reset(row("oneios-motion")))
        assertEquals("sensors=off\nsensors-hz=100\n", OneiosConf.stdin(listOf(OneiosConf.Change.Put("sensors", "off"), OneiosConf.Change.Put("sensors-hz", "100"))))
        assertEquals("sensors\n", OneiosConf.stdin(listOf(OneiosConf.Change.Unset("sensors"))))
        assertTrue(runCatching { OneiosConf.stdin(listOf(OneiosConf.Change.Put("a b", "1"))) }.isFailure)
        assertTrue(runCatching { OneiosConf.stdin(listOf(OneiosConf.Change.Put("a", "1"), OneiosConf.Change.Unset("b"))) }.isFailure)
        assertTrue(runCatching { OneiosConf.stdin(emptyList()) }.isFailure)
    }

    @Test
    fun rootsAnswerIsReadPartByPart() {
        val lines = listOf(
            "@@RESULT conf tool",
            "@@RESULT part catalog",
        ) + catalogJson.lines().map { "| $it" } + listOf(
            "@@RESULT part show",
            "| $showJson".replace("\n", " "),
            "@@RESULT part answer",
            "| {\"ok\": false, \"error\": \"the file has errors\", \"errors\": [{\"line\": 2, \"message\": \"not KEY=VALUE\"}]}",
            "@@REFUSED oneios-tool refused conf write (its answer above)",
        )
        val r = OneiosConf.Reply.parse(lines)
        assertTrue(r.tool)
        assertFalse(r.noCatalog)
        assertEquals(7, r.catalog!!.switches.size)
        assertEquals("off", r.show!!.set["sensors"])
        val a = r.answer!!
        assertFalse(a.ok)
        assertEquals("the file has errors", a.error)
        assertEquals(listOf(OneiosConf.LineError(2, "not KEY=VALUE")), a.errors)
        // The plain file of a runtime without conf: its text as root read it, the empty line kept.
        val plain = OneiosConf.Reply.parse(listOf("@@RESULT conf plain", "@@RESULT catalog none", "@@RESULT part text", "| pen=auto", "|", "| # end", "@@OK conf load"))
        assertFalse(plain.tool)
        assertTrue(plain.noCatalog)
        assertNull(plain.catalog)
        assertEquals("pen=auto\n\n# end\n", plain.show!!.text)
        assertTrue(plain.show!!.set.isEmpty())
        assertEquals(OneiosConf.Answer(true, null, emptyList()), OneiosConf.parseAnswer("{\"ok\": true}"))
        assertNull(OneiosConf.parseAnswer("not json"))
    }

    @Test
    fun flagWordsAreXnuhosts() {
        for (w in listOf("1", "yes", "true", "on", "TRUE")) assertEquals(true, OneiosConf.truthy(w))
        for (w in listOf("0", "no", "false", "off")) assertEquals(false, OneiosConf.truthy(w))
        assertNull(OneiosConf.truthy("auto"))
    }
}
