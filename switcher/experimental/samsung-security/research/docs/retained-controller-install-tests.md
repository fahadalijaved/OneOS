# Retained controller installer source models

The selected 20 shell and 13 public app-setup cases have **split-run evidence**. There has been no successful full-default workflow. No installation result here means a running controller, native custody, guest/PIN permission, full APK acceptance, or a phone result.

| Evidence group | Saved receipt | Actual scope |
| --- | --- | --- |
| First19 shell case assertions | `r-91780c1a/receipt.json`, `e39e802626e9cf94df969082356b07f0eaff2a9b206d0b507012b4d443000dc2` | Overall job FAILED at the next case. Root observed completed case markers0â€“18; saved commands include their expected success/refusal/error exits. |
| Real replacement action | `r-e157d5b5/receipt.json`, `88f53ce7a25898875cbece8d821783e935aa882116c36a5edf5ab2cadeb38e07` | PASS_SELECTED_INSTALLER_CASES_ONLY; one filtered case, fullDefaultMatrix=false. |
| Public setup calls | `r-7962981e/receipt.json`, `a47e7a6416acf9e117ed0473a79248e7b268a03aa34d00a1b472870c30d24074` | PASS_SELECTED_INSTALLER_CASES_ONLY;13 filtered app cases, fullDefaultMatrix=false. |

Receipts are under `out/retained-controller-install-tests/`. The focused replacement has independent saved-output proof `out/retained-controller-install-review/FOCUSED-RENAME-ACTUAL-CHECK.json` (`0522e1e4911e8d0fc37cefaa385b617571f138740431b6a04fe79a3ca3bbe978`). The13app saved-output proof is `out/retained-controller-install-review/APP-SELECTED-ACTUAL-CHECK.json` (`ab4a8907e436a6c07d81a0f3d64eeb98dd4bbc4cfca8158ee1a36b34544a9ebb`), covering the actual source outcomes and four genuine contained-shell ACKs without replay. Source-phase report beforeimages are retained under `out/retained-controller-install-model/history/pre-split-result-report/`.

The focused and app jobs have identical177 static-output and197 model-output entries. Their actual Kotlin source bodies are unchanged. Kotlin2.1.21 is an isolated subset tool here, not the app's matching Kotlin2.4.21/Gradle/APK stack. Real RootShell is separately compiled but never run. Actual RootScript/AppAssets/RootVerbs/SetDownloader/RetainedControllerSetup bodies run against authored Android public APIs, model BuildConfig pins, and the approved public RootShell process/path adapter.

The primary shell tests use the actual RootScript validator/launcher and exact captured installer/helper functions. A pinned functions-only script and inert128-byte sample are streamed; the full OneOS script, su and native controller are never executed. UID/mode facts are explicitly synthetic. Existing MSYS tools exercise real private-directory FDs, file identities, SHA checks, exclusive links and contained rename. They do not establish Android/kernel/SELinux ownership.

Coverage includes short/long/corrupt data and prefixes, missing/writable stage/bin, old normal root script, idempotent matching image, foreign/directory/symlink/racing targets, exclusive work ownership, chmod/cleanup failures, and actual replacement after hashing an old held FD. App calls cover asset validation/close failures, expected-pin/context/main refusal, feed failure, install-cancel cutoff, callback reentry, lost/duplicate genuine ACK delivery and refusal to rearm. ACK and End derive from actual contained output/exit/feed; no canned success is supplied.

The replacement diagnostic matters: Python Win32 `os.replace` failed with PermissionError errno13/winerror5 while the MSYS FD was held. The corrected designated adapter uses pinned MSYS `mv -T`; success requires the incoming inode conserved into the target, a different original inode, exact foreign bytes and the incoming name consumed. The strict case then observes handler REFUSED2. However, stat projection also refuses the old FD's `(deleted)` pathname. Thus real replacement plus refusal is proven; the final named-leaf inode-comparison predicate is **not isolated** from that stat-adapter refusal. This remains a coverage limit.

All three earlier failed jobs remain FAILED: `r-86fb3020`/`d5e69090` exposed runner variable shadowing; `r-91780c1a`/`e39e8026` did not exercise its final replacement action; `r-973dbbec`/`b9d71f7a` recorded the Win32 rename failure in a filtered diagnostic. Exact source/receipt/state histories are preserved in corresponding `out/retained-controller-install-model/history/failed-*` directories. None is relabeled a full passing job. The later rename change is confined to its designated action, proven by the exact inverse source delta `MSYS-RENAME-DELTA.json` (`124082b5e3274577a8c17e79d1ec5f1be70228bd3cbf1900f3fb5a5591db056c`).

The public runner accepts existing tools and an explicit checkout:

```text
python -B tools/test_retained_controller_install.py --java-home <JDK home> --kotlin-home <Kotlin home> --shell <Git bash> --oneos-root firmware/oneos-pr/OneOS --case shell:replace_after_hash
```

Repeat `--case app:<name>` to select app cases; filtered receipts cannot claim fullDefaultMatrix. Default invocation attempts all cases but has no successful full-run evidence. No additional workflow was run by this report update. Real RootShell reader/writer/drain/lifetime, actual packaging, minSdk/runtime, native lifecycle and authority remain unaccepted by these models.
