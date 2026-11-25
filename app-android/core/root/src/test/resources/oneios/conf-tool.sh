#!/bin/sh
# A stand-in for the staged runtime's bin/oneios-tool as the app's Switches screen calls it through
# oneios_root.sh conf, for OneiosScriptTest. It answers as OneiOS's oneios-tool does (tools/oneios-tool/crates/
# oneios-conf, OneiOS aa8cfa4): `switches --json --runtime DIR` prints DIR/lib/switches.json (exit 1 without one);
# `conf <show|check|set|unset|write|restore> --json [--runtime DIR] [--force] FILE [NAME=VALUE...|NAME...]`; exit 0
# done, 1 refused with {"error": ...} (the file untouched), 2 a wrong command line. show, and set, unset, write and
# restore after their change, print the file as `conf show --json` does (text, set, boot_args_add, unknown, errors,
# warnings, exists, backup). A line "bad line" (no '=') is the one error it finds; a key given twice is a warning. The
# name "refuseme" is refused by set. Changes keep FILE.bak (restore swaps them). --runtime DIR without
# DIR/lib/switches.json is refused, as the real tool's catalog load. Every call is appended to
# $ONEIOS_TEST_ROOT/conftool/calls. $ONEIOS_TEST_ROOT/conftool/mode "old" is a runtime's tool from before these
# commands (clap's unknown subcommand: usage on stderr, exit 2).
R="$ONEIOS_TEST_ROOT/conftool"
mkdir -p "$R"
echo "$*" >> "$R/calls"
if [ "$(cat "$R/mode" 2>/dev/null)" = old ]; then
    echo "error: unrecognized subcommand '$1'" >&2
    exit 2
fi

json_text() { # <file>: its text as a JSON string
    awk 'BEGIN { printf "\"" } { gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); gsub(/\t/, "\\t"); printf "%s\\n", $0 } END { printf "\"" }' "$1"
}
json_set() { # <file>: {"key": "value"} of its KEY=VALUE lines (the last wins), boot-args-add's words left out
    awk -F= '/^[A-Za-z0-9][A-Za-z0-9._-]*=/ && $1 != "boot-args-add" { v[$1] = substr($0, length($1) + 2); if (!($1 in seen)) { order[++n] = $1; seen[$1] = 1 } }
        END { printf "{"; for (i = 1; i <= n; i++) printf "%s\"%s\": \"%s\"", (i > 1 ? ", " : ""), order[i], v[order[i]]; printf "}" }' "$1"
}
json_boot() { # <file>: {"word": "value"} of its boot-args-add= words
    awk '/^boot-args-add=/ { s = substr($0, 15); m = split(s, w, " "); for (i = 1; i <= m; i++) { split(w[i], kv, "="); if (!(kv[1] in seen)) { order[++n] = kv[1]; seen[kv[1]] = 1 } v[kv[1]] = kv[2] } }
        END { printf "{"; for (i = 1; i <= n; i++) printf "%s\"%s\": \"%s\"", (i > 1 ? ", " : ""), order[i], v[order[i]]; printf "}" }' "$1"
}
errors() { # <file>: the JSON list of its errors
    awk 'BEGIN { printf "[" } !/^#/ && !/^$/ && !/=/ { printf "%s{\"line\": %d, \"message\": \"not KEY=VALUE\"}", (n++ ? ", " : ""), NR } END { printf "]" }' "$1"
}
warnings() { # <file>: a key given again
    awk -F= 'BEGIN { printf "[" } /^[A-Za-z0-9][A-Za-z0-9._-]*=/ && $1 != "boot-args-add" { if ($1 in first) printf "%s{\"line\": %d, \"message\": \"%s is given again (first on line %d): the last one is used\"}", (n++ ? ", " : ""), NR, $1, first[$1]; else first[$1] = NR } END { printf "]" }' "$1"
}
has_errors() { grep -v '^#' "$1" | grep -v '^$' | grep -qv '='; }
show() { # <file>
    f=$1
    exists=true
    [ -f "$f" ] || { exists=false; : > "$R/empty"; f="$R/empty"; }
    backup=false
    [ ! -f "$1.bak" ] || backup=true
    printf '{"path": "%s", "text": %s, "set": %s, "boot_args_add": %s, "unknown": [], "errors": %s, "warnings": %s, "exists": %s, "backup": %s}\n' \
        "$1" "$(json_text "$f")" "$(json_set "$f")" "$(json_boot "$f")" "$(errors "$f")" "$(warnings "$f")" "$exists" "$backup"
}

if [ "$1" = switches ]; then
    [ "$2" = --json ] && [ "$3" = --runtime ] && [ -n "$4" ] || { echo "usage: switches --json --runtime DIR" >&2; exit 2; }
    [ -f "$4/lib/switches.json" ] || { echo "{\"error\": \"$4/lib/switches.json: no such file\"}"; exit 1; }
    cat "$4/lib/switches.json"
    exit 0
fi
[ "$1" = conf ] || { echo "conf-tool.sh: not a stand-in for: $*" >&2; exit 2; }
op=$2
shift 2
json= force=
while :; do
    case "$1" in
        --json) json=1; shift ;;
        --force) force=1; shift ;;
        --runtime)
            [ -f "$2/lib/switches.json" ] || { echo "{\"error\": \"$2/lib/switches.json: no such file\"}"; exit 1; }
            shift 2 ;;
        *) break ;;
    esac
done
[ -n "$json" ] || { echo "conf-tool.sh: the app always asks for --json" >&2; exit 2; }
f=$1
[ -n "$f" ] || { echo "usage: conf $op FILE" >&2; exit 2; }
shift
case "$op" in
    show) show "$f" ;;
    check)
        if has_errors "$f"; then printf '{"errors": %s, "unknown": [], "warnings": %s}\n' "$(errors "$f")" "$(warnings "$f")"; exit 1; fi
        printf '{"errors": [], "unknown": [], "warnings": %s}\n' "$(warnings "$f")" ;;
    set|unset)
        [ $# -gt 0 ] || { echo "usage: conf $op FILE NAME..." >&2; exit 2; }
        for a in "$@"; do
            case "$a" in refuseme*) echo "{\"error\": \"refused: $a\"}"; exit 1 ;; esac
        done
        cp "$f" "$f.bak"
        for a in "$@"; do
            k=${a%%=*}
            grep -v "^$k=" "$f" > "$f.tmp"
            [ "$op" = unset ] || echo "$a" >> "$f.tmp"
            mv "$f.tmp" "$f"
        done
        show "$f" ;;
    write)
        cat > "$f.in"
        if [ -z "$force" ] && has_errors "$f.in"; then
            printf '{"error": "the text has errors: xnuhost would refuse the file; nothing written (--force writes it anyway)", "errors": %s, "unknown": [], "warnings": []}\n' "$(errors "$f.in")"
            rm -f "$f.in"
            exit 1
        fi
        cp "$f" "$f.bak"
        mv "$f.in" "$f"
        show "$f" ;;
    restore)
        [ -f "$f.bak" ] || { echo "{\"error\": \"$f.bak: no backup\"}"; exit 1; }
        mv "$f" "$f.swap" && mv "$f.bak" "$f" && mv "$f.swap" "$f.bak"
        show "$f" ;;
    *) echo "error: unrecognized subcommand '$op'" >&2; exit 2 ;;
esac
exit 0
