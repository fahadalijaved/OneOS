package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.Images
import com.fahadali.oneos.core.model.InstalldExpected
import com.fahadali.oneos.core.model.PackageSets
import com.fahadali.oneos.core.model.Profiles
import com.fahadali.oneos.core.model.SessionEnv
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** StageAudit on the shipped root script and launcher, and the script's tables against the model. */
class StageAuditTest {
    private val script = Shipped.rootScriptText
    private val launcher = RootScript.launcher(RootScript.Verb.BEGIN, listOf("new", "f8u", "coloros17-findn6", "n6-f8u", "4"), "a".repeat(64), 1000)

    @Test
    fun shippedScriptPassesTheAudit() {
        val p = StageAudit.audit(script)
        assertTrue("audit problems:\n${p.joinToString("\n")}", p.isEmpty())
    }

    @Test
    fun selfUpdateGetsNoMoreThanItsOwnInstall() {
        fun bad(from: String, to: String) {
            assertTrue("no '$from' in the script", script.contains(from))
            assertTrue("'$to' passed the audit", StageAudit.audit(script.replace(from, to)).isNotEmpty())
        }
        bad("pm install -r --pkg \"\$APP_PACKAGE\" \"\$upapk\"", "pm install -r \"\$upapk\"")
        bad("pm install -r --pkg \"\$APP_PACKAGE\" \"\$upapk\"", "pm install -r --pkg \"\$APP_PACKAGE\" \"\$upsrc\"")
        bad("am start -n \"\$APP_PACKAGE/.ui.MainActivity\"", "am start -n com.android.settings/.Settings")
        bad("trap '' PIPE", "trap '' INT")
        bad("upsrc=\"\$DATA/user/0/\$APP_PACKAGE/files/oneos-update/OneOS.apk\"", "upsrc=\"\$DATA/user/0/com.android.chrome/x.apk\"")
        bad("    upd=\"\$STAGE/update\"\n", "    upd=\"\$STAGE/update\"\n    x=\"\$DATA/user/0\"\n")
        bad("    upapk=\"\$STAGE/update/OneOS-\$code.apk\"", "    upapk=\"\$DATA/local/OneOS-\$code.apk\"")
    }

    @Test
    fun theLaunchWaitIsTheScriptsOnlySleep() {
        val wait = "        sleep 1\n    done\n}\n\ndo_launch() {\n"
        assertEquals("the wait is not where the test expects it", 1, script.split(wait).size - 1)
        assertEquals(1, Regex("""(?m)^\s*sleep\b""").findAll(script).count())
        assertTrue(StageAudit.audit(script.replace(wait, wait.replace("sleep 1", "sleep 600"))).any { "sleep 600" in it })
        // The same words in another function do not pass.
        assertTrue(StageAudit.audit(script.replace(wait, wait + "    sleep 1\n")).any { it.endsWith("sleep 1") })
    }

    @Test
    fun launcherPassesTheAudit() {
        val p = StageAudit.auditLauncher(launcher)
        assertTrue("launcher problems:\n${p.joinToString("\n")}", p.isEmpty())
        // The old path only stands in for the stage (S=$L), never anything else.
        assertTrue(StageAudit.auditLauncher(launcher.replace("    S=\$L\n", "    S=\$HOME\n")).isNotEmpty())
        assertTrue(StageAudit.auditLauncher(launcher.replace("L=${RootScript.LEGACY_STAGE}\n", "L=\$HOME\n")).isNotEmpty())
        // It writes only the stage, its bin and the script (and moves an old bin aside).
        val scan = ShellScan.scan(launcher)
        assertEquals(setOf("\"\$F.new\""), scan.redirects.filter { it.op.contains('>') && it.target != "/dev/null" }.map { it.target }.toSet())
    }

    @Test
    fun scannerSeesCommandsInFunctionsCasesAndSubstitutions() {
        val scan = ShellScan.scan(script)
        val names = scan.commands.map { it.name }.toSet()
        assertTrue(names.containsAll(listOf("head", "sha256sum", "mv", "chown", "awk", "do_begin", "refuse", "\"\$BB\"")))
        assertTrue(scan.functions.containsAll(listOf("do_begin", "do_launch", "to_attic", "check_table", "profile_info", "profile_set", "set_image", "pair_set")))
        // Commands inside case branches and $(...) are found.
        assertTrue(scan.commands.any { it.name == "echo" && it.args.firstOrNull()?.contains("SM-S948") == true })
        assertTrue(scan.commands.any { it.name == "stat" && it.args.contains("'%d:%i:%s:%Y'") })
    }

    @Test
    fun auditCatchesWritesOutsideTheStage() {
        fun bad(line: String, inFunction: Boolean = false) {
            val text = if (inFunction) script.replace("do_recover() {\n", "do_recover() {\n    $line\n") else "$script\n$line\n"
            assertTrue("not caught: $line", StageAudit.audit(text).isNotEmpty())
        }
        bad("rm -rf \"\$STAGE/data\"")
        bad("rm -f /data/system/packages.xml")
        bad("echo x > /data/local/tmp/other")
        bad("mv \"\$STAGE/system.raw\" /data/local/tmp/x")
        bad("cp \"\$STAGE/x\" /sdcard/x")
        bad("settings put global adb_enabled 1")
        bad("pm uninstall com.example")
        bad("reboot")
        bad("setprop sys.powerctl reboot")
        bad("mount -o bind /data/data \"\$STAGE/x\"")
        bad("dd if=/dev/zero of=\"\$STAGE/x\"")
        bad("chmod 777 /data/adb")
        bad("chown 0:0 \"\$HOME\"")
        bad("curl http://example.com")
        bad("part=/data/user/0/x", inFunction = true)
        bad("\"\$BB\" rm -rf /")
        bad("sed -i s/a/b/ \"\$STAGE/session.env\"")
        bad("own /data/misc 0644", inFunction = true)
    }

    /** The renames from the names up to 0.3.6: only migrate_legacy's two, from exactly the old names. */
    @Test
    fun auditAllowsOnlyTheMigrationRenames() {
        fun bad(line: String, inFunction: String? = null) {
            val text = if (inFunction != null) script.replace("$inFunction() {", "$inFunction() {\n    $line") else "$script\n$line\n"
            assertTrue("not caught: $line in ${inFunction ?: "main"}", StageAudit.audit(text).isNotEmpty())
        }
        val m = "migrate_legacy"
        assertTrue(script.contains("$m() {"))
        bad("mv \"\$LEGACY\" \"\$STAGE\"")
        bad("mv \"\$LEGACY\" \"\$STAGE\"", "do_begin")
        bad("mv \"\$MFROM\" \"\$MTO\"", "do_purge")
        bad("mv \"\$LEGACY\" /data/local/tmp/x", m)
        bad("mv \"\$STAGE\" \"\$LEGACY\"", m)
        bad("mv \"\$MTO\" \"\$MFROM\"", m)
        bad("rm -f \"\$LEGACY/x\"", m)
        bad("mkdir \"\$STAGE/x\"", m)
        bad("to_attic x", m)
        bad("LEGACY=/data")
        bad("LEGACY=\"\$T/data/local/tmp\"")
        bad("MTO=\"\$OLD_PARENT/x\"", m)
        bad("MFROM=\"\$OLD_PARENT/x\"", m)
        bad("STAGE=\"\$LEGACY\"", "do_begin")
        bad("STAGE=/data/local/tmp/other")
        bad("for MFROM in \"\$OLD_PARENT\"/*; do true; done", m)
        bad("TRASH=\"\$OLD_PARENT/lineage_stage.trash-1\"", "do_purge")
    }

    /** Bring apps: One UI's app data is read by exactly bring-collect's tests, its du and its two copies and bring-status's one find, and never written. */
    @Test
    fun bringReadsOnlyTheChosenAppsDataAndNeverWritesIt() {
        val b = "do_bring_collect"
        assertTrue(script.contains("$b() {"))
        fun bad(line: String, inFunction: String?, expect: String) {
            val text = if (inFunction != null) script.replace("$inFunction() {", "$inFunction() {\n    $line") else "$script\n$line\n"
            val p = StageAudit.audit(text)
            assertTrue("not caught as '$expect': $line in ${inFunction ?: "main"}\n${p.joinToString("\n")}", p.any { it.contains(expect) })
        }
        val source = "takes a bring source"
        // Writes to One UI's side, in bring-collect itself.
        bad("rm -f \"\$BCE/x\"", b, source)
        bad("mv \"\$BFROM\" \"\$dst/ce/\"", b, source)
        bad("cp -a \"\$dst/ce\" \"\$BCE\"", b, source)
        bad("cp -a \"\$dst/de/x\" \"\$BDE/x\"", b, source)
        bad("chown 0:0 \"\$BDE\"", b, source)
        bad("chmod 777 \"\${BCE}\"", b, source)
        bad("mkdir \"\$BCE/x\"", b, source)
        bad("echo x > \"\$BCE/x\"", b, "names a bring source")
        bad("echo x >> \"\$BFROM\"", b, "names a bring source")
        // Reads other than the documented ones, or to anywhere but the two stage folders.
        bad("cat \"\$BCE/shared_prefs/x.xml\"", b, source)
        bad("cat < \"\$BDE/x\"", b, "names a bring source")
        bad("cp -a \"\$BFROM\" \"\$STAGE/x\"", b, source)
        bad("cp -a \"\$BFROM\" \"\$OLD\"", b, source)
        bad("cp \"\$BFROM\" \"\$NEW/ce/\"", b, source)
        bad("cp -a \"\$BFROM\" \"\$dst/ce/\"", b, source)
        bad("du -sk \"\$BCE\" /", b, source)
        bad("ls \"\$BCE\"", b, source)
        // The documented ones, in another function.
        bad("cp -a \"\$BFROM\" \"\$NEW/ce/\"", "do_recover", source)
        bad("[ -d \"\$BCE\" ]", "do_bring_status", source)
        bad("[ -d \"\$BCE\" ]", "do_recover", source)
        // The three variables are only what they are documented to be.
        bad("BCE=\"\$STAGE/x\"", b, "BCE=")
        bad("BDE=\"\$PROC/1/root\"", b, "BDE=")
        bad("BCE=\"\$PROC/1/root\$DATA/data/\$pkg\"", "do_recover", "BCE=")
        bad("BCE=\"\$PROC/1/root\$DATA/data/\$pkg\"", b, "BCE=")
        bad("BDE=\"\$STAGE/x\"", "bring_sources", "BDE=")
        bad("BFROM=\"\$STAGE/x\"", b, "BFROM=")
        bad("for BFROM in \"\$DATA\"/*; do true; done", b, "for BFROM in")
        bad("for BFROM in \"\$BCE\"/../*; do true; done", b, "for BFROM in")
        // One UI's app data and init's root are named nowhere else.
        bad("x=\"\$DATA/data\"", b, "names \$DATA/user or \$DATA/data")
        bad("x=\"\$DATA\"/user_de/0", b, "names \$DATA/user or \$DATA/data")
        bad("x=\"\$PROC/1/root\"", b, "names init's root")
        // bring-status looks with exactly its one find, against the copy's own since mark; find runs nowhere else.
        val st = "do_bring_status"
        assertTrue(script.contains("$st() {"))
        assertTrue(script.contains("find \"\$BCE\" \"\$BDE\" -newer \"\$ref\" -type f 2>/dev/null"))
        bad("find \"\$BCE\" \"\$BDE\" -newer \"\$ref\" -type f -delete", st, "find ")
        bad("find \"\$BCE\" -newer \"\$ref\"", st, "find ")
        bad("find \"\$STAGE\" -name x", st, "find ")
        bad("find / -newer \"\$ref\" -type f", b, "find ")
        bad("ref=\"\$BCE/x\"", st, "ref=")
        bad("ref=/data/local/tmp/x", st, "ref=")
        bad("cat \"\$BCE/shared_prefs/x.xml\"", st, source)
        bad("rm -f \"\$BDE/x\"", st, source)
        // The copy's place until it is whole is in the stage, and bring's deletes go through purge_one's checks.
        bad("NEW=/data/local/tmp/x", b, "NEW=")
        bad("NEW=\"\$DATA/local\"", b, "NEW=")
        bad("bring_drop \"\$BCE\"", b, source)
        bad("bring_drop /data/local/tmp/x", b, "is not under the stage")
        bad("bring_drop \"\$OLD_PARENT/x\"", st, "is not under the stage")
        assertTrue(StageAudit.VERBS.containsAll(listOf("bring-collect", "bring-clear", "bring-status")))
        bad("rm -rf \"\$STAGE/data/oneos_bring\"", "bring_drop", "rm -r")
        bad("rm -rf \"\$1\"", "bring_drop", "rm -r")
    }

    @Test
    fun auditChecksTheVerbs() {
        assertTrue(StageAudit.audit(script.replace("    recover) do_recover \"\$@\" ;;\n", "")).any { it.startsWith("verbs are") })
    }

    /** The script's built-in tables are the model's (one source of truth, checked here). */
    @Test
    fun scriptTablesMatchTheModel() {
        fun shVar(name: String) = Regex("""^$name="?([^"\n]*)"?$""", RegexOption.MULTILINE).find(script)?.groupValues?.get(1)
            ?: error("no $name in the script")
        assertEquals(InstalldExpected.SHA256, shVar("INSTALLD_SHA"))
        assertEquals(SessionEnv.SPLASH_COMPONENT, shVar("SPLASH_COMPONENT"))
        assertEquals("com.wewaffles.onelineage", shVar("OLD_SWITCHER"))
        assertEquals(RootScript.SCRIPTS, shVar("SCRIPTS").split(' '))
        assertEquals(SessionEnv.ALLOWED.keys.toList(), shVar("ENV_KEYS").split(' '))
        // 0.4.66: SDK per image: IMAGE_SDK (37) for all but IMAGES_SDK36, and each SDK's installd tables.
        assertEquals("37", shVar("IMAGE_SDK"))
        assertTrue(Images.ALL.all { it.sdk == 36 || it.sdk == 37 })
        assertEquals(Images.ALL.filter { it.sdk == 36 }.map { it.id }, shVar("IMAGES_SDK36").split(' ').filter { it.isNotEmpty() })
        assertEquals(InstalldExpected.carried(36), shVar("INSTALLD_SHA_36"))
        assertEquals(InstalldExpected.accepted(36), shVar("INSTALLD_OK_36").split(' ').toSet())
        assertEquals(InstalldExpected.accepted(37), setOf(shVar("INSTALLD_SHA")))
        // Enabled profiles only, each with its ids and form (SM- model numbers, and docomo's SC- ones;
        // 0.4.17: the Z Flip7's flip, which root runs with the phone settings; 0.4.74: au's SCG ones).
        val rows = Regex("""^\s+([a-z0-9-]+)\) echo "(S[MC]-\S+|SCG\S+) (\S+) (\S+) (fold|bar|flip)" ;;$""", RegexOption.MULTILINE)
            .findAll(script).associate { it.groupValues[1] to it.groupValues.drop(2) }
        val enabled = Profiles.BUILT_IN.filter { it.enabled }
        assertEquals(enabled.map { it.id }.toSet(), rows.keys)
        for (p in enabled) {
            assertEquals(listOf(p.modelPrefix, p.codename, p.socModel, p.form.name.lowercase()), rows[p.id])
        }
        // Every (profile, image) pair a phone takes and its set: exactly the profiles' choices (0.3.3).
        val pairs = Regex("""^\s+"([a-z0-9-]+) ([a-z0-9-]+)"\) echo ([a-z0-9-]+) ;;$""", RegexOption.MULTILINE)
            .findAll(script).map { Triple(it.groupValues[1], it.groupValues[2], it.groupValues[3]) }.toList()
        assertEquals(enabled.flatMap { p -> p.choices.map { Triple(p.id, it.imageId, it.packageSetId) } }.toSet(), pairs.toSet())
        assertEquals(pairs.size, pairs.map { it.first to it.second }.toSet().size)
        for (img in Images.ALL) {
            assertTrue(img.id, script.contains("${img.id}) echo \"${img.rawBytes} ${img.rawSha256}\" ;;"))
        }
        // The system each image is a build of (keep never crosses systems): exactly the model's families,
        // and the retired images' (0.4.51: the CN Find X9 Ultra build), so their stages are still known.
        val families = Regex("""^\s+([a-z0-9|-]+)\) echo ([a-z]+) ;;$""", RegexOption.MULTILINE)
            .findAll(function("image_family")).flatMap { m -> m.groupValues[1].split('|').map { it to m.groupValues[2] } }.toMap()
        assertEquals(listOf("coloros17-findx9u"), Images.RETIRED.map { it.id })
        assertEquals(Images.ALL.associate { it.id to it.family.name.lowercase() } + ("coloros17-findx9u" to "coloros"), families)
        // data_family reads the same words as status.list, in the same order as StageStatus (Infinity-X first,
        // 0.4.27: its data has OPPO's packages too; then ColorOS, then Pixel, then HyperOS).
        val data = function("data_family")
        assertTrue(data.indexOf(StageStatus.INFINITYX_WORD) in 0 until data.indexOf("com.oplus."))
        assertTrue(data.indexOf("com.oplus.") in 0 until data.indexOf(StageStatus.PIXEL_WORD))
        assertTrue(data.indexOf(StageStatus.PIXEL_WORD) < data.indexOf("\"${StageStatus.HYPEROS_WORD}\""))
        assertTrue(data.contains("com.coloros."))
        val status = File(Shipped.fullAssets, "root/status.list").readText()
        assertTrue(status.contains("for w in com.oplus. com.coloros. org.lineageos. ${StageStatus.PIXEL_WORD} ${StageStatus.INFINITYX_WORD} ${StageStatus.HYPEROS_WORD} ${StageStatus.OXYGENOS_WORD} ${StageStatus.ORIGINOS_WORD}; do"))
        // 0.4.67: OxygenOS's word right after Infinity-X's and before ColorOS's (its data has com.oplus. too).
        assertTrue(data.indexOf(StageStatus.INFINITYX_WORD) < data.indexOf(StageStatus.OXYGENOS_WORD))
        assertTrue(data.indexOf(StageStatus.OXYGENOS_WORD) in 0 until data.indexOf("com.oplus."))
        // 0.4.73: vivo's launcher (OriginOS 7) before ColorOS's words too.
        assertTrue(data.indexOf(StageStatus.ORIGINOS_WORD) in 0 until data.indexOf("com.oplus."))
        // Google services: the images whose services a session may hide (0.3.7: none; the Pixel image's sessions present them).
        assertEquals(Images.ALL.filter { it.gmsHideable }.map { it.id }, shVar("IMAGES_GMS").split(' ').filter { it.isNotEmpty() })
        // The sets' files (SET_COMMON for the ColorOS sets, SET_PIXEL for the Pixel set) and the image each was built from.
        val common = shVar("SET_COMMON").split(' ')
        // 0.4.51: no set is SET_COMMON alone any more (the debloated Find X9 Ultra set retired); the IN set is
        // SET_COMMON and its own files.
        assertTrue(PackageSets.X9U_IN_SULTRA.names.containsAll(common))
        assertEquals(
            setOf("cellbroadcast_payload.img", "framework_patched.jar", "telephony-common_patched.jar", "libcamera_client_patched.so", "samcam.tar", PackageSets.THEME_STORE_APK, PackageSets.ODM_AI),
            PackageSets.X9U_IN_SULTRA.names.toSet() - common.toSet(),
        )
        // 0.4.59: the bar Pixel sets add double tap to sleep (their own SystemUI and launcher) to SET_PIXEL.
        assertEquals(PackageSets.PIXEL_SULTRA.names.toSet() - setOf("OneOSPixelSystemUI.apk", "OneOSPixelLauncher.apk"),
            shVar("SET_PIXEL").split(' ').toSet())
        val setFiles = Regex("""^\s+([a-z0-9-]+)\) echo "\${'$'}(SET_[A-Z]+)([^"]*)" ;;$""", RegexOption.MULTILINE)
            .findAll(script).associate { it.groupValues[1] to (shVar(it.groupValues[2]).split(' ') + it.groupValues[3].split(' ').filter { n -> n.isNotEmpty() }) }
        assertEquals(PackageSets.ALL.map { it.id }.toSet(), setFiles.keys)
        for (set in PackageSets.ALL) assertEquals(set.id, set.names.toSet(), setFiles.getValue(set.id).toSet())
        val built = Regex("""^\s+([a-z0-9|-]+)\) echo ([a-z0-9-]+) ;;$""", RegexOption.MULTILINE)
            .findAll(function("set_image")).flatMap { m -> m.groupValues[1].split('|').map { it to m.groupValues[2] } }.toMap()
        assertEquals(PackageSets.ALL.associate { it.id to it.imageId }, built)
        // Modes: what root gives each staged file is the model's (vold_patched executable since 0.3.7).
        val exec = Regex("""^\s+(\S+)\) echo 0755 ;;$""", RegexOption.MULTILINE).find(function("file_mode"))!!.groupValues[1].split('|')
        fun mode(n: String) = if (exec.any { glob(it, n) }) "0755" else "0644"
        for (set in PackageSets.ALL) for (f in set.files) assertEquals("${set.id} ${f.name}", f.mode, mode(f.name))
        val notExecutable = setOf("guest_zygisk.so", "guest_vector.bundle", "guest_manager.apk", "oneos_boot_icon.png", "OneOSBootStatus.dex", "host_installd.txt", "OneOSEdmStub.dex", "OneOSOverlayDimen.dex", "OneOSFold8Geometry.dex")
        for (n in RootScript.SCRIPTS) assertEquals(n, if (n in notExecutable) "0644" else "0755", mode(n))
        // session.env values: what root accepts is what the app generates (StageScriptTest runs it).
        for (p in enabled) SessionEnv.generate(p)
    }

    /** The body of the script's function [name] (up to its closing brace at the start of a line). */
    private fun function(name: String): String {
        val start = script.indexOf("\n$name() {")
        assertTrue("no $name() in the script", start >= 0)
        return script.substring(start, script.indexOf("\n}\n", start))
    }

    /** A shell case pattern of plain characters and `*` (what the root script's patterns use). */
    private fun glob(pattern: String, name: String): Boolean =
        Regex(pattern.split('*').joinToString(".*") { Regex.escape(it) }).matches(name)

    /**
     * What check_files refuses as a leftover (a flat file not prepared that the session scripts would bind,
     * run or read) is what StageStatus flags for the app's own check (0.3.7: with the Pixel set's oneos-*).
     */
    @Test
    fun leftoverPatternsMatchTheScript() {
        val body = function("check_files")
        val patterns = Regex("""^\s+([^\s)]+)\)\n\s+in_list""", RegexOption.MULTILINE).find(body)!!.groupValues[1].split('|')
        assertTrue(patterns.contains("oneos-*"))
        val names = PackageSets.ALL.flatMap { it.names } + RootScript.SCRIPTS + listOf(
            "framework_patched.jar", "libaudioclient_aidl_conversion_patched.so", "PermissionController_patched.apk", "clean_apex_info_list.xml",
            "tethering_payload.img", "switch_to_lineage.sh", "7zz", "system.raw", "system.raw.id", "files.sha256", "session.env",
            "host_installd.table", "takeover_app.log", "payload_loops", "persist_props.snapshot", "oneos_vrr.xml", "guest_locale",
        )
        for (n in names) assertEquals(n, patterns.any { glob(it, n) }, StageStatus.LEFTOVER.matches(n))
        // Every file of every set is one of them, except guards.txt (oneos_switch.sh and guest_prepare.sh check it by hash).
        for (set in PackageSets.ALL) for (f in set.names) {
            if (f != "guards.txt") assertTrue("${set.id} $f", patterns.any { glob(it, f) })
        }
    }

    /** The bridges root checks are at least the ones bridges.sh lists (it can only grow). */
    @Test
    fun bridgeListCoversBridgesSh() {
        val bridges = File(Shipped.switcherAssets, "bridges.sh").readText()
        val hosts = Regex("""^BRIDGES="([^"]*)"""", RegexOption.MULTILINE).find(bridges)!!.groupValues[1]
            .split(' ').filter { it.isNotBlank() }.map { it.substringBefore(':') }
        val mine = Regex("""^BRIDGE_HOSTS="([^"]*)"""", RegexOption.MULTILINE).find(script)!!.groupValues[1].split(' ')
        assertTrue("bridges.sh has ${hosts - mine.toSet()} that oneos_root.sh does not check", mine.containsAll(hosts))
        val status = File(Shipped.fullAssets, "root/status.list").readText()
        for (h in hosts) assertTrue("status.list does not check /data/$h", Regex("""(^|\s)${Regex.escape(h)}(\s|;)""").containsMatchIn(status))
    }

    /**
     * The guards a set with GmsCore must name in guards.txt's comments (PackageSet.checkGuards) are the ones
     * oneos_switch.sh's preflight and guest_prepare.sh require before they present Google services, and
     * guest_google.sh before it copies One UI's Play services for a ColorOS guest.
     */
    @Test
    fun gmsGuardsAreTheSessionScriptsOnes() {
        val loop = Regex("""for t in ([a-z0-9 ]+); do\n\s+grep '\^#' "\${'$'}STAGE/guards\.txt"""")
        for (n in listOf("oneos_switch.sh", "guest_prepare.sh", "guest_google.sh")) {
            val found = loop.findAll(File(Shipped.switcherAssets, n).readText()).map { it.groupValues[1].trim().split(' ') }.toList()
            assertEquals(n, listOf(PackageSets.GMS_GUARDS), found)
        }
    }

    /** The names the scripts read are where the app writes them. */
    @Test
    fun sessionScriptsReadTheFilesTheScriptWrites() {
        val sw = File(Shipped.switcherAssets, "oneos_switch.sh").readText()
        for (f in listOf("files.sha256", "system.raw.id", "session.env")) assertTrue("oneos_switch.sh does not read $f", sw.contains(f))
        val gp = File(Shipped.switcherAssets, "guest_props.sh").readText()
        assertTrue(gp.contains("recover)"))
        assertTrue(gp.contains(".oneos_stage"))
    }
}
