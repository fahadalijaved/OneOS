package com.fahadali.oneos.core.root

/**
 * A small POSIX sh scanner for the root script's audit: simple commands
 * (with the function they are in), redirections, assignments, `for` loops
 * and function names. It understands what oneos_root.sh and the launcher use
 * (single and double quotes, `$(...)`, `${...}`, `case` patterns, functions,
 * `{ }` groups); it is not a general shell parser.
 */
object ShellScan {
    data class Command(val name: String, val args: List<String>, val function: String?, val line: Int)

    data class Redirect(val op: String, val target: String, val function: String?, val line: Int)

    data class Assignment(val name: String, val value: String, val function: String?, val line: Int)

    data class Loop(val variable: String, val words: List<String>, val line: Int)

    data class Result(
        val commands: List<Command>,
        val redirects: List<Redirect>,
        val assignments: List<Assignment>,
        val loops: List<Loop>,
        val functions: Set<String>,
        val problems: List<String>,
    )

    private sealed class Tok(val line: Int) {
        class Word(val text: String, line: Int) : Tok(line)
        class Op(val op: String, line: Int) : Tok(line)
        class Redir(val op: String, val target: String, line: Int) : Tok(line)
    }

    fun scan(text: String): Result {
        val subs = mutableListOf<Pair<String, Int>>()
        val problems = mutableListOf<String>()
        val toks = lex(text, subs, problems)
        val out = Parser(toks, problems).run()
        // Command substitutions are scanned as scripts of their own.
        val commands = out.commands.toMutableList()
        val redirects = out.redirects.toMutableList()
        val assignments = out.assignments.toMutableList()
        var i = 0
        while (i < subs.size) {
            val (sub, line) = subs[i]
            val inner = Parser(lex(sub, subs, problems, line), problems).run()
            commands += inner.commands
            redirects += inner.redirects
            assignments += inner.assignments
            i++
        }
        return Result(commands, redirects, assignments, out.loops, out.functions, problems.distinct())
    }

    private fun lex(s: String, subs: MutableList<Pair<String, Int>>, problems: MutableList<String>, firstLine: Int = 1): List<Tok> {
        val toks = mutableListOf<Tok>()
        var i = 0
        var line = firstLine
        fun readBalanced(start: Int): Int {
            // s[start] is just after "$(": find the matching ")", quotes respected.
            var depth = 1
            var j = start
            while (j < s.length) {
                when (s[j]) {
                    '\\' -> j++
                    '\'' -> j = s.indexOf('\'', j + 1).let { if (it < 0) s.length else it }
                    '"' -> {
                        j++
                        while (j < s.length && s[j] != '"') {
                            if (s[j] == '\\') j++
                            j++
                        }
                    }
                    '(' -> depth++
                    ')' -> {
                        depth--
                        if (depth == 0) return j
                    }
                }
                j++
            }
            problems += "unbalanced \$( on line $line"
            return s.length
        }
        // `$(cmd)` is scanned as a script; `$((expr))` is arithmetic, but a
        // `$(cmd)` inside it is scanned too.
        fun substitution(dollar: Int, end: Int) {
            if (dollar + 2 < s.length && s[dollar + 2] == '(') {
                var j = dollar + 3
                while (j < end) {
                    if (s[j] == '$' && j + 1 < end && s[j + 1] == '(' && !(j + 2 < end && s[j + 2] == '(')) {
                        val e = readBalanced(j + 2)
                        subs += s.substring(j + 2, minOf(e, s.length)) to line
                        j = e + 1
                    } else {
                        j++
                    }
                }
            } else {
                subs += s.substring(dollar + 2, minOf(end, s.length)) to line
            }
        }
        fun readWord(): String {
            val sb = StringBuilder()
            while (i < s.length) {
                val c = s[i]
                when {
                    c in " \t\n;&|()<>" -> break
                    c == '\\' -> {
                        if (i + 1 < s.length && s[i + 1] == '\n') {
                            i += 2
                            line++
                        } else {
                            sb.append(c)
                            if (i + 1 < s.length) sb.append(s[i + 1])
                            i += 2
                        }
                    }
                    c == '\'' -> {
                        val end = s.indexOf('\'', i + 1).let { if (it < 0) s.length - 1 else it }
                        val q = s.substring(i, end + 1)
                        line += q.count { it == '\n' }
                        sb.append(q)
                        i = end + 1
                    }
                    c == '"' -> {
                        sb.append(c)
                        i++
                        while (i < s.length && s[i] != '"') {
                            when {
                                s[i] == '\\' && i + 1 < s.length -> {
                                    sb.append(s[i]).append(s[i + 1])
                                    i += 2
                                }
                                s[i] == '$' && i + 1 < s.length && s[i + 1] == '(' -> {
                                    val end = readBalanced(i + 2)
                                    substitution(i, end)
                                    sb.append(s, i, minOf(end + 1, s.length))
                                    i = end + 1
                                }
                                s[i] == '`' -> {
                                    problems += "backtick on line $line"
                                    i++
                                }
                                else -> {
                                    if (s[i] == '\n') line++
                                    sb.append(s[i])
                                    i++
                                }
                            }
                        }
                        if (i < s.length) sb.append('"')
                        i++
                    }
                    c == '$' && i + 1 < s.length && s[i + 1] == '(' -> {
                        val end = readBalanced(i + 2)
                        substitution(i, end)
                        sb.append(s, i, minOf(end + 1, s.length))
                        i = end + 1
                    }
                    c == '$' && i + 1 < s.length && s[i + 1] == '{' -> {
                        val end = s.indexOf('}', i).let { if (it < 0) s.length - 1 else it }
                        sb.append(s, i, end + 1)
                        i = end + 1
                    }
                    c == '`' -> {
                        problems += "backtick on line $line"
                        i++
                    }
                    else -> {
                        sb.append(c)
                        i++
                    }
                }
            }
            return sb.toString()
        }
        while (i < s.length) {
            val c = s[i]
            when {
                c == ' ' || c == '\t' -> i++
                c == '\\' && i + 1 < s.length && s[i + 1] == '\n' -> {
                    i += 2
                    line++
                }
                c == '#' && (i == 0 || s[i - 1] in " \t\n;") -> while (i < s.length && s[i] != '\n') i++
                c == '\n' -> {
                    toks += Tok.Op("\n", line)
                    line++
                    i++
                }
                c == ';' -> {
                    if (i + 1 < s.length && s[i + 1] == ';') {
                        toks += Tok.Op(";;", line)
                        i += 2
                    } else {
                        toks += Tok.Op(";", line)
                        i++
                    }
                }
                c == '&' || c == '|' -> {
                    if (i + 1 < s.length && s[i + 1] == c) {
                        toks += Tok.Op("$c$c", line)
                        i += 2
                    } else {
                        toks += Tok.Op("$c", line)
                        i++
                    }
                }
                c == '(' || c == ')' -> {
                    toks += Tok.Op("$c", line)
                    i++
                }
                c == '<' || c == '>' -> redirect(s, i, line, toks).let { i = it }
                else -> {
                    val start = i
                    val w = readWord()
                    if (w.isNotEmpty() && w.all(Char::isDigit) && i < s.length && (s[i] == '<' || s[i] == '>')) {
                        i = redirect(s, i, line, toks, fd = w)
                    } else if (w.isEmpty() && i == start) {
                        i++
                    } else {
                        toks += Tok.Word(w, line)
                    }
                }
            }
        }
        return toks
    }

    /** Reads a redirection at s[i] (`>`, `>>`, `<`, `>&N`); returns the index after its target. */
    private fun redirect(s: String, start: Int, line: Int, toks: MutableList<Tok>, fd: String = ""): Int {
        var i = start
        val op = StringBuilder(fd)
        while (i < s.length && (s[i] == '<' || s[i] == '>')) op.append(s[i++])
        if (i < s.length && s[i] == '&') {
            op.append('&')
            i++
        }
        while (i < s.length && (s[i] == ' ' || s[i] == '\t')) i++
        val sb = StringBuilder()
        var quote: Char? = null
        while (i < s.length) {
            val c = s[i]
            if (quote == null && c in " \t\n;&|()<>") break
            if (c == '"' || c == '\'') quote = if (quote == c) null else quote ?: c
            sb.append(c)
            i++
        }
        toks += Tok.Redir(op.toString(), sb.toString(), line)
        return i
    }

    private class Parser(private val toks: List<Tok>, private val problems: MutableList<String>) {
        val commands = mutableListOf<Command>()
        val redirects = mutableListOf<Redirect>()
        val assignments = mutableListOf<Assignment>()
        val loops = mutableListOf<Loop>()
        val functions = mutableSetOf<String>()

        private var k = 0
        private var name: String? = null
        private var args = mutableListOf<String>()
        private var cmdLine = 0
        private var cmdPos = true
        private val funcStack = ArrayDeque<Pair<String, Int>>()
        private var braceDepth = 0
        private var casePatterns = 0
        private var expectPattern = false

        private fun fn() = funcStack.lastOrNull()?.first

        private fun end() {
            name?.let { commands += Command(it, args.toList(), fn(), cmdLine) }
            name = null
            args = mutableListOf()
        }

        fun run(): Parser {
            while (k < toks.size) {
                when (val t = toks[k++]) {
                    is Tok.Redir -> redirects += Redirect(t.op, t.target, fn(), t.line)
                    is Tok.Op -> op(t)
                    is Tok.Word -> word(t)
                }
            }
            end()
            return this
        }

        private fun op(t: Tok.Op) {
            when (t.op) {
                ";;" -> {
                    end()
                    expectPattern = true
                    cmdPos = true
                }
                ")" -> {
                    if (expectPattern) {
                        expectPattern = false
                        cmdPos = true
                    } else {
                        end()
                        cmdPos = false
                    }
                }
                "(" -> {
                    if (!expectPattern) {
                        end()
                        cmdPos = true
                    }
                }
                "|" -> if (expectPattern) Unit else {
                    end()
                    cmdPos = true
                }
                else -> {
                    end()
                    if (!(expectPattern && t.op == "\n")) cmdPos = true
                }
            }
        }

        private fun word(t: Tok.Word) {
            val w = t.text
            if (expectPattern) {
                if (w == "esac") {
                    expectPattern = false
                    casePatterns--
                    cmdPos = false
                }
                return
            }
            if (!cmdPos || name != null) {
                args += w
                return
            }
            when (w) {
                "if", "then", "else", "elif", "do", "while", "until", "!" -> return
                "{" -> {
                    braceDepth++
                    return
                }
                "}" -> {
                    braceDepth--
                    funcStack.lastOrNull()?.let { if (it.second == braceDepth) funcStack.removeLast() }
                    cmdPos = false
                    return
                }
                "fi", "done" -> {
                    cmdPos = false
                    return
                }
                "esac" -> {
                    casePatterns--
                    cmdPos = false
                    return
                }
                "for" -> {
                    val v = (toks.getOrNull(k++) as? Tok.Word)?.text.orEmpty()
                    val words = mutableListOf<String>()
                    if ((toks.getOrNull(k) as? Tok.Word)?.text == "in") {
                        k++
                        while (k < toks.size && toks[k] is Tok.Word) words += (toks[k++] as Tok.Word).text
                    }
                    loops += Loop(v, words, t.line)
                    return
                }
                "case" -> {
                    k++ // the word
                    if ((toks.getOrNull(k) as? Tok.Word)?.text == "in") k++
                    casePatterns++
                    expectPattern = true
                    return
                }
            }
            val next = toks.getOrNull(k)
            val after = toks.getOrNull(k + 1)
            if (next is Tok.Op && next.op == "(" && after is Tok.Op && after.op == ")" && FUNC.matches(w)) {
                functions += w
                k += 2
                funcStack.addLast(w to braceDepth)
                cmdPos = true
                return
            }
            val eq = ASSIGN.find(w)
            if (eq != null) {
                assignments += Assignment(eq.groupValues[1], w.substring(eq.range.last + 1), fn(), t.line)
                return
            }
            name = w
            cmdLine = t.line
        }

        companion object {
            val FUNC = Regex("^[A-Za-z_][A-Za-z0-9_]*$")
            val ASSIGN = Regex("^([A-Za-z_][A-Za-z0-9_]*)=")
        }
    }
}

/**
 * The audit of the root script and its launcher (AA10 "StageAudit"), run by
 * the unit tests: every command is on an allow-list, every write (mkdir, mv,
 * cp, rm, chown, chmod, output redirection) goes to a path under the stage
 * or to one of the documented exceptions, and the script never mentions the
 * phone's user data, reboots, settings, package wipes or mounts.
 */
object StageAudit {
    val VERBS = listOf("begin", "receive", "keep-raw", "table", "env", "finish", "launch", "recover", "old-list", "purge", "restore", "remove")

    val ALLOWED: Set<String> = setOf(
        "umask", "[", "echo", "printf", "id", "stat", "awk", "sed", "grep", "sort", "head", "tail", "cut", "tr", "wc",
        "cat", "ls", "mkdir", "mv", "cp", "rm", "chown", "chmod", "sha256sum", "date", "getprop", "pm", "getevent", "du",
        "env", "unset", "export", "set", "read", "exit", "return", "shift", "true", "false", "break", "continue", "exec",
    )

    private val WRITES = setOf("mkdir", "mv", "cp", "rm", "chown", "chmod")

    /** Never in the root code: the phone's user data, reboots, settings, wipes, mounts, props. */
    val FORBIDDEN_TEXT = listOf(
        "/data/data", "/data/user", "/data/media", "/sdcard", "/storage", "reboot", "settings put", "settings delete",
        "pm clear", "pm uninstall", "rm -r", "rm -fr", "mkfs", "losetup", "mount ", "umount", "wipe", "setprop", "svc ",
        "/proc/sysrq", "dd if", "dd of", "/dev/block",
    )

    /** Path expressions that are the stage or under it (variables the audit checks the assignments of). */
    private val STAGE_VARS = setOf("STAGE", "ATTIC", "PLAN", "RECEIVED", "part", "dst", "S", "F")

    /** Helpers that write their first argument; their call sites must pass a stage path. */
    private val WRITE_HELPERS = setOf("own", "mkdir_mine")

    /**
     * Documented exceptions: `begin aside` renames the stage to its sibling
     * `$OLD` (`$STAGE.old-<epoch>`); `launch` moves itself out of the app's
     * cgroup.
     */
    private val EXCEPTION_VARS = setOf("OLD")
    private const val CGROUP = "/sys/fs/cgroup/cgroup.procs"

    /**
     * 0.3.5's one deletion of user data, `purge` (purge_one only, which purge
     * and remove call): `$OLDDIR` is `$OLD_PARENT/$1` after old_name_ok,
     * `$TRASH` its `oneos.trash-<epoch>` sibling, `$OLD_PARENT` is
     * `$DATA/local/tmp`; the only `rm -r` in the script is `rm -rf "$TRASH"`.
     */
    private const val PURGE_FUNCTION = "purge_one"
    private val PURGE_VARS = setOf("OLDDIR", "TRASH")
    private const val PURGE_RM = "rm -rf \"\$TRASH\""

    /**
     * `restore` (do_restore only, 0.4.10): `$RFROM` is `$OLD_PARENT/$1` after
     * old_name_ok, renamed to `$STAGE` once the stage is renamed to its `$OLD`
     * sibling (the documented exception above); no other write there.
     */
    private const val RESTORE_FUNCTION = "do_restore"
    private val RESTORE_VARS = setOf("RFROM")

    /**
     * `remove` (do_remove only, 0.4.25) moves exactly these into the stage
     * before purge_one deletes it: `$LOGS`, `$OLD_PARENT/oneos_logs`, and
     * `$HELPER`, the variable of a loop over exactly the session's six helper
     * files in `$OLD_PARENT`; no other write outside the stage there.
     */
    private const val REMOVE_FUNCTION = "do_remove"
    private val REMOVE_VARS = setOf("LOGS", "HELPER")
    private const val LOGS_VALUE = "\"\$OLD_PARENT/oneos_logs\""
    private val HELPER_WORDS = listOf("adb_watchdog.sh", "adb_watchdog.log", "ims_watchdog.sh", "ims_watchdog.log", "ui_activator.log", "restore_app.log")
        .map { "\"\$OLD_PARENT/$it\"" }

    /**
     * The renames from the names up to 0.3.6 (migrate_legacy only), and no
     * other write there: `mv "$LEGACY" "$STAGE"`, `$LEGACY` being exactly
     * `$T/data/local/tmp/lineage_stage`, and `mv "$MFROM" "$MTO"`, `$MFROM`
     * the variable of a loop over exactly `lineage_stage.old-*` and
     * `lineage_stage.trash-*` in `$OLD_PARENT`, `$MTO` its `oneos.` sibling.
     */
    private const val MIGRATE_FUNCTION = "migrate_legacy"
    private val MIGRATE_VARS = setOf("LEGACY", "MFROM", "MTO")
    private val MIGRATE_MOVES = setOf(
        listOf("\"\$LEGACY\"", "\"\$STAGE\""),
        listOf("\"\$MFROM\"", "\"\$MTO\""),
    )
    private const val LEGACY_VALUE = "\"\$T/data/local/tmp/lineage_stage\""
    private val MFROM_WORDS = listOf("\"\$OLD_PARENT\"/lineage_stage.old-*", "\"\$OLD_PARENT\"/lineage_stage.trash-*")
    private const val MTO_VALUE = "\"\$OLD_PARENT/oneos.\${mn#lineage_stage.}\""

    private fun stagePath(arg: String, function: String?, loopVars: Set<String>): Boolean {
        val a = arg.removePrefix("\"")
        val v = Regex("""^\$\{?([A-Za-z_][A-Za-z0-9_]*|1)""").find(a)?.groupValues?.get(1) ?: return false
        if (v in PURGE_VARS) return function == PURGE_FUNCTION
        if (v in RESTORE_VARS) return function == RESTORE_FUNCTION
        if (v in REMOVE_VARS) return function == REMOVE_FUNCTION
        if (v in MIGRATE_VARS) return function == MIGRATE_FUNCTION
        return v in STAGE_VARS || v in EXCEPTION_VARS || v in loopVars || (v == "1" && function in WRITE_HELPERS)
    }

    fun audit(script: String, verbs: List<String> = VERBS): List<String> {
        val p = mutableListOf<String>()
        val code = script.lines().filterNot { it.trimStart().startsWith("#") }.joinToString("\n")
        // purge's one rm -rf is allowed as that exact text (its function and
        // argument are checked on the command below); any other rm -r still fails.
        val purgeRms = Regex("(?m)^\\s*" + Regex.escape(PURGE_RM) + " \\|\\| true$").findAll(code).count()
        if (purgeRms > 1) p += "rm -rf \"\$TRASH\" appears $purgeRms times"
        val textCode = code.replace(Regex("(?m)^\\s*" + Regex.escape(PURGE_RM) + " \\|\\| true$"), "")
        for (bad in FORBIDDEN_TEXT) {
            if (Regex("(?<![A-Za-z0-9_])" + Regex.escape(bad)).containsMatchIn(textCode)) p += "mentions '$bad'"
        }
        val scan = ShellScan.scan(code)
        p += scan.problems
        val functions = scan.functions

        // Loop variables used as paths must loop over stage paths only.
        val loopVars = scan.loops.filter { l -> l.words.isNotEmpty() && l.words.all { it.startsWith("\"\$STAGE") } }.map { it.variable }.toSet()
        for (l in scan.loops) {
            if (l.variable == "MFROM" && l.words != MFROM_WORDS) p += "line ${l.line}: for MFROM in ${l.words.joinToString(" ")}"
            if (l.variable == "HELPER" && l.words != HELPER_WORDS) p += "line ${l.line}: for HELPER in ${l.words.joinToString(" ")}"
        }
        for (a in scan.assignments) {
            val v = a.value.removePrefix("\"")
            val self = v.startsWith("\$${a.name}") || v == "\""
            when (a.name) {
                "STAGE" -> if (a.value != "\"\$T/data/local/tmp/oneos\"" && a.value != "\"\$STAGE\"" &&
                    !(a.value == "\"\$LEGACY\"" && a.function == MIGRATE_FUNCTION)
                ) p += "line ${a.line}: STAGE=${a.value}"
                "LEGACY" -> if (a.value != LEGACY_VALUE || a.function != null) p += "line ${a.line}: LEGACY=${a.value}"
                "MFROM" -> p += "line ${a.line}: MFROM=${a.value} (only the loop sets it)"
                "HELPER" -> p += "line ${a.line}: HELPER=${a.value} (only the loop sets it)"
                "LOGS" -> if (a.value != LOGS_VALUE || a.function != REMOVE_FUNCTION) p += "line ${a.line}: LOGS=${a.value}"
                "MTO" -> if (a.value != MTO_VALUE || a.function != MIGRATE_FUNCTION) p += "line ${a.line}: MTO=${a.value}"
                "S" -> if (a.value != RootScript.STAGE && a.value != "\$L" && !a.value.matches(Regex("^/[A-Za-z0-9._/-]+$"))) p += "line ${a.line}: S=${a.value}"
                "L" -> if (a.value != RootScript.LEGACY_STAGE && !a.value.matches(Regex("^/[A-Za-z0-9._/-]+$"))) p += "line ${a.line}: L=${a.value}"
                "OLD" -> if (!v.startsWith("\$STAGE.old-") && !self) p += "line ${a.line}: OLD=${a.value}"
                "OLD_PARENT" -> if (a.value != "\"\$DATA/local/tmp\"") p += "line ${a.line}: OLD_PARENT=${a.value}"
                "OLDDIR" -> if (a.value != "\"\$OLD_PARENT/\$1\"" || a.function != PURGE_FUNCTION) p += "line ${a.line}: OLDDIR=${a.value}"
                "RFROM" -> if (a.value != "\"\$OLD_PARENT/\$1\"" || a.function != RESTORE_FUNCTION) p += "line ${a.line}: RFROM=${a.value}"
                "TRASH" -> if (a.function != PURGE_FUNCTION ||
                    !(v.startsWith("\$OLD_PARENT/oneos.trash-") || a.value == "\"\$OLDDIR\"" || self)
                ) p += "line ${a.line}: TRASH=${a.value}"
                in STAGE_VARS -> if (!(v.startsWith("\$STAGE") || v.startsWith("\$S/") || self)) {
                    p += "line ${a.line}: ${a.name}=${a.value} is not under the stage"
                }
            }
        }
        for (c in scan.commands) {
            val n = c.name
            val ok = n in ALLOWED || n in functions || n == "\"\$BB\""
            if (!ok) {
                p += "line ${c.line}: '$n' is not on the root script's allow-list"
                continue
            }
            val args = c.args
            when (n) {
                "\"\$BB\"" -> {
                    val first = args.firstOrNull()
                    if (first != "--list" && first != "nsenter") p += "line ${c.line}: busybox $first"
                    if (first == "nsenter" && args.subList(1, minOf(4, args.size)) != listOf("-t", "1", "-m")) p += "line ${c.line}: nsenter ${args.joinToString(" ")}"
                }
                "rm" -> {
                    val purge = c.function == PURGE_FUNCTION && args == listOf("-rf", "\"\$TRASH\"")
                    if (!purge) args.filter { it.startsWith("-") }.forEach { if (it != "-f") p += "line ${c.line}: rm $it" }
                }
                "pm" -> if (args.firstOrNull() != "path" || args.size != 2) p += "line ${c.line}: pm ${args.joinToString(" ")}"
                "getevent" -> if (args != listOf("-pl")) p += "line ${c.line}: getevent ${args.joinToString(" ")}"
                "exec" -> if (args.firstOrNull()?.endsWith("/system/bin/sh") != true && args.firstOrNull() != "@SH@") p += "line ${c.line}: exec ${args.firstOrNull()}"
                "sed" -> if (args.any { it == "-i" || it.startsWith("-i") }) p += "line ${c.line}: sed -i"
            }
            if (c.function == MIGRATE_FUNCTION && (n in WRITES || n in WRITE_HELPERS || n == "to_attic") &&
                !(n == "mv" && args in MIGRATE_MOVES)
            ) p += "line ${c.line}: $n ${args.joinToString(" ")} in $MIGRATE_FUNCTION (only its two renames)"
            if (n == "mv" && args in MIGRATE_MOVES && c.function != MIGRATE_FUNCTION) p += "line ${c.line}: mv ${args.joinToString(" ")} outside $MIGRATE_FUNCTION"
            if (n in WRITES) {
                val paths = when (n) {
                    "chown", "chmod" -> args.drop(1)
                    else -> args.filterNot { it.startsWith("-") }
                }
                for (a in paths) if (!stagePath(a, c.function, loopVars)) p += "line ${c.line}: $n $a is not under the stage"
            }
            if (n in WRITE_HELPERS) {
                val a = args.firstOrNull().orEmpty()
                if (!stagePath(a, c.function, loopVars)) p += "line ${c.line}: $n $a is not under the stage"
            }
            if (n == "to_attic") for (a in args) if (a.startsWith("/") || a.contains("..")) p += "line ${c.line}: to_attic $a"
        }
        for (r in scan.redirects) {
            if (!r.op.contains('>')) continue
            val t = r.target
            val fine = t == "/dev/null" || t.startsWith("&") || r.op.endsWith("&") || t == CGROUP || stagePath(t, r.function, loopVars)
            if (!fine) p += "line ${r.line}: writes to $t"
        }
        // The verbs: main's case dispatches exactly these.
        val dispatched = Regex("""^\s{4}([a-z-]+)\) do_""", RegexOption.MULTILINE).findAll(script).map { it.groupValues[1] }.toList()
        if (dispatched.isNotEmpty() || verbs.isNotEmpty()) {
            if (dispatched != verbs) p += "verbs are $dispatched, expected $verbs"
        }
        return p.distinct()
    }

    /** The launcher (rendered for the phone): the same rules, no verbs of its own. */
    fun auditLauncher(launcher: String): List<String> = audit(launcher, verbs = emptyList())
}
