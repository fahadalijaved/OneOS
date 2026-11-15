#!/bin/sh
# GNU stat's `-c FORMAT`, `-L` and `-f` on a machine whose stat is BSD's (macOS), for the core:root
# tests only: host-tools.sh installs it as `stat` when this machine's own stat does not take `-c`.
# The root scripts are written for the phone's stat (toybox, busybox), which reads `-c` as GNU's
# does; the tests run them unchanged and give them this where the machine differs.
#
# Directives: %u %g %U %G %a %A %f %s %b %B %o %Y %X %Z %d %D %i %h %t %T %F %n %N %C %%; with -f:
# %a %f %b %s %S %n %%. Anything else prints `?`, as GNU's prints for what it cannot tell.
REAL=@REAL_STAT@
follow=
fs=
fmt=
have=
while [ $# -gt 0 ]; do
    case "$1" in
        --) shift; break ;;
        --format=*) fmt=${1#--format=}; have=1; shift ;;
        --dereference) follow=-L; shift ;;
        --file-system) fs=1; shift ;;
        -?*)
            a=${1#-}
            shift
            while [ -n "$a" ]; do
                c=${a%"${a#?}"}
                a=${a#?}
                case "$c" in
                    L) follow=-L ;;
                    f) fs=1 ;;
                    c)
                        if [ -n "$a" ]; then fmt=$a; a=
                        else [ $# -gt 0 ] || { echo "stat: option requires an argument -- 'c'" >&2; exit 1; }; fmt=$1; shift
                        fi
                        have=1 ;;
                    *) echo "stat (gnu-stat.sh): unsupported option -$c" >&2; exit 1 ;;
                esac
            done ;;
        *) break ;;
    esac
done
[ $# -gt 0 ] || { echo "stat: missing operand" >&2; exit 1; }
# Without -c the output is BSD's own: nothing in the scripts reads it.
[ -n "$have" ] || exec "$REAL" $follow "$@"

NL='
'
# One BSD call per file: the fields, one a line (BSD stat copies a literal newline of its format).
BSD="%u$NL%g$NL%Su$NL%Sg$NL%Op$NL%Sp$NL%z$NL%b$NL%k$NL%m$NL%a$NL%c$NL%d$NL%i$NL%l$NL%Hr$NL%Lr"

# GNU %F from the file type bits.
ftype() {
    case $(( $1 & 0170000 )) in
        $((0100000))) if [ "$2" = 0 ]; then echo "regular empty file"; else echo "regular file"; fi ;;
        $((0040000))) echo directory ;;
        $((0120000))) echo "symbolic link" ;;
        $((0020000))) echo "character special file" ;;
        $((0060000))) echo "block special file" ;;
        $((0010000))) echo fifo ;;
        $((0140000))) echo socket ;;
        *) echo "weird file" ;;
    esac
}

rc=0
for f in "$@"; do
    if [ -n "$fs" ]; then
        # BSD's stat has no file system mode: df's 1024-byte blocks (-P: one line, no wrapping).
        set -- $(df -Pk "$f" 2>/dev/null | awk 'NR == 2 { print $2, $3, $4 }')
        [ $# = 3 ] || { echo "stat: cannot read file system information for '$f'" >&2; rc=1; continue; }
        total=$1 used=$2 avail=$3
    else
        raw=$("$REAL" $follow -f "$BSD" -- "$f") || { rc=1; continue; }
        { read -r u; read -r g; read -r un; read -r gn; read -r om; read -r sp; read -r sz; read -r blk
          read -r bsz; read -r mt; read -r at; read -r ct; read -r dev; read -r ino; read -r nl; read -r maj
          read -r min; } <<EOF
$raw
EOF
        mode=$(( 0$om ))
    fi
    out=
    rest=$fmt
    while [ -n "$rest" ]; do
        c=${rest%"${rest#?}"}
        rest=${rest#?}
        if [ "$c" != % ]; then out=$out$c; continue; fi
        d=${rest%"${rest#?}"}
        rest=${rest#?}
        if [ -n "$fs" ]; then
            case "$d" in
                a) v=$avail ;;
                f) v=$(( total - used )) ;;
                b) v=$total ;;
                s|S) v=1024 ;;
                n) v=$f ;;
                %) v=% ;;
                *) v='?' ;;
            esac
        else
            case "$d" in
                u) v=$u ;;
                g) v=$g ;;
                U) v=$un ;;
                G) v=$gn ;;
                a) v=$(printf '%o' $(( mode & 07777 ))) ;;
                A) v=$sp ;;
                f) v=$(printf '%x' "$mode") ;;
                s) v=$sz ;;
                b) v=$blk ;;
                B) v=512 ;;
                o) v=$bsz ;;
                Y) v=$mt ;;
                X) v=$at ;;
                Z) v=$ct ;;
                d) v=$dev ;;
                D) v=$(printf '%x' "$dev") ;;
                i) v=$ino ;;
                h) v=$nl ;;
                t) v=$(printf '%x' "$maj") ;;
                T) v=$(printf '%x' "$min") ;;
                F) v=$(ftype "$mode" "$sz") ;;
                n) v=$f ;;
                N) v="'$f'" ;;
                C) v='?' ;;
                %) v=% ;;
                '') v=% ;;
                *) v='?' ;;
            esac
        fi
        out=$out$v
    done
    printf '%s\n' "$out"
done
exit $rc
