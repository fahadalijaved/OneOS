package com.fahadali.oneos.core.root;

/** Separate fixed v2 image launcher. Build identity is not host authority. */
final class RetainedRootOfferCommand {
    private RetainedRootOfferCommand() { }
    static String build(String sha256, long bytes) {
        if (sha256 == null || !sha256.matches("[0-9a-f]{64}") || bytes < 1 || bytes > 2097152) {
            throw new IllegalArgumentException("Fixed v2 controller build required");
        }
        return "set -efu\nPATH=/system/bin; export PATH\n"
                + "unset LD_PRELOAD LD_LIBRARY_PATH ENV BASH_ENV\n"
                + "[ \"$(id -u)\" = 0 ] || exit 77\n"
                + "S=/data/local/tmp/oneos\nB=$S/bin\nP=$B/oneos_retained_root_handoff\n"
                + "for D in \"$S\" \"$B\"; do\n"
                + "  [ -d \"$D\" ] && [ ! -L \"$D\" ] || exit 76\n"
                + "  [ \"$(stat -c %u \"$D\")\" = 0 ] || exit 76\n"
                + "  M=$(stat -c %a \"$D\")\n"
                + "  case \"$M\" in [57][0145][0145]) ;; *) exit 76 ;; esac\n"
                + "done\n"
                + "[ -f \"$P\" ] && [ ! -L \"$P\" ] || exit 76\n"
                + "exec 3<\"$P\"\nF=/proc/self/fd/3\n"
                + "[ -f \"$F\" ] && [ \"$(stat -Lc %u \"$F\")\" = 0 ] || exit 76\n"
                + "M=$(stat -Lc %a \"$F\")\n"
                + "case \"$M\" in [57][0145][0145]) ;; *) exit 76 ;; esac\n"
                + "[ \"$(stat -Lc %s \"$F\")\" = " + bytes + " ] || exit 76\n"
                + "H=$(sha256sum \"$F\")\nH=${H%% *}\n"
                + "[ \"$H\" = " + sha256 + " ] || exit 76\n"
                + "exec \"$F\" --host-control-v2\n";
    }
}
