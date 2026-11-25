package com.fahadali.oneos.core.model

/**
 * xnuhost's switches on this phone (docs/oneios.md, "UI (2026-11-25)": Switches and Edit file): the staged runtime's
 * catalog (OneiOS's `oneios-tool switches --json`), the staged image's `overlay/userland/xnuhost.conf` as the tool
 * reads it (`conf show FILE --json`), the rows the Switches screen shows, and the change a tap makes. Root's `conf`
 * verb (`oneios_root.sh`) runs the tool; this only reads what came back and says what to send.
 *
 * The JSON is OneiOS's (fields may be added there, never renamed): unknown fields are ignored, a missing optional one
 * is null. Values may come as strings, whole numbers or booleans; they are kept as the text xnuhost.conf holds
 * ([text]: true is "1", false "0").
 */
object OneiosConf {
    /** The file root edits: in the staged image set, read by xnuhost after `image/xnuhost.conf`. */
    const val FILE = "overlay/userland/xnuhost.conf"

    /** The first runtime whose oneios-tool has `switches` and `conf` (OneiOS's interface for this screen). */
    const val FIRST_RUNTIME = "0.1.33"

    /** Root's limit for the text of `conf write` and `conf check` (the file is a few KiB). */
    const val MAX_TEXT_BYTES = 65_536

    /** A name `conf set` and `conf unset` take (a switch's catalog name, or a boot-arg word). */
    private val NAME = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

    /** Most names root takes in one `conf set` or `conf unset`. */
    const val MAX_CHANGES = 64

    enum class Where { CONF, BOOT_ARG }

    enum class Kind { BOOL, CHOICE, INT, TEXT }

    /** How the screen changes a switch: a toggle (bool, or a choice with an `off`), else a picker of its kind. */
    enum class Control { TOGGLE, CHOICE, NUMBER, TEXT }

    data class Switch(
        val name: String,
        val where: Where,
        val kind: Kind,
        val values: List<String>?,
        val min: Long?,
        val max: Long?,
        val default: String?,
        val off: String?,
        val group: String,
        val title: String,
        val help: String?,
        /** "tested", "not booted", "broken", or another word OneiOS adds; null when the catalog says nothing. */
        val phone: String?,
        val warning: String?,
        /** "session" (the next switch) or "kernel" (needs Update the kernel). */
        val restart: String?,
    ) {
        val control: Control
            get() = when {
                kind == Kind.BOOL -> Control.TOGGLE
                kind == Kind.CHOICE && off != null && default != null && off != default -> Control.TOGGLE
                kind == Kind.CHOICE -> Control.CHOICE
                kind == Kind.INT -> Control.NUMBER
                else -> Control.TEXT
            }

        /** The badge of a switch whose phone state is not "tested": its words ("not booted", "broken"); null otherwise. */
        val badge: String? get() = phone?.takeIf { it.isNotBlank() && it != "tested" }

        val needsKernel: Boolean get() = restart == "kernel"

        /** The value a toggle's on and off stand for. */
        val onValue: String?
            get() = when (kind) {
                Kind.BOOL -> values?.firstOrNull { truthy(it) == true } ?: "1"
                else -> default
            }
        val offValue: String?
            get() = when (kind) {
                Kind.BOOL -> values?.firstOrNull { truthy(it) == false } ?: "0"
                else -> off
            }

        /** A value the catalog takes for this switch; the reason it does not otherwise. */
        fun problem(value: String): String? = when {
            value.isEmpty() && kind != Kind.TEXT -> "a value is needed"
            value.contains('\n') || value.contains('\r') -> "one line only"
            kind == Kind.BOOL -> if (truthy(value) == null) "on or off (1 or 0)" else null
            kind == Kind.CHOICE -> values?.takeIf { it.isNotEmpty() && value !in it }?.let { "one of ${it.joinToString(", ")}" }
            kind == Kind.INT -> {
                val n = value.toLongOrNull()
                when {
                    n == null -> "a whole number"
                    min != null && n < min -> "at least $min"
                    max != null && n > max -> "at most $max"
                    else -> null
                }
            }
            else -> null
        }
    }

    data class Catalog(val version: Int, val switches: List<Switch>)

    data class LineError(val line: Int?, val message: String)

    /** `conf show FILE --json`: the file's text and what it sets. */
    data class Show(
        val path: String?,
        val text: String,
        val set: Map<String, String>,
        val bootArgsAdd: Map<String, String>,
        val unknown: List<String>,
        /** What xnuhost refuses: with one of these the whole file is refused and iOS does not start at the next switch. */
        val errors: List<LineError>,
        /** What xnuhost reads but the tool points out (a key given twice): they do not stop anything. */
        val warnings: List<LineError> = emptyList(),
        /** The file is there (false: an image set without one, shown empty). */
        val exists: Boolean? = null,
        /** The tool kept the file before the last change (FILE.bak): Restore previous can take it back. */
        val backup: Boolean? = null,
    ) {
        /** The value the file gives [s] (its key, or its boot-arg word in `boot-args-add=`); null: the default. */
        fun valueOf(s: Switch): String? = when (s.where) {
            Where.CONF -> set[s.name]
            Where.BOOT_ARG -> bootArgsAdd[s.name] ?: set[s.name]
        }

        companion object {
            /** A file root read without the tool (a runtime older than `conf`): its text only, nothing parsed. */
            fun plain(text: String): Show = Show(null, text, emptyMap(), emptyMap(), emptyList(), emptyList())
        }
    }

    /** One row of the Switches screen. */
    data class Row(
        val switch: Switch,
        /** What the file sets; null: not set (the default holds). */
        val set: String?,
    ) {
        /** The value in effect: the file's, else the default. */
        val value: String? get() = set ?: switch.default

        /** Not at the default: the row is marked and has Reset. A value equal to the default written out is not a change. */
        val changed: Boolean get() = set != null && !same(set, switch.default, switch.kind)

        /** A toggle's position; null for other controls. */
        val on: Boolean?
            get() = when {
                switch.control != Control.TOGGLE -> null
                switch.kind == Kind.BOOL -> truthy(value ?: "") ?: false
                else -> value != switch.offValue
            }
    }

    data class Group(val name: String, val rows: List<Row>)

    /** What a change sends to root: `conf set NAME=VALUE` or `conf unset NAME`. */
    sealed class Change {
        abstract val name: String

        data class Put(override val name: String, val value: String) : Change() {
            val line: String get() = "$name=$value"
        }

        data class Unset(override val name: String) : Change()
    }

    // --- Reading ----------------------------------------------------------------------

    fun parseCatalog(json: String): Result<Catalog> = runCatching {
        val root = JsonRead.parse(json) as? Map<*, *> ?: error("the catalog is not a JSON object")
        val version = (root["version"] as? Long)?.toInt() ?: error("the catalog has no version")
        val list = root["switches"] as? List<*> ?: error("the catalog has no switches")
        val seen = HashSet<String>()
        val switches = list.mapIndexedNotNull { i, v ->
            val o = v as? Map<*, *> ?: error("switch ${i + 1} is not an object")
            val name = (o["name"] as? String)?.takeIf(NAME::matches) ?: return@mapIndexedNotNull null
            if (!seen.add(name)) return@mapIndexedNotNull null
            val kind = when (o["kind"]) {
                "bool" -> Kind.BOOL
                "choice" -> Kind.CHOICE
                "int" -> Kind.INT
                "text" -> Kind.TEXT
                else -> return@mapIndexedNotNull null
            }
            Switch(
                name = name,
                where = if (o["where"] == "boot-arg") Where.BOOT_ARG else Where.CONF,
                kind = kind,
                values = (o["values"] as? List<*>)?.mapNotNull { text(it) },
                min = number(o["min"]),
                max = number(o["max"]),
                default = text(o["default"]),
                off = text(o["off"]),
                group = (o["group"] as? String)?.takeIf { it.isNotBlank() } ?: "Other",
                title = (o["title"] as? String)?.takeIf { it.isNotBlank() } ?: name,
                help = (o["help"] as? String)?.takeIf { it.isNotBlank() },
                phone = o["phone"] as? String,
                warning = (o["warning"] as? String)?.takeIf { it.isNotBlank() },
                restart = o["restart"] as? String,
            )
        }
        Catalog(version, switches)
    }

    fun parseShow(json: String): Result<Show> = runCatching {
        val root = JsonRead.parse(json) as? Map<*, *> ?: error("conf show's answer is not a JSON object")
        Show(
            path = root["path"] as? String,
            text = root["text"] as? String ?: "",
            set = map(root["set"]),
            bootArgsAdd = map(root["boot_args_add"]),
            unknown = (root["unknown"] as? List<*>)?.mapNotNull { text(it) }.orEmpty(),
            errors = errors(root["errors"]),
            warnings = errors(root["warnings"]),
            exists = root["exists"] as? Boolean,
            backup = root["backup"] as? Boolean,
        )
    }

    /** A refusal of the tool (`{"error": ..., "errors": [...]}`), or the errors of `conf check`/`conf write`; null: none. */
    data class Answer(val ok: Boolean, val error: String?, val errors: List<LineError>, val warnings: List<LineError> = emptyList())

    fun parseAnswer(json: String): Answer? {
        val root = runCatching { JsonRead.parse(json) }.getOrNull() as? Map<*, *> ?: return null
        val error = (root["error"] as? String)?.takeIf { it.isNotBlank() }
        val errors = errors(root["errors"])
        val ok = (root["ok"] as? Boolean) ?: (error == null && errors.isEmpty())
        return Answer(ok, error, errors, errors(root["warnings"]))
    }

    private fun errors(v: Any?): List<LineError> = (v as? List<*>)?.mapNotNull { e ->
        when (e) {
            is Map<*, *> -> (e["message"] as? String)?.let { LineError((e["line"] as? Long)?.toInt(), it) }
            is String -> LineError(null, e)
            else -> null
        }
    }.orEmpty()

    private fun map(v: Any?): Map<String, String> = (v as? Map<*, *>)?.entries?.mapNotNull { (k, x) ->
        (k as? String)?.let { key -> text(x)?.let { key to it } }
    }?.toMap().orEmpty()

    /** A JSON value as the text xnuhost.conf holds: a string as it is, a number in digits, true "1", false "0". */
    fun text(v: Any?): String? = when (v) {
        is String -> v
        is Long -> v.toString()
        is Double -> if (v % 1.0 == 0.0) v.toLong().toString() else v.toString()
        true -> "1"
        false -> "0"
        else -> null
    }

    private fun number(v: Any?): Long? = when (v) {
        is Long -> v
        is Double -> v.toLong()
        is String -> v.toLongOrNull()
        else -> null
    }

    /** xnuhost's flag words: 1, yes, true, on; 0, no, false, off. Null: neither. */
    fun truthy(v: String): Boolean? = when (v.trim().lowercase()) {
        "1", "yes", "true", "on" -> true
        "0", "no", "false", "off" -> false
        else -> null
    }

    private fun same(a: String?, b: String?, kind: Kind): Boolean = when {
        a == b -> true
        a == null || b == null -> false
        kind == Kind.BOOL -> truthy(a) != null && truthy(a) == truthy(b)
        kind == Kind.INT -> a.toLongOrNull() != null && a.toLongOrNull() == b.toLongOrNull()
        else -> false
    }

    // --- The screen -------------------------------------------------------------------

    /** The rows grouped by the catalog's `group`, in the catalog's order of first appearance. */
    fun groups(catalog: Catalog, show: Show): List<Group> =
        catalog.switches.groupBy { it.group }.map { (g, list) -> Group(g, list.map { Row(it, show.valueOf(it)) }) }

    /**
     * What setting [row] to [value] sends: the default is an `unset` (the file names only what differs), anything
     * else a `set`. Null when the value is not one the catalog takes ([Switch.problem]).
     */
    fun change(row: Row, value: String): Change? {
        val s = row.switch
        if (s.problem(value) != null) return null
        return if (s.default != null && same(value, s.default, s.kind)) Change.Unset(s.name) else Change.Put(s.name, value)
    }

    /** A toggle flipped to [on]. */
    fun toggle(row: Row, on: Boolean): Change? {
        val v = (if (on) row.switch.onValue else row.switch.offValue) ?: return null
        return change(row, v)
    }

    /** Reset: back to the default. */
    fun reset(row: Row): Change = Change.Unset(row.switch.name)

    /** Root's stdin for `conf set` or `conf unset`: one `NAME=VALUE` (or `NAME`) a line. */
    fun stdin(changes: List<Change>): String {
        require(changes.isNotEmpty() && changes.size <= MAX_CHANGES) { "1 to $MAX_CHANGES changes" }
        require(changes.all { it is Change.Put } || changes.all { it is Change.Unset }) { "set and unset go in separate calls" }
        return changes.joinToString("") { c ->
            require(NAME.matches(c.name)) { "'${c.name}' is not a switch name" }
            when (c) {
                is Change.Put -> {
                    require(!c.value.contains('\n') && !c.value.contains('\r')) { "one line only" }
                    c.line + "\n"
                }
                is Change.Unset -> c.name + "\n"
            }
        }
    }

    // --- Root's answer ----------------------------------------------------------------

    /**
     * Root's `conf` answer, read from its lines: `@@RESULT conf tool|plain` (whether the staged tool reads the file),
     * then parts, each `@@RESULT part <name>` followed by its lines as `| <text>` (`catalog`, `show`, `answer`: the
     * tool's JSON; `text`: the plain file), and `@@RESULT catalog none` when the runtime has no catalog.
     */
    data class Reply(
        val tool: Boolean,
        val parts: Map<String, String>,
        val noCatalog: Boolean,
    ) {
        val catalog: Catalog? get() = parts["catalog"]?.let { parseCatalog(it).getOrNull() }

        /** The file now: the tool's `conf show`, or the plain text root read. */
        val show: Show?
            get() = parts["show"]?.let { parseShow(it).getOrNull() } ?: parts["text"]?.let { Show.plain(it) }

        val answer: Answer? get() = parts["answer"]?.let { parseAnswer(it) }

        companion object {
            fun parse(lines: List<String>): Reply {
                var tool = false
                var noCatalog = false
                val parts = LinkedHashMap<String, StringBuilder>()
                var current: StringBuilder? = null
                for (raw in lines) {
                    val l = raw.trimEnd('\r')
                    when {
                        l == "@@RESULT conf tool" -> tool = true
                        l == "@@RESULT conf plain" -> tool = false
                        l == "@@RESULT catalog none" -> noCatalog = true
                        l.startsWith("@@RESULT part ") -> current = StringBuilder().also { parts[l.removePrefix("@@RESULT part ").trim()] = it }
                        l.startsWith("@@") -> current = null
                        l.startsWith("| ") || l == "|" -> current?.let { b ->
                            if (b.isNotEmpty()) b.append('\n')
                            b.append(if (l == "|") "" else l.substring(2))
                        }
                    }
                }
                return Reply(tool, parts.mapValues { (k, v) -> if (k == "text" && v.isNotEmpty()) "$v\n" else v.toString() }, noCatalog)
            }
        }
    }
}
