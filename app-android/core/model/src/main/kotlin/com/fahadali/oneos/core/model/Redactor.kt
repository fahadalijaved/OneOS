package com.fahadali.oneos.core.model

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.EnumMap
import java.util.Locale
import java.util.TreeSet

/** What a removed value was. [token] goes into the replacement `<token:hash>`. */
enum class RedactionKind(val token: String, val label: String) {
    IMEI("imei", "IMEI"),
    MEID("meid", "MEID"),
    SERIAL("serial", "serial number"),
    DEVICE_ID("device-id", "device ID"),
    MAC("mac", "MAC address"),
    BSSID("bssid", "Wi-Fi BSSID"),
    SSID("ssid", "Wi-Fi network name or Wi-Fi setting"),
    ICCID("iccid", "SIM card number (ICCID)"),
    EID("eid", "eSIM chip ID (EID)"),
    IMSI("imsi", "subscriber ID (IMSI)"),
    PHONE("phone", "phone number"),
    EMAIL("email", "email address"),
    ACCOUNT("account", "account name"),
    DEVICE_NAME("name", "device or Bluetooth name"),
    IP("ip", "IP address"),
    GEO("geo", "location"),
}

/**
 * What the [Redactor] removed: counts per kind and per file and the property
 * names it removed by key. Never holds a value; goes into the bundle as
 * `redaction.txt` and the `redaction` block of report.json.
 */
class RedactionLog {
    private val counts = EnumMap<RedactionKind, Int>(RedactionKind::class.java)
    private val tokens = EnumMap<RedactionKind, MutableSet<String>>(RedactionKind::class.java)
    private val perFile = sortedMapOf<String, EnumMap<RedactionKind, Int>>()

    /** Property names whose value was removed because of the key name. */
    val propKeys: MutableSet<String> = TreeSet()

    fun record(file: String, kind: RedactionKind, token: String) {
        counts.merge(kind, 1, Int::plus)
        tokens.getOrPut(kind) { mutableSetOf() } += token
        perFile.getOrPut(file) { EnumMap(RedactionKind::class.java) }.merge(kind, 1, Int::plus)
    }

    val total: Int get() = counts.values.sum()

    fun count(kind: RedactionKind): Int = counts[kind] ?: 0

    fun distinct(kind: RedactionKind): Int = tokens[kind]?.size ?: 0

    fun counts(): Map<RedactionKind, Int> = counts.toMap()

    fun fileCounts(): Map<String, Map<RedactionKind, Int>> = perFile.mapValues { it.value.toMap() }

    /** "imei 2, serial 3" (kinds in enum order). */
    fun short(): String =
        if (counts.isEmpty()) "nothing found" else counts.entries.joinToString(", ") { "${it.key.token} ${it.value}" }

    fun render(): String = buildString {
        append("OneOS redaction log (rules ${Redactor.RULES})\n\n")
        append("Every personal value below was replaced by <kind:hash> before this bundle was made.\n")
        append("The hash is salted per bundle: the same value has the same token inside this bundle\n")
        append("only, and cannot be matched across bundles. No value is shown here.\n\n")
        append("Removed values: $total\n")
        for ((kind, n) in counts) {
            append("  ${kind.token.padEnd(10)} ${n.toString().padStart(5)}  (${distinct(kind)} distinct) ${kind.label}\n")
        }
        if (perFile.isNotEmpty()) {
            append("\nBy file:\n")
            for ((file, m) in perFile) {
                append("  $file: ${m.entries.joinToString(", ") { "${it.key.token} ${it.value}" }}\n")
            }
        }
        if (propKeys.isNotEmpty()) {
            append("\nProperties whose value was removed because of the property name:\n")
            for (k in propKeys) append("  $k\n")
        }
    }

    fun toJson(): Map<String, Any?> = linkedMapOf(
        "rules" to Redactor.RULES,
        "saltedPerBundle" to true,
        "total" to total,
        "counts" to counts.entries.associate { it.key.token to it.value },
        "distinct" to counts.keys.associate { it.token to distinct(it) },
        "files" to perFile.mapValues { e -> e.value.entries.associate { it.key.token to it.value } },
        "propertiesByKey" to propKeys.toList(),
    )
}

/**
 * Removes personal data from probe outputs before anything can be shared
 * (docs/app/compat-safety-logs.md sections 3.3 and 7.5). Two ways:
 *
 * - **By key name**: property names (getprop `[key]: [value]` lines, also
 *   values over several lines, and `prop.name=value` lines in other files) that
 *   hold IMEI, MEID, ICCID, EID, IMSI, serial numbers, Samsung device IDs, MAC
 *   addresses, phone numbers, accounts, device names, locations, cell ids, IPs
 *   and Wi-Fi values (`wifi.`/`wifi_` anywhere in the name, `*ssid*`,
 *   `*hotspot*`; plain interface names, numbers and paths stay). Service-state
 *   properties (`init.svc.*`, `ro.boottime.*`) are named after services and
 *   never removed by name. Every value removed this way is also removed
 *   wherever else it appears (identifiers in any letter case, and MAC
 *   addresses with or without separators).
 * - **Bluetooth input device names** ([learnBluetoothInputNames]): removed
 *   wherever they appear.
 * - **By value pattern** in every text line: emails, account names, MAC
 *   addresses (also after a `wifi:` or `mac:` prefix) and BSSIDs, EIDs,
 *   ICCIDs, IMSI/IMEI/MEID next to their label, 15-digit numbers that pass the
 *   IMEI Luhn check, serial numbers next to their label and input device
 *   `Uniq=` values, E.164 phone numbers (+966...), Saudi numbers (05xxxxxxxx,
 *   9665xxxxxxxx), SSIDs next to their label, GPS coordinates, cell ids, and
 *   the names of virtual and Wi-Fi displays (a TV's name in Smart View).
 *
 * Each value becomes `<kind:hash>`, the hash being the first 6 hex digits of
 * SHA-256(salt, kind, value) with a random [salt] per bundle, so a value stays
 * recognisable inside one bundle and nowhere else. Over-removal is accepted;
 * a missed value is a bug.
 */
class Redactor(private val salt: ByteArray) {
    val log = RedactionLog()

    /** A value removed by name: its kind and the spelling its token is made from. */
    private class Known(val kind: RedactionKind, val canonical: String) {
        /** Identifiers match in any letter case; names only as written. */
        val ignoreCase: Boolean get() = kind in CASE_FREE
    }

    /**
     * What a line holds, read in one pass, so a rule skips a line it cannot match
     * (0.4.25: every rule scanned every line, and a session's 180 MB log capture
     * took minutes to read). Only for ASCII lines: with letters outside ASCII,
     * `(?i)` and `ignoreCase` also match other spellings (`ſ` for `s`), so every
     * rule runs as before.
     */
    private class Shape(val s: String) {
        val ascii: Boolean
        /** The longest run of digits 0-9 (`\d`). */
        val digits: Int
        /** The longest chain of hex pairs each followed by `:` or `-` (`a4:c3:`... of a MAC address has 5). */
        val pairs: Int

        /** The longest run of digits right after a `.` (`48.1234` has 4). */
        val decimals: Int

        init {
            var a = true
            var run = 0
            var longest = 0
            var chain = 0
            var lastSep = -4
            var most = 0
            var afterDot = false
            var dec = 0
            for (i in s.indices) {
                val c = s[i]
                if (c.code >= 0x80) a = false
                if (c in '0'..'9') {
                    run++
                    if (run > longest) longest = run
                    if (afterDot && run > dec) dec = run
                } else {
                    run = 0
                    afterDot = c == '.'
                    if ((c == ':' || c == '-') && i >= 2 && hex(s[i - 1]) && hex(s[i - 2])) {
                        chain = if (lastSep == i - 3) chain + 1 else 1
                        lastSep = i
                        if (chain > most) most = chain
                    }
                }
            }
            ascii = a
            digits = longest
            pairs = most
            decimals = dec
        }

        private fun hex(c: Char) = c in '0'..'9' || c in 'a'..'f' || c in 'A'..'F'

        /** The line in lower case (ASCII lines only, where [has] uses it). */
        val lower: String by lazy(LazyThreadSafetyMode.NONE) { s.lowercase(Locale.ROOT) }

        fun has(text: String) = s.contains(text)

        /** [text] right before a character [next] accepts (`+` before `1`-`9`). */
        fun hasBefore(text: String, next: (Char) -> Boolean): Boolean {
            var i = s.indexOf(text)
            while (i >= 0) {
                val j = i + text.length
                if (j < s.length && next(s[j])) return true
                i = s.indexOf(text, i + 1)
            }
            return false
        }

        /** [text] in lower case: true when the line holds it in any letter case. */
        fun hasAnyCase(text: String) = lower.contains(text)
    }

    private val known = LinkedHashMap<String, Known>()
    private var knownSorted: List<Map.Entry<String, Known>>? = null

    fun token(kind: RedactionKind, value: String): String {
        val md = MessageDigest.getInstance("SHA-256")
        md.update(salt)
        md.update(kind.token.toByteArray(Charsets.UTF_8))
        md.update(0)
        md.update(canonical(kind, value).toByteArray(Charsets.UTF_8))
        return "<${kind.token}:${Hashes.hex(md.digest()).take(6)}>"
    }

    /** One spelling per identifier, so `A4-C3-...`, `a4:c3:...` and `A4C3...` get the same token. */
    private fun canonical(kind: RedactionKind, value: String): String {
        if (kind == RedactionKind.MAC || kind == RedactionKind.BSSID) {
            val hex = value.replace(":", "").replace("-", "")
            if (MAC_PLAIN.matches(hex)) return hex.lowercase(Locale.ROOT).chunked(2).joinToString(":")
        }
        return if (kind in CASE_FREE) value.uppercase(Locale.ROOT) else value
    }

    /**
     * A `getprop` dump. All lines are read first so that every value removed by
     * key name is known before any line is written (a serial number can sit in
     * another property, such as the boot config).
     */
    fun redactGetprop(text: String, file: String): String {
        val records = getpropRecords(text.split('\n'))
        for (r in records) {
            if (r.key == null) continue
            keyKind(r.key, r.value)?.let { learn(it, r.value) }
        }
        return records.joinToString("\n") { r ->
            val key = r.key
            val kind = key?.let { keyKind(it, r.value) }
            when {
                key == null -> r.lines.joinToString("\n") { redactLine(it, file) }
                kind != null -> {
                    log.propKeys += key
                    "[$key]: [${whole(kind, r.value, file)}]"
                }
                r.lines.size == 1 -> "[$key]: [${redactValue(r.value, file, context = key)}]"
                else -> r.lines.joinToString("\n") { redactValue(it, file, context = key) }
            }
        }
    }

    /** One property of a getprop dump (its value may span lines), or one other line ([key] null). */
    private class PropRecord(val key: String?, val value: String, val lines: List<String>)

    private fun getpropRecords(lines: List<String>): List<PropRecord> {
        val out = mutableListOf<PropRecord>()
        var i = 0
        while (i < lines.size) {
            val line = lines[i].trimEnd('\r')
            val whole = PROP_LINE.matchEntire(line)
            val start = if (whole == null) PROP_START.matchEntire(line) else null
            when {
                whole != null -> {
                    out += PropRecord(whole.groupValues[1], whole.groupValues[2], listOf(lines[i]))
                    i++
                }
                start != null -> {
                    // A value with line breaks ends at the line ending in `]` before the next property.
                    var end = -1
                    var j = i + 1
                    while (j < lines.size && j <= i + MAX_VALUE_LINES) {
                        val next = lines.getOrNull(j + 1)?.trimEnd('\r')
                        if (PROP_START.matches(lines[j].trimEnd('\r'))) break
                        if (lines[j].trimEnd('\r').endsWith("]") && (next == null || next.isEmpty() || PROP_START.matches(next))) {
                            end = j
                            break
                        }
                        j++
                    }
                    if (end < 0) {
                        out += PropRecord(null, line, listOf(lines[i]))
                        i++
                    } else {
                        val span = lines.subList(i, end + 1)
                        val value = (listOf(start.groupValues[2]) + span.drop(1).map { it.trimEnd('\r') })
                            .joinToString("\n").removeSuffix("]")
                        out += PropRecord(start.groupValues[1], value, span)
                        i = end + 1
                    }
                }
                else -> {
                    out += PropRecord(null, line, listOf(lines[i]))
                    i++
                }
            }
        }
        return out
    }

    /** Any other text file. `prop.name=value` lines get the key-name rules too. */
    fun redactText(text: String, file: String): String =
        if ('\n' !in text) redactLine(text, file) else text.split('\n').joinToString("\n") { redactLine(it, file) }

    private fun redactLine(line: String, file: String): String {
        val kv = KEY_VALUE_LINE.matchEntire(line)
        if (kv != null) {
            val key = kv.groupValues[1]
            val value = kv.groupValues[2]
            val kind = keyKind(key, value.trimEnd('\r'))
            if (kind != null) {
                learn(kind, value.trimEnd('\r'))
                log.propKeys += key
                return "$key=${whole(kind, value.trimEnd('\r'), file)}" + if (value.endsWith('\r')) "\r" else ""
            }
        }
        return redactValue(line, file)
    }

    private fun whole(kind: RedactionKind, value: String, file: String): String {
        val t = token(kind, value)
        log.record(file, kind, t)
        return t
    }

    /**
     * Value patterns first (an email holding a known account name goes as one
     * email), then every value already removed by key name, wherever it is.
     */
    /** [context]: the property name of a getprop value, for rules that look at the whole line. */
    private fun redactValue(input: String, file: String, context: String? = null): String {
        var s = input
        var shape = Shape(s)
        for (rule in VALUE_RULES) {
            if (shape.ascii && !rule.could(shape)) continue
            val t = rule.apply(s, file, context)
            if (t != s) {
                s = t
                shape = Shape(s)
            }
        }
        for ((value, k) in sortedKnown()) {
            if (shape.s !== s) shape = Shape(s)
            val present = when {
                !k.ignoreCase -> s.contains(value)
                shape.ascii && value.all { it.code < 0x80 } -> shape.hasAnyCase(value.lowercase(Locale.ROOT))
                else -> s.contains(value, ignoreCase = true)
            }
            if (!present) continue
            val t = token(k.kind, k.canonical)
            var from = 0
            while (true) {
                val i = s.indexOf(value, from, ignoreCase = k.ignoreCase)
                if (i < 0) break
                log.record(file, k.kind, t)
                from = i + value.length
            }
            s = s.replace(value, t, ignoreCase = k.ignoreCase)
        }
        return s
    }

    private fun sortedKnown(): List<Map.Entry<String, Known>> =
        knownSorted ?: known.entries.sortedByDescending { it.key.length }.also { knownSorted = it }

    /**
     * Bluetooth input devices (`I: Bus=0005` blocks of /proc/bus/input/devices)
     * carry the remote device's name, often the owner's ("Alex's Keyboard").
     * Call before redacting any file, so the name also goes from getevent.txt
     * (which names devices without their bus). Built-in devices stay.
     */
    fun learnBluetoothInputNames(procBusInputDevices: String) {
        var bluetooth = false
        for (raw in procBusInputDevices.lineSequence()) {
            val line = raw.trim()
            when {
                line.isEmpty() -> bluetooth = false
                line.startsWith("I:") -> bluetooth = BUS_BLUETOOTH.containsMatchIn(line)
                bluetooth && line.startsWith("N:") ->
                    INPUT_NAME.find(line)?.let { learn(RedactionKind.DEVICE_NAME, it.groupValues[1], split = false) }
            }
        }
    }

    /**
     * Values the app read elsewhere, such as the saved Wi-Fi network names
     * the log collection reads as root (the home network is often the
     * owner's name): removed wherever they appear in what is redacted after
     * this call, under the same length rules as values removed by key name.
     */
    fun learnNames(kind: RedactionKind, values: Collection<String>) {
        for (v in values) learn(kind, v, split = false)
    }

    /**
     * Remembers [value] (and, with [split], each item of a list such as
     * `imei1,imei2`) so it is removed wherever it appears later. Short and
     * low-variety values (`00000001`) are not spread: they would cut into
     * unrelated numbers such as the input bitmaps of /proc/bus/input/devices.
     */
    private fun learn(kind: RedactionKind, value: String, split: Boolean = true) {
        val parts = if (split) listOf(value) + value.split(',', ' ', ';', '\n').map { it.trim() } else listOf(value.trim())
        for (p in parts) {
            if (p.length < MIN_KNOWN_LENGTH || TRIVIAL.matches(p) || p.startsWith("<")) continue
            if (p.toSet().size < MIN_KNOWN_DISTINCT) continue
            for (spelling in spellings(kind, p)) {
                if (spelling.length < MIN_KNOWN_LENGTH) continue
                if (known.putIfAbsent(spelling, Known(kind, p)) == null) knownSorted = null
            }
        }
    }

    /** The other ways an identifier is written: a MAC with `:`, `-` or no separator; a hex ID without `0x`. */
    private fun spellings(kind: RedactionKind, p: String): List<String> {
        val out = mutableListOf(p)
        if (kind == RedactionKind.MAC || kind == RedactionKind.BSSID) {
            val hex = p.replace(":", "").replace("-", "")
            if (MAC_PLAIN.matches(hex)) {
                val pairs = hex.chunked(2)
                out += hex
                out += pairs.joinToString(":")
                out += pairs.joinToString("-")
            }
        }
        if (kind in CASE_FREE && HEX_0X.matches(p)) out += p.substring(2)
        return out.distinct()
    }

    /** The kind a property name says its value is; null = keep (value patterns still apply). */
    internal fun keyKind(key: String, value: String): RedactionKind? {
        val v = value.trim()
        if (TRIVIAL.matches(v) || v.startsWith("<")) return null
        // init.svc.vendor.serial_logger is a service's state, not a serial number.
        if (SERVICE_STATE_KEY.containsMatchIn(key)) return null
        // The same on every phone of a model or carrier: carrier codes, the Bluetooth
        // DI profile, ro.quick_start.device_id (SM-F976), libraries, and
        // ro.bt.bdaddr_path (where the address is kept, not the address).
        if (NOT_PERSONAL_KEY.containsMatchIn(key)) return null
        if (MODEL_VALUE.matches(v) || LIBRARY_VALUE.matches(v) || PATH_VALUE.matches(v)) return null
        for ((kind, re) in KEY_RULES) {
            if (!re.containsMatchIn(key)) continue
            return when (kind) {
                RedactionKind.IP -> if (IP_LIKE.containsMatchIn(v)) kind else null
                RedactionKind.GEO -> if (NUMBER_LIKE.containsMatchIn(v)) kind else null
                else -> kind
            }
        }
        if (WIFI_KEY.containsMatchIn(key)) {
            if (WIFI_TECHNICAL.matches(v)) return null
            return if (MAC_WHOLE.matches(v)) RedactionKind.BSSID else RedactionKind.SSID
        }
        // Safety net for IDs under names no rule knows (ro.vendor.security.vaultkeeper.id):
        // a long random-looking value, unless the name says it is a digest or build ID.
        if (!UNIQUE_SAFE_KEY.containsMatchIn(key) && looksUnique(v)) return RedactionKind.DEVICE_ID
        return null
    }

    private inner class ValueRule(
        val kind: RedactionKind,
        val regex: Regex,
        /** Capture group holding the value (0 = the whole match). */
        val group: Int = 1,
        /** Only lines that also match this (null = every line). */
        val onlyIn: Regex? = null,
        val accept: (String) -> Boolean = { true },
        /** False only when [regex] cannot match an ASCII line of this [Shape] (text it needs is not there). */
        val could: (Shape) -> Boolean = { true },
    ) {
        fun apply(s: String, file: String, context: String? = null): String {
            if (!regex.containsMatchIn(s)) return s
            if (onlyIn != null && !onlyIn.containsMatchIn(s) && !(context != null && onlyIn.containsMatchIn(context))) {
                return s
            }
            // Tokens already in the text (`<serial:1a2b3c>` looks like "serial: 1a2b3c") are never touched.
            val tokens = TOKEN.findAll(s).map { it.range }.toList()
            return regex.replace(s) { m -> replaceMatch(m, tokens, file) }
        }

        private fun replaceMatch(m: MatchResult, tokens: List<IntRange>, file: String): String {
            val g = m.groups[group] ?: return m.value
            val value = g.value
            if (tokens.any { it.first <= g.range.last && g.range.first <= it.last }) return m.value
            if (value.startsWith("<") || !accept(value)) return m.value
            val t = token(kind, value)
            log.record(file, kind, t)
            val start = g.range.first - m.range.first
            val end = g.range.last + 1 - m.range.first
            return m.value.substring(0, start) + t + m.value.substring(end)
        }
    }

    private val VALUE_RULES: List<ValueRule> = listOf(
        // Not a link of an `a@b@c` chain (oat files: system@framework@services.jar@classes.odex)
        // or a file name (samsung.software.media.c2@1.0-service.rc).
        ValueRule(
            RedactionKind.EMAIL,
            Regex("""(?<![A-Za-z0-9._%+@-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9@-]|\.[A-Za-z0-9])"""),
            group = 0,
            accept = { it.substringAfterLast('.').lowercase(Locale.ROOT) !in FILE_EXTENSIONS },
            could = { it.has("@") },
        ),
        ValueRule(RedactionKind.ACCOUNT, Regex("""Account \{name=([^,}]+)"""), could = { it.has("Account {name=") }),
        ValueRule(
            RedactionKind.ACCOUNT,
            Regex("""(?i)\b(?:account_?name|account)["']?[ \t]*[=:][ \t]*"?([^\s",}<>\]]+)"""),
            accept = { it.length >= 3 && !TRIVIAL.matches(it) },
            could = { it.hasAnyCase("account") },
        ),
        ValueRule(
            RedactionKind.BSSID,
            Regex("""(?i)\bbssid["']?[ \t]*[=:][ \t]*"?((?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2})"""),
            could = { it.pairs >= 5 && it.hasAnyCase("bssid") },
        ),
        // A prefix such as `wifi:` (Wi-Fi display ids) or `mac:` may touch the address; a
        // hex pair before it (`11:` of a longer colon run) may not.
        ValueRule(
            RedactionKind.MAC,
            Regex(
                """(?<![0-9A-Za-z])(?<!\b[0-9A-Fa-f]{2}[:-])((?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})""" +
                    """(?![0-9A-Za-z]|[:-][0-9A-Fa-f])""",
            ),
            accept = { it.lowercase(Locale.ROOT).replace('-', ':') !in MAC_PLACEHOLDERS },
            could = { it.pairs >= 5 },
        ),
        // Input devices: a USB accessory's serial number (Bluetooth ones hold a MAC, removed above).
        ValueRule(RedactionKind.SERIAL, Regex("""\bUniq=([^\s<]\S*)"""), could = { it.has("Uniq=") }),
        // The names of virtual displays (Smart View, a TV's name) and Wi-Fi displays.
        ValueRule(
            RedactionKind.DEVICE_NAME,
            Regex("""\buniqueId[=' "]{1,3}virtual:[^,"'\n]*,\d+,([^"'\n]+),\d+["']"""),
            could = { it.has("uniqueId") },
        ),
        ValueRule(
            RedactionKind.DEVICE_NAME,
            Regex("""\{"([^"\n]+)"[:,](?=[^\n]*?\buniqueId[=' "]{1,3}(?:virtual|wifi):)"""),
            could = { it.has("uniqueId") },
        ),
        ValueRule(RedactionKind.EID, Regex("""(?<![0-9A-Za-z])(89\d{30})(?![0-9A-Za-z])"""), could = { it.digits >= 32 }),
        ValueRule(RedactionKind.ICCID, Regex("""(?<![0-9A-Za-z])(89\d{17,18}[0-9Ff]?)(?![0-9A-Za-z])"""), could = { it.digits >= 19 }),
        ValueRule(
            RedactionKind.IMSI,
            Regex("""(?i)imsi[^0-9\n]{0,20}?(\d{14,15})(?!\d)"""),
            could = { it.digits >= 14 && it.hasAnyCase("imsi") },
        ),
        ValueRule(
            RedactionKind.MEID,
            Regex("""(?i)meid[^0-9A-Za-z\n]{0,20}([0-9A-Fa-f]{14}|\d{18})(?![0-9A-Za-z])"""),
            could = { it.hasAnyCase("meid") },
        ),
        ValueRule(
            RedactionKind.IMEI,
            Regex("""(?i)imei[^0-9\n]{0,20}?(\d{14,16})(?!\d)"""),
            could = { it.digits >= 14 && it.hasAnyCase("imei") },
        ),
        ValueRule(
            RedactionKind.IMEI,
            Regex("""(?<![0-9A-Za-z.])(\d{15})(?![0-9A-Za-z.])"""),
            accept = { luhn(it) },
            could = { it.digits >= 15 },
        ),
        ValueRule(
            RedactionKind.SERIAL,
            Regex("""(?i)\bserial(?:[ _]?no|[ _]?number)?["']?[ \t]*[=:][ \t]*["']?([A-Za-z0-9]{6,})"""),
            could = { it.hasAnyCase("serial") },
        ),
        ValueRule(RedactionKind.PHONE, Regex("""(?<![\w+])(\+[1-9](?:[ -]?\d){7,14})(?!\d)"""), could = { s -> s.hasBefore("+") { it in '1'..'9' } }),
        ValueRule(RedactionKind.PHONE, Regex("""(?<![\w+])((?:00)?966[ -]?5(?:[ -]?\d){8})(?!\d)"""), could = { s -> s.hasBefore("966") { it == '5' || it == ' ' || it == '-' } }),
        ValueRule(RedactionKind.PHONE, Regex("""(?<![\w+.])(05\d(?:[ -]?\d){7})(?![\w.])"""), could = { s -> s.hasBefore("05") { it in '0'..'9' } }),
        ValueRule(
            RedactionKind.SSID,
            Regex("""(?i)\bssid["']?[ \t]*[=:][ \t]*("[^"\n]*"|[^\s,}\]]+)"""),
            accept = { it != "\"\"" },
            could = { it.hasAnyCase("ssid") },
        ),
        // An unlabelled pair only on a line about a location: refresh rates
        // (60.00001, 48.000008) and cutout paths (192.6666666666667,0) are pairs too.
        ValueRule(
            RedactionKind.GEO,
            Regex("""(?<![\d.])(-?\d{1,3}\.\d{4,}[ \t]*,[ \t]*-?\d{1,3}\.\d{4,})(?![\d.])"""),
            onlyIn = LOCATION_CONTEXT,
            accept = { plausibleLatLon(it) },
            could = { it.decimals >= 4 && it.has(",") },
        ),
        ValueRule(
            RedactionKind.GEO,
            Regex("""(?i)\b(?:lat|lon|lng|latitude|longitude)["']?[ \t]*[=:][ \t]*(-?\d{1,3}\.\d+)"""),
            could = { it.decimals >= 1 && (it.hasAnyCase("lat") || it.hasAnyCase("lon") || it.hasAnyCase("lng")) },
        ),
        // Cell ids (CellIdentity* toString) place the phone within a few hundred metres.
        ValueRule(
            RedactionKind.GEO,
            Regex("""\bm(?:Ci|Pci|Tac|Lac|Nci|Cid)=(\d{2,})"""),
            could = { s -> CELL_KEYS.any { s.has(it) } },
        ),
    )

    companion object {
        const val RULES = "oneos.redact/1"

        /** Known values shorter than this are only removed where their key is. */
        const val MIN_KNOWN_LENGTH = 5

        /** Known values with fewer different characters (`00000001`) are only removed where their key is. */
        const val MIN_KNOWN_DISTINCT = 4

        /** Lines a single getprop value may span. */
        private const val MAX_VALUE_LINES = 64

        /** Identifier kinds: matched in any letter case, never a plain path. */
        private val CASE_FREE = setOf(
            RedactionKind.IMEI, RedactionKind.MEID, RedactionKind.SERIAL, RedactionKind.DEVICE_ID, RedactionKind.MAC,
            RedactionKind.BSSID, RedactionKind.ICCID, RedactionKind.EID, RedactionKind.IMSI,
        )

        /** A fresh random salt: one per bundle, never stored. */
        fun forBundle(): Redactor = Redactor(ByteArray(16).also { SecureRandom().nextBytes(it) })

        /** A replacement this redactor wrote: `<kind:6 hex>`. */
        private val TOKEN = Regex("<[a-z-]+:[0-9a-f]{6}>")
        private val CELL_KEYS = listOf("mCi=", "mPci=", "mTac=", "mLac=", "mNci=", "mCid=")

        private val PROP_LINE = Regex("""^\[([^\]]+)]: \[(.*)]$""")
        private val PROP_START = Regex("""^\[([^\]]+)]: \[(.*)$""")

        /** Properties named after a service (its state, pid or start time); never personal. */
        private val SERVICE_STATE_KEY = Regex("""^(init\.svc\.|init\.svc_debug_pid\.|ro\.boottime\.)""")

        /** `I: Bus=0005 ...` (BUS_BLUETOOTH) and `N: Name="..."` of /proc/bus/input/devices. */
        private val BUS_BLUETOOTH = Regex("""(?i)\bBus=0005\b""")
        private val INPUT_NAME = Regex("""^N:\s*Name="(.*)"\s*$""")

        /** `ro.serialno=...`-style lines in files other than getprop (key has a dot). */
        private val KEY_VALUE_LINE = Regex("""^([A-Za-z0-9_\-]+\.[A-Za-z0-9_.\-]+)=(.*)$""")

        /**
         * Values no key rule removes: empty, booleans, 0/1, service states and
         * the like (`net.bt.name` is `Android` on every phone).
         */
        private val TRIVIAL = Regex(
            """(?i)^(|0|1|-1|true|false|none|null|unknown|n/a|default|disabled|enabled|on|off|yes|no|ok|ready|""" +
                """running|stopped|stopping|starting|restarting|loaded|unloaded|android)$""",
        )

        private val KEY_RULES: List<Pair<RedactionKind, Regex>> = listOf(
            RedactionKind.IMEI to Regex("(?i)imei"),
            RedactionKind.MEID to Regex("(?i)meid"),
            RedactionKind.ICCID to Regex("(?i)iccid"),
            RedactionKind.EID to Regex("(?i)(^|[._])(e_?id|euicc_?id)($|[._])"),
            RedactionKind.IMSI to Regex("(?i)imsi"),
            RedactionKind.SERIAL to Regex("(?i)serial"),
            // ro.boot.em.did (Samsung device ID), ro.boot.un (UFS unique number), chip/eMMC/UFS ids,
            // ro.boot.kg.ap (Knox Guard), ro.vendor.skeymast.distname (keystore), the factory
            // calibration date.
            RedactionKind.DEVICE_ID to Regex(
                "(?i)((^|[._])(did|cid|un|unique_?(no|id|number)|device_?id|android_id|ufs_?id|chip_?id|cpu_?id|" +
                    "emmc_?id|kg[._]ap|dist_?name|vaultkeeper[._]id|rfcal_?date)($|[._]))",
            ),
            RedactionKind.MAC to Regex(
                "(?i)(macaddr|mac_addr|mac_address|bdaddr|btaddr|(bt|bluetooth|wifi|wlan|eth|p2p)[._]?addr(ess)?|" +
                    "(^|[._])(wifi_?|wlan_?|bt_?|eth_?|p2p_?)?mac($|[._]))",
            ),
            RedactionKind.PHONE to Regex(
                "(?i)(msisdn|(^|[._])mdn($|[._])|phone[._]?num|line[._]?1[._]?num|voice[._]?mail[._]?num|vm[._]?num|" +
                    "own[._]?num|my[._]?num|subscriber[._]?num)",
            ),
            RedactionKind.ACCOUNT to Regex("(?i)(account|e_?mail|user[._]?name)"),
            RedactionKind.DEVICE_NAME to Regex(
                "(?i)(device[._]?name|host[._]?name|friendly[._]?name|owner[._]?name|nick[._]?name|" +
                    "(^|[._])(bt|bluetooth)[._a-z0-9]*name$)",
            ),
            RedactionKind.GEO to Regex(
                "(?i)((^|[._])(lat|lon|lng|latitude|longitude|cell[._]?id|cell[._]?loc(ation)?)($|[._]))",
            ),
            RedactionKind.IP to Regex("(?i)(dns|ipaddr|ip_addr|gateway|ipv4|ipv6|(^|[._])ip($|[._]))"),
        )

        /** Wi-Fi properties (`wifi.`/`wifi_` anywhere in the name): values are removed unless plainly technical. */
        private val WIFI_KEY = Regex("""(?i)((^|[._])wifi[._]|ssid|hotspot|softap|tether[._a-z]*name)""")
        private const val WIFI_IFACE =
            """(wlan\d*|swlan\d*|p2p\d*|p2p-dev-wlan\d*|p2p-wlan\d*|wifi-aware\d*|aware_nmi\d*|ap\d*|ap_br_wlan\d*|""" +
                """wigig\d*|nan\d*)"""
        private val WIFI_TECHNICAL = Regex(
            """(?i)^($WIFI_IFACE([ ,]+$WIFI_IFACE)*|\d{1,6}|\d+(\.\d+)?m?s|(/[\w.@+-]+)+/?)$""",
        )

        /**
         * Never personal although a rule would match the name: Samsung carrier codes
         * (`*.sec_cid`, `*.sec_pcid`, `sec_cid_ver`), the Bluetooth DI profile
         * (`bluetooth.device_id.*`: Samsung's vendor and product ids), cache nonces and
         * the remote provisioning server.
         */
        private val NOT_PERSONAL_KEY = Regex(
            """(?i)(^(bluetooth\.device_id\.|cache_key\.|remote_provisioning\.hostname$)|(^|[._])sec_p?cid\d*($|[._]))""",
        )

        /** A Samsung model or model prefix (`SM-F976B`, `ro.quick_start.device_id` = `SM-F976`). */
        private val MODEL_VALUE = Regex("""^SM-[A-Z0-9]{3,8}$""")

        /** A library file name (`ro.bluetooth.library_name` = `libbluetooth_qti.so`). */
        private val LIBRARY_VALUE = Regex("""^[\w+-]+(\.[\w+-]+)*\.so(\.\d+)*$""")

        /** Names whose long random-looking values are digests or build IDs, not the phone's. */
        private val UNIQUE_SAFE_KEY = Regex("""(?i)(digest|uuid|fingerprint|vbmeta|(^|[._])build[._]|sha256|checksum)""")

        /** A run of 16+ letters and digits with 4+ digits and 8+ different characters. */
        private val UNIQUE_RUN = Regex("""[A-Za-z0-9]{16,}""")

        private fun looksUnique(v: String): Boolean = UNIQUE_RUN.findAll(v).any { m ->
            val r = m.value
            r.count { it.isDigit() } >= 4 && r.any { it.isLetter() } && r.toSet().size >= 8
        }

        /** Words that make an unlabelled decimal pair a location (`persist.vendor.gnss.lastfix`). */
        private val LOCATION_CONTEXT = Regex("""(?i)(location|gps|gnss|fused|fix|latitude|longitude|\blat\b|\blon\b|\blng\b|coord|geo)""")

        /** File name endings that are also letters-only "top-level domains" after an `@`. */
        private val FILE_EXTENSIONS = setOf(
            "rc", "so", "jar", "apk", "apex", "capex", "dex", "odex", "vdex", "oat", "art", "xml", "json", "txt",
            "conf", "cfg", "prop", "bin", "img", "sh", "cil", "ko", "mbn", "policy", "list",
        )

        /** An absolute path and nothing else. */
        private val PATH_VALUE = Regex("""^(/[\w.@+-]+)+/?$""")
        private val HEX_0X = Regex("""^0[xX][0-9A-Fa-f]{8,}$""")
        private val MAC_PLAIN = Regex("""^[0-9A-Fa-f]{12}$""")
        private val MAC_WHOLE = Regex("""^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$""")
        private val MAC_PLACEHOLDERS = setOf("00:00:00:00:00:00", "02:00:00:00:00:00", "ff:ff:ff:ff:ff:ff")
        /** IPv4, or IPv6 (2+ colons); not `default:6 0:400` (persist.device_config.netd_native.dns_event_subsample_map). */
        private val IP_LIKE = Regex("""\b\d{1,3}(\.\d{1,3}){3}\b|[0-9a-fA-F]{0,4}(:[0-9a-fA-F]{0,4}){2,}""")
        private val NUMBER_LIKE = Regex("""\d""")

        /** IMEIs end in a Luhn check digit. */
        fun luhn(digits: String): Boolean {
            if (digits.isEmpty() || !digits.all { it in '0'..'9' }) return false
            var sum = 0
            for ((i, c) in digits.reversed().withIndex()) {
                var d = c - '0'
                if (i % 2 == 1) {
                    d *= 2
                    if (d > 9) d -= 9
                }
                sum += d
            }
            return sum % 10 == 0
        }

        private fun plausibleLatLon(pair: String): Boolean {
            val parts = pair.split(',').map { it.trim().toDoubleOrNull() }
            val lat = parts.getOrNull(0) ?: return false
            val lon = parts.getOrNull(1) ?: return false
            return kotlin.math.abs(lat) <= 90.0 && kotlin.math.abs(lon) <= 180.0
        }
    }
}
