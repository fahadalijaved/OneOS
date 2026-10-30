package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Hashes
import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.InstalldTableFormat
import com.fahadali.oneos.core.model.PackageSet
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.PhoneProfile
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SessionEnv
import com.fahadali.oneos.core.model.ShaList
import com.fahadali.oneos.core.model.StageMarker
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * oneos_root.sh and its launcher under dash and busybox ash (AA23), and mksh
 * when there is one (TestShell), against a
 * fake root folder (FakeRoot): the whole preparation, and the refusals, each
 * of which must leave the stage exactly as it was.
 */
class StageScriptTest {
    private val shells = TestShell.available()

    private fun eachShell(script: ByteArray = Shipped.rootScript.readBytes(), block: (FakeRoot) -> Unit) {
        assumeTrue("no dash or busybox on this machine", shells.isNotEmpty())
        for (s in shells) {
            FakeRoot(s, script).use { fr ->
                try {
                    block(fr)
                } catch (e: AssertionError) {
                    throw AssertionError("[${s.name}] ${e.message}", e)
                }
            }
        }
    }

    /** Prepares a stage the way PrepareJob does, with small stand-ins for every file: [imageId] (default the profile's first) and its set. */
    // The first image that is not the IN build (0.4.11 lists it first on the bar phones): these tests
    // stage the CN build unless they ask for another.
    private class Stager(
        val fr: FakeRoot,
        val profile: PhoneProfile = Profiles.S_ULTRA_8850,
        val imageId: String = profile.choices.first { it.imageId != Images.ID_FIND_X9U_IN }.imageId,
    ) {
        val set: PackageSet = PackageSets.byId(profile.choice(imageId)!!.packageSetId)!!
        val files: Map<String, ByteArray> = (RootScript.SCRIPTS + set.names).associateWith { n ->
            when (n) {
                "host_installd.txt" -> Shipped.installdFixture.readBytes()
                "guest_props.sh" -> "echo \"fake guest_props \$1\"\nexit \${FAKE_RC:-0}\n".toByteArray()
                else -> "$n stand-in\n".toByteArray()
            }
        }
        val raw = ByteArray(70_000) { (it % 251).toByte() }

        init {
            fr.env["ONEOS_TEST_RAW"] = "${raw.size} ${Hashes.sha256(raw)}"
        }

        val code = "4"

        fun begin(mode: String = "new", setId: String = set.id) = fr.run(RootScript.Verb.BEGIN, mode, profile.id, imageId, setId, code)

        fun receive(name: String, bytes: ByteArray = files.getValue(name), sha: String = Hashes.sha256(bytes), send: ByteArray = bytes) =
            fr.run(RootScript.Verb.RECEIVE, name, bytes.size.toString(), sha, stdin = send)

        fun receiveRaw() = fr.run(RootScript.Verb.RECEIVE, "system.raw", raw.size.toString(), Hashes.sha256(raw), stdin = raw)

        fun table(fingerprint: String = fr.props.getValue("ro.build.fingerprint")): FakeRoot.Run {
            val t = InstalldTableFormat.write(
                fingerprint, "/system/framework/framework.jar", Hashes.sha256(fr.frameworkJar),
                InstalldTableFormat.parseLegacy(Shipped.installdFixture.readText()),
            ).toByteArray()
            return fr.run(RootScript.Verb.TABLE, t.size.toString(), stdin = t)
        }

        fun env(text: String = SessionEnv.generate(profile)): FakeRoot.Run {
            val b = text.toByteArray()
            return fr.run(RootScript.Verb.ENV, b.size.toString(), stdin = b)
        }

        fun finish(setId: String = set.id) = fr.run(RootScript.Verb.FINISH, profile.id, imageId, setId, code)

        fun launch(
            mode: String = "session", hideGms: String = "0", code: String = this.code,
            heatCap: String = "1", secIms: String = "0", edmStub: String = "0",
        ) = fr.run(RootScript.Verb.LAUNCH, mode, code, "0123456789abcdef", hideGms, heatCap, secIms, edmStub)

        fun prepare(mode: String = "new") {
            ok(begin(mode))
            for (n in files.keys) ok(receive(n))
            ok(receiveRaw())
            ok(table())
            ok(env())
            ok(finish())
        }

        fun ok(r: FakeRoot.Run) {
            assertEquals("expected success:\n$r", 0, r.exit)
            assertNotNull("no @@OK:\n$r", r.reply.ok)
        }
    }

    private fun refused(r: FakeRoot.Run, part: String) {
        assertEquals("expected a refusal:\n$r", RootScript.EXIT_REFUSED, r.exit)
        assertTrue("refusal '${r.reply.refused}' should mention '$part'\n$r", r.reply.refused.orEmpty().contains(part))
    }

    @Test
    fun fullPreparationThenLaunchChecksPass() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val stage = fr.stage
        // files.sha256: every script and set file, sha256sum layout, not system.raw.
        val sums = ShaList.parse(File(stage, "files.sha256").readText())
        assertTrue(sums.problems.isEmpty())
        assertEquals((RootScript.SCRIPTS + s.set.names).toSet(), sums.entries.keys)
        for ((n, b) in s.files) assertEquals(n, Hashes.sha256(b), sums.entries[n])
        // The marker is exactly what the app parses.
        val m = StageMarker.parse(File(stage, StageMarker.FILE_NAME).readText())
        assertNotNull(m)
        assertEquals(s.profile.id, m!!.profileId)
        assertEquals(s.imageId, m.imageId)
        assertEquals(s.set.id, m.setId)
        assertEquals(4, m.versionCode)
        // system.raw.id: size, sha256, identity.
        val id = File(stage, "system.raw.id").readText().trim().split(' ')
        assertEquals(listOf(s.raw.size.toString(), Hashes.sha256(s.raw)), id.take(2))
        assertEquals(3, id.size)
        // Modes: scripts and surfaceflinger executable, the rest 0644; stage and bin 0755.
        assertEquals("755", fr.mode(stage))
        assertEquals("755", fr.mode(File(stage, "bin")))
        assertEquals("755", fr.mode(File(stage, "oneos_switch.sh")))
        assertEquals("755", fr.mode(File(stage, "surfaceflinger_patched")))
        assertEquals("644", fr.mode(File(stage, "services_patched.jar")))
        assertEquals("644", fr.mode(File(stage, "session.env")))
        assertFalse(File(stage, "incoming/plan").exists())
        assertEquals(SessionEnv.generate(s.profile), File(stage, "session.env").readText())
        // Launch: every check passes, then the test root refuses before anything starts.
        val l = s.launch()
        refused(l, "test root: every launch check passed")
        assertEquals(SessionEnv.generate(s.profile), File(stage, "session.env").readText())
        assertFalse(File(stage, "session/current.json").exists())
        assertFalse(File(stage, "takeover_app.log").exists())
    }

    @Test
    fun foldProfileGetsItsGridAndFoldSettings() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val s = Stager(fr, Profiles.F8U)
        s.prepare()
        assertTrue(File(fr.stage, "OneOSWallpapersFoldGrid.apk").isFile)
        refused(s.launch("dry"), "test root")
        // The S Ultra's settings are refused for the Fold profile.
        ok(s.begin("keep"))
        val bar = SessionEnv.generate(Profiles.F8U).replace("ONEOS_GUEST_FORM=fold", "ONEOS_GUEST_FORM=phone")
        refused(s.env(bar), "ONEOS_GUEST_FORM=phone")
    }

    @Test
    fun launchRefusesWhatChangedAfterPreparing() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        File(fr.stage, "art_payload.img").appendText("x")
        refused(s.launch(), "art_payload.img changed")
        File(fr.stage, "art_payload.img").writeBytes(s.files.getValue("art_payload.img"))
        // A leftover the scripts would bind.
        File(fr.stage, "framework_patched.jar").writeText("old")
        refused(s.launch(), "framework_patched.jar")
        File(fr.stage, "framework_patched.jar").delete()
        // Another app build, another phone, a lock-free but drained battery, the old switcher, no keys.
        refused(s.launch(code = "5"), "prepare again")
        fr.props["ro.product.device"] = "pa3q"
        fr.writeProps()
        refused(s.launch(), "codename pa3q")
        fr.props["ro.product.device"] = "m3q"
        fr.writeProps()
        fr.battery("12", "Discharging", "300")
        refused(s.launch(), "battery")
        fr.battery("12", "Charging", "300")
        File(fr.root, "old_switcher").writeText("")
        refused(s.launch(), "old switcher")
        File(fr.root, "old_switcher").delete()
        File(fr.root, "no_keys").writeText("")
        refused(s.launch(), "Volume Up")
        File(fr.root, "no_keys").delete()
        // An unfinished session must be restored first.
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        refused(s.launch(), "restore One UI's settings")
        File(fr.stage, "persist_session.active").delete()
        // A One UI update: another fingerprint than the table's.
        fr.props["ro.build.fingerprint"] = "samsung/m3qxxx/m3q:17/NEWER:user/release-keys"
        fr.writeProps()
        refused(s.launch(), "not for this One UI build")
    }

    @Test
    fun appDataIsolationIsNotABridge() = eachShell { fr ->
        // The root script runs in the app's mount namespace, where Android's app
        // data isolation puts tmpfs on /data/data, /data/user and /data/user_de.
        // 0.3.0 on the Fold refused a cleanly rebooted phone with "still bridged".
        val s = Stager(fr)
        s.prepare()
        fr.mountinfo(emptyList(), self = listOf("data", "user", "user_de").map { "${fr.root.path}/data/$it" })
        ok(s.begin("keep"))
        // The same mounts in init's table are a real bridge.
        fr.mountinfo(listOf("${fr.root.path}/data/user"))
        refused(s.begin("keep"), "still bridged")
    }

    @Test
    fun refusalsChangeNothing() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val before = fr.snapshot()
        // Something mounted in the stage (a running session).
        fr.mountinfo(listOf("${fr.stage.path}/rootfs"))
        refused(s.begin("keep"), "mounted in the stage")
        refused(s.launch(), "mounted in the stage")
        // A host /data tree still bridged.
        fr.mountinfo(listOf("${fr.root.path}/data/app"))
        refused(s.begin("keep"), "still bridged")
        // The image on a loop device.
        fr.mountinfo(emptyList())
        File(fr.root, "sys/block/loop0/loop/backing_file").writeText("${fr.stage.path}/system.raw\n")
        refused(s.begin("keep"), "loop device")
        File(fr.root, "sys/block/loop0/loop/backing_file").delete()
        // Unknown session.env keys and the ones that would turn the way back off.
        assertEquals(before, fr.snapshot())
        ok(s.begin("keep"))
        val good = SessionEnv.generate(s.profile)
        for (bad in listOf(
            good + "ONEOS_RETURN_MAX=0\n",
            good + "ONEOS_RETURN_KEYS=0\n",
            good + "ONEOS_TUNNEL_SERVER=1.2.3.4\n",
            good + "ONEOS_SOMETHING=1\n",
            good.replace("ONEOS_LOGCAT=1\n", ""),
            good + "ONEOS_RECORD=0\n",
            good.replace("ONEOS_PROFILE=s-ultra-8850", "ONEOS_PROFILE=f8u"),
            good.replace("\n", "\r\n"),
            good.removeSuffix("\n"),
            good + "ONEOS_APP=1; reboot\n",
        )) {
            val r = s.env(bad)
            assertEquals("should refuse:\n$bad\n$r", RootScript.EXIT_REFUSED, r.exit)
            assertFalse(File(fr.stage, "incoming/session.env.part").exists())
        }
        // An installd table for another One UI build.
        ok(s.receive("host_installd.txt"))
        refused(s.table("samsung/other/m3q:17/X:user/release-keys"), "not for this One UI build")
        // A file that is not in the set, and one that is too short or wrong.
        // 0.4.24: framework_patched.jar is a Pixel set file now; a name no set carries.
        assertTrue(RootScript.problems(RootScript.Verb.RECEIVE, listOf("framework_other_patched.jar", "1", "a".repeat(64))).isNotEmpty())
        refused(s.receive("OneOSWallpapersFoldGrid.apk", "x".toByteArray()), "not a file of x9u-sultra")
        val b = s.files.getValue("art_payload.img")
        refused(s.receive("art_payload.img", b, send = b.copyOf(b.size - 3)), "arrived with")
        assertFalse(File(fr.stage, "incoming/art_payload.img.part").exists())
        refused(s.receive("art_payload.img", b, sha = Hashes.sha256("other")), "does not match its SHA-256")
        assertFalse(File(fr.stage, "incoming/art_payload.img.part").exists())
        refused(fr.run(RootScript.Verb.RECEIVE, "system.raw", "5", "a".repeat(64), stdin = "abcde".toByteArray()), "not the coloros17-findx9u image")
        // finish before everything arrived.
        refused(s.finish(), "was not received")
    }

    private fun ok(r: FakeRoot.Run) {
        assertEquals("expected success:\n$r", 0, r.exit)
    }

    /** An old stage as begin aside leaves it: a ColorOS install with guest data and a marker. */
    private fun oldStage(fr: FakeRoot, name: String, image: String = "coloros17-findn6"): File {
        val d = File(fr.root, "data/local/tmp/$name")
        File(d, "data/system").mkdirs()
        File(d, "data/system/packages.xml").writeText("<packages/>")
        File(d, "system.raw").writeBytes(ByteArray(9000) { 1 })
        File(d, ".oneos_stage").writeText(StageMarker(4, "f8u", image, "n6-f8u", 1792000000L).toJson())
        return d
    }

    @Test
    fun oldStagesAreListedWithTheirImageAndState() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        oldStage(fr, "oneos.old-1792000000")
        File(fr.root, "data/local/tmp/oneos.old-1792000001-77").mkdirs()
        File(fr.root, "data/local/tmp/oneos.other").mkdirs() // not ours: never listed
        File(fr.root, "data/local/tmp/oneos_logs").mkdirs()
        val r = fr.run(RootScript.Verb.OLD_LIST)
        ok(r)
        val rows = r.reply.results.filter { it.startsWith("old ") }.map { it.split(" ") }.associateBy { it[1] }
        assertEquals(setOf("oneos.old-1792000000", "oneos.old-1792000001-77"), rows.keys)
        val a = rows.getValue("oneos.old-1792000000")
        assertEquals(listOf("coloros17-findn6", "1", "0"), a.subList(3, 6))
        assertTrue(a[2].toLong() > 0)
        assertEquals(listOf("unknown", "0", "0"), rows.getValue("oneos.old-1792000001-77").subList(3, 6))
    }

    @Test
    fun purgeRefusesEveryUnsafeCaseAndChangesNothing() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val old = oldStage(fr, "oneos.old-1792000000")
        val name = old.name
        var before = fr.snapshot()
        fun purgeRefused(part: String) {
            refused(fr.run(RootScript.Verb.PURGE, name), part)
            assertEquals(before, fr.snapshot())
        }
        // Mounted under it: in init's table, only in another process's table, or a table root cannot read.
        fr.mountinfo(listOf("${old.path}/data"))
        purgeRefused("mounted")
        fr.mountinfo(emptyList())
        val other = File(fr.root, "proc/4242").apply { mkdirs() }
        File(other, "mountinfo").writeText("22 1 253:0 / / rw - ext4 /dev/root rw\n31 22 0:41 / ${old.path}/data/user rw - f2fs /dev/x rw\n")
        purgeRefused("mounted")
        File(other, "mountinfo").writeText("22 1 253:0 / / rw - ext4 /dev/root rw\n")
        FakeRoot.exec(listOf("chmod", "000", File(other, "mountinfo").path))
        purgeRefused("unreadable")
        FakeRoot.exec(listOf("chmod", "644", File(other, "mountinfo").path))
        // A loop device on its image.
        File(fr.root, "sys/block/loop0/loop/backing_file").writeText("${old.path}/system.raw\n")
        purgeRefused("loop device")
        File(fr.root, "sys/block/loop0/loop/backing_file").delete()
        // A host /data tree still bridged.
        fr.mountinfo(listOf("${fr.root.path}/data/app"))
        purgeRefused("still bridged")
        fr.mountinfo(emptyList())
        // A session of this boot.
        File(old, "persist_session.active").writeText("format=2\nboot_id=11111111-2222-3333-4444-555555555555\n")
        before = fr.snapshot()
        purgeRefused("this boot")
        File(old, "persist_session.active").writeText("format=2\nboot_id=99999999-0000-0000-0000-000000000000\n")
        val before2 = fr.snapshot()
        // A link with an old stage's name, and a name that is not there.
        val link = File(fr.root, "data/local/tmp/oneos.old-1792000005")
        java.nio.file.Files.createSymbolicLink(link.toPath(), fr.stage.toPath())
        refused(fr.run(RootScript.Verb.PURGE, link.name), "root-owned folder")
        refused(fr.run(RootScript.Verb.PURGE, "oneos.old-1792000009"), "root-owned folder")
        refused(fr.run(RootScript.Verb.PURGE, "lineage_stage.old-1792000009"), "root-owned folder")
        assertTrue(File(fr.stage, ".oneos_stage").isFile)
        link.delete()
        assertEquals(before2, fr.snapshot())
    }

    @Test
    fun purgeDeletesOnlyThatOldStage() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val keep = oldStage(fr, "oneos.old-1792000000")
        val gone = oldStage(fr, "oneos.old-1792000100-12")
        File(gone, "persist_session.active").writeText("format=2\nboot_id=99999999-0000-0000-0000-000000000000\n")
        // 0.4.13: a session earlier in this boot that returned in place leaves the return watcher's
        // record; that alone does not keep it (nothing mounted, no loop device, nothing bridged).
        File(gone, "return_keys").mkdirs()
        File(gone, "return_keys/boot").writeText("11111111-2222-3333-4444-555555555555\n")
        // A link inside points at the active stage: deleting must not follow it.
        java.nio.file.Files.createSymbolicLink(File(gone, "data/stage_link").toPath(), fr.stage.toPath())
        val stageBefore = FakeRoot.exec(listOf("find", fr.stage.path, "-printf", "%P %y %s\\n")).lines().sorted()
        val r = fr.run(RootScript.Verb.PURGE, gone.name)
        ok(r)
        assertTrue(r.toString(), r.reply.results.any { it.startsWith("purged ${gone.name} ") })
        assertFalse(gone.exists())
        assertTrue(File(keep, "data/system/packages.xml").isFile)
        assertEquals(stageBefore, FakeRoot.exec(listOf("find", fr.stage.path, "-printf", "%P %y %s\\n")).lines().sorted())
        // No trash left behind; a trash folder from an interrupted purge can be finished.
        val tmp = File(fr.root, "data/local/tmp")
        assertTrue(tmp.list()!!.none { it.startsWith("oneos.trash-") })
        val trash = File(tmp, "oneos.trash-1792000200").apply { File(this, "x").mkdirs() }
        ok(fr.run(RootScript.Verb.PURGE, trash.name))
        assertFalse(trash.exists())
    }

    /** 0.4.25: remove deletes the stage, every copy, the log capture and the helper files, and nothing else. */
    @Test
    fun removeDeletesEverythingOursAndNothingElse() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val tmp = File(fr.root, "data/local/tmp")
        val a = oldStage(fr, "oneos.old-1792000000")
        oldStage(fr, "oneos.old-1792000100-12")
        File(tmp, "oneos.trash-1792000200").apply { File(this, "x").mkdirs() }
        File(tmp, "oneos_logs/head").mkdirs()
        File(tmp, "oneos_logs/boot.log").writeText("log\n")
        val helpers = listOf("adb_watchdog.sh", "adb_watchdog.log", "ims_watchdog.sh", "ims_watchdog.log", "ui_activator.log", "restore_app.log")
        for (h in helpers) File(tmp, h).writeText("x\n")
        // Not ours: kept, also through links inside what is deleted.
        val tunnel = File(tmp, "oneos_tunnel").apply { mkdirs(); File(this, "key").writeText("k\n") }
        File(tmp, "oneos.other").mkdirs()
        File(tmp, "lineage_backups/b").mkdirs()
        File(tmp, "notes.txt").writeText("n\n")
        java.nio.file.Files.createSymbolicLink(File(fr.stage, "tunnel_link").toPath(), tunnel.toPath())
        java.nio.file.Files.createSymbolicLink(File(a, "data/tunnel_link").toPath(), tunnel.toPath())

        val r = fr.run(RootScript.Verb.REMOVE)
        ok(r)
        assertTrue(r.toString(), r.reply.results.any { it.startsWith("removed ") })
        assertFalse(fr.stage.exists())
        assertEquals(
            setOf("oneos_tunnel", "oneos.other", "lineage_backups", "notes.txt"),
            tmp.list()!!.toSet(),
        )
        assertEquals("k\n", File(tunnel, "key").readText())
        assertTrue(File(tmp, "lineage_backups/b").isDirectory)
    }

    @Test
    fun removeRefusesEveryUnsafeCaseAndChangesNothing() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val tmp = File(fr.root, "data/local/tmp")
        val old = oldStage(fr, "oneos.old-1792000000")
        File(tmp, "oneos_logs").mkdirs()
        val before = fr.snapshot()
        fun removeRefused(part: String) {
            refused(fr.run(RootScript.Verb.REMOVE), part)
            assertEquals(before, fr.snapshot())
        }
        // Mounted in the stage, in a copy or in the log folder.
        fr.mountinfo(listOf("${fr.stage.path}/rootfs"))
        removeRefused("mounted")
        fr.mountinfo(listOf("${old.path}/data"))
        removeRefused("mounted")
        fr.mountinfo(listOf("${tmp.path}/oneos_logs/x"))
        removeRefused("mounted")
        fr.mountinfo(emptyList())
        // A loop device on the staged image.
        File(fr.root, "sys/block/loop0/loop/backing_file").writeText("${fr.stage.path}/system.raw\n")
        removeRefused("loop device")
        File(fr.root, "sys/block/loop0/loop/backing_file").delete()
        // A host /data tree still bridged.
        fr.mountinfo(listOf("${fr.root.path}/data/app"))
        removeRefused("still bridged")
        fr.mountinfo(emptyList())
        // A session running now, or one that never returned.
        File(fr.stage, "guest_props.boot").writeText("11111111-2222-3333-4444-555555555555\n")
        refused(fr.run(RootScript.Verb.REMOVE), "session running")
        File(fr.stage, "guest_props.boot").delete()
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=99999999-0000-0000-0000-000000000000\n")
        refused(fr.run(RootScript.Verb.REMOVE), "never returned")
        File(fr.stage, "persist_session.active").delete()
        assertEquals(before, fr.snapshot())
        // No arguments.
        assertTrue(RootScript.problems(RootScript.Verb.REMOVE, listOf("x")).isNotEmpty())
        assertEquals(emptyList<String>(), RootScript.problems(RootScript.Verb.REMOVE, emptyList()))
    }

    /** 0.4.10: restore puts a set-aside stage back and keeps the one set up now as another old copy. */
    @Test
    fun restoreSwapsTheStageWithASetAsideCopy() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val markerBefore = File(fr.stage, ".oneos_stage").readText()
        val old = oldStage(fr, "oneos.old-1792000000", image = Images.ID_PIXEL_YOGI)
        File(old, "bin").mkdirs()
        FakeRoot.exec(listOf("chmod", "755", old.path, File(old, "bin").path))
        val oldMarker = File(old, ".oneos_stage").readText()
        // A session earlier in this boot that returned does not stop it (purge would refuse it).
        File(fr.stage, "return_keys").mkdirs()
        File(fr.stage, "return_keys/boot").writeText("11111111-2222-3333-4444-555555555555\n")
        val r = fr.run(RootScript.Verb.RESTORE, old.name)
        ok(r)
        val aside = OldStages.setAsideBy(r.reply.results, old.name)
        assertTrue(r.toString(), aside != null && aside.startsWith("oneos.old-"))
        assertEquals(oldMarker, File(fr.stage, ".oneos_stage").readText())
        assertTrue(File(fr.stage, "data/system/packages.xml").isFile)
        assertFalse(old.exists())
        assertEquals(markerBefore, File(fr.root, "data/local/tmp/$aside/.oneos_stage").readText())
        // And back the same way.
        ok(fr.run(RootScript.Verb.RESTORE, aside!!))
        assertEquals(markerBefore, File(fr.stage, ".oneos_stage").readText())
    }

    @Test
    fun restoreRefusesEveryUnsafeCaseAndChangesNothing() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val old = oldStage(fr, "oneos.old-1792000000")
        File(old, "bin").mkdirs()
        FakeRoot.exec(listOf("chmod", "755", old.path, File(old, "bin").path))
        var before = fr.snapshot()
        fun restoreRefused(name: String, part: String) {
            refused(fr.run(RootScript.Verb.RESTORE, name), part)
            assertEquals(before, fr.snapshot())
        }
        // Mounted under the copy or under the stage.
        fr.mountinfo(listOf("${old.path}/data"))
        restoreRefused(old.name, "mounted")
        fr.mountinfo(listOf("${fr.stage.path}/rootfs"))
        restoreRefused(old.name, "mounted")
        fr.mountinfo(emptyList())
        // A loop device on a file in either.
        File(fr.root, "sys/block/loop0/loop/backing_file").writeText("${fr.stage.path}/system.raw\n")
        restoreRefused(old.name, "loop device")
        File(fr.root, "sys/block/loop0/loop/backing_file").delete()
        // A host /data tree still bridged.
        fr.mountinfo(listOf("${fr.root.path}/data/app"))
        restoreRefused(old.name, "still bridged")
        fr.mountinfo(emptyList())
        // A session that never returned, in the copy or in the stage; one running now.
        File(old, "persist_session.active").writeText("format=2\nboot_id=99999999-0000-0000-0000-000000000000\n")
        before = fr.snapshot()
        restoreRefused(old.name, "never returned")
        File(old, "persist_session.active").delete()
        File(fr.stage, "guest_props.boot").writeText("11111111-2222-3333-4444-555555555555")
        before = fr.snapshot()
        restoreRefused(old.name, "session running")
        File(fr.stage, "guest_props.boot").delete()
        before = fr.snapshot()
        // Not a set-aside copy: a stopped delete, a folder without a marker, a name that is not there.
        val trash = File(fr.root, "data/local/tmp/oneos.trash-1792000200").apply { mkdirs() }
        before = fr.snapshot()
        assertTrue(RootScript.problems(RootScript.Verb.RESTORE, listOf(trash.name)).isNotEmpty())
        File(old, "bin").delete()
        before = fr.snapshot()
        restoreRefused(old.name, "no bin folder")
        File(old, "bin").mkdirs()
        FakeRoot.exec(listOf("chmod", "775", File(old, "bin").path))
        before = fr.snapshot()
        restoreRefused(old.name, "writable by others")
        FakeRoot.exec(listOf("chmod", "755", File(old, "bin").path))
        File(old, ".oneos_stage").delete()
        before = fr.snapshot()
        restoreRefused(old.name, "no stage marker")
        restoreRefused("oneos.old-1792000009", "no stage marker")
        assertTrue(File(fr.stage, ".oneos_stage").isFile)
    }

    @Test
    fun purgeTakesOnlyOldStageNames() {
        for (bad in listOf(
            "oneos", "oneos.old-", "oneos.old-x", "oneos.old-1/..", "../oneos.old-1", "/data/local/tmp/oneos.old-1",
            "oneos.old-1-", "oneos.old-1-2-3", "oneos.new-1", "oneos_logs", "oneos.old-1.x",
            "lineage_stage", "lineage_stage.old-", "lineage_stage.old-x", "lineage_stage.old-1/..", "../lineage_stage.old-1",
            "/data/local/tmp/lineage_stage.old-1", "lineage_stage.old-1-", "lineage_stage.old-1-2-3", "lineage_stage.new-1",
        )) {
            assertTrue(bad, RootScript.problems(RootScript.Verb.PURGE, listOf(bad)).isNotEmpty())
        }
        // Their names up to 0.3.6 too, until the script renames them.
        for (good in listOf(
            "oneos.old-1792758413", "oneos.old-1792758413-4242", "oneos.trash-1792758413",
            "lineage_stage.old-1792758413", "lineage_stage.old-1792758413-4242", "lineage_stage.trash-1792758413",
        )) {
            assertEquals(good, emptyList<String>(), RootScript.problems(RootScript.Verb.PURGE, listOf(good)))
        }
        assertTrue(RootScript.problems(RootScript.Verb.PURGE, emptyList()).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.OLD_LIST, listOf("x")).isNotEmpty())
    }

    @Test
    fun foreignWorldWritableStageIsMovedAsideNeverDeleted() = eachShell { fr ->
        // OneLineage's stage on the S26 Ultra, at its own path (lineage_stage): 0777, its
        // own scripts, a LineageOS guest. The first verb renames it to the OneOS stage.
        val st = fr.legacy.apply { mkdirs() }
        File(st, "switch_to_lineage.sh").writeText("old")
        File(st, "7zz").writeText("tool")
        File(st, "data/system").mkdirs()
        File(st, "data/system/packages.xml").writeText("<packages><package name=\"org.lineageos.updater\"/></packages>")
        File(st, "persist_session.active").writeText("format=1\n")
        FakeRoot.exec(listOf("chmod", "0777", st.path))
        val s = Stager(fr)
        refused(s.begin("new"), "not empty")
        assertFalse(fr.legacy.exists())
        assertEquals("old", File(fr.stage, "switch_to_lineage.sh").readText())
        refused(s.begin("keep"), "LineageOS")
        val r = s.begin("aside")
        ok(r)
        val moved = fr.root.resolve("data/local/tmp").listFiles()!!.single { it.name.startsWith("oneos.old-") }
        assertEquals("tool", File(moved, "7zz").readText())
        assertTrue(File(moved, "data/system/packages.xml").isFile)
        assertTrue(File(moved, "persist_session.active").isFile)
        // The new stage holds only the root script, its plan and nothing of the old one.
        assertEquals(listOf("bin", "incoming"), fr.stage.list()!!.sorted())
        assertEquals(fr.scriptSha, Hashes.sha256(File(fr.stage, "bin/oneos_root.sh")))
        assertEquals("755", fr.mode(fr.stage))
        // And it prepares.
        for (n in s.files.keys) ok(s.receive(n))
        ok(s.receiveRaw())
        ok(s.table())
        ok(s.env())
        ok(s.finish())
    }

    @Test
    fun keepAdoptsAColorOsStageAndMovesLeftoversToTheAttic() = eachShell { fr ->
        // The owner's Fold: a stage scripts/deploy-phone.sh made (no marker), a ColorOS guest, the N6 image.
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val s = Stager(fr, Profiles.F8U)
        val st = fr.stage.apply { mkdirs() }
        File(st, "data/system").mkdirs()
        File(st, "data/system/packages.xml").writeText("com.oplus.launcher com.coloros.gallery3d")
        File(st, "data/takeover.log").writeText("guest log")
        File(st, "system.raw").writeBytes(s.raw)
        File(st, "framework_patched.jar").writeText("old run")
        File(st, "tethering_payload.img").writeText("never mounted")
        File(st, "auto_return.log").writeText("old session\n")
        File(st, "persist_session.active").writeText("format=2\nboot_id=x\n")
        File(st, "persist_props.snapshot").writeText("persist.sys.locale=en-US\n")
        ok(s.begin("keep"))
        // Another stage's persist snapshot is never trusted: in the attic, not deleted.
        assertFalse(File(st, "persist_session.active").exists())
        val attic = File(st, "attic").listFiles()!!.single()
        assertTrue(File(attic, "persist_props.snapshot").isFile)
        // Image already on the phone: root hashes it, the .gz is skipped.
        val kr = fr.run(RootScript.Verb.KEEP_RAW, s.raw.size.toString(), Hashes.sha256(s.raw))
        ok(kr)
        for (n in s.files.keys) ok(s.receive(n))
        ok(s.table())
        ok(s.env())
        ok(s.finish())
        // Guest data untouched; leftovers the scripts would bind are in the attic; logs stay.
        assertEquals("guest log", File(st, "data/takeover.log").readText())
        assertFalse(File(st, "framework_patched.jar").exists())
        assertFalse(File(st, "tethering_payload.img").exists())
        assertTrue(File(st, "auto_return.log").isFile)
        val attics = File(st, "attic").walkTopDown().filter { it.isFile }.map { it.name }.toSet()
        assertTrue(attics.containsAll(listOf("framework_patched.jar", "tethering_payload.img", "persist_props.snapshot")))
        assertTrue(File(st, "system.raw").isFile)
    }

    @Test
    fun keepRawMovesAWrongImageToTheAttic() = eachShell { fr ->
        val s = Stager(fr)
        val st = fr.stage.apply { mkdirs() }
        File(st, "system.raw").writeBytes(s.raw.copyOf().also { it[100] = 9 })
        ok(s.begin("keep"))
        refused(fr.run(RootScript.Verb.KEEP_RAW, s.raw.size.toString(), Hashes.sha256(s.raw)), "moved to the attic")
        assertFalse(File(st, "system.raw").exists())
        assertTrue(File(st, "attic").walkTopDown().any { it.name == "system.raw" })
    }

    @Test
    fun launcherRunsOnlyThePinnedRootOwnedScript() = eachShell { fr ->
        val s = Stager(fr)
        // Nothing installed: only begin may install, from stdin, checked against the pin.
        refused(s.finish(), "not in the stage")
        refused(fr.run(RootScript.Verb.BEGIN, "new", s.profile.id, s.imageId, s.set.id, "4", stdin = "echo hacked\n".toByteArray()), "did not arrive intact")
        assertFalse(File(fr.stage, "bin/oneos_root.sh").exists())
        ok(s.begin())
        // A changed installed copy is never run (recover installs the pinned one only into a stage with a marker).
        File(fr.stage, "bin/oneos_root.sh").appendText("\necho changed\n")
        refused(s.finish(), "or it changed")
        refused(fr.run(RootScript.Verb.RECOVER), "nothing to restore")
        assertTrue(File(fr.stage, "bin/oneos_root.sh").readText().endsWith("echo changed\n"))
        ok(s.begin("keep"))
        assertEquals(fr.scriptSha, Hashes.sha256(File(fr.stage, "bin/oneos_root.sh")))
        // A bin that is not root's folder (a link) is moved aside, never followed.
        val other = File(fr.root, "elsewhere").apply { mkdirs() }
        File(fr.stage, "bin").renameTo(File(fr.root, "oldbin"))
        java.nio.file.Files.createSymbolicLink(File(fr.stage, "bin").toPath(), other.toPath())
        ok(s.begin("keep"))
        assertTrue(other.list()!!.isEmpty())
        assertTrue(fr.stage.list()!!.any { it.startsWith("bin.old-") })
        // A stage that is a link is refused, its target untouched.
        fr.stage.renameTo(File(fr.root, "realstage"))
        java.nio.file.Files.createSymbolicLink(fr.stage.toPath(), other.toPath())
        refused(s.begin("aside"), "is not a folder")
        assertTrue(other.list()!!.isEmpty())
    }

    @Test
    fun recoverRunsOnlyThePreparedGuestProps() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        ok(fr.run(RootScript.Verb.RECOVER))
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        val r = fr.run(RootScript.Verb.RECOVER)
        ok(r)
        assertTrue(r.toString(), r.out.contains("fake guest_props recover"))
        fr.env["FAKE_RC"] = "3"
        refused(fr.run(RootScript.Verb.RECOVER), "may still be running")
        fr.env.remove("FAKE_RC")
        File(fr.stage, "guest_props.sh").appendText("# changed\n")
        refused(fr.run(RootScript.Verb.RECOVER), "not the prepared one")
    }

    /**
     * 0.3.7: the Pixel 11 Fold image on the Fold with its own set: every file a Pixel session uses, in the
     * modes scripts/deploy-phone.sh gives them, and the launch checks pass. Its Google services are presented
     * by the session, so no launch may hide them.
     */
    @Test
    fun pixelImageWithItsSetOnTheFold() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val s = Stager(fr, Profiles.F8U, Images.ID_PIXEL_YOGI)
        assertEquals(PackageSets.PIXEL_F8U, s.set)
        s.prepare()
        val stage = fr.stage
        val sums = ShaList.parse(File(stage, "files.sha256").readText()).entries
        assertEquals((RootScript.SCRIPTS + PackageSets.PIXEL_F8U.names).toSet(), sums.keys)
        for (n in listOf("vold_patched", "service.incremental_patched.so", "oneos-telephony.jar", "oneos-telephony.sha256", "OneOSPhoneInjection.apk",
            "OneOSPixelStatusBar.apk", PackageSets.GUEST_APP, PackageSets.GMS_PAYLOAD, PackageSets.CELLBROADCAST, "telephonycore_payload.img")) {
            assertTrue(n, File(stage, n).isFile)
        }
        for (n in listOf("surfaceflinger_patched", "oplus-services_patched.jar", PackageSets.WALLPAPER_GRID_RRO, PackageSets.TETHERING)) {
            assertFalse(n, File(stage, n).exists())
        }
        // Modes: vold_patched executable like the scripts (guest_prepare.sh binds it over the guest's vold), the rest 0644.
        assertEquals("755", fr.mode(File(stage, "vold_patched")))
        assertEquals("755", fr.mode(File(stage, "guest_prepare.sh")))
        for (n in listOf("service.incremental_patched.so", "services_patched.jar", "guards.txt", "oneos-telephony.jar", "oneos-telephony.sha256", PackageSets.GUEST_APP, PackageSets.GMS_PAYLOAD)) {
            assertEquals(n, "644", fr.mode(File(stage, n)))
        }
        for (f in PackageSets.PIXEL_F8U.files) assertEquals(f.name, f.mode.removePrefix("0"), fr.mode(File(stage, f.name)))
        val m = StageMarker.parse(File(stage, StageMarker.FILE_NAME).readText())!!
        assertEquals(StageMarker(4, "f8u", "pixel11fold-yogi", "pixel-f8u", m.createdEpoch), m)
        assertEquals(SessionEnv.generate(Profiles.F8U), File(stage, "session.env").readText())
        assertTrue(File(stage, "session.env").readLines().containsAll(listOf("ONEOS_GUEST_FORM=fold", "ONEOS_GUEST_HIDE_GMS=0")))
        // system.raw.id: the Pixel image's record (the test root's stand-in bytes).
        assertEquals(listOf(s.raw.size.toString(), Hashes.sha256(s.raw)), File(stage, "system.raw.id").readText().trim().split(' ').take(2))
        refused(s.launch(), "test root: every launch check passed")
        refused(s.launch("dry"), "test root")
        // Hiding Google services: refused by launch and env, and the refused launch changes nothing.
        val before = fr.snapshot()
        refused(s.launch(hideGms = "1"), "pixel11fold-yogi has no Google services a session may hide")
        assertEquals(before, fr.snapshot())
        ok(s.begin("keep"))
        refused(s.env(SessionEnv.generate(s.profile).replace("ONEOS_GUEST_HIDE_GMS=0", "ONEOS_GUEST_HIDE_GMS=1")), "hides Google services, but pixel11fold-yogi has none a session may hide")
        assertFalse(File(stage, "incoming/session.env.part").exists())
        // A changed guarded binary or a changed injection check is refused at launch.
        s.prepare("keep")
        for (n in listOf("vold_patched", "oneos-telephony.sha256")) {
            File(stage, n).appendText("x")
            refused(s.launch(), "$n changed")
            File(stage, n).writeBytes(s.files.getValue(n))
        }
        refused(s.launch(), "test root: every launch check passed")
    }

    /**
     * Switching the Fold's stage between the ColorOS and the Pixel set (keep, no guest data yet): finish moves
     * every file the new set does not carry to the attic, so guest_prepare.sh can never use another set's
     * vold_patched, oneos-telephony.* or OneOSGuest.apk, or ColorOS's surfaceflinger_patched and oplus jars.
     */
    @Test
    fun switchingTheFoldBetweenColorOsAndPixelLeavesNoOtherSetsFiles() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val n6 = Stager(fr, Profiles.F8U)
        val pixel = Stager(fr, Profiles.F8U, Images.ID_PIXEL_YOGI)
        val onlyN6 = PackageSets.N6_F8U.names - PackageSets.PIXEL_F8U.names.toSet()
        val onlyPixel = PackageSets.PIXEL_F8U.names - PackageSets.N6_F8U.names.toSet()
        assertTrue(onlyN6.containsAll(listOf("surfaceflinger_patched", "oplus-services_patched.jar", PackageSets.WALLPAPER_GRID_RRO)))
        assertTrue(onlyPixel.containsAll(listOf("oneos-telephony.jar", "oneos-telephony.sha256", "OneOSPixelStatusBar.apk", PackageSets.GMS_PAYLOAD)))
        // Both sets carry the guest vold as gvld and the in-guest app since 0.4.8 (each its own vold build).
        assertTrue(listOf("vold_patched", "service.incremental_patched.so", PackageSets.GUEST_APP).none { it in onlyN6 || it in onlyPixel })
        fun attic() = File(fr.stage, "attic").walkTopDown().filter { it.isFile }.map { it.name }.toSet()

        n6.prepare()
        refused(n6.launch(), "test root: every launch check passed")
        // To the Pixel set: the Find N6 image, its files and its marker go; nothing of them stays where the scripts look.
        pixel.prepare("keep")
        for (n in onlyN6) assertFalse(n, File(fr.stage, n).exists())
        assertTrue(attic().containsAll(onlyN6))
        assertEquals(StageMarker.parse(File(fr.stage, StageMarker.FILE_NAME).readText())!!.setId, PackageSets.ID_PIXEL_F8U)
        refused(pixel.launch(), "test root: every launch check passed")
        // And back to ColorOS.
        n6.prepare("keep")
        for (n in onlyPixel) assertFalse(n, File(fr.stage, n).exists())
        assertTrue(attic().containsAll(onlyPixel))
        refused(n6.launch(), "test root: every launch check passed")
        // A Pixel file put back after finish (not root's own doing) is refused at launch, the .sha256 too.
        for (n in onlyPixel) {
            File(fr.stage, n).writeText("left\n")
            refused(n6.launch(), "$n is in the stage but was not prepared")
            File(fr.stage, n).delete()
        }
        refused(n6.launch(), "test root: every launch check passed")
        // Once the Pixel system has guest data, keeping it for the Find N6 image is refused; moved aside it stays whole.
        pixel.prepare("keep")
        File(fr.stage, "data/system").mkdirs()
        File(fr.stage, "data/system/packages.xml").writeText("com.google.android.gms com.google.android.apps.nexuslauncher")
        val before = fr.snapshot()
        refused(n6.begin("keep"), "guest data is from pixel11fold-yogi, not coloros17-findn6")
        assertEquals(before, fr.snapshot())
        ok(n6.begin("aside"))
        val old = fr.root.resolve("data/local/tmp").listFiles()!!.single { it.name.startsWith("oneos.old-") }
        assertTrue(File(old, "data/system/packages.xml").isFile)
        assertTrue(File(old, "vold_patched").isFile)
    }

    /** 0.3.4: the Galaxy S25 (SM-S931, pa1q, SM8750) takes the S Ultra sets under its own profile, and only on itself. */
    @Test
    fun galaxyS25TakesTheSUltraSets() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-S931B"
        fr.props["ro.product.device"] = "pa1q"
        fr.props["ro.soc.model"] = "SM8750"
        fr.writeProps()
        val s = Stager(fr, Profiles.S_8750)
        assertEquals(PackageSets.X9U_SULTRA, s.set)
        s.prepare()
        val m = StageMarker.parse(File(fr.stage, StageMarker.FILE_NAME).readText())!!
        assertEquals(StageMarker(4, "s-8750", Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, m.createdEpoch), m)
        assertEquals(SessionEnv.generate(Profiles.S_8750), File(fr.stage, "session.env").readText())
        refused(s.launch(), "test root: every launch check passed")
        // The same stage on an S25 Ultra, or on an S25 with another codename: refused.
        fr.props["ro.product.model"] = "SM-S938B"
        fr.writeProps()
        refused(s.launch(), "is not a SM-S931")
        fr.props["ro.product.model"] = "SM-S931B"
        fr.props["ro.product.device"] = "pa3q"
        fr.writeProps()
        refused(s.launch(), "codename pa3q, profile s-8750 is pa1q")
        // Its pairs are exactly the S Ultra's: never the Fold's Find N6 or Pixel image; the IN build
        // (0.3.3-0.3.6, again from 0.4.11) with its own set only.
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "s-8750", Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8U, "4"), "does not run pixel11fold-yogi")
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "s-8750", Images.ID_FIND_X9U_IN, PackageSets.ID_X9U_SULTRA, "4"), "is not the file set of coloros17-findx9u-in")
        assertEquals(PackageSets.X9U_IN_SULTRA, Stager(fr, Profiles.S_8750, Images.ID_FIND_X9U_IN).set)
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "s-8750", Images.ID_FIND_N6, PackageSets.ID_N6_F8U, "4"), "does not run coloros17-findn6")
    }

    /** 0.4.8: the Galaxy Z Fold7 (SM-F966, q7q, SM8750) takes the Find N6 image with the Fold's set, and only on itself. */
    @Test
    fun galaxyZFold7TakesTheFindN6Set() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F966B"
        fr.props["ro.product.device"] = "q7q"
        fr.props["ro.soc.model"] = "SM8750"
        fr.writeProps()
        val s = Stager(fr, Profiles.FOLD7)
        assertEquals(PackageSets.N6_F8U, s.set)
        s.prepare()
        val m = StageMarker.parse(File(fr.stage, StageMarker.FILE_NAME).readText())!!
        assertEquals(StageMarker(4, "f7", Images.ID_FIND_N6, PackageSets.ID_N6_F8U, m.createdEpoch), m)
        assertEquals(SessionEnv.generate(Profiles.FOLD7), File(fr.stage, "session.env").readText())
        refused(s.launch(), "test root: every launch check passed")
        // The same stage on a Fold8 Ultra: refused.
        fr.props["ro.product.model"] = "SM-F976B"
        fr.writeProps()
        refused(s.launch(), "is not a SM-F966")
        // Never the Pixel image (it needs SVE) nor the S Ultras' Find X9 Ultra image.
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "f7", Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8U, "4"), "does not run pixel11fold-yogi")
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "f7", Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, "4"), "does not run coloros17-findx9u")
    }

    /** 0.4.10: the Galaxy S25+ (SM-S936, pa2q, SM8750) takes the S25's Find X9 Ultra set, never a Pixel or Fold image. */
    @Test
    fun galaxyS25PlusTakesTheSUltraSet() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-S936B"
        fr.props["ro.product.device"] = "pa2q"
        fr.props["ro.soc.model"] = "SM8750"
        fr.writeProps()
        val s = Stager(fr, Profiles.S_PLUS_8750)
        assertEquals(PackageSets.X9U_SULTRA, s.set)
        s.prepare()
        val m = StageMarker.parse(File(fr.stage, StageMarker.FILE_NAME).readText())!!
        assertEquals(StageMarker(4, "s-plus-8750", Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, m.createdEpoch), m)
        refused(s.launch(), "test root: every launch check passed")
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "s-plus-8750", Images.ID_PIXEL_KODIAK, PackageSets.ID_PIXEL_SULTRA, "4"), "does not run pixel11pro-kodiak")
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "s-plus-8750", Images.ID_FIND_N6, PackageSets.ID_N6_F8U, "4"), "does not run coloros17-findn6")
    }

    /** 0.4.10: the Galaxy Z Fold8 (SM-F971, h8q, SM8850) takes the Fold's two images, the Find N6 one with its own set (0.4.14), and only on itself. */
    @Test
    fun galaxyZFold8TakesTheFoldSets() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F971B"
        fr.props["ro.product.device"] = "h8q"
        fr.props["ro.soc.model"] = "SM8850"
        fr.writeProps()
        val n6 = Stager(fr, Profiles.FOLD8)
        // 0.4.14 (pull request #1): the Find N6 image with its own set, n6-f8.
        assertEquals(PackageSets.N6_F8, n6.set)
        n6.prepare()
        val marker = StageMarker.parse(File(fr.stage, StageMarker.FILE_NAME).readText())!!
        assertEquals(listOf("f8", PackageSets.ID_N6_F8), listOf(marker.profileId, marker.setId))
        for (name in PackageSets.N6_F8.names) assertTrue(name, File(fr.stage, name).isFile)
        refused(n6.launch(), "test root: every launch check passed")
        val pixel = Stager(fr, Profiles.FOLD8, Images.ID_PIXEL_YOGI)
        assertEquals(PackageSets.PIXEL_F8, pixel.set)
        // On a Fold8 Ultra: refused.
        fr.props["ro.product.model"] = "SM-F976B"
        fr.writeProps()
        refused(n6.launch(), "is not a SM-F971")
        refused(fr.run(RootScript.Verb.BEGIN, "keep", "f8", Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, "4"), "does not run coloros17-findx9u")
    }

    /**
     * 0.4.11: the Galaxy S26 (SM-S942 and the Japanese SC-51G, m1q, SM8850)
     * takes the S Ultra's two sets; the S24 Ultra (SM-S928, e3q, SM8650), S23
     * (SM-S911, dm1q) and S23+ (SM-S916, dm2q, SM8550) take the X9U set only.
     */
    @Test
    fun galaxyS26S24UltraAndS23sTakeTheSUltraSets() {
        for ((p, model) in listOf(
            Profiles.S_8850 to "SM-S942B",
            Profiles.S_8850_JP to "SC-51G",
            Profiles.S_ULTRA_8650 to "SM-S928B",
            Profiles.S_8550 to "SM-S911B",
            Profiles.S_PLUS_8550 to "SM-S916U",
            Profiles.S_PLUS_8850 to "SM-S947U",
            // 0.4.17: the Exynos S26+ and Z Flip7 (root compares ro.soc.model as Android reports it).
            Profiles.S_PLUS_9965 to "SM-S947B",
            Profiles.FLIP7 to "SM-F766U",
            // 0.4.29: the Galaxy A57.
            Profiles.A57 to "SM-A576B",
            // 0.4.31: the Galaxy A56.
            Profiles.A56 to "SM-A566B",
            Profiles.FLIP5 to "SM-F731B",
        )) {
            eachShell { fr ->
                fr.props["ro.product.model"] = model
                fr.props["ro.product.device"] = p.codename
                fr.props["ro.soc.model"] = p.socModel
                fr.writeProps()
                val s = Stager(fr, p)
                assertEquals(p.id, PackageSets.X9U_SULTRA, s.set)
                assertEquals(p.id, PackageSets.X9U_IN_SULTRA, Stager(fr, p, Images.ID_FIND_X9U_IN).set)
                if (p.choice(Images.ID_PIXEL_KODIAK) != null) {
                    assertEquals(p.id, PackageSets.PIXEL_SULTRA, Stager(fr, p, Images.ID_PIXEL_KODIAK).set)
                } else {
                    refused(fr.run(RootScript.Verb.BEGIN, "keep", p.id, Images.ID_PIXEL_KODIAK, PackageSets.ID_PIXEL_SULTRA, "4"), "does not run pixel11pro-kodiak")
                }
                refused(fr.run(RootScript.Verb.BEGIN, "keep", p.id, Images.ID_FIND_N6, PackageSets.ID_N6_F8U, "4"), "does not run coloros17-findn6")
                s.prepare()
                val m = StageMarker.parse(File(fr.stage, StageMarker.FILE_NAME).readText())!!
                assertEquals(StageMarker(4, p.id, Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, m.createdEpoch), m)
                refused(s.launch(), "test root: every launch check passed")
            }
        }
    }

    /** The CN builds have no Google services: neither env nor launch may hide them, and a refused launch changes nothing. */
    @Test
    fun googleServicesCannotBeHiddenOnACnImage() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val before = fr.snapshot()
        val env = File(fr.stage, "session.env").readText()
        refused(s.launch(hideGms = "1"), "coloros17-findx9u has no Google services a session may hide")
        assertEquals(before, fr.snapshot())
        assertEquals(env, File(fr.stage, "session.env").readText())
        ok(s.begin("keep"))
        refused(s.env(SessionEnv.generate(s.profile).replace("ONEOS_GUEST_HIDE_GMS=0", "ONEOS_GUEST_HIDE_GMS=1")), "hides Google services, but coloros17-findx9u has none a session may hide")
        assertFalse(File(fr.stage, "incoming/session.env.part").exists())
    }

    /** The staged image decides the set: root refuses any other set, at begin, finish, receive and launch (fail closed). */
    @Test
    fun aSetThatIsNotTheImagesIsRefused() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val s = Stager(fr, Profiles.F8U, Images.ID_PIXEL_YOGI)
        // begin: a ColorOS set with the Pixel image on the Fold; an image the phone does not take.
        refused(s.begin(setId = PackageSets.ID_N6_F8U), "n6-f8u is not the file set of pixel11fold-yogi on f8u")
        refused(s.begin(setId = PackageSets.ID_X9U_SULTRA), "is not the file set")
        refused(fr.run(RootScript.Verb.BEGIN, "new", "s-ultra-8850", Images.ID_PIXEL_YOGI, PackageSets.ID_PIXEL_F8U, "4"), "does not run pixel11fold-yogi")
        refused(fr.run(RootScript.Verb.BEGIN, "new", "f8u", Images.ID_FIND_X9U, PackageSets.ID_X9U_SULTRA, "4"), "does not run coloros17-findx9u")
        refused(fr.run(RootScript.Verb.BEGIN, "new", "f8u", "coloros17-findx9u-in", "x9u-in-f8u", "4"), "does not run coloros17-findx9u-in")
        assertFalse(File(fr.stage, "incoming/plan").exists())
        // finish with another set than begin's.
        ok(s.begin())
        refused(s.finish(PackageSets.ID_N6_F8U), "finish does not match the plan")
        // A file of another set, either way.
        refused(s.receive("surfaceflinger_patched", "x".toByteArray()), "not a file of pixel-f8u")
        val n6 = Stager(fr, Profiles.F8U)
        ok(n6.begin("keep"))
        refused(n6.receive("OneOSPhoneInjection.apk", "x".toByteArray()), "not a file of n6-f8u")
        refused(n6.receive("oneos-telephony.sha256", "x".toByteArray()), "not a file of n6-f8u")
        // A plan that pairs the image with another set (not root's own doing) is not used.
        File(fr.stage, "incoming/plan").writeText("f8u pixel11fold-yogi n6-f8u 4 1\n")
        refused(n6.receive("art_payload.img"), "the plan is not well formed")
        // launch: a marker naming another set with the Pixel image, or no set (0.3.2), is refused.
        s.prepare("keep")
        refused(s.launch(), "test root")
        val mk = File(fr.stage, StageMarker.FILE_NAME)
        for (bad in listOf(
            StageMarker(4, "f8u", Images.ID_PIXEL_YOGI, PackageSets.ID_N6_F8U, 1),
            StageMarker(4, "f8u", Images.ID_PIXEL_YOGI, PackageSets.ID_X9U_SULTRA, 1),
            StageMarker(4, "f8u", Images.ID_PIXEL_YOGI, null, 1),
        )) {
            mk.writeText(bad.toJson())
            refused(s.launch(), "not its file set for f8u")
        }
        // A stage the IN build left (0.3.3-0.3.6): this build does not switch it.
        mk.writeText(StageMarker(4, "f8u", "coloros17-findx9u-in", "x9u-in-f8u", 1).toJson())
        refused(s.launch(), "not its file set for f8u")
    }

    /** A 0.3.2 stage (oneos.stage/1, no set) stays OneOS's: an unfinished session is restored first, never trusted away. */
    @Test
    fun anOlderStageIsStillOursForKeepAndRecover() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        File(fr.stage, StageMarker.FILE_NAME).writeText(StageMarker(4, s.profile.id, s.imageId, null, 1_792_000_000).toJson())
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        refused(s.begin("keep"), "restore One UI's settings first")
        assertTrue(File(fr.stage, "persist_session.active").isFile)
        val r = fr.run(RootScript.Verb.RECOVER)
        ok(r)
        assertTrue(r.toString(), r.out.contains("fake guest_props recover"))
        File(fr.stage, "persist_session.active").delete()
        refused(s.launch(), "no file set")
        ok(s.begin("keep"))
    }

    /**
     * 0.3.2's oneos_root.sh is not 0.3.3's pin: an unfinished 0.3.2 session
     * must still be restorable after the update (Prepare and Switch BLOCK until
     * it is), so recover installs the pinned script into OneOS's stage first.
     */
    @Test
    fun anOlderBuildsUnfinishedSessionIsStillRestored() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        File(fr.stage, StageMarker.FILE_NAME).writeText(StageMarker(6, s.profile.id, s.imageId, null, 1_792_000_000).toJson())
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        val bin = File(fr.stage, "bin/oneos_root.sh")
        bin.writeText("# an older build's oneos_root.sh\nexit 9\n")
        refused(s.launch(), "or it changed")
        val r = fr.run(RootScript.Verb.RECOVER)
        ok(r)
        assertTrue(r.toString(), r.out.contains("fake guest_props recover"))
        assertEquals(fr.scriptSha, Hashes.sha256(bin))
        assertEquals("755", fr.mode(bin))
        // No marker, or a bin that is not root's folder alone: nothing is installed, nothing changes.
        bin.writeText("exit 9\n")
        val mk = File(fr.stage, StageMarker.FILE_NAME)
        val away = File(fr.root, "marker")
        assertTrue(mk.renameTo(away))
        val before = fr.snapshot()
        refused(fr.run(RootScript.Verb.RECOVER), "nothing to restore")
        assertEquals(before, fr.snapshot())
        assertTrue(away.renameTo(mk))
        FakeRoot.exec(listOf("chmod", "0777", File(fr.stage, "bin").path))
        refused(fr.run(RootScript.Verb.RECOVER), "nothing to restore")
        assertEquals("exit 9\n", bin.readText())
    }

    /**
     * 0.3.3: a phone takes two images, and the stage's guest data stays with
     * the one that made it. Keep with another image is refused before any
     * change (from the marker, or from the plan of a preparation that did not
     * finish); moved aside, the data stays with the old stage. 0.3.7: the
     * Fold's Find N6 data, then the Pixel image.
     */
    @Test
    fun keepRefusesAnotherImagesGuestData() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val n6 = Stager(fr, Profiles.F8U)
        val pixel = Stager(fr, Profiles.F8U, Images.ID_PIXEL_YOGI)
        n6.prepare()
        // Prepared but never switched: no guest data, so the other image may keep the stage.
        ok(pixel.begin("keep"))
        n6.prepare("keep")
        // The owner's Find N6 data.
        File(fr.stage, "data/system").mkdirs()
        File(fr.stage, "data/system/packages.xml").writeText("com.oplus.launcher com.coloros.gallery3d")
        val before = fr.snapshot()
        refused(pixel.begin("keep"), "guest data is from coloros17-findn6, not pixel11fold-yogi")
        assertEquals(before, fr.snapshot())
        // The marker in the attic (a preparation that stopped): its plan says whose data it is.
        ok(n6.begin("keep"))
        assertFalse(File(fr.stage, StageMarker.FILE_NAME).exists())
        val partial = fr.snapshot()
        refused(pixel.begin("keep"), "guest data is from coloros17-findn6")
        assertEquals(partial, fr.snapshot())
        ok(pixel.begin("aside"))
        assertFalse(File(fr.stage, "data").exists())
        val old = fr.root.resolve("data/local/tmp").listFiles()!!.single { it.name.startsWith("oneos.old-") }
        assertTrue(File(old, "data/system/packages.xml").isFile)
        // The new stage prepares the Pixel image from nothing.
        for (n in pixel.files.keys) ok(pixel.receive(n))
        ok(pixel.receiveRaw())
        ok(pixel.table())
        ok(pixel.env())
        ok(pixel.finish())
        refused(pixel.launch(), "test root: every launch check passed")
    }

    /**
     * 0.3.7: guest data stays with its own system on a stage OneOS did not prepare too (scripts/deploy-phone.sh:
     * no marker, no plan): its ColorOS data is never kept for the Pixel image, nor its Pixel data (Pixel's
     * launcher, no ColorOS package) for a ColorOS image; each refusal changes nothing, and aside keeps it whole.
     * Its own system may keep it. A marker that names an image its data is not from is refused the same way.
     */
    @Test
    fun keepRefusesAnotherSystemsDataOnAStageOneOsDidNotPrepare() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val n6 = Stager(fr, Profiles.F8U)
        val pixel = Stager(fr, Profiles.F8U, Images.ID_PIXEL_YOGI)
        val st = fr.stage
        fun foreignStage(packages: String) {
            st.deleteRecursively()
            File(st, "data/system").mkdirs()
            File(st, "data/system/packages.xml").writeText(packages)
            File(st, "system.raw").writeBytes(pixel.raw)
            File(st, "auto_return.log").writeText("old session\n")
        }
        // Refused, and (once the launcher has put the root script in bin, as the first begin does) nothing changes.
        fun refusedUnchanged(r: () -> FakeRoot.Run, part: String) {
            refused(r(), part)
            val before = fr.snapshot()
            refused(r(), part)
            assertEquals(before, fr.snapshot())
        }
        // The deploy-phone.sh ColorOS stage, then the Pixel image: refused; its own image keeps it.
        foreignStage("com.oplus.launcher com.coloros.gallery3d com.google.android.gms")
        refusedUnchanged({ pixel.begin("keep") }, "another system's guest data (coloros), not pixel11fold-yogi's")
        ok(n6.begin("keep"))
        // The Fold's deploy-phone.sh Pixel stage (runs 41-44): refused for the Find N6 image, kept for the Pixel image.
        foreignStage("com.google.android.gms com.google.android.apps.nexuslauncher")
        refusedUnchanged({ n6.begin("keep") }, "another system's guest data (pixel), not coloros17-findn6's")
        ok(pixel.begin("keep"))
        assertEquals("com.google.android.gms com.google.android.apps.nexuslauncher", File(st, "data/system/packages.xml").readText())
        // Pixel data on a stage whose marker names the Find N6 image (deploy-phone.sh over an app stage without --fresh).
        assertTrue(File(st, "data").renameTo(File(fr.root, "pixel-data")))
        n6.prepare("keep")
        assertTrue(File(fr.root, "pixel-data").renameTo(File(st, "data")))
        refusedUnchanged({ n6.begin("keep") }, "another system's guest data (pixel), not coloros17-findn6's")
        // LineageOS data names the image it is refused for.
        foreignStage("org.lineageos.updater")
        refusedUnchanged({ n6.begin("keep") }, "the stage holds LineageOS data, not coloros17-findn6's")
        // Moved aside, the data stays whole with the old stage.
        foreignStage("com.google.android.apps.nexuslauncher")
        ok(n6.begin("aside"))
        assertFalse(File(st, "data").exists())
        val old = fr.root.resolve("data/local/tmp").listFiles()!!.filter { it.name.startsWith("oneos.old-") }
        assertTrue(old.any { File(it, "data/system/packages.xml").readText() == "com.google.android.apps.nexuslauncher" })
    }

    /** recover's reply says what a Pixel session's restore puts back: the language only (guest_props.sh recover). */
    @Test
    fun recoverAfterAPixelSessionSaysWhatItRestored() = eachShell { fr ->
        fr.props["ro.product.model"] = "SM-F976B"
        fr.props["ro.product.device"] = "q8q"
        fr.writeProps()
        val pixel = Stager(fr, Profiles.F8U, Images.ID_PIXEL_YOGI)
        pixel.prepare()
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        val r = fr.run(RootScript.Verb.RECOVER)
        pixel.ok(r)
        assertEquals("recover restored the language only (other settings the session saved stay)", r.reply.ok)
        // A ColorOS stage's reply is as before (the stand-in guest_props.sh leaves the marker; the real one deletes it).
        File(fr.stage, "persist_session.active").delete()
        val n6 = Stager(fr, Profiles.F8U)
        n6.prepare("keep")
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        assertEquals("recover restored", fr.run(RootScript.Verb.RECOVER).reply.ok)
    }

    /**
     * The path a hideable image takes (ImageRef.gmsHideable; none in 0.3.7, so the shipped IMAGES_GMS is empty):
     * a copy of the script with the Find X9 Ultra image in IMAGES_GMS, under its own pin. env accepts
     * ONEOS_GUEST_HIDE_GMS=1, and launch writes this launch's choice into session.env after every check.
     */
    @Test
    fun aHideableImagesLaunchWritesItsGoogleServicesChoice() {
        // 0.4.11: the Find X9 Ultra IN build, the one image whose Google services a launch may hide.
        assertTrue(Shipped.rootScriptText.contains("\nIMAGES_GMS=\"coloros17-findx9u-in\"\n"))
        eachShell { fr ->
            val s = Stager(fr, Profiles.S_ULTRA_8850, Images.ID_FIND_X9U_IN)
            assertEquals(PackageSets.X9U_IN_SULTRA, s.set)
            s.prepare()
            val env = File(fr.stage, "session.env")
            assertTrue(env.readLines().contains("ONEOS_GUEST_HIDE_GMS=0"))
            refused(s.launch(hideGms = "1"), "test root: every launch check passed")
            assertTrue(env.readLines().contains("ONEOS_GUEST_HIDE_GMS=1"))
            assertEquals(env.readLines().size, SessionEnv.generate(s.profile).lines().filter { it.isNotEmpty() }.size)
            refused(s.launch(hideGms = "0"), "test root: every launch check passed")
            assertEquals(SessionEnv.generate(s.profile), env.readText())
            // 0.4.20: the Samsung IMS choice the same way, on any image; nothing else of the file moves.
            refused(s.launch(secIms = "1"), "test root: every launch check passed")
            assertEquals(SessionEnv.generate(s.profile).replace("ONEOS_GUEST_SEC_IMS=0", "ONEOS_GUEST_SEC_IMS=1"), env.readText())
            // 0.4.32: the Knox edm stub choice the same way.
            refused(s.launch(edmStub = "1"), "test root: every launch check passed")
            assertEquals(SessionEnv.generate(s.profile).replace("ONEOS_GUEST_EDM_STUB=0", "ONEOS_GUEST_EDM_STUB=1"), env.readText())
            refused(s.launch(), "test root: every launch check passed")
            assertEquals(SessionEnv.generate(s.profile), env.readText())
            // env accepts the 1 for that image (Prepare writes 0; a launch decides).
            ok(s.begin("keep"))
            s.ok(s.env(SessionEnv.generate(s.profile).replace("ONEOS_GUEST_HIDE_GMS=0", "ONEOS_GUEST_HIDE_GMS=1")))
        }
    }

    /**
     * 0.4.23, Cool down when hot (Advanced): Prepare writes ONEOS_HEAT_CAP=1, a launch writes its own
     * choice after every check, env takes 0 or 1 and nothing else, and launch needs the word.
     */
    @Test
    fun aLaunchWritesItsHeatCap() {
        eachShell { fr ->
            val s = Stager(fr)
            s.prepare()
            val env = File(fr.stage, "session.env")
            assertTrue(env.readLines().contains("ONEOS_HEAT_CAP=1"))
            refused(s.launch(heatCap = "0"), "test root: every launch check passed")
            assertTrue(env.readLines().contains("ONEOS_HEAT_CAP=0"))
            assertEquals(SessionEnv.generate(s.profile).replace("ONEOS_HEAT_CAP=1", "ONEOS_HEAT_CAP=0"), env.readText())
            refused(s.launch(heatCap = "1"), "test root: every launch check passed")
            assertEquals(SessionEnv.generate(s.profile), env.readText())
            // The launcher never builds a launch without the word (RootScript.problems, tested below).
            assertTrue(runCatching { fr.run(RootScript.Verb.LAUNCH, "session", s.code, "0123456789abcdef", "0") }.isFailure)
            ok(s.begin("keep"))
            s.ok(s.env(SessionEnv.generate(s.profile).replace("ONEOS_HEAT_CAP=1", "ONEOS_HEAT_CAP=0")))
            ok(s.begin("keep"))
            refused(s.env(SessionEnv.generate(s.profile).replace("ONEOS_HEAT_CAP=1", "ONEOS_HEAT_CAP=2")), "ONEOS_HEAT_CAP=2")
        }
    }

    // --- The names up to 0.3.6 (lineage_stage, lineage_stage.old-*): migrate_legacy ---

    /**
     * A stage 0.3.6 prepared, at the old path: the session scripts under their
     * old names, that build's root script in its bin, ColorOS data and a log.
     */
    private fun legacyStage(fr: FakeRoot, s: Stager): File {
        s.prepare()
        File(fr.stage, "data/system").mkdirs()
        File(fr.stage, "data/system/packages.xml").writeText("com.oplus.launcher com.coloros.gallery3d")
        File(fr.stage, "auto_return.log").writeText("0.3.6 session\n")
        for ((now, before) in OLD_SCRIPT_NAMES) assertTrue(File(fr.stage, now).renameTo(File(fr.stage, before)))
        assertTrue(fr.stage.renameTo(fr.legacy))
        File(fr.legacy, "bin/oneos_root.sh").writeText("# 0.3.6's oneos_root.sh\nexit 9\n")
        return fr.legacy
    }

    private val OLD_SCRIPT_NAMES = mapOf(
        "oneos_switch.sh" to "switch_to_lineage.sh",
        "guest_prepare.sh" to "master_prepare.sh",
        "guest_start.sh" to "master_inner.sh",
    )

    private fun legacyCopy(fr: FakeRoot, name: String): File = oldStage(fr, name)

    @Test
    fun anOldStageIsRenamedAndPreparesAgainWithItsData() = eachShell { fr ->
        val s = Stager(fr)
        legacyStage(fr, s)
        val copy = legacyCopy(fr, "lineage_stage.old-1792000000")
        val trash = File(fr.root, "data/local/tmp/lineage_stage.trash-1792000200").apply { File(this, "x").mkdirs() }
        File(fr.root, "data/local/tmp/lineage_stage.other").mkdirs() // not an old stage: never touched
        // The update's first root command: an older build's script is never run, the pinned one is installed in the old stage first.
        val r = s.begin("keep")
        ok(r)
        assertTrue(r.toString(), r.reply.infos.any { it.contains("renamed the stage") })
        assertFalse(fr.legacy.exists())
        assertEquals(fr.scriptSha, Hashes.sha256(File(fr.stage, "bin/oneos_root.sh")))
        // The guest data, the image and the logs came along.
        assertEquals("com.oplus.launcher com.coloros.gallery3d", File(fr.stage, "data/system/packages.xml").readText())
        assertEquals(s.raw.size.toLong(), File(fr.stage, "system.raw").length())
        assertTrue(File(fr.stage, "auto_return.log").isFile)
        // The copies, same suffix; nothing else.
        val tmp = File(fr.root, "data/local/tmp")
        assertFalse(copy.exists())
        assertTrue(File(tmp, "oneos.old-1792000000/data/system/packages.xml").isFile)
        assertFalse(trash.exists())
        assertTrue(File(tmp, "oneos.trash-1792000200/x").isDirectory)
        assertTrue(File(tmp, "lineage_stage.other").isDirectory)
        // And it prepares again with the new script names (the old ones go to the attic at finish).
        ok(fr.run(RootScript.Verb.KEEP_RAW, s.raw.size.toString(), Hashes.sha256(s.raw)))
        for (n in s.files.keys) ok(s.receive(n))
        ok(s.table())
        ok(s.env())
        ok(s.finish())
        for (before in OLD_SCRIPT_NAMES.values) {
            assertFalse(before, File(fr.stage, before).exists())
            assertTrue(before, File(fr.stage, "attic").walkTopDown().any { it.name == before })
        }
        refused(s.launch(), "test root: every launch check passed")
        // Nothing more to rename: the next verbs say nothing about it.
        assertTrue(fr.run(RootScript.Verb.OLD_LIST).reply.infos.none { it.contains("renamed") })
    }

    @Test
    fun anOldStageMovedAsideOnItsFirstVerbKeepsTheRootScript() = eachShell { fr ->
        // begin aside straight from the old stage: the new stage's bin gets the running script (SELF after the rename).
        val s = Stager(fr)
        legacyStage(fr, s)
        ok(s.begin("aside"))
        assertFalse(fr.legacy.exists())
        assertEquals(listOf("bin", "incoming"), fr.stage.list()!!.sorted())
        assertEquals(fr.scriptSha, Hashes.sha256(File(fr.stage, "bin/oneos_root.sh")))
        val moved = File(fr.root, "data/local/tmp").listFiles()!!.single { it.name.startsWith("oneos.old-") }
        assertTrue(File(moved, "data/system/packages.xml").isFile)
        // An unfinished 0.3.6 session is restored from the renamed stage (recover installs the pinned script first).
        val fr2 = s
        fr2.prepare("keep")
        File(fr.stage, "persist_session.active").writeText("format=2\nboot_id=old\n")
        assertTrue(fr.stage.renameTo(fr.legacy))
        File(fr.legacy, "bin/oneos_root.sh").writeText("exit 9\n")
        val rec = fr.run(RootScript.Verb.RECOVER)
        ok(rec)
        assertTrue(rec.toString(), rec.out.contains("fake guest_props recover"))
        assertFalse(fr.legacy.exists())
        assertTrue(File(fr.stage, "persist_session.active").isFile)
    }

    @Test
    fun aBusyOldStageIsNotRenamedAndOnlyTheOldCopyVerbsGoOn() = eachShell { fr ->
        val s = Stager(fr)
        legacyStage(fr, s)
        val copy = legacyCopy(fr, "lineage_stage.old-1792000000")
        val busyCopy = legacyCopy(fr, "lineage_stage.old-1792000100")
        // Mounted in a namespace of its own (pid 4343): every verb leaves its name as it is.
        val holder = File(fr.root, "proc/4343").apply { mkdirs() }
        File(holder, "mountinfo").writeText("22 1 253:0 / / rw - ext4 /dev/root rw\n31 22 0:41 / ${busyCopy.path}/data rw - f2fs /dev/x rw\n")
        val tmp = File(fr.root, "data/local/tmp")
        fun stays(r: FakeRoot.Run, part: String) {
            refused(r, part)
            assertTrue(fr.legacy.isDirectory)
            assertFalse(fr.stage.exists())
        }
        // Mounted under it, with 0.3.6's script in bin: the launcher refuses before it installs anything.
        fr.mountinfo(listOf("${fr.legacy.path}/rootfs"))
        stays(s.begin("keep"), "mounted in the stage")
        assertTrue(File(fr.legacy, "bin/oneos_root.sh").readText().endsWith("exit 9\n"))
        // With this build's script there (installed by an earlier verb), the script's own checks: init's table,
        // or only another process's (a guest namespace that is still around).
        File(fr.legacy, "bin/oneos_root.sh").writeBytes(fr.script)
        stays(s.begin("keep"), "cannot be renamed")
        stays(s.begin("keep"), "something is mounted")
        stays(s.launch(), "restart the phone first")
        stays(fr.run(RootScript.Verb.RECOVER), "cannot be renamed")
        fr.mountinfo(emptyList())
        val other = File(fr.root, "proc/4242").apply { mkdirs() }
        File(other, "mountinfo").writeText("22 1 253:0 / / rw - ext4 /dev/root rw\n31 22 0:41 / ${fr.legacy.path}/data/user rw - f2fs /dev/x rw\n")
        val before = fr.snapshot()
        stays(s.begin("keep"), "something is mounted")
        assertEquals(before, fr.snapshot())
        File(other, "mountinfo").writeText("22 1 253:0 / / rw - ext4 /dev/root rw\n")
        // Its image on a loop device.
        File(fr.root, "sys/block/loop0/loop/backing_file").writeText("${fr.legacy.path}/system.raw\n")
        stays(s.begin("keep"), "loop device")
        File(fr.root, "sys/block/loop0/loop/backing_file").delete()
        // A session of this boot (running, or never restarted since).
        File(fr.legacy, "persist_session.active").writeText("format=2\nboot_id=11111111-2222-3333-4444-555555555555\n")
        stays(s.begin("keep"), "session in this boot")
        // Meanwhile the old copies: listed from the old stage, the idle copy renamed (by the first verb the script ran),
        // the busy one under its old name.
        val r = fr.run(RootScript.Verb.OLD_LIST)
        ok(r)
        assertTrue(r.toString(), r.reply.infos.any { it.contains("stays at") })
        assertFalse(copy.exists())
        assertTrue(busyCopy.isDirectory)
        val rows = r.reply.results.filter { it.startsWith("old ") }.map { it.split(" ") }.associateBy { it[1] }
        assertEquals(setOf("oneos.old-1792000000", "lineage_stage.old-1792000100"), rows.keys)
        assertEquals("1", rows.getValue("lineage_stage.old-1792000100")[5])
        // purge under the name the list showed, also once the copy is renamed after the list.
        refused(fr.run(RootScript.Verb.PURGE, "lineage_stage.old-1792000100"), "mounted")
        File(holder, "mountinfo").writeText("22 1 253:0 / / rw - ext4 /dev/root rw\n")
        val p = fr.run(RootScript.Verb.PURGE, "lineage_stage.old-1792000100")
        ok(p)
        assertTrue(p.toString(), p.reply.results.any { it.startsWith("purged lineage_stage.old-1792000100 ") })
        assertFalse(busyCopy.exists())
        assertFalse(File(tmp, "oneos.old-1792000100").exists())
        assertTrue(File(tmp, "oneos.old-1792000000").isDirectory)
        assertTrue(fr.legacy.isDirectory)
        // After a restart (another boot): renamed by the next verb.
        File(fr.root, "proc/sys/kernel/random/boot_id").writeText("99999999-2222-3333-4444-555555555555\n")
        refused(s.launch(), "restore One UI's settings first")
        assertFalse(fr.legacy.exists())
        assertTrue(File(fr.stage, "persist_session.active").isFile)
    }

    @Test
    fun anOldAndANewStageTogetherAreRefused() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val old = fr.legacy.apply { File(this, "data/system").mkdirs() }
        File(old, "data/system/packages.xml").writeText("com.oplus.launcher")
        val copy = legacyCopy(fr, "lineage_stage.old-1792000000")
        val before = fr.snapshot()
        for (r in listOf(s.begin("keep"), s.launch(), s.env(), fr.run(RootScript.Verb.RECOVER))) {
            refused(r, "both")
            assertTrue(r.toString(), r.reply.refused!!.contains("/data/local/tmp/lineage_stage"))
        }
        // The copy was renamed by the first of them; the stages are as they were.
        assertFalse(copy.exists())
        assertEquals(
            before.replace("lineage_stage.old-1792000000", "oneos.old-1792000000").lines().sorted(),
            fr.snapshot().lines().sorted(),
        )
        // The old copies can still be listed and deleted.
        val r = fr.run(RootScript.Verb.OLD_LIST)
        ok(r)
        assertTrue(r.reply.infos.any { it.contains("both") })
        assertEquals(listOf("old oneos.old-1792000000"), r.reply.results.map { it.split(" ").take(2).joinToString(" ") })
        ok(fr.run(RootScript.Verb.PURGE, "oneos.old-1792000000"))
        assertTrue(File(old, "data/system/packages.xml").isFile)
        assertTrue(File(fr.stage, ".oneos_stage").isFile)
    }

    @Test
    fun oldCopiesKeepTheirNameWhenTheNewOneIsTaken() = eachShell { fr ->
        val s = Stager(fr)
        s.prepare()
        val tmp = File(fr.root, "data/local/tmp")
        val a = legacyCopy(fr, "lineage_stage.old-1792000001-77")
        val taken = legacyCopy(fr, "lineage_stage.old-1792000002")
        val there = File(tmp, "oneos.old-1792000002").apply { mkdirs() }
        // A link with an old copy's name is never followed or renamed.
        val link = File(tmp, "lineage_stage.old-1792000003")
        java.nio.file.Files.createSymbolicLink(link.toPath(), fr.stage.toPath())
        val r = fr.run(RootScript.Verb.OLD_LIST)
        ok(r)
        assertTrue(File(tmp, "oneos.old-1792000001-77/data/system/packages.xml").isFile)
        assertFalse(a.exists())
        assertTrue(taken.isDirectory)
        assertTrue(there.isDirectory)
        assertTrue(java.nio.file.Files.isSymbolicLink(link.toPath()))
        assertFalse(File(tmp, "oneos.old-1792000003").exists())
        assertEquals(
            setOf("oneos.old-1792000001-77", "oneos.old-1792000002", "lineage_stage.old-1792000002"),
            r.reply.results.filter { it.startsWith("old ") }.map { it.split(" ")[1] }.toSet(),
        )
    }

    @Test
    fun anOldPathThatIsALinkIsNeverUsed() = eachShell { fr ->
        val other = File(fr.root, "elsewhere").apply { mkdirs() }
        java.nio.file.Files.createSymbolicLink(fr.legacy.toPath(), other.toPath())
        val s = Stager(fr)
        ok(s.begin())
        assertTrue(File(fr.stage, "bin/oneos_root.sh").isFile)
        assertTrue(java.nio.file.Files.isSymbolicLink(fr.legacy.toPath()))
        assertTrue(other.list()!!.isEmpty())
    }

    @Test
    fun argumentsAreCheckedBeforeTheLauncherIsBuilt() {
        assertTrue(RootScript.problems(RootScript.Verb.RECEIVE, listOf("../x", "1", "a".repeat(64))).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.RECEIVE, listOf("services_patched.jar", "1;reboot", "a".repeat(64))).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.BEGIN, listOf("wipe", "f8u", "coloros17-findn6", "n6-f8u", "4")).isNotEmpty())
        // 0.3.3: begin and finish name the set, launch carries hideGms (0 or 1).
        assertTrue(RootScript.problems(RootScript.Verb.BEGIN, listOf("new", "f8u", "coloros17-findn6", "4")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.FINISH, listOf("f8u", "coloros17-findn6", "4")).isNotEmpty())
        assertEquals(emptyList<String>(), RootScript.problems(RootScript.Verb.FINISH, listOf("f8u", "coloros17-findn6", "n6-f8u", "4")))
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "\$(id)", "0", "1", "0", "0")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "2", "1", "0", "0")).isNotEmpty())
        // 0.4.23: launch carries the heat cap too (0 or 1); 0.4.25: and secIms; 0.4.32: and edmStub. All needed.
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0", "1")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0", "1", "0")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0", "2", "0", "0")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0", "1", "2", "0")).isNotEmpty())
        assertTrue(RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0", "1", "0", "2")).isNotEmpty())
        assertEquals(emptyList<String>(), RootScript.problems(RootScript.Verb.LAUNCH, listOf("dry", "4", "0123456789abcdef", "1", "0", "0", "0")))
        assertEquals(emptyList<String>(), RootScript.problems(RootScript.Verb.LAUNCH, listOf("session", "4", "0123456789abcdef", "0", "1", "1", "1")))
        assertTrue(RootScript.problems(RootScript.Verb.RECOVER, listOf("x")).isNotEmpty())
        assertEquals(emptyList<String>(), RootScript.problems(RootScript.Verb.KEEP_RAW, listOf("10385141760", "a".repeat(64))))
        // Rendered, the arguments are one plain `set --` line.
        val l = RootScript.launcher(RootScript.Verb.BEGIN, listOf("new", "f8u", "coloros17-findn6", "n6-f8u", "4"), "a".repeat(64), 100)
        assertTrue(l.lines().contains("set -- begin new f8u coloros17-findn6 n6-f8u 4"))
        assertFalse(Regex("@[A-Z]+@").containsMatchIn(l))
        assertTrue(l.lines().containsAll(listOf("S=/data/local/tmp/oneos", "L=/data/local/tmp/lineage_stage")))
    }
}
