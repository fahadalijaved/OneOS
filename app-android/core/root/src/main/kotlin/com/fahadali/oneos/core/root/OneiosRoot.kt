package com.fahadali.oneos.core.root

import com.fahadali.oneos.core.model.OneiosChecks
import com.fahadali.oneos.core.model.OneiosKbFiles
import com.fahadali.oneos.core.model.OneiosKind
import com.fahadali.oneos.core.model.OneiosLogs
import com.fahadali.oneos.core.model.OneiosManifests
import com.fahadali.oneos.core.model.OneiosSystem

/**
 * The OneiOS root script (`app/src/full/assets/root/oneios_root.sh`) and its
 * launcher, built like [RootScript]'s: every root command for the iOS 27
 * (OneiOS) system is `su -c "<launcher>"`, a fixed text with only the verb's
 * arguments, the script's pinned SHA-256 and its length filled in. The
 * launcher runs `$STAGE/bin/oneios_root.sh` only when the stage, its `bin` and
 * the script are root's and the script has the pinned hash; `status`, `begin`
 * and `remove` may install it first (the app writes it to su's stdin).
 * `status` on a phone without a stage answers without making one.
 */
object OneiosRoot {
    const val ASSET = "root/oneios_root.sh"
    const val STAGE = OneiosSystem.STAGE

    /** The session scripts root stages beside the runtime and the image (switcher/assets). */
    val SESSION_SCRIPTS: List<String> = listOf("oneios_switch.sh", "oneios_return.sh")

    /**
     * OneOS's boot screen (the Android guests' own: its script, its renderer and the OneOS icon), which the
     * switch shows from the stop of One UI's framework until iOS draws. Root stages them in the stage's `bin/`.
     */
    val BOOT_SCREEN_FILES: List<String> = listOf("boot_status.sh", "OneOSBootStatus.dex", "oneos_boot_icon.png")

    /** Everything the `script` verb takes: staged with every import and before every switch. */
    val SESSION_FILES: List<String> = SESSION_SCRIPTS + BOOT_SCREEN_FILES

    enum class Stdin { NONE, SCRIPT, DATA }

    enum class Verb(val word: String, val stdin: Stdin) {
        STATUS("status", Stdin.SCRIPT),
        BEGIN("begin", Stdin.SCRIPT),
        RECEIVE("receive", Stdin.DATA),
        SCRIPT("script", Stdin.DATA),
        FINISH("finish", Stdin.NONE),
        SWITCH("switch", Stdin.NONE),

        /** Back to One UI: runs oneios_return.sh; nothing happens without an open session. */
        RETURN("return", Stdin.NONE),
        REMOVE("remove", Stdin.SCRIPT),

        /** One hardware check ([OneiosChecks]): a tool of the staged runtime, beside One UI, with a time limit. */
        CHECK("check", Stdin.NONE),

        /** The put-back step of a check alone, when its root command had to be ended. */
        UNCHECK("uncheck", Stdin.NONE),

        /** The picture a camera check wrote, in base64. */
        CHECKFILE("checkfile", Stdin.NONE),

        /** Read only: the session logs in the stage ([OneiosLogs]), each with its size, time and last lines. */
        LOGS("logs", Stdin.NONE),

        /** Read only: up to 1 MiB of one log, whole lines, ending at a byte offset (0 = the file's end). */
        LOGFILE("logfile", Stdin.NONE),

        /** One kernel-build input file into the stage ([OneiosKb]). */
        KBINPUT("kbinput", Stdin.DATA),

        /** Apple's kernelcache the phone's tool fetched from Apple and decoded (`make-kernel/kernelcache.macho`) into `kb/`, when it is the pinned one. */
        KBCACHE("kbcache", Stdin.NONE),

        /** The kernel update's work folder (`make-kernel/`) removed; the cached kernelcache in `kb/` stays. */
        KBCLEAN("kbclean", Stdin.NONE),

        /** Back to the kept kernel set after a kernel update. */
        RESTORE("restore", Stdin.NONE),

        /** One flow of OneiOS's Rust tools: the staged runtime's bin/oneios-tool serve on this command's pipe ([OneiosToolSession]). */
        TOOL("tool", Stdin.NONE),

        /** The backstop: ends every process of the staged bin/oneios-tool serve. */
        UNTOOL("untool", Stdin.NONE);
    }

    /** What the launcher's checks look at: the phone, or a fake root in the tests. */
    data class Layout(val stage: String, val sh: String, val proc: String, val uid: String, val owner: String) {
        companion object {
            val PHONE = Layout(STAGE, "/system/bin/sh", "/proc", "0", "0:0")
        }
    }

    private val TOKEN = Regex("^[A-Za-z0-9][A-Za-z0-9._+,/-]{0,199}$")
    private val DEC = Regex("^[0-9]{1,18}$")

    /** The switch verb's optional third word: the session mode (oneios_switch.sh, "THE SESSION MODE"). */
    val SESSION_MODES: Set<String> = setOf(OneiosSystem.MODE_HOSTED, OneiosSystem.MODE_TAKEOVER)
    private val HEX64 = Regex("^[0-9a-f]{64}$")
    private val WORD = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
    private val BID = Regex("^xnu-[A-Za-z0-9._-]{1,85}$")
    private val FORMATS = Regex("^[0-9]{1,4}(,[0-9]{1,4}){0,15}$")
    private val KINDS = OneiosKind.entries.map { it.word }.toSet()

    /** Problems with these arguments for [verb]; empty = the launcher may carry them. */
    fun problems(verb: Verb, args: List<String>): List<String> {
        val p = mutableListOf<String>()
        args.filterNot(TOKEN::matches).forEach { p += "argument '${it.take(40)}' is not a plain word" }
        fun need(n: Int) {
            if (args.size != n) p += "${verb.word} takes $n arguments, got ${args.size}"
        }
        fun arg(i: Int, re: Regex, what: String) {
            val a = args.getOrNull(i) ?: return
            if (!re.matches(a)) p += "${verb.word}: '${a.take(40)}' is not $what"
        }
        fun kind(i: Int) {
            args.getOrNull(i)?.let { if (it !in KINDS) p += "${verb.word}: '${it.take(40)}' is not runtime or image" }
        }
        fun path(i: Int) {
            args.getOrNull(i)?.let { if (!OneiosManifests.validPath(it)) p += "${verb.word}: '${it.take(40)}' is not a plain relative path" }
        }
        when (verb) {
            Verb.STATUS, Verb.REMOVE, Verb.RETURN, Verb.LOGS, Verb.UNTOOL, Verb.KBCLEAN -> need(0)
            Verb.LOGFILE -> {
                need(3)
                args.getOrNull(0)?.let { if (!OneiosLogs.validId(it)) p += "logfile: '${it.take(40)}' is not a session log" }
                arg(1, DEC, "an offset")
                args.getOrNull(2)?.let { if ((it.toLongOrNull() ?: 0) !in 1..OneiosLogs.CHUNK_MAX) p += "logfile: 1 to ${OneiosLogs.CHUNK_MAX} bytes a call" }
            }
            Verb.BEGIN -> { need(1); kind(0) }
            Verb.TOOL -> {
                need(1)
                args.getOrNull(0)?.let { if (it != "work" && it != "read") p += "tool: '${it.take(40)}' is not work or read" }
            }
            Verb.RECEIVE -> {
                need(5); kind(0); path(1); arg(2, DEC, "a size"); arg(3, HEX64, "a SHA-256")
                args.getOrNull(4)?.let { if (it != "0644" && it != "0755") p += "receive: mode '$it'" }
            }
            Verb.SCRIPT -> {
                need(3)
                args.getOrNull(0)?.let { if (it !in SESSION_FILES) p += "script: '${it.take(40)}' is not a session script" }
                arg(1, DEC, "a size"); arg(2, HEX64, "a SHA-256")
            }
            Verb.FINISH -> when (args.getOrNull(0)) {
                OneiosKind.RUNTIME.word -> {
                    need(10); arg(1, DEC, "a file count"); arg(2, WORD, "a version"); arg(3, DEC, "a session ABI")
                    path(4); arg(5, FORMATS, "a list of image formats")
                    args.getOrNull(6)?.let { if (it != "0" && it != "1") p += "finish: placeholder is 0 or 1" }
                    args.getOrNull(7)?.let { if (it != "none" && !BID.matches(it)) p += "finish: kernel build id" }
                    args.getOrNull(8)?.let { if (it != "none" && !HEX64.matches(it)) p += "finish: kernel SHA-256" }
                    args.getOrNull(9)?.let { if (it != "none" && !WORD.matches(it)) p += "finish: kernel xnu" }
                    val kb = args.drop(7).take(3)
                    if (kb.size == 3 && (kb.any { it == "none" } && kb.any { it != "none" })) {
                        p += "finish: the kernel facts come together or not at all"
                    }
                }
                OneiosKind.IMAGE.word -> {
                    need(5); arg(1, DEC, "a file count"); arg(2, DEC, "a format"); arg(3, WORD, "a version"); arg(4, WORD, "a build")
                }
                "kernel" -> {
                    need(3); arg(1, HEX64, "a kernel SHA-256"); arg(2, BID, "a build id")
                }
                else -> p += "finish: runtime, image or kernel"
            }
            Verb.KBINPUT -> {
                need(3)
                args.getOrNull(0)?.let { if (it !in OneiosKbFiles.NAMES) p += "kbinput: '${it.take(40)}' is not a kernel-build input" }
                arg(1, DEC, "a size"); arg(2, HEX64, "a SHA-256")
            }
            Verb.KBCACHE -> {
                need(2); arg(0, DEC, "a size"); arg(1, HEX64, "a SHA-256")
            }
            Verb.RESTORE -> {
                need(1)
                args.getOrNull(0)?.let { if (it != "kernel") p += "restore: '${it.take(40)}' is not restorable" }
            }
            Verb.CHECK, Verb.UNCHECK -> {
                need(1)
                args.getOrNull(0)?.let { if (OneiosChecks.byId(it) == null) p += "${verb.word}: '${it.take(40)}' is not a hardware check" }
            }
            Verb.CHECKFILE -> {
                need(1)
                args.getOrNull(0)?.let { if (OneiosChecks.byId(it)?.picture != true) p += "checkfile: '${it.take(40)}' has no picture" }
            }
            Verb.SWITCH -> {
                // The third word, the session mode (docs/oneios.md, "Android takeover"), is optional: hosted or takeover.
                if (args.size != 2 && args.size != 3) p += "${verb.word} takes 2 or 3 arguments, got ${args.size}"
                arg(0, DEC, "a versionCode")
                args.getOrNull(1)?.let { if (it != "0" && it != "1") p += "switch: the tick is 0 or 1" }
                args.getOrNull(2)?.let { if (it !in SESSION_MODES) p += "switch: the session mode is hosted or takeover" }
            }
        }
        return p
    }

    /** The launcher text for `su -c`; [scriptSha256] and [scriptBytes] are the pinned values (BuildConfig). */
    fun launcher(verb: Verb, args: List<String>, scriptSha256: String, scriptBytes: Long, layout: Layout = Layout.PHONE): String {
        val p = problems(verb, args)
        require(p.isEmpty()) { p.joinToString("; ") }
        require(HEX64.matches(scriptSha256)) { "bad script hash" }
        require(scriptBytes in 1..1_048_576) { "bad script size" }
        for (v in listOf(layout.stage, layout.sh, layout.proc)) require(PATH.matches(v)) { "bad path $v" }
        require(Regex("^[0-9]{1,10}$").matches(layout.uid) && Regex("^[0-9]{1,10}:[0-9]{1,10}$").matches(layout.owner)) { "bad owner" }
        return TEMPLATE
            .replace("@ARGS@", (listOf(verb.word) + args).joinToString(" "))
            .replace("@STAGE@", layout.stage)
            .replace("@SH@", layout.sh)
            .replace("@PROC@", layout.proc)
            .replace("@UID@", layout.uid)
            .replace("@OWNER@", layout.owner)
            .replace("@SHA@", scriptSha256)
            .replace("@LEN@", scriptBytes.toString())
    }

    private val PATH = Regex("^/[A-Za-z0-9._/-]+$")

    const val TEMPLATE = $$"""umask 077
set -- @ARGS@
S=@STAGE@
F=$S/bin/oneios_root.sh
W=@SHA@
mine() {
    [ -L "$1" ] && return 1
    [ -e "$1" ] || return 1
    case "$(stat -c '%u %A' "$1" 2>/dev/null)" in
        "@UID@ "?????w*|"@UID@ "????????w*) return 1 ;;
        "@UID@ "*) return 0 ;;
    esac
    return 1
}
if mine "$S" && mine "$S/bin" && mine "$F" && [ "$(sha256sum "$F" 2>/dev/null | cut -d' ' -f1)" = "$W" ]; then
    exec @SH@ "$F" "$@"
fi
case "$1" in
    status)
        if [ ! -e "$S" ] && [ ! -L "$S" ]; then
            echo "@@RESULT stage none"
            echo "@@OK status"
            exit 0
        fi
        ;;
    begin) ;;
    remove)
        if [ ! -e "$S" ] && [ ! -L "$S" ]; then
            echo "@@OK remove nothing"
            exit 0
        fi
        ;;
    *)
        echo "@@REFUSED OneiOS's root script is not in the stage, or it changed: set up again"
        exit 2
        ;;
esac
for m in @PROC@/1/mountinfo @PROC@/self/mountinfo; do
    awk '$5 == "/" { f = 1 } END { exit !f }' "$m" 2>/dev/null || { echo "@@REFUSED could not read $m"; exit 2; }
done
if awk -v s="$S" '$5 == s || index($5, s "/") == 1 { f = 1 } END { exit !f }' @PROC@/1/mountinfo @PROC@/self/mountinfo; then
    echo "@@REFUSED something is mounted in the stage - restart the phone first"
    exit 2
fi
if [ -L "$S" ] || { [ -e "$S" ] && [ ! -d "$S" ]; }; then
    echo "@@REFUSED $S is not a folder"
    exit 2
fi
[ -d "$S" ] || mkdir "$S" || { echo "@@FAILED could not make the stage"; exit 4; }
chown @OWNER@ "$S" && chmod 0700 "$S" || { echo "@@FAILED could not make the stage root's"; exit 4; }
if [ -e "$S/bin" ] || [ -L "$S/bin" ]; then
    if [ -L "$S/bin" ] || [ ! -d "$S/bin" ] || ! mine "$S/bin"; then
        mv "$S/bin" "$S/bin.old-$(date +%s)-$$" || { echo "@@FAILED could not move the old bin aside"; exit 4; }
    fi
fi
[ -d "$S/bin" ] || mkdir "$S/bin" || { echo "@@FAILED could not make the stage's bin"; exit 4; }
chown @OWNER@ "$S/bin" && chmod 0700 "$S/bin" || { echo "@@FAILED could not make bin root's"; exit 4; }
rm -f "$F.new"
head -c @LEN@ > "$F.new" || { rm -f "$F.new"; echo "@@FAILED could not write the root script"; exit 4; }
if [ "$(sha256sum "$F.new" 2>/dev/null | cut -d' ' -f1)" != "$W" ]; then
    rm -f "$F.new"
    echo "@@REFUSED the root script did not arrive intact"
    exit 2
fi
chown @OWNER@ "$F.new" && chmod 0700 "$F.new" && mv -f "$F.new" "$F" || { echo "@@FAILED could not install the root script"; exit 4; }
exec @SH@ "$F" "$@"
"""
}

/**
 * What `status` printed (`@@RESULT` lines of oneios_root.sh): what is staged,
 * whether a session is open, how the last one returned, and whether a switch
 * would start now ([ready]) or the one line why not ([notReady]).
 */
data class OneiosStatus(
    val staged: Boolean = false,
    val runtime: Runtime? = null,
    val image: Image? = null,
    /** The staged runtime's own kernel (`runtime.json`'s `kernel`); null = none recorded. */
    val runtimeKernel: Kernel? = null,
    /** The staged image set's kernel.kc; null = none recorded. */
    val imageKernel: Kernel? = null,
    val sessionOpen: Boolean = false,
    val sessionState: String? = null,
    /** The staged kernel-build inputs. */
    val kb: Kb = Kb(null, 0),
    /** "inplace", "failsafe" or "reboot": how the last session came back; null = none yet. */
    val lastReturn: String? = null,
    val lastReturnDetail: String? = null,
    val ready: Boolean = false,
    val notReady: String? = null,
    /**
     * Root has printed what is staged but its preflight (the `ready` line, the last) still runs: the screens show
     * the stage and "checking" for the last check ([partial]). Never set by [parse].
     */
    val checking: Boolean = false,
) {
    data class Runtime(val version: String, val sessionAbi: String, val xnuhost: String, val imageFormats: String, val placeholder: Boolean = false)

    data class Image(val format: String, val version: String, val build: String, val bytes: Long?)

    /** A staged kernel: its build id, and for an image's kernel.kc its SHA-256 and whether a fallback set is kept. */
    data class Kernel(val buildId: String, val xnu: String = "", val kcSha256: String = "", val hasFallback: Boolean = false)

    /** The kernel-build inputs: Apple's kernelcache SHA-256 (or null) and how many of the 13 inputs are staged. */
    data class Kb(val kernelcacheSha256: String?, val inputs: Int)

    companion object {
        fun parse(results: List<String>): OneiosStatus {
            var s = OneiosStatus()
            for (line in results) {
                val w = line.trim().split(' ')
                val rest = { n: Int -> w.drop(n).joinToString(" ").takeIf { it.isNotBlank() } }
                when (w.firstOrNull()) {
                    "stage" -> s = s.copy(staged = w.getOrNull(1) == "present")
                    "runtime" -> if (w.size >= 5) s = s.copy(runtime = Runtime(w[1], w[2], w[3], w[4], w.getOrNull(5) == "1"))
                    "image" -> if (w.size >= 4 && w[1] != "none") s = s.copy(image = Image(w[1], w[2], w[3], w.getOrNull(4)?.toLongOrNull()))
                    "kernel" -> when (w.getOrNull(1)) {
                        "runtime" -> if (w.size >= 3 && w[2] != "none") s = s.copy(runtimeKernel = Kernel(w[2], w.getOrNull(3).orEmpty()))
                        "image" -> if (w.size >= 4 && w[2] != "none") s = s.copy(
                            imageKernel = Kernel(w[2], kcSha256 = w.getOrNull(3).orEmpty(), hasFallback = w.getOrNull(4) == "1"),
                        )
                    }
                    "kb" -> if (w.size >= 3) s = s.copy(
                        kb = Kb(w[1].takeIf { it != "none" }, w[2].toIntOrNull()?.coerceIn(0, 13) ?: 0),
                    )
                    "session" -> s = s.copy(sessionOpen = w.getOrNull(1) == "open", sessionState = w.getOrNull(2))
                    "outcome" -> if (w.getOrNull(1) in setOf("inplace", "failsafe", "reboot")) {
                        s = s.copy(lastReturn = w[1], lastReturnDetail = rest(3))
                    }
                    "ready" -> s = s.copy(ready = w.getOrNull(1) == "1", notReady = if (w.getOrNull(1) == "1") null else rest(2))
                }
            }
            return s
        }

        /**
         * What `status` has printed so far, once it has said everything but the preflight's `ready` line (its last,
         * after `outcome`): the stage as it is, [checking] set. Null before that, and for a stage that is not there
         * (`stage none`: the whole answer, no preflight follows).
         */
        fun partial(results: List<String>): OneiosStatus? {
            if (results.none { it.startsWith("outcome") } || results.any { it.startsWith("ready") }) return null
            return parse(results).takeIf { it.staged }?.copy(checking = true)
        }
    }
}
