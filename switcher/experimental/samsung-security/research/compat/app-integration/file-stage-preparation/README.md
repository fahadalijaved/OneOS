# File-backed OneOS Prepare and Stop

This sidecar derives a standalone tester from the held isolated OneOS activity and broker. The package is `com.fahadali.oneos.viewprep.filetree` with version code 1 and version name `0.0.1-filetree`. Its manifest keeps the launcher activity and the same-process, unexported `RetainedRootHostServiceV2`. The default build disables both the Prepare action and the broker's BEGIN entry. An explicitly enabled source candidate still needs an exact protected host profile and confirmation in the activity.

Run from the nested workspace. Both commands generate Java and manifest files under `out/file-stage-preparation-app/` with an exact input and output receipt.

```text
python -B compat/app-integration/file-stage-preparation/prepare.py
python -B compat/app-integration/file-stage-preparation/prepare.py --enable-preparation
```

The held Full app goes through `SwitchConfirm` and `RetainedHandoffControllerSetup`. That setup uses `RootVerbs` and `RootShell` to install a fixed controller in the stock OneOS stage. The standalone tester instead requires the preprovisioned, root-owned controller at `/data/local/tmp/oneos-viewprep/bin/oneos_retained_tree_preparation`. BEGIN requires the exact 746,760-byte `r-b40000a8` executable digest. The existing command checks the opened file's owner, mode, length and digest, then passes FD 3 through the `--host-control-v2` exec. The separately provisioned `guest.erofs`, fs-verity pin, backing anchor and private data are controller prerequisites. The sidecar does no provisioning.

The real host worker keeps one Prepare and one Stop on the same retained occurrence. Native requires the complete first PREPARE frame within 120 seconds of COMMIT and retains the 30-second frame budget. The activity's bind wait and the broker's shorter reply wait only bound observation. Neither extends the native window nor proves that an in-flight command was cancelled. The activity keeps the serial worker's terminal observation before posting the UI update, so a queued Stop cannot race a known terminal receipt.

Native mode 6 means local tree and stage closure. Host status 6 reports that receipt while process and descriptor cleanup is still pending. Host status 7 also requires the same native process's pidfd exit, ended workers and successful owned cleanup. Only status 8 identifies a Stop before native dispatch. Failed Prepare can still reach a local terminal, and a missing reply can leave cleanup unconfirmed. These outcomes carry no launch or security authority.
