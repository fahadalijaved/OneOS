# Closed-controller installer: shell source constraints

These are primary-source compatibility findings, not observed execution on the
phone. The exact Samsung shell/utility binaries remain a separate device-profile
obligation. No Android shell or generated controller was executed on the PC.

Android's current upstream mksh lexer recognizes a redirection prefix consisting
of one digit. Its manual specifies the same limit. A descriptor above nine used
internally by the shell does not make `exec 10<...` a supported user redirection.
The first bootstrap draft used slots 10 and 11; the successor uses only slots
3–6 in the parent and closes the child's owned copies that conflict with the
installer's slots 5–9. The parent retains its own descriptors through child exit.
See the [AOSP lexer](https://android.googlesource.com/platform/external/mksh/+/refs/heads/main/src/lex.c)
and [manual](https://android.googlesource.com/platform/external/mksh/+/refs/heads/main/src/mksh.1).

The current upstream Toybox `ln` option declaration supports `-T` but does not
include `-L`. The installer therefore uses the regular payload name beneath its
actual retained private-directory descriptor, rather than using a magic-link
source with an unproved dereference flag. Before publication it checks that this
regular nonlink name is the retained payload inode; after publication it checks
the destination against that same inode. Publication remains a single no-clobber
hard link with `-T`; there is no overwrite or weaker fallback. See the
[AOSP implementation](https://android.googlesource.com/platform/external/toybox/+/refs/heads/main/toys/posix/ln.c).

The selected raw sources were read through Gitiles' base64 text endpoint and are
kept only in ignored `firmware/full-app-shell-reference/`. Their hashes and URLs
are recorded in `out/full-app-integration/aosp-shell-source-read.json`:
lexer `56edd10b...`, mksh header `b50e3f2c...`, manual `abf44a61...` and Toybox
`ln` `53e41858...`. The browser's raw-code views failed; the read-only Windows
HTTP client retrieved those bytes without executing them.

The Windows checkout also contained CRLF shell-asset bytes. Root preserved that
exact before-image, converted only CRLF to LF for the selected app root script,
and added one path-specific `.gitattributes` rule. The original public Git blob
is LF, SHA256 `04eace4bd0c0bc9b6979ea3048975c85b3821fe669a3777dd407a6de7ff222ae`.
The revised runnable asset is `7d2bedaf...`, 92,233 bytes; this EOL conversion does
not alter its selected source statements. Its exact record is
`out/full-app-integration/rootsh-lf-normalization.json`. Global Git settings and
other existing assets were not changed. A later full APK still needs its own
packaged-byte and Android runtime checks.

The existing Git Bash successfully opened a repository-owned directory on a
single-digit descriptor and resolved/stat'ed its `/proc/self/fd` entry. This
permits a contained desktop test of the authored installer and real launcher
generation. It is not Android mount, ownership, utility or process acceptance.
