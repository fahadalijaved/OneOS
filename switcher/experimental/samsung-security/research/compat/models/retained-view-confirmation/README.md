# View-only confirmation occurrence fixture

The held OneOS app's positive confirmation reaches `LaunchJob.start`. The worker checks cancellation, screen lock, stage and warning gates, then calls the actual `LaunchCommitGuard.commit()`. It creates the legacy session ID, saves the launch and calls `RootVerbs.run(..., LAUNCH, ...)` after that cut.

`ViewPreparationOccurrence` is an inert fixture for a future explicitly selected view-only branch. That branch would call `recordAtCommitCut` with the same attempt's actual guard after the fresh checks, in place of the stock commit. It would then return before creating the legacy session ID, writing the launch record or constructing a root command. The fixture has no operation beyond recording the local occurrence. The candidate branch would need to preserve the real attempt owner and the distinct view-only confirmation.

The fixture compiles with the unchanged `LaunchCommitGuard.kt` from the held build source. The guard supplies the synchronized cancellation-versus-commit decision. A successful view claim burns that attempt's commit and blocks a second view claim or a stock claim on the same guard. An already cancelled or stock-committed attempt earns no occurrence. The recording method makes no external calls and cannot dispatch a callback or launch a process.

Six pure JVM cases passed with the existing Kotlin 2.1.21 compiler and JBR. They cover one occurrence, immediate reentry, prior cancellation, stock-first exclusion, two competing claims, cancellation racing claim and distinct guards. The race cases sample the authored model. See `out/retained-view-confirmation/r-3446106c/receipt.json`, SHA-256 `3c0d04c7604f9d545a6159d3a550a5b976416d358eb9c5cb060b635351cd15e7`.

The fixture sits outside the app source sets and supplies no app or host integration. It neither establishes user-input provenance nor authenticates stage, view or credential access. The saved cut in `docs/retained-root-view-writer-successor.md` still requires the actual selected action, exact stage association where an image is named, and current app-to-host ownership. The built APK, original app sources and build runner were untouched.
