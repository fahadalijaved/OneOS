# Authored safety/profile adapters only; tool tokens become quoted retained paths.
# Actual source functions/launcher are appended unchanged after this prelude.
fx_resolve() { @@READLINK@@ -m -- "$1"; }
fx_meta() { @@PYTHON@@ @@ADAPTER@@ @@CASE@@ @@STATE@@ "$@"; }
stat() {
    [ "$#" = 3 ] || return 97
    fx_path=$(fx_resolve "$3") || return 97
    case "$2" in
        %u|%a) fx_meta stat "$fx_path" "$2" ;;
        %s|%d:%i) fx_meta guard "$fx_path" && @@STAT@@ "$@" ;;
        *) return 97 ;;
    esac
}
chown() {
    [ "$#" = 2 ] || return 97
    fx_path=$(fx_resolve "$2") || return 97
    fx_meta chown "$fx_path" "$1"
}
chmod() {
    [ "$#" = 2 ] || return 97
    fx_path=$(fx_resolve "$2") || return 97
    fx_meta chmod "$fx_path" "$1"
}
mkdir() {
    case "$#" in 1) fx_path=$1 ;; 3) [ "$1" = -m ] || return 97; fx_path=$3 ;; *) return 97 ;; esac
    fx_path=$(fx_resolve "$fx_path") || return 97
    fx_meta guard "$fx_path" && @@MKDIR@@ "$@"
}
rm() {
    [ "$#" = 1 ] || return 97
    fx_path=$(fx_resolve "$1") || return 97
    fx_meta rm "$fx_path" && @@RM@@ "$@"
}
rmdir() {
    [ "$#" = 1 ] || return 97
    fx_path=$(fx_resolve "$1") || return 97
    fx_meta rmdir "$fx_path" && @@RMDIR@@ "$@"
}
ln() {
    [ "$#" = 3 ] && [ "$1" = -T ] || return 97
    fx_from=$(fx_resolve "$2") && fx_to=$(fx_resolve "$3") || return 97
    fx_meta guard "$fx_from" && fx_meta link_target "$fx_to" && @@LN@@ "$@"
}
sha256sum() {
    [ "$#" = 1 ] || return 97
    fx_path=$(fx_resolve "$1") || return 97
    fx_meta guard "$fx_path" || return 97
    fx_sha=$(@@SHA256@@ "$1") || return 97
    case "$1" in /proc/self/fd/7) fx_meta after_target_hash "$fx_path" || return 97 ;; esac
    printf '%s\n' "$fx_sha"
}
