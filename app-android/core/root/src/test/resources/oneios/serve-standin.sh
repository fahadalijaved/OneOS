#!/bin/sh
# A stand-in for `oneios-tool serve` (OneiOS's tools/oneios-tool/README.md, "serve: one process for the app (the
# protocol)", protocol 1), for OneiosToolSessionTest and OneiosToolScriptTest. It speaks the protocol's lines and
# does no work. POSIX sh (dash, bash, mksh).
#   serve-standin.sh serve [--stage DIR] ...
# Requests (one JSON line each; only "id", "cmd" and "seconds" are read):
#   ping            ok at once
#   wait            the tool's own test command: start, step, progress every 0.1 s for STANDIN_TICKS ticks
#                   (default 10), then ok. It starts a child (`sleep 300`, its pid in $STANDIN_DIR/child.ID) as a
#                   worker would, and ends it
#   cancel          {"cmd":"cancel","id":X}: the running request X ends (its child too) with cancelled, by request
#   pause, resume   {"cmd":"pause","id":X}: the running wait X holds (no progress) and says paused; resume: resumed, it goes on
#   standin-net     net waiting (next 2.0), STANDIN_PAUSE s of silence, net resumed, ok
#   standin-refuse  refused, code space, with the tool's kind of text
#   standin-fail    failed, code io
#   standin-lines   three line events and a row, then ok
#   standin-quiet   no answer at all (for the app's silence limit)
#   standin-heat    heat paused, STANDIN_PAUSE s (default 1.5) of silence, heat resumed, ok
#   anything else   refused, code unknown
# The end of stdin cancels the running work (by eof), then bye (why eof). With STANDIN_IDLE=N it ends by itself N s
# after the last request (bye, why idle). With STANDIN_HANG=1 it does not end at the end of its input (for the app's
# backstop). STANDIN_PROTOCOL changes the hello's proto.
D=${STANDIN_DIR:-${TMPDIR:-/tmp}}
say() { printf '%s\n' "$*"; }
field() { # <line> <key>: a string or number value
    printf '%s\n' "$1" | sed -n "s/.*\"$2\":\"*\([A-Za-z0-9._-]*\)\"*.*/\1/p" | head -n 1
}
say "{\"ev\":\"hello\",\"proto\":${STANDIN_PROTOCOL:-1},\"tool\":\"0.0.0-standin\",\"pid\":$$,\"jobs\":2,\"nice\":10,\"idle\":${STANDIN_IDLE:-300},\"stage\":\"$D\",\"cmds\":[\"ping\",\"cancel\",\"wait\",\"pause\",\"resume\"]}"
IDLE_PID=
idle() {
    [ -n "$IDLE_PID" ] && kill "$IDLE_PID" 2>/dev/null
    IDLE_PID=
    [ -n "${STANDIN_IDLE:-}" ] || return 0
    me=$$
    ( sleep "$STANDIN_IDLE"; touch "$D/idle.$me"; kill -TERM "$me" ) < /dev/null > /dev/null 2>&1 &
    IDLE_PID=$!
}
end_work() { # <id> <by>: its worker and its child, then its cancelled
    w=$(cat "$D/worker.$1" 2>/dev/null)
    c=$(cat "$D/child.$1" 2>/dev/null)
    [ -n "$w" ] && kill "$w" 2>/dev/null
    [ -n "$c" ] && kill "$c" 2>/dev/null
    rm -f "$D/worker.$1" "$D/child.$1"
    say "{\"ev\":\"cancelled\",\"id\":\"$1\",\"cmd\":\"wait\",\"by\":\"$2\",\"removed\":1,\"text\":\"stopped; its file was removed\"}"
}
end_all() { # <by>
    for f in "$D"/worker.*; do [ -f "$f" ] && end_work "${f##*.}" "$1"; done
    [ -n "$IDLE_PID" ] && kill "$IDLE_PID" 2>/dev/null
}
on_term() {
    if [ -e "$D/idle.$$" ]; then rm -f "$D/idle.$$"; end_all idle; say '{"ev":"bye","why":"idle","threads":1,"children":0}'
    else end_all sigterm; say '{"ev":"bye","why":"sigterm","threads":1,"children":0}'; fi
    exit 0
}
trap on_term TERM
idle
while IFS= read -r line; do
    id=$(field "$line" id)
    cmd=$(field "$line" cmd)
    idle
    case "$cmd" in
        ping) say "{\"ev\":\"ok\",\"id\":\"$id\",\"cmd\":\"ping\",\"seconds\":0.0,\"text\":\"pong\"}" ;;
        wait)
            sleep 300 < /dev/null > /dev/null 2>&1 &
            echo $! > "$D/child.$id"
            (
                n=${STANDIN_TICKS:-10}
                say "{\"ev\":\"start\",\"id\":\"$id\",\"cmd\":\"wait\",\"jobs\":2,\"steps\":[{\"step\":\"wait\",\"text\":\"Waiting\"},{\"step\":\"place\",\"text\":\"Putting it in place\"}]}"
                say "{\"ev\":\"space\",\"id\":\"$id\",\"path\":\"$D\",\"need\":1000,\"free\":5000000000,\"reserve\":268435456}"
                say "{\"ev\":\"step\",\"id\":\"$id\",\"step\":\"wait\",\"n\":1,\"of\":2,\"text\":\"Waiting\"}"
                i=0
                while [ $i -lt "$n" ]; do
                    if [ -e "$D/held.$id" ]; then sleep 0.1; continue; fi
                    i=$((i + 1))
                    say "{\"ev\":\"progress\",\"id\":\"$id\",\"step\":\"wait\",\"done\":$i,\"total\":$n,\"unit\":\"seconds\",\"percent\":$((i * 100 / n)).0,\"eta\":$((n - i))}"
                    sleep 0.1
                done
                say "{\"ev\":\"step\",\"id\":\"$id\",\"step\":\"place\",\"n\":2,\"of\":2,\"text\":\"Putting it in place\"}"
                kill "$(cat "$D/child.$id" 2>/dev/null)" 2>/dev/null
                rm -f "$D/child.$id" "$D/worker.$id"
                say "{\"ev\":\"ok\",\"id\":\"$id\",\"cmd\":\"wait\",\"seconds\":1.0,\"text\":\"waited $n ticks\",\"ticks\":$n}"
            ) < /dev/null &
            echo $! > "$D/worker.$id"
            ;;
        cancel)
            if [ -f "$D/worker.$id" ]; then end_work "$id" request
            else say "{\"ev\":\"error\",\"text\":\"cancel: no request $id runs or waits\"}"; fi
            ;;
        standin-refuse) say "{\"ev\":\"refused\",\"id\":\"$id\",\"cmd\":\"$cmd\",\"code\":\"space\",\"text\":\"not enough free space in /data: 12.0 GB needed, 3.1 GB free\"}" ;;
        standin-fail) say "{\"ev\":\"failed\",\"id\":\"$id\",\"cmd\":\"$cmd\",\"code\":\"io\",\"text\":\"os.img: read error at 4096\"}" ;;
        standin-lines)
            for k in 1 2 3; do say "{\"ev\":\"line\",\"id\":\"$id\",\"stream\":\"out\",\"text\":\"line $k\"}"; done
            say "{\"ev\":\"row\",\"id\":\"$id\",\"kind\":\"file\",\"path\":\"bin/xnuhost\",\"ok\":true}"
            say "{\"ev\":\"ok\",\"id\":\"$id\",\"cmd\":\"$cmd\",\"seconds\":0.0,\"text\":\"3 lines\",\"lines\":3}"
            ;;
        standin-quiet) ;;
        pause)
            if [ -f "$D/worker.$id" ]; then touch "$D/held.$id"; say "{\"ev\":\"paused\",\"id\":\"$id\",\"by\":\"request\",\"text\":\"paused; the parts are kept\"}"
            else say "{\"ev\":\"error\",\"id\":\"$id\",\"code\":\"no-such-request\",\"text\":\"pause: no request $id runs\"}"; fi
            ;;
        resume)
            if [ -e "$D/held.$id" ]; then rm -f "$D/held.$id"; say "{\"ev\":\"resumed\",\"id\":\"$id\",\"by\":\"request\",\"text\":\"going on\"}"
            else say "{\"ev\":\"error\",\"id\":\"$id\",\"code\":\"not-paused\",\"text\":\"resume: request $id is not paused\"}"; fi
            ;;
        standin-net)
            (
                say "{\"ev\":\"net\",\"id\":\"$id\",\"state\":\"waiting\",\"try\":1,\"next\":2.0,\"text\":\"no network: trying again in 2 s\"}"
                sleep "${STANDIN_PAUSE:-1.5}"
                say "{\"ev\":\"net\",\"id\":\"$id\",\"state\":\"resumed\",\"text\":\"the network is back\"}"
                say "{\"ev\":\"ok\",\"id\":\"$id\",\"cmd\":\"$cmd\",\"seconds\":1.5,\"text\":\"done after the network came back\"}"
            ) < /dev/null &
            ;;
        standin-heat)
            (
                say "{\"ev\":\"heat\",\"id\":\"$id\",\"state\":\"paused\",\"why\":\"case\",\"text\":\"the case is at 44 C: the work waits\",\"case\":44}"
                sleep "${STANDIN_PAUSE:-1.5}"
                say "{\"ev\":\"heat\",\"id\":\"$id\",\"state\":\"resumed\",\"why\":\"case\",\"text\":\"cool again\",\"case\":42}"
                say "{\"ev\":\"ok\",\"id\":\"$id\",\"cmd\":\"$cmd\",\"seconds\":1.5,\"text\":\"done after the pause\"}"
            ) < /dev/null &
            ;;
        *) say "{\"ev\":\"refused\",\"id\":\"${id:-0}\",\"cmd\":\"$cmd\",\"code\":\"unknown\",\"text\":\"no such command: $cmd\"}" ;;
    esac
done
if [ "${STANDIN_HANG:-0}" = 1 ]; then
    while :; do sleep 1; done
fi
end_all eof
say '{"ev":"bye","why":"eof","threads":1,"children":0}'
