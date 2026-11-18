# Read-only live profile and source freshness

The saved November 6 local-date captures identify SM-S948U1, build
`CP2A.260605.016.S948U1UES4BZIG`, API37 and SELinux Enforcing. The initial and
profile batches were recorded at 2026-11-07 00:07 and 00:14 UTC. This synthesis
made no new phone query, write, installation, restart, helper launch or build.
The matching inventory pins the selected raw files without publishing device
identifiers, process IDs, namespace numbers, memory addresses or installation
paths.

The new on-device file hash observations match the pinned, independently
rehashed local archives:

| Source role | SHA256 prefix | Existing byte evidence |
| --- | --- | --- |
| Samsung framework.jar | `8095a9ae…` | 54,708,192 bytes |
| Samsung services.jar | `def967fb…` | 28,190,402 bytes |
| Installed OneOS base APK | `9b559545…` | 42,790,067 bytes |

The installed package query reports versionCode74. The byte-identical previously
inspected APK identifies version0.4.57, Full/release. This refreshes those host
archive and installed-app source identities; it does not equate current installed
code with the newer upstream source or prove which bytes a running loader holds.
The earlier staged guest JAR acquisitions are not freshly rehashed by this batch.

The captured compressed kernel configuration decompresses exactly to the saved
plain configuration. It states `# CONFIG_PID_NS is not set`,
`# CONFIG_USER_NS is not set` and `CONFIG_CGROUPS=y`. PID-namespace entry queries
returned no value and failure; no equality is inferred from two empty results.
The initial-role and root-shell cgroup namespace observations match the sampled
SystemServer-role observation. Initial-role and root-shell mount namespace
observations match each other and differ from the SystemServer role. Only these
booleans are published; the observations are separate point samples.

The same saved configuration selects `CONFIG_HAVE_PAGE_SIZE_4KB=y` and
`CONFIG_PAGE_SIZE_4KB=y` (lines824–825). This is a captured 4KB kernel-build
configuration fact, not a runtime `getpagesize` observation or an ELF-loading
result. The current native 4KB build profile has still not been executed.

The untouched binary cgroup captures preserve LF framing. The initial role has
five legacy v1 rows and one root unified row. The root-shell role also has five
legacy rows and one unified row, whose path is non-root. The sampled SystemServer
role has the same hybrid row counts and a non-root unified path. No private path
or PID is reproduced. The earlier text captures use CRLF and remain distinct
historical evidence, not silently normalized parser tests. These observations
support the bounded hybrid source-profile correction; they are not a cgroup
migration, view preparation or native-parser execution result.

The actual public-shell FD observations discriminate the command profiles:

| Operation through proc/self/fd | Implicit descriptor | Explicit same-FD redirection |
| --- | --- | --- |
| File stat | failure, no output | success |
| File hash | failure, no output | success, checksum-shaped output |
| Directory-relative stat | failure, no output | success |

The two successful stat sizes agree. These queries captured command status as
well as client status; the raw cgroup exec-out reads captured client exit0
without a separate remote-exit channel. Explicit descriptor propagation is
therefore required by the observed external-command profile. This is not an
universal claim about all shell internals, FD flags or launcher cleanup. The
separate initial implicit/explicit FD probe shows the same failure/success split.

This closes the selected source-baseline freshness check only. It does not
publish a retained host graph, authenticate a live service/callback occurrence,
prove process or root-manager survival, perform a cgroup write, execute the
native owner, launch a guest or accept credential/biometric/CE behavior. The
current source patches are unchanged by this synthesis. Sampling is non-atomic;
the archive hashes, configuration, namespaces and FD results do not form an
atomic lifetime or authority lease.
