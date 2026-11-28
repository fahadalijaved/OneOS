#!/usr/bin/env python3
"""Priority non-camera fixes for Galaxy S22 (SM8450, android12-5.10, One UI 8.0 host):
1. VINTF vndk_fragment + system_ext farm_dir fallbacks (oneos-vendor-ndk.xml, hwservicemanager,
   oneos-telephony.jar) + system/etc/vintf/manifest.xml fallback (guest_prepare.sh).
2. product/etc/displayconfig farm_dir fallback when overlayfs is refused (guest_prepare.sh).
3. Bixby voice wake-up guard for SM8450 Snapdragon profiles (oneos_switch.sh).
4. a16_connectivity_compat.py setPollOnOpen(false) fallback for R8-stripped One UI 9.5 services.jar.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARE = (ROOT / "switcher/assets/guest_prepare.sh").read_text()
SWITCH = (ROOT / "switcher/assets/oneos_switch.sh").read_text()
A16CC = ROOT / "switcher/patches/a16_connectivity_compat.py"


def extract_fn(src: str, name: str) -> str:
    marker = f"\n{name}() {{"
    part = src.split(marker, 1)[1]
    body = part.split("\n}\n", 1)[0]
    return f"{name}() {{{body}\n}}\n"


FARM_FN = extract_fn(PREPARE, "farm_dir")
UNFARM_FN = extract_fn(PREPARE, "unfarm_dir")
DDC_XML_FN = extract_fn(PREPARE, "ddc_xml")

SYSEXT_BLOCK = (
    "vndk_fragment() {"
    + PREPARE.split("\nvndk_fragment() {", 1)[1].split(
        "\n# Display configs for the phone's two panels", 1
    )[0]
    + "\n"
)

DISPLAYCONFIG_BLOCK = (
    'PETC="$GUEST_PRODUCT/etc"\n'
    + PREPARE.split('\nPETC="$GUEST_PRODUCT/etc"\n', 1)[1].split(
        "\n# ", 1
    )[0]
)
# Ensure we stop cleanly right after the displayconfig outer `fi`.
_dc_start = PREPARE.index('\nPETC="$GUEST_PRODUCT/etc"\n') + 1
_dc_end = PREPARE.index("\n    else\n        echo \"Display config: read-only overlay on product/etc refused, left out\"\n    fi\nfi\n", _dc_start)
DISPLAYCONFIG_BLOCK = PREPARE[_dc_start : _dc_end] + (
    '\n    else\n        echo "Display config: read-only overlay on product/etc refused, left out"\n    fi\nfi\n'
)

# Stateful mock busybox supporting tmpfs, overlay (configurable), --bind, --rbind,
# remount,bind,ro, umount -l, chcon, and failure injection by target/source substring.
MOCK_BB = r'''#!/bin/sh
cmd=$1; shift
echo "BB $cmd $*" >> "$CALLS"
case "$cmd" in
    chcon)
        exit 0 ;;
    mount)
        # Parse options & args
        fstype=""
        opts=""
        bind=0
        rbind=0
        make_priv=0
        args=""
        while [ $# -gt 0 ]; do
            case "$1" in
                -t) fstype=$2; shift 2 ;;
                -o) opts=$2; shift 2 ;;
                --bind) bind=1; shift ;;
                --rbind) rbind=1; shift ;;
                --make-private|--make-rprivate|--make-rslave) make_priv=1; shift ;;
                *) args="$args|$1"; shift ;;
            esac
        done
        [ $make_priv = 1 ] && exit 0
        # Split positional args (up to 2)
        a1=$(printf '%s' "$args" | cut -d'|' -f2)
        a2=$(printf '%s' "$args" | cut -d'|' -f3)
        if [ "$fstype" = overlay ]; then
            [ "${ALLOW_OVERLAY:-0}" = 1 ] || exit 1
            # Simulate overlay: rw overlay uses upperdir as top layer; ro overlay uses first lowerdir.
            top=$(printf '%s' "$opts" | sed -n 's/.*upperdir=\([^,]*\).*/\1/p')
            if [ -z "$top" ]; then
                top=$(printf '%s' "$opts" | sed -n 's/.*lowerdir=\([^:,]*\).*/\1/p')
            fi
            [ -n "$top" ] && [ -d "$top" ] && cp -a "$top"/. "$a2"/ 2>/dev/null || true
            ro="rw"
            case ",$opts," in *,ro,*) ro="ro" ;; esac
            printf 'overlay %s overlay %s,%s 0 0\n' "$a2" "$ro" "$opts" >> "$PROC_MOUNTS"
            printf 'overlay on %s type overlay (%s,%s)\n' "$a2" "$ro" "$opts" >> "$MOUNT_OUT"
            exit 0
        fi
        if [ "$fstype" = tmpfs ]; then
            mkdir -p "$a2"
            printf 'tmpfs %s tmpfs rw 0 0\n' "$a2" >> "$PROC_MOUNTS"
            printf 'tmpfs on %s type tmpfs (rw)\n' "$a2" >> "$MOUNT_OUT"
            exit 0
        fi
        if [ -n "$opts" ]; then
            case ",$opts," in
                *,remount,*)
                    if [ -n "${FAIL_REMOUNT:-}" ] && [ "$a1" = "$FAIL_REMOUNT" ]; then
                        exit 1
                    fi
                    if [ "${SKIP_RO_RECORD:-0}" != 1 ]; then
                        awk -v m="$a1" '$2 == m { $4 = "ro" } { print }' "$PROC_MOUNTS" > "$PROC_MOUNTS.tmp" && mv "$PROC_MOUNTS.tmp" "$PROC_MOUNTS"
                    fi
                    exit 0 ;;
            esac
        fi
        if [ $bind = 1 ] || [ $rbind = 1 ]; then
            if [ -n "${FAIL_BIND_DST:-}" ] && [ "$a2" = "$FAIL_BIND_DST" ]; then
                exit 1
            fi
            if [ -n "${FAIL_BIND_SRC:-}" ] && [ "$a1" = "$FAIL_BIND_SRC" ]; then
                exit 1
            fi
            if [ -d "$a1" ]; then
                rm -rf "$a2" && mkdir -p "$a2"
                cp -a "$a1"/. "$a2"/ 2>/dev/null || true
            elif [ -f "$a1" ]; then
                mkdir -p "$(dirname "$a2")"
                cp -a "$a1" "$a2"
            fi
            printf 'bindsrc %s tmpfs rw 0 0\n' "$a2" >> "$PROC_MOUNTS"
            printf 'bindsrc on %s type tmpfs (rw)\n' "$a2" >> "$MOUNT_OUT"
            exit 0
        fi
        exit 0 ;;
    umount)
        [ "$1" = -l ] && shift
        target=$1
        awk -v m="$target" '$2 != m { print }' "$PROC_MOUNTS" > "$PROC_MOUNTS.tmp" && mv "$PROC_MOUNTS.tmp" "$PROC_MOUNTS"
        awk -v m="$target" '$3 != m { print }' "$MOUNT_OUT" > "$MOUNT_OUT.tmp" && mv "$MOUNT_OUT.tmp" "$MOUNT_OUT"
        exit 0 ;;
    *)
        exec "$cmd" "$@" ;;
esac
'''


def patch_shell_paths(code: str) -> str:
    return (
        code.replace("/proc/mounts", "$PROC_MOUNTS")
        .replace("/system_ext/apex", "$HOST_SE_APEX")
    )


class SyntaxAndSwitchGuardTest(unittest.TestCase):
    def test_shell_scripts_pass_sh_n(self):
        for rel in ("switcher/assets/guest_prepare.sh", "switcher/assets/oneos_switch.sh"):
            r = subprocess.run(["sh", "-n", str(ROOT / rel)], capture_output=True, text=True)
            self.assertEqual(0, r.returncode, f"{rel}: {r.stderr}")

    def test_bixby_guard_profiles_and_opt_in(self):
        start = SWITCH.index('            case \\"${ONEOS_PROFILE:-}\\" in\n')
        end = SWITCH.index("            esac\n", start) + len("            esac\n")
        raw = SWITCH[start:end]
        # Verify the inner double-quoted shell snippet expands to valid sh and runs as expected.
        expanded = raw.replace('\\"', '"').replace("\\$", "$")
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            calls = t / "calls.log"
            bb = t / "bb"
            bb.write_text('#!/bin/sh\necho "$*" >> "$CALLS"\nexit 0\n')
            bb.chmod(0o755)
            # Check inner syntax after expansion
            syn = subprocess.run(["sh", "-n", "-c", expanded], capture_output=True, text=True)
            self.assertEqual(0, syn.returncode, syn.stderr)

            def run_guard(profile: str, bixby: str = "0"):
                calls.write_text("")
                env = dict(
                    os.environ,
                    BB=str(bb),
                    PID="4242",
                    ONEOS_PROFILE=profile,
                    ONEOS_GUEST_BIXBY=bixby,
                    CALLS=str(calls),
                )
                r = subprocess.run(["sh", "-c", expanded], env=env, capture_output=True, text=True)
                self.assertEqual(0, r.returncode, r.stderr)
                return [l for l in calls.read_text().splitlines() if l], r.stdout

            for prof in ("s-ultra-8750", "s-8450", "s-plus-8450", "s-ultra-8450", "s-ultra-8450-jp", "s-fe-8450"):
                with self.subTest(disabled=prof):
                    got, out = run_guard(prof, "0")
                    self.assertEqual(2, len(got))
                    self.assertIn("pm disable-user --user 0 com.samsung.android.bixby.wakeup", got[0])
                    self.assertIn("pm disable-user --user 0 com.samsung.android.bixby.agent", got[1])
                    self.assertIn(f"[UI Activator] {prof}: com.samsung.android.bixby.wakeup turned off", out)

            for prof in ("s-8450", "s-ultra-8750"):
                with self.subTest(opt_in=prof):
                    got, out = run_guard(prof, "1")
                    self.assertEqual([], got)
                    self.assertEqual("", out)

            for prof in ("s-ultra-8850", "s-9925", "f8u", ""):
                with self.subTest(untouched=prof):
                    got, out = run_guard(prof, "0")
                    self.assertEqual([], got)
                    self.assertEqual("", out)


class SystemExtAndVintfFallbackTest(unittest.TestCase):
    def run_sysext(
        self,
        *,
        allow_overlay: bool = False,
        vndk_need: str = "31",
        has_sysext_vintf_dir: bool = True,
        hwsm: int = 0,
        inj: int = 0,
        fail_bind_dst: str = "",
        fail_remount: str = "",
        skip_ro_record: bool = False,
    ):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            stage = t / "stage"
            rootfs = t / "rootfs"
            sysext = rootfs / "system/system_ext"
            host_se_apex = t / "host_se_apex"
            stage.mkdir(parents=True)
            host_se_apex.mkdir(parents=True)
            (rootfs / "system/etc/vintf").mkdir(parents=True)
            (rootfs / "system/etc/vintf/manifest.xml").write_text(
                '<manifest version="1.0" type="framework">\n    <hal/>\n</manifest>\n'
            )
            (sysext / "etc").mkdir(parents=True)
            if has_sysext_vintf_dir:
                (sysext / "etc/vintf/manifest").mkdir(parents=True)
                (sysext / "etc/vintf/manifest/existing.xml").write_text("<manifest/>\n")
            (sysext / "bin").mkdir(parents=True)
            (sysext / "bin/keepbin").write_text("bin")
            (sysext / "framework").mkdir(parents=True)
            (sysext / "framework/existing.jar").write_text("jar")
            if inj:
                (stage / "oneos-telephony.jar").write_text("ONEOS-TELEPHONY-JAR")

            bb = t / "bb"
            bb.write_text(MOCK_BB)
            bb.chmod(0o755)
            bin_dir = t / "bin"
            bin_dir.mkdir()
            (bin_dir / "pidof").write_text("#!/bin/sh\necho 777\n")
            (bin_dir / "pidof").chmod(0o755)

            proc_mounts = t / "proc_mounts"
            proc_mounts.write_text("")
            mount_out = t / "mount_out"
            mount_out.write_text("")
            calls = t / "calls"
            calls.write_text("")

            script = (
                'mount() { cat "$MOUNT_OUT"; }\n'
                + patch_shell_paths(FARM_FN)
                + patch_shell_paths(UNFARM_FN)
                + patch_shell_paths(SYSEXT_BLOCK)
                + '\necho "FINAL VNDK_NEED=$VNDK_NEED INJ=$INJ HWSM=$HWSM"\n'
            )
            env = dict(
                os.environ,
                BB=str(bb),
                STAGE=str(stage),
                ROOTFS=str(rootfs),
                GUEST_SYSTEM_EXT=str(sysext),
                HOST_SE_APEX=str(host_se_apex),
                PROC_MOUNTS=str(proc_mounts),
                MOUNT_OUT=str(mount_out),
                CALLS=str(calls),
                VNDK_NEED=vndk_need,
                INJ=str(inj),
                HWSM=str(hwsm),
                HWSM_WHY="radio HAL",
                SEC_IMS="0",
                SAMCAM="0",
                ONEUI95_TAB_S9_FE="0",
                ALLOW_OVERLAY="1" if allow_overlay else "0",
                FAIL_BIND_DST=fail_bind_dst.replace("{SYSEXT}", str(sysext)).replace("{ROOTFS}", str(rootfs)),
                FAIL_REMOUNT=fail_remount.replace("{SYSEXT}", str(sysext)),
                SKIP_RO_RECORD="1" if skip_ro_record else "0",
                PATH=f"{bin_dir}:{os.environ['PATH']}",
            )
            r = subprocess.run(["sh", "-c", script], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, r.returncode, f"stdout={r.stdout}\nstderr={r.stderr}")
            return {
                "stdout": r.stdout,
                "stderr": r.stderr,
                "calls": calls.read_text().splitlines(),
                "mounts": proc_mounts.read_text(),
                "sysext": sysext,
                "rootfs": rootfs,
                "stage": stage,
                "manifest_text": (rootfs / "system/etc/vintf/manifest.xml").read_text(),
                "frag_path": sysext / "etc/vintf/manifest/oneos-vendor-ndk.xml",
                "frag_exists": (sysext / "etc/vintf/manifest/oneos-vendor-ndk.xml").exists(),
                "frag_text": (sysext / "etc/vintf/manifest/oneos-vendor-ndk.xml").read_text()
                if (sysext / "etc/vintf/manifest/oneos-vendor-ndk.xml").exists()
                else "",
                "hwsm_exists": (sysext / "bin/hwservicemanager").exists(),
                "inj_text": (sysext / "framework/oneos-telephony.jar").read_text()
                if (sysext / "framework/oneos-telephony.jar").exists()
                else "",
            }

    def test_kernel510_binds_vintf_fragment_via_farm_dir_when_manifest_dir_exists(self):
        res = self.run_sysext(allow_overlay=False, vndk_need="31", has_sysext_vintf_dir=True)
        self.assertIn("FINAL VNDK_NEED= INJ=0 HWSM=0", res["stdout"])
        self.assertIn("VINTF: vendor-ndk 31 bound into system_ext/etc/vintf/manifest (no overlayfs)", res["stdout"])
        self.assertNotIn("bound copy of the guest's system manifest", res["stdout"])
        self.assertTrue(any("mount --make-private" in c and "system_ext_ov" in c for c in res["calls"]), res["calls"])
        self.assertTrue(res["frag_exists"])
        self.assertIn("<version>31</version>", res["frag_text"])
        self.assertNotIn("<vendor-ndk>", res["manifest_text"])

    def test_kernel510_falls_back_to_system_manifest_when_sysext_vintf_dir_absent(self):
        res = self.run_sysext(allow_overlay=False, vndk_need="31", has_sysext_vintf_dir=False)
        self.assertIn("FINAL VNDK_NEED= INJ=0 HWSM=0", res["stdout"])
        self.assertIn("VINTF: vendor-ndk 31 added to a bound copy of the guest's system manifest", res["stdout"])
        self.assertIn("<vendor-ndk>\n        <version>31</version>\n    </vendor-ndk>\n</manifest>", res["manifest_text"])

    def test_kernel510_unwinds_vintf_farm_on_bind_failure_and_uses_system_manifest(self):
        res = self.run_sysext(
            allow_overlay=False,
            vndk_need="31",
            has_sysext_vintf_dir=True,
            fail_bind_dst="{SYSEXT}/etc/vintf/manifest/oneos-vendor-ndk.xml",
        )
        self.assertIn("FINAL VNDK_NEED= INJ=0 HWSM=0", res["stdout"])
        self.assertIn("VINTF: vendor-ndk 31 added to a bound copy of the guest's system manifest", res["stdout"])
        # unfarm_dir must have been called for vintf_farm
        self.assertTrue(any("umount -l" in c and "vintf_farm/farm" in c for c in res["calls"]), res["calls"])
        self.assertIn("<version>31</version>", res["manifest_text"])

    def test_overlay_success_adds_vintf_fragment_and_clears_vndk_need(self):
        res = self.run_sysext(allow_overlay=True, vndk_need="31", has_sysext_vintf_dir=True)
        self.assertIn("FINAL VNDK_NEED= INJ=0 HWSM=0", res["stdout"])
        self.assertIn("VINTF: vendor-ndk 31 added to the guest's framework manifest", res["stdout"])
        self.assertNotIn("bound copy of the guest's system manifest", res["stdout"])

    def test_kernel510_binds_hwsm_and_readonly_telephony_jar_via_farm_dir(self):
        res = self.run_sysext(allow_overlay=False, vndk_need="", hwsm=1, inj=1)
        self.assertIn("FINAL VNDK_NEED= INJ=1 HWSM=1", res["stdout"])
        self.assertIn("HIDL: the guest sees system_ext/bin/hwservicemanager", res["stdout"])
        self.assertIn("Signal poll: framework/oneos-telephony.jar bound read-only via farm_dir (no overlayfs)", res["stdout"])
        self.assertTrue(res["hwsm_exists"])
        self.assertEqual("ONEOS-TELEPHONY-JAR", res["inj_text"])

    def test_kernel510_telephony_jar_fails_closed_if_not_readonly(self):
        res = self.run_sysext(
            allow_overlay=False,
            vndk_need="",
            inj=1,
            fail_remount="{SYSEXT}/framework/oneos-telephony.jar",
        )
        self.assertIn("FINAL VNDK_NEED= INJ=0 HWSM=0", res["stdout"])
        self.assertNotIn("bound read-only via farm_dir", res["stdout"])
        self.assertTrue(any("umount -l" in c and "fw_farm/farm" in c for c in res["calls"]), res["calls"])


class DisplayConfigFallbackTest(unittest.TestCase):
    HOST_LOG = (
        "Display 4619827259835644672 (HWC display 0): port=0 pnpId=SEC\n"
        'DisplayDeviceInfo{"Built-in Screen": uniqueId="local:4619827259835644672", 1080 x 2340, '
        "modeId 1, density 420, brightnessMaximum 1.0, port=0}\n"
    )

    def run_dc(
        self,
        *,
        allow_overlay: bool = False,
        existing_dc_files=None,
        existing_mounts: str = "",
        host_log: str = HOST_LOG,
        fail_bind_dst: str = "",
    ):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            stage = t / "stage"
            rootfs = t / "rootfs"
            product = rootfs / "system/product"
            petc = product / "etc"
            stage.mkdir(parents=True)
            (rootfs / "system/framework").mkdir(parents=True)
            (petc / "selinux").mkdir(parents=True)
            (petc / "selinux/product_seapp_contexts").write_text("seapp=keep\n")
            if existing_dc_files is not None:
                (petc / "displayconfig").mkdir(parents=True)
                for name, content in existing_dc_files.items():
                    (petc / "displayconfig" / name).write_text(content)
            if host_log:
                (stage / "display_modes_host.log").write_text(host_log)

            bb = t / "bb"
            bb.write_text(MOCK_BB)
            bb.chmod(0o755)
            proc_mounts = t / "proc_mounts"
            proc_mounts.write_text(existing_mounts.replace("{PETC}", str(petc)).replace("{STAGE}", str(stage)))
            mount_out = t / "mount_out"
            mount_out.write_text("")
            calls = t / "calls"
            calls.write_text("")

            script = (
                'mount() { cat "$MOUNT_OUT"; }\n'
                + patch_shell_paths(FARM_FN)
                + patch_shell_paths(UNFARM_FN)
                + DDC_XML_FN
                + patch_shell_paths(DISPLAYCONFIG_BLOCK)
            )
            env = dict(
                os.environ,
                BB=str(bb),
                STAGE=str(stage),
                ROOTFS=str(rootfs),
                GUEST_PRODUCT=str(product),
                PROC_MOUNTS=str(proc_mounts),
                MOUNT_OUT=str(mount_out),
                CALLS=str(calls),
                ONEOS_GUEST_FORM="bar",
                ONEOS_PROFILE="s-8450",
                ONEUI95_FOLD8="0",
                ONEUI95_TAB_S9_FE="0",
                ALLOW_OVERLAY="1" if allow_overlay else "0",
                FAIL_BIND_DST=fail_bind_dst.replace("{PETC}", str(petc)),
            )
            r = subprocess.run(["sh", "-c", script], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, r.returncode, f"stdout={r.stdout}\nstderr={r.stderr}")
            dc_files = {}
            if (petc / "displayconfig").is_dir():
                for p in sorted((petc / "displayconfig").iterdir()):
                    if p.is_file():
                        dc_files[p.name] = p.read_text()
            return {
                "stdout": r.stdout,
                "stderr": r.stderr,
                "calls": calls.read_text().splitlines(),
                "mounts": proc_mounts.read_text(),
                "dc_files": dc_files,
                "seapp_text": (petc / "selinux/product_seapp_contexts").read_text()
                if (petc / "selinux/product_seapp_contexts").is_file()
                else "",
            }

    def test_kernel510_missing_displayconfig_dir_farms_petc_and_keeps_siblings(self):
        res = self.run_dc(allow_overlay=False, existing_dc_files=None)
        self.assertIn("Display config: product/etc/displayconfig/display_port_ for ports 0  via farm_dir (no overlayfs;", res["stdout"])
        self.assertIn("display_port_0.xml", res["dc_files"])
        txt = res["dc_files"]["display_port_0.xml"]
        self.assertIn("<displayConfiguration>", txt)
        self.assertNotIn("<proxSensor>", txt)
        # Pre-existing sibling dir inside product/etc must remain intact
        self.assertEqual("seapp=keep\n", res["seapp_text"])

    def test_kernel510_existing_displayconfig_dir_preserves_donor_xml(self):
        res = self.run_dc(allow_overlay=False, existing_dc_files={"display_id_donor.xml": "<donor/>\n"})
        self.assertIn("via farm_dir (no overlayfs;", res["stdout"])
        self.assertIn("display_port_0.xml", res["dc_files"])
        self.assertEqual("<donor/>\n", res["dc_files"].get("display_id_donor.xml"))

    def test_reprepare_detects_farmed_displayconfig_and_skips(self):
        for line in (
            "bindsrc {PETC}/displayconfig tmpfs ro 0 0\n",
            "bindsrc {PETC}/displayconfig/display_port_0.xml tmpfs ro 0 0\n",
        ):
            with self.subTest(mount=line.strip()):
                res = self.run_dc(allow_overlay=False, existing_mounts=line)
                self.assertIn("already mounted (an earlier prepare), left as it is", res["stdout"])
                self.assertEqual([], res["calls"])

    def test_bind_failure_unwinds_etc_farm(self):
        res = self.run_dc(allow_overlay=False, existing_dc_files=None, fail_bind_dst="{PETC}/displayconfig")
        self.assertIn("read-only overlay and farm_dir fallback on product/etc refused, left out", res["stdout"])
        self.assertTrue(any("umount -l" in c and "etc_farm/farm" in c for c in res["calls"]), res["calls"])

    def test_empty_ddc_ports_does_not_error(self):
        res = self.run_dc(allow_overlay=False, host_log="")
        self.assertIn("no panel ports from One UI's SurfaceFlinger", res["stdout"])
        self.assertIn("read-only overlay on product/etc refused, left out", res["stdout"])


class A16ConnectivityCompatTest(unittest.TestCase):
    def make_services_tree(self, root: Path, *, npms_regs=("v4", "v10", "11"), include_flag: bool = False):
        s = root / "smali"
        def write(rel: str, content: str):
            p = s / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(".class public LTest;\n.super Ljava/lang/Object;\n\n" + content)

        write("com/android/server/SystemServer.smali", "")
        write(
            "com/android/server/connectivity/IpConnectivityMetrics.smali",
            ".method public a()I\n    .locals 2\n"
            "    invoke-static {v0}, Landroid/net/ConnectivitySettingsManager;->getL4sDeveloperOption(Landroid/content/Context;)I\n\n"
            "    move-result v1\n\n"
            "    return v1\n.end method\n",
        )
        write(
            "com/android/server/connectivity/NetdEventListenerService$2.smali",
            ".method public a()I\n    .locals 2\n"
            "    invoke-static {v0}, Landroid/net/ConnectivitySettingsManager;->getL4sDeveloperOption(Landroid/content/Context;)I\n\n"
            "    move-result v1\n\n"
            "    return v1\n.end method\n",
        )
        write(
            "com/android/server/connectivity/NetdEventListenerService.smali",
            ".method public a()V\n    .locals 2\n"
            "    invoke-static {v0, v1}, Landroid/net/ConnectivitySettingsManager;->setL4sDeveloperOption(Landroid/content/Context;I)V\n\n"
            "    invoke-static {v0, v1}, Landroid/net/ConnectivitySettingsManager;->setL4sDeveloperOption(Landroid/content/Context;I)V\n\n"
            "    return-void\n.end method\n",
        )
        write(
            "com/android/server/stats/pull/StatsPullAtomService.smali",
            ".method public a()Ljava/lang/Object;\n    .locals 3\n"
            "    new-instance v0, Landroid/net/NetworkTemplate$Builder;\n\n"
            "    invoke-direct {v0}, Landroid/net/NetworkTemplate$Builder;-><init>()V\n\n"
            "    invoke-virtual {v0, v1}, Landroid/net/NetworkTemplate$Builder;->setTransportType(I)Landroid/net/NetworkTemplate$Builder;\n\n"
            "    move-result-object v2\n\n"
            "    return-object v2\n.end method\n",
        )
        write(
            "com/android/server/stats/pull/StatsPullAtomService$$ExternalSyntheticLambda5.smali",
            ".method public run()V\n    .locals 11\n"
            "    invoke-virtual/range {v2 .. v8}, Landroid/app/usage/NetworkStatsManager;->querySummary(Landroid/net/NetworkTemplate;JJI)Landroid/app/usage/NetworkStats;\n\n"
            "    move-result-object v10\n\n"
            "    invoke-virtual/range {v2 .. v8}, Landroid/app/usage/NetworkStatsManager;->queryTaggedSummary(Landroid/net/NetworkTemplate;JJI)Landroid/app/usage/NetworkStats;\n\n"
            "    move-result-object v9\n\n"
            "    return-void\n.end method\n",
        )
        flag_read = (
            "    invoke-static {}, Lcom/android/internal/hidden_from_bootclasspath/android/net/platform/flags/Flags;->useNetstatsPerQueryFlags()Z\n\n"
            "    move-result v0\n\n"
            if include_flag
            else ""
        )
        a, b, loc = npms_regs
        write(
            "com/android/server/net/NetworkPolicyManagerService$Dependencies.smali",
            f".method public getNetworkTotalBytes()V\n    .locals {loc}\n"
            f"{flag_read}"
            f"    invoke-virtual/range {{{a} .. {b}}}, Landroid/app/usage/NetworkStatsManager;->querySummaryForDevice(Landroid/net/NetworkTemplate;JJI)Landroid/app/usage/NetworkStats$Bucket;\n\n"
            f"    move-result-object v1\n\n"
            f"    return-void\n.end method\n\n"
            f".method public getNetworkUidBytes()V\n    .locals 11\n"
            f"    invoke-virtual/range {{v4 .. v10}}, Landroid/app/usage/NetworkStatsManager;->querySummary(Landroid/net/NetworkTemplate;JJI)Landroid/app/usage/NetworkStats;\n\n"
            f"    move-result-object v1\n\n"
            f"    return-void\n.end method\n",
        )
        write(
            "com/android/server/connectivity/MultipathPolicyTracker$MultipathTracker.smali",
            ".method public getNetworkTotalBytes()V\n    .locals 7\n"
            "    invoke-virtual/range {v0 .. v6}, Landroid/app/usage/NetworkStatsManager;->querySummaryForDevice(Landroid/net/NetworkTemplate;JJI)Landroid/app/usage/NetworkStats$Bucket;\n\n"
            "    move-result-object v0\n\n"
            "    return-void\n.end method\n",
        )

    def test_r8_stripped_oneui95_emits_setPollOnOpen_without_extra_locals(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_services_tree(root, npms_regs=("v4", "v10", "11"), include_flag=False)
            r = subprocess.run([sys.executable, str(A16CC), str(root)], capture_output=True, text=True)
            self.assertEqual(0, r.returncode, r.stderr)
            npms = (root / "smali/com/android/server/net/NetworkPolicyManagerService$Dependencies.smali").read_text()
            self.assertIn("    .locals 11\n", npms)
            self.assertIn("    if-nez v10, :oneos_a16cc_2_p\n", npms)
            self.assertIn("    invoke-virtual {v4, v10}, Landroid/app/usage/NetworkStatsManager;->setPollOnOpen(Z)V\n", npms)
            self.assertIn("    invoke-virtual/range {v4 .. v9}, Landroid/app/usage/NetworkStatsManager;->querySummaryForDevice(Landroid/net/NetworkTemplate;JJ)Landroid/app/usage/NetworkStats$Bucket;\n", npms)
            self.assertIn("    invoke-virtual/range {v4 .. v9}, Landroid/app/usage/NetworkStatsManager;->querySummary(Landroid/net/NetworkTemplate;JJ)Landroid/app/usage/NetworkStats;\n", npms)
            self.assertNotIn("{TAG}", npms)
            self.assertNotIn("{NEWREG", npms)

            mp = (root / "smali/com/android/server/connectivity/MultipathPolicyTracker$MultipathTracker.smali").read_text()
            self.assertIn("    if-nez v6, :oneos_a16cc_1_p\n", mp)
            self.assertIn("    invoke-virtual {v0, v6}, Landroid/app/usage/NetworkStatsManager;->setPollOnOpen(Z)V\n", mp)

            sp = (root / "smali/com/android/server/stats/pull/StatsPullAtomService$$ExternalSyntheticLambda5.smali").read_text()
            self.assertIn("    invoke-virtual {v2, v8}, Landroid/app/usage/NetworkStatsManager;->setPollOnOpen(Z)V\n", sp)
            self.assertEqual(2, sp.count("->setPollOnOpen(Z)V"))

    def test_high_register_and_param_ranges_use_invoke_virtual_range_and_bump_locals(self):
        for regs, want_loc, want_mov, want_rng in (
            (("v10", "v16", "17"), "    .locals 19\n", "    move-object/from16 v17, v10\n", "    invoke-virtual/range {v17 .. v18}, Landroid/app/usage/NetworkStatsManager;->setPollOnOpen(Z)V\n"),
            (("p0", "p6", "15"), "    .locals 17\n", "    move-object/from16 v15, p0\n", "    invoke-virtual/range {v15 .. v16}, Landroid/app/usage/NetworkStatsManager;->setPollOnOpen(Z)V\n"),
        ):
            with self.subTest(regs=regs), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self.make_services_tree(root, npms_regs=regs, include_flag=False)
                r = subprocess.run([sys.executable, str(A16CC), str(root)], capture_output=True, text=True)
                self.assertEqual(0, r.returncode, r.stderr)
                npms = (root / "smali/com/android/server/net/NetworkPolicyManagerService$Dependencies.smali").read_text()
                self.assertIn(want_loc, npms)
                self.assertIn(want_mov, npms)
                self.assertIn(want_rng, npms)
                self.assertNotIn("{NEWREG", npms)

    def test_mixed_v_to_p_range_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_services_tree(root, npms_regs=("v12", "p2", "16"), include_flag=False)
            r = subprocess.run([sys.executable, str(A16CC), str(root)], capture_output=True, text=True)
            self.assertNotEqual(0, r.returncode)
            self.assertIn("mixed register range", r.stderr)

    def test_non_r8_build_still_replaces_useNetstatsPerQueryFlags(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_services_tree(root, npms_regs=("v4", "v10", "11"), include_flag=True)
            r = subprocess.run([sys.executable, str(A16CC), str(root)], capture_output=True, text=True)
            self.assertEqual(0, r.returncode, r.stderr)
            npms = (root / "smali/com/android/server/net/NetworkPolicyManagerService$Dependencies.smali").read_text()
            self.assertIn("useNetstatsPerQueryFlags: false", npms)
            self.assertIn("    const/4 v0, 0x0\n", npms)
            self.assertIn("->setPollOnOpen(Z)V", npms)


if __name__ == "__main__":
    unittest.main()
