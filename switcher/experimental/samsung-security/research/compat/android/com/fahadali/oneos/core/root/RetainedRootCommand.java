package com.fahadali.oneos.core.root;

/** Fixed, opened-image launcher. Build identity is not host authority. */
final class RetainedRootCommand {
    private RetainedRootCommand() { }

    static String build(String expectedSha256, long expectedBytes) {
        if (expectedSha256 == null || expectedSha256.length() != 64
                || expectedBytes < 1 || expectedBytes > 2097152) {
            throw new IllegalArgumentException("Fixed root-controller identity required");
        }
        for (int i = 0; i < expectedSha256.length(); i++) {
            char c = expectedSha256.charAt(i);
            if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) {
                throw new IllegalArgumentException("Lowercase SHA256 required");
            }
        }
        return "set -efu\n"
                + "PATH=/system/bin; export PATH\n"
                + "unset LD_PRELOAD LD_LIBRARY_PATH ENV BASH_ENV\n"
                + "[ \"$(id -u)\" = 0 ] || exit 77\n"
                + "S=/data/local/tmp/oneos\nB=$S/bin\nP=$B/oneos_retained_root_session\n"
                + "for D in \"$S\" \"$B\"; do\n"
                + "  [ -d \"$D\" ] && [ ! -L \"$D\" ] || exit 76\n"
                + "  [ \"$(stat -c %u \"$D\")\" = 0 ] || exit 76\n"
                + "  M=$(stat -c %a \"$D\")\n"
                + "  case \"$M\" in [57][0145][0145]) ;; *) exit 76 ;; esac\n"
                + "done\n"
                + "[ -f \"$P\" ] && [ ! -L \"$P\" ] || exit 76\n"
                // Keep the same opened image for metadata, hashing and exec.
                + "exec 3<\"$P\"\n"
                + "F=/proc/self/fd/3\n"
                + "[ -f \"$F\" ] && [ \"$(stat -Lc %u \"$F\")\" = 0 ] || exit 76\n"
                + "M=$(stat -Lc %a \"$F\")\n"
                + "case \"$M\" in [57][0145][0145]) ;; *) exit 76 ;; esac\n"
                + "[ \"$(stat -Lc %s \"$F\")\" = " + expectedBytes + " ] || exit 76\n"
                + "H=$(sha256sum \"$F\")\nH=${H%% *}\n"
                + "[ \"$H\" = " + expectedSha256 + " ] || exit 76\n"
                + "exec \"$F\" --closed-session-v1\n";
    }
}
