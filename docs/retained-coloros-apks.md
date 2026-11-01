# Retained ColorOS APK activation

The Fold8/Find N6 preparation path now activates the previously verified local
APK bundle retained in `stage/verified_addons`. Updating OneOS had preserved
those files but replaced the custom preparation hooks, so the guest reverted
to the unpatched launcher, Wallpapers, SystemUI, Mind Space and Account Centre.

The checked `fold8_coloros.sh` session asset contains the post-scan loader and
pins the accepted five-entry manifest to SHA-256
`dc070965265f33c3b8c6825b0bd3ffae2877f847a4de41b39d24594ae9d748fc`.
All replacement APK hashes are checked before activation. Changed original
APKs are skipped rather than overwritten. The loader is restricted to the
Fold8/Find N6 stage and matching guest data namespace. A stock stage without
this optional local bundle is unchanged; proprietary APKs are not added to git.

At the end of guest preparation, before framework startup, the loader captures
the existing launcher grid. After original signed package scanning, it binds
the patches into the guest namespaces and restores the captured grid before
refreshing the launcher. It preserves a deliberately selected grid rather than
forcing 4×5 for every user. Existing Chrome preference rollback and path checks
are retained.

If the exact provided official global Photos APK is retained, preparation also
checks its SHA-256 and the donor gallery hash, then binds a clean replacement
directory before package scanning. This releases the donor's duplicate permission
ownership through the normal boot scan. It cannot be applied equivalently by
restarting Photos in an already running guest. Existing shared media is not
cleared. The prior on-device gallery rollback remains available.

Both activation hooks are in existing declared session scripts, so normal app
builds hash and package them and compile their updated integrity pins together.
Do not replace only the staged script files without installing the matching app.

Validation on 2026-11-01: the five original APK hashes matched, and the integrated
worker successfully restored all five patched hashes live. The saved launcher
grid is 4×5. Four activation-boundary tests, four overlay/path tests and the
existing Fold8, performance and ColorOS follow-up tests pass. The matching app and stage update was installed from One UI; all 49 staged
payload hashes passed and the installed APK SHA-256 matches
`bfc37067aa5c273aea8ca2c366eb91a5b1dbe17f527db7ee581ae05b352b620f`.
OneOS offers Boot into ColorOS 17 without a repair prompt. The installed APK
was rebuilt from the exact installed baseline; only the two activation assets,
asset index/list and compiled integrity pins in classes7.dex/classes8.dex changed.
Their DEX verification passed. Original scripts/manifest are backed up at
`/data/local/tmp/oneos-addon-activation-rollback-20261101`; the original APK is
retained locally in `out/addon-integration/installed-baseline.apk`.
Photos activation and persistence across another complete switch still need
the next ColorOS boot. No guest data or shared media was cleared.
