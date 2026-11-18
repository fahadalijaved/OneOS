# Guest scope population parser

`guest_scope_events_parse` parses the selected non-root cgroup2
`cgroup.events` profile. Linux 6.12 emits two LF-terminated keys, `populated`
and `frozen`, with Boolean values. Population describes live processes
in the subtree. The parser validates both rows and reports only population.
[Kernel ABI](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html#un-populated-notification)
· [Linux 6.12 emitter](https://github.com/torvalds/linux/blob/v6.12/kernel/cgroup/cgroup.c#L3434-L3441)

The selected byte profile is exactly 21 bytes with one ASCII space per
row and no terminal NUL. Either key order is accepted. Each key must occur
once and each value must be one byte, `0` or `1`. Unknown keys, duplicates,
missing rows, excess bytes and malformed or partial input return
`GUEST_SCOPE_POPULATION_UNKNOWN`, the zero value. The existing mountinfo
parser handles variable-width fields. This fixed grammar needs no shared
scanner, allocation or I/O.
[Parser](../compat/native/guest_scope_events.c)
· [Interface](../compat/native/guest_scope_events.h)

The owner must close ingress, verify the actual held scope generation,
and read that scope's real events descriptor from offset zero through
EOF. Reserve at least one extra byte to detect longer input, and keep a
read failure or uncertain EOF out of the parser's success path. A
successful `GUEST_SCOPE_POPULATION_EMPTY` describes only the supplied
sample. The owner still needs migration exclusion, independent child and
adopted-descendant wait accounting, and real resource cleanup before
releasing the view.
[Lifetime contract](guest-zygote-cgroup-lifetime.md)

The authored C parser compiled with pinned UCRT64 GCC under
`-std=c99 -Wall -Wextra -Werror -pedantic -O2`. The resulting PC
executable passed 78 inert byte checks. Coverage includes both row
orders, populated and frozen combinations, equal and conflicting
duplicates, malformed bytes, every proper prefix of both orders, and a
complete span with no NUL terminator. The first build rejected the
fixture's omitted terminator under the strict warning policy. Explicit
array bytes corrected the fixture while the parser stayed unchanged.
The run exercised no kernel or device interface.
[Passing receipt](../out/guest-scope-events/r-b44ea03a/receipt.json)
· [Initial compile diagnostic](../out/guest-scope-events/r-43ad2cd9/compile.stderr)
· [Fixtures](../compat/tests/native/guest_scope_events_test.c)

The exact same parser also compiled with the existing Android NDK targeting
AArch64 API 31. Static ELF inspection confirmed the parser symbol in the
1,496-byte relocatable object. Compile and inspection both exited zero.
[Android compile receipt](../out/guest-scope-events/android-object-5733cae3/receipt.json)

## Read from the held descriptor

The [borrowed-descriptor reader](../compat/native/guest_scope_events_read.c)
requests one full sample from offset zero, then verifies EOF at the exact
sample length. Any short read, excess byte or error returns `UNKNOWN`.
The reader leaves the descriptor open and its cursor unchanged. It relies
on the caller to retain the admitted descriptor and scope generation.

Eleven inert cases checked success, cursor and descriptor ownership, short
and long reads, malformed samples, and failed or nonempty EOF confirmation.
The SDK 31 ARM64 object linked with the existing parser, leaving only the
platform `pread` symbol unresolved. The fixture exercised no cgroup.
Actual scope identity, ingress cutoff and independent process reap remain
required before any view release.
[Reader fixture](../out/guest-scope-events-read/r-a70fdf62/receipt.json)
· [ARM64 link](../out/guest-scope-events-read/link-3b634d46/receipt.json)
