# Capture permit: current access remains unproved

**The proposed DAC permissions fit the observed Samsung system_server IDs; SELinux read access remains unknown.** The dedicated directory and request do not currently exist. Their absence is not an SELinux denial, and root readability would not prove access from system_server. No permit, label, policy, code or phone state was changed by this task.

Root's read-only observation pins PID27202 in `u:r:system_server:s0`, filesystem UID/GID1000, and global **Enforcing**. Observed parents are:

| Path | Mode/owner | Actual label |
| --- | --- | --- |
| `/data` | 0771 system:system | `system_data_root_file:s0` |
| `/data/local` | 0751 root:root | `system_data_file:s0` |
| `/data/local/tmp` | 0771 shell:shell | `shell_data_file:s0` |
| `/data/system` | 0775 system:system | `system_data_file:s0` |

Both `/data/local/tmp/oneos-samsung-security-capture` and its `request-v1` are reported **ABSENT**. The observation is `out/retained-capture-permit-preflight/20261106T040831455570Z-ecc1ece9e4954c8390ed44eb0abe4cbc/observation.json`, SHA256 `ba8a463e484ec7528391387f06c4b4af407bbfae2dc8a442d553bf6616a88e1f`. This is metadata at that observation, not an attempted read in the target process.

## Actual fixed source behavior

`PermitFile.java:12–13` fixes the current pathname. Lines23–32 perform named metadata lookup, **O_RDONLY directory open**, held metadata validation, then O_RDONLY request open. Lines38/46 read the request and explicit EOF; lines47–56 recheck held/named identities. The required directory is root:1000 **0750** (67–68); the request is a single-link regular root:1000 **0440** file (72–74), not0640. With observed filesystem GID1000, those hypothetical target permissions and the observed parent modes fit DAC traversal/read. No target inode, ACL or identity exists to verify yet.

SELinux must separately permit parent search and applicable metadata operations, opening the directory for read, and opening/reading the actual request type. This is an access-category description, not a decoded complete kernel check trace. A policy allowing only file read would not by itself close this source path's directory open. Any failure is caught at line58 and returns false; the helper itself supplies no denial diagnostic. It does not bypass policy, change credentials or relabel an object.

## Available policy evidence and limits

Bounded `rg --files` searches of captured Samsung/nested firmware found no unpacked applicable Samsung file-context or CIL/policy input; the full mounted-OS archive was **not extracted**. Keystore key-context files are present, but do not answer this filesystem access question. Bounded existing tool/toolchain filename and source searches found no named `sesearch`, `seinfo`, `checkpolicy`, `secilc`, `sepolicy-analyze`, `libsepol` or authored compiled-policy reader. This is a scoped search result, not an assertion that no such file exists anywhere on the PC or inside archives. No software was installed and no OEM tool ran.

Unpacked **ColorOS donor** policy/context files exist and were identified by path. They are excluded from Samsung admission evidence. No conclusion about Samsung allow rules follows from donor label names, a generic Android neverallow, presumed parent inheritance, or Enforcing alone. The actual object type can depend on creation/transition behavior and later labeling; a pathname is not an active label.

## Dedicated `/data/system` alternative

`/data/system/oneos-samsung-security-capture` is a **conditional alternative**, not an approved change. Its observed parent type is more aligned with system service state than the current shell-data parent; its parent DAC also fits system_server. However, current evidence does not prove applicable Samsung file-context/type-transition/allow constraints or the labels of future root-created objects there. Moving the pathname does not automatically establish access. The current source is fixed and would require a separately reviewed source/build change. No existing data directory or policy should be reused or modified to manufacture a pass.

The minimal remaining evidence is applicable **effective Samsung policy** for the observed domain, actual directory/file types and required operations. If a permit is separately authorized and created later, exact read-only labels/modes/owner/inode metadata must be checked. A bounded AVC record from an already-authorized attempt could prove that particular denial; no new attempt is requested here, and absent AVC is not success. The fresh parent/domain/ID queries have already been supplied by root; no further phone action is needed merely to restate this unknown.

The authored verifier checks 24 saved source/metadata facts and emits [the bounded inventory](../inventory/retained-capture-permit-access.json). It is not a policy decoder or an Android access test.
