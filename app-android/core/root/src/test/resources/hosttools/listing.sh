#!/bin/sh
# listing.sh DIR FORMAT: `find DIR -printf FORMAT` for the core:root tests' snapshots of a fake root
# (FakeRoot.listing, FakeRoot.snapshot), with GNU find's %P %y %m %s and \n. GNU find where it takes
# -printf; else (BSD find, macOS) the same lines from find's names and `stat -c` (gnu-stat.sh there:
# HostTools puts it first on PATH).
dir=$1
fmt=$2
if find "$dir" -maxdepth 0 -printf '' >/dev/null 2>&1; then
    exec find "$dir" -printf "$fmt"
fi
find "$dir" | while IFS= read -r p; do
    set -- $(stat -c '%f %a %s' "$p")
    case $(( 0x$1 & 0170000 )) in
        $((0100000))) y=f ;; $((0040000))) y=d ;; $((0120000))) y=l ;; $((0020000))) y=c ;;
        $((0060000))) y=b ;; $((0010000))) y=p ;; $((0140000))) y=s ;; *) y=U ;;
    esac
    rel=${p#"$dir"}
    rel=${rel#/}
    out=
    rest=$fmt
    while [ -n "$rest" ]; do
        c=${rest%"${rest#?}"}
        rest=${rest#?}
        case "$c" in
            %) d=${rest%"${rest#?}"}; rest=${rest#?}
               case "$d" in P) out=$out$rel ;; y) out=$out$y ;; m) out=$out$2 ;; s) out=$out$3 ;; %) out=$out% ;; esac ;;
            \\) d=${rest%"${rest#?}"}; rest=${rest#?}
               case "$d" in n) out=$out'
' ;; t) out=$out'	' ;; *) out=$out\\$d ;; esac ;;
            *) out=$out$c ;;
        esac
    done
    printf '%s' "$out"
done
