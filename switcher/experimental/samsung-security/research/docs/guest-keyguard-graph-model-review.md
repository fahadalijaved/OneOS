# Guest keyguard graph model review

**PASS for saved authored-model evidence only.** The one recorded workflow
`out/gkm-build/r-8579be32` passed 17 cases and 75 checks; all four compiler
commands and the model JVM exited0. Independent proof
`out/guest-keyguard-graph-model-review/actual/actual-output-check.json`
(`dcdb306d…`) reads saved files only. The reviewer did not replay the producer,
compiler, models or helper classes, and made no Android/native/device call.

The review rehashed all 155 delivery pins, compared 37 executed-input snapshots
and 25 staged Java sources, and independently decoded 63 class files: F17, C15,
V4, driver25 and the two copied authored helper classes. All 24 declaring-field
names, types and modifiers match the pinned graph schema. The four natural
enclosing-instance fields, including Delegate `$2` and `$4`, have the required
descriptor and FINAL|SYNTHETIC flags4112; superclass/interface, InnerClasses and
EnclosingMethod records match. Actual field offsets473/630/786/725 were observed,
not prescribed. No shaping, offset436 repair or production-class patch occurred.
The saved workflow source checks this metadata before starting the helper JVM.

The original and copied helper bytes remain exactly `c687dd93…` and
`205f8f9e…`, derived from unchanged source `d32795c6…`. They were copied rather
than recompiled; no D8 command ran. The actual model JVM executes those authored
SDK37-compiled helpers against small authored worlds, with driver-only system
classpath, `-Xint`, F/platform, C/F, V/C and M/F separation. The positive case
requires V to differ from C. Android.jar, OEM archives and old compiled model
cohorts are absent from the recorded runtime classpath. All commands use owned
cwd/temp/home/native paths, clear five JVM injection variables, bound output and
time, and record successful process reaping. Java8 option warnings are retained.

The public capture/check cases cover nullable service changes, base Context
versus ignored vendor shadow, parents, canonical Class keys/map/cache, CCL,
thread, a held replacement map and final root drift. They do not inspect private
helper data. Named private-field mutations affect authored fixtures only. The
final-root regression is explicitly a source-callstack-selected Looper fault
injection; its passing result does not establish Android Looper callbacks,
scheduling or universal race detection.

Pre-use finding KG-MODEL-01 is resolved in driver `e85316ea…`: constructor
failure restores prior TCCL and attempts every acquired loader close while
preserving the primary throwable. Its initial source and finding, and source
PASS `eadc976a…` / freeze `e919b483…`, remain immutable. Actual receipt
`2b67a94c…` and saved terminal metadata corroborate root-reported execution
`6b7178`, exit0; the terminal metadata is not a second run or raw tool transcript.

No remaining material conflict was found within this saved-byte review.
Authored fixture results establish neither ART access nor actual initialized
guest/vendor placement, policy/user/connection readiness, native security,
callback drain, source-loss handling or an authority/lifetime lease. The graph
component remains unselected; no phone action or goal acceptance follows.
