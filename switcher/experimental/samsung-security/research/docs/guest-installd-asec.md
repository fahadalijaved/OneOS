# Private ASEC path for the native sibling

The unselected [GVO patch](../compat/native/guest-installd-asec.patch) creates
`/mnt/asec` on the child’s existing private scaffold tmpfs. It covers the
proposed Samsung native sibling that keeps the inherited root in GVO’s private
mount namespace. It supplies a directory for the
[fixed environment input](guest-installd-environment.md), with no daemon launch
or change to the ColorOS image root.

## Which `/mnt` is involved

| Held source | Exact path behavior |
| --- | --- |
| OneOS 0.4.58 `guest_prepare.sh:1231–1235` | Imports the host’s `/mnt` recursively into `$ROOTFS/mnt` and attempts to make the import a slave. It later attempts to make `$ROOTFS` recursively private at line 4405. These propagation changes leave underlying directory objects shared. |
| OneOS 0.4.58 `guest_start.sh:53–75,94–97` | Detaches the listed storage mounts, then rebuilds `/mnt/user/0`, `/mnt/installer`, `/mnt/androidwritable` and the emulated media path. ASEC and non-null volume roots lie outside its removal selector. Neither inspected script has a literal ASEC path or environment variable. |
| Captured Samsung `init.rc:325` | Creates `/mnt/asec` with owner root:system and mode 0755. The nearby `/mnt/secure/asec` directory is a distinct source path. |
| GVO V3 `guest_private_view_owner.c:549–570,599–626` | The child unshares its namespace and makes the inherited mount tree recursively private. It mounts a bounded tmpfs over its own `/mnt`, verifies a fresh mount ID, private propagation and tmpfs identity, then opens a matching writable FD and creates the `gvi/root` scaffold for the image. |

The existing scripts retain their storage behavior. This patch does not create
anything through the legacy `$ROOTFS/mnt` import. It also does not cover
`/mnt/expand` volumes or select an ASEC volume format or migration.

## Preparation and custody

The only new filesystem object is a directory created with an exclusive
`mkdirat` under the verified writable tmpfs FD. The child opens it without
following links, checks the same mount, then sets owner 0:1000 and mode 0755
on that new FD. The scaffold parent keeps mode 0700. This suits the proposed
root native sibling view and grants no traversal profile to a non-root caller.

The child retains that FD through its existing control lifetime. Before
sending `W_PARTIAL`, it independently reopens `/mnt/asec` from its own root
and checks the same inode and mount ID plus the fixed owner and mode. Setup
and readback failures follow the existing child error path. Both child exit
paths consume the FD. The seven transferred roles and parent admission stay
unchanged. A future daemon fork must recheck the actual resolved path before
exec and establish the complete process, loader and endpoint profile.

`python -B tools/prepare_guest_installd_asec.py` verifies seven exact inputs
and applies the one-file patch in memory with the existing strict patch
reader. The inverse reconstructs the entire CRLF original exactly. See the
[inventory](../inventory/guest-installd-asec.json). The canonical source, native
build inputs and application overlays remain unchanged. The static check
ran without compiling, mounting or executing native code.

The separate [guarded controller build](../inventory/retained-asec-controller-build.json)
then compiled this exact one-file change with the seven other saved native
inputs. The 664,296-byte AArch64 static PIE passed the existing ELF checks
and the saved NDK readelf inspection. This build uses the 4 KiB load
alignment profile. The app and host module still select their earlier
controller build. The ASEC directory behavior awaits target execution.
