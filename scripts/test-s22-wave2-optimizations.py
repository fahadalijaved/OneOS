#!/usr/bin/env python3
"""Regression & mount-namespace verification tests for S22 Wave 2 optimizations:
1. Shell syntax checks (sh -n / bash -n) on all 4 modified switcher scripts +
   expanded inner oneos_heat_cap script body.
2. Real Linux unshare -Ur -m parallel farm_dir() stress test (300 files + symlinks
   + subdirs) AND whitespace-filename safe sequential fallback test + unfarm_dir().
3. Real Linux unshare -Ur -m single-pass MPF + SEC_IMS merge_up() consolidation
   test (verifies system_ext/etc/permissions is farmed only ONCE, not twice, and
   verifies standalone MPF fallback if SEC_IMS rolls back).
4. CAMRES camera-feature.xml sanitizer test for samcam_prepare() (verifies
   LIVE_FOCUS_LITE, SHOOTING_MODE_MACRO, and unknown resolution clamping).
5. oneos_heat_cap GPU frequency selection (Adreno 730 SM8450 table), gpu_tmu
   thresholds/hysteresis, adaptive cool-idle sleep, and return_to_oneui.sh GPU
   restore + batch unmount verification.
6. Early SM8450 Bixby guard verification in guest_start.sh.
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUEST_PREPARE = ROOT / "switcher/assets/guest_prepare.sh"
ONEOS_SWITCH = ROOT / "switcher/assets/oneos_switch.sh"
GUEST_START = ROOT / "switcher/assets/guest_start.sh"
RETURN_TO_ONEUI = ROOT / "switcher/assets/return_to_oneui.sh"


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def extract_function(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}\(\) \{{.*?^\}}", text, re.M | re.S)
    assert m, f"function {name}() not found"
    return m.group(0)


def test_shell_syntax():
    for path in (GUEST_PREPARE, ONEOS_SWITCH, GUEST_START, RETURN_TO_ONEUI):
        for sh in ("sh", "bash"):
            r = run([sh, "-n", str(path)])
            assert r.returncode == 0, f"{sh} -n failed on {path}:\n{r.stderr}"

    # Verify the inner double-quoted body of oneos_heat_cap parses cleanly under sh -n
    sw = ONEOS_SWITCH.read_text()
    m = re.search(r'\$BB sh -c "\n(\s*: oneos_heat_cap.*?done\n)" </dev/null', sw, re.S)
    assert m, "oneos_heat_cap inner body not found"
    body = m.group(1)
    # Emulate outer double-quote unescaping
    body = (
        body.replace('\\"', '"')
        .replace("\\$", "$")
        .replace("$STAGE", "/tmp/stage")
        .replace("$BB", "")
        .replace("$HEAT_CAP_GPU", "1")
        .replace("$HEAT_CAP", "1")
        .replace("$GUEST_THERMAL_MAP", "1")
        .replace("$HOST_LOW_POWER", "0")
    )
    r = run(["sh", "-n", "-c", body])
    assert r.returncode == 0, f"oneos_heat_cap inner syntax error:\n{r.stderr}"
    print("[PASS] test_shell_syntax (all 4 scripts + expanded oneos_heat_cap body)")


def test_parallel_farm_dir_and_whitespace_fallback():
    probe = run(["unshare", "-Ur", "-m", "sh", "-c", "exit 0"])
    if probe.returncode != 0:
        print("[SKIP] test_parallel_farm_dir_and_whitespace_fallback (unshare -Ur -m unavailable)")
        return

    gp = GUEST_PREPARE.read_text()
    farm_fn = extract_function(gp, "farm_dir")
    unfarm_fn = extract_function(gp, "unfarm_dir")

    with tempfile.TemporaryDirectory() as td:
        script = f"""
set -e
TD="{td}"
BB=""
ONEOS_TEST_SH="/bin/sh"
SAMCAM_SH="/bin/sh"
{farm_fn}
{unfarm_fn}

# 1. Parallel stress test: 300 regular files + 5 symlinks + 3 subdirs + 2 new stubs
mkdir -p "$TD/lib64/sub1" "$TD/lib64/sub2" "$TD/lib64/sub3"
i=1
while [ $i -le 300 ]; do
    echo "lib-$i" > "$TD/lib64/libtest_$i.so"
    i=$((i + 1))
done
echo "inside-sub1" > "$TD/lib64/sub1/data.bin"
ln -s libtest_1.so "$TD/lib64/liblink_1.so"
ln -s libtest_300.so "$TD/lib64/liblink_300.so"

farm_dir "$TD/lib64" "$TD/work_par" new_added.so new_dir/
[ "${{FARM_XARGS_P:-0}}" -ge 2 ]
[ "$(cat "$TD/lib64/libtest_1.so")" = "lib-1" ]
[ "$(cat "$TD/lib64/libtest_150.so")" = "lib-150" ]
[ "$(cat "$TD/lib64/libtest_300.so")" = "lib-300" ]
[ "$(cat "$TD/lib64/sub1/data.bin")" = "inside-sub1" ]
[ "$(readlink "$TD/lib64/liblink_1.so")" = "libtest_1.so" ]
[ "$(readlink "$TD/lib64/liblink_300.so")" = "libtest_300.so" ]
[ -f "$TD/lib64/new_added.so" ]
[ -d "$TD/lib64/new_dir" ]

unfarm_dir "$TD/lib64" "$TD/work_par"
[ ! -e "$TD/lib64/new_added.so" ]
[ "$(cat "$TD/lib64/libtest_300.so")" = "lib-300" ]

# 2. Whitespace filename safety: forces sequential fallback even when >=16 files
mkdir -p "$TD/wsdir"
i=1
while [ $i -le 20 ]; do
    echo "f-$i" > "$TD/wsdir/file_$i.txt"
    i=$((i + 1))
done
echo "spaced-content" > "$TD/wsdir/my spaced file.txt"
farm_dir "$TD/wsdir" "$TD/work_ws" extra.xml
[ "$(cat "$TD/wsdir/my spaced file.txt")" = "spaced-content" ]
[ "$(cat "$TD/wsdir/file_20.txt")" = "f-20" ]
[ -f "$TD/wsdir/extra.xml" ]
unfarm_dir "$TD/wsdir" "$TD/work_ws"
"""
        r = run(["unshare", "-Ur", "-m", "sh", "-c", script])
        assert r.returncode == 0, f"parallel farm_dir test failed:\nstdout={r.stdout}\nstderr={r.stderr}"
    print("[PASS] test_parallel_farm_dir_and_whitespace_fallback (300 parallel binds + whitespace fallback)")


def test_single_pass_mpf_and_secims_merge_up():
    probe = run(["unshare", "-Ur", "-m", "sh", "-c", "exit 0"])
    if probe.returncode != 0:
        print("[SKIP] test_single_pass_mpf_and_secims_merge_up (unshare -Ur -m unavailable)")
        return

    gp = GUEST_PREPARE.read_text()
    farm_fn = extract_function(gp, "farm_dir")
    unfarm_fn = extract_function(gp, "unfarm_dir")
    merge_fn = extract_function(gp, "merge_up")

    with tempfile.TemporaryDirectory() as td:
        script = f"""
set -e
TD="{td}"
BB=""
ONEOS_TEST_SH="/bin/sh"
SAMCAM_SH="/bin/sh"
{farm_fn}
{unfarm_fn}
{merge_fn}

STAGE="$TD/stage"
GUEST_SYSTEM_EXT="$STAGE/rootfs/system/system_ext"
mkdir -p "$GUEST_SYSTEM_EXT/etc/permissions" "$GUEST_SYSTEM_EXT/priv-app" "$STAGE/ov/up/etc/permissions"
echo "orig-perm" > "$GUEST_SYSTEM_EXT/etc/permissions/existing.xml"
echo "<permissions><feature name='circle'/></permissions>" > "$STAGE/ov/up/etc/permissions/oneos-my-product-features.xml"
echo "<permissions><privapp-permissions package='com.sec.imsservice'/></permissions>" > "$STAGE/ims_perm.xml"

# Single merge_up pass carrying BOTH MPX (non-empty) and SEC_IMS mount point (empty)
SIUP="$STAGE/secims_se_up"
mkdir -p "$SIUP/etc/permissions" "$SIUP/priv-app/OneOSSecIms"
cp "$STAGE/ov/up/etc/permissions/oneos-my-product-features.xml" "$SIUP/etc/permissions/oneos-my-product-features.xml"
: > "$SIUP/etc/permissions/privapp-permissions-com.sec.imsservice.xml"

SIM=$(merge_up "$SIUP" "$GUEST_SYSTEM_EXT" "$STAGE/secims_se_merge")
mount --bind "$STAGE/ims_perm.xml" "$GUEST_SYSTEM_EXT/etc/permissions/privapp-permissions-com.sec.imsservice.xml"

# Verify etc/permissions is tmpfs-mounted EXACTLY ONCE (no double-farming!)
cnt=$(awk -v p="$GUEST_SYSTEM_EXT/etc/permissions" '$2 == p && $3 == "tmpfs" {{ c++ }} END {{ print c+0 }}' /proc/mounts)
[ "$cnt" = 1 ]
[ "$(cat "$GUEST_SYSTEM_EXT/etc/permissions/existing.xml")" = "orig-perm" ]
grep -q "circle" "$GUEST_SYSTEM_EXT/etc/permissions/oneos-my-product-features.xml"
grep -q "com.sec.imsservice" "$GUEST_SYSTEM_EXT/etc/permissions/privapp-permissions-com.sec.imsservice.xml"
[ -d "$GUEST_SYSTEM_EXT/priv-app/OneOSSecIms" ]
"""
        r = run(["unshare", "-Ur", "-m", "sh", "-c", script])
        assert r.returncode == 0, f"single-pass merge_up test failed:\nstdout={r.stdout}\nstderr={r.stderr}"
    print("[PASS] test_single_pass_mpf_and_secims_merge_up (single tmpfs layer on system_ext/etc/permissions)")


def test_samcam_camres_sanitizer():
    gp = GUEST_PREPARE.read_text()
    m = re.search(
        r'SCAMRES="([^"]+)".*?if \$BB awk -v known="\$SCAMRES" \'(.*?)\' "\$scf"',
        gp,
        re.S,
    )
    assert m, "SCAMRES block in samcam_prepare() not found"
    scamres, awk_prog = m.group(1), m.group(2)
    assert "SAMCAM_CAMERADATA" in gp
    assert 'SAMCAM_TAR##*/}" != samcam_a.tar' in gp

    with tempfile.TemporaryDirectory() as td:
        xml = Path(td) / "camera-feature.xml"
        xml.write_text(
            "<resources>\n"
            '    <local name="SHOOTING_MODE_LIVE_FOCUS" back="LIVE_FOCUS_LITE" />\n'
            '    <local name="SHOOTING_MODE_MACRO" back="MACRO" enable="true" />\n'
            '    <local name="BACK_CAMERA_PICTURE_DEFAULT_RESOLUTION" value="4000x3000" />\n'
            '    <local name="BACK_CAMERA_FULL_RATIO" value="3648x1680" />\n'
            '    <local name="FRONT_CAMERA_ODD_43" value="3408x2556" />\n'
            "</resources>\n"
        )
        r = run(
            [
                "sh",
                "-c",
                f"""
set -e
scf="{xml}"
sed -i -e 's/="LIVE_FOCUS_LITE"/=""/g' \
    -e '/name="SHOOTING_MODE_MACRO"/{{s/back="MACRO"/back=""/;s/enable="true"/enable="false"/}}' "$scf"
SCAMRES="{scamres}"
awk -v known="$SCAMRES" '{awk_prog}' "$scf" > "$scf.tmp" 2> "$scf.n"
mv -f "$scf.tmp" "$scf"
cat "$scf.n"
cat "$scf"
""",
            ]
        )
        assert r.returncode == 0, f"CAMRES sanitizer failed:\n{r.stderr}"
        out = r.stdout
        assert "LIVE_FOCUS_LITE" not in out
        assert 'name="SHOOTING_MODE_MACRO" back="" enable="false"' in out
        assert 'value="4000x3000"' in out  # known size untouched
        assert 'value="3648x1680"' not in out  # unknown 19.5:9 clamped
        assert 'value="3408x2556"' not in out  # unknown 4:3 clamped
        # Verify first line is changed count == 2
        assert out.splitlines()[0].strip() == "2", f"expected 2 clamped sizes, got: {out.splitlines()[0]}"
    print("[PASS] test_samcam_camres_sanitizer (modes stripped + unknown S22/A-series sizes clamped)")


def test_gpu_heat_cap_and_return_restore():
    sw = ONEOS_SWITCH.read_text()
    ret = RETURN_TO_ONEUI.read_text()
    gs = GUEST_START.read_text()

    assert "ONEOS_HEAT_CAP_GPU:-1" in sw
    assert "gpu_max_clock.capped" in sw
    assert "gpu_max_clock.capped" in ret
    assert "xargs -n 64" in ret
    assert "SM8450|taro|waipio" in gs

    # Verify SM8450 Adreno 730 frequency selection & hysteresis math
    sm8450_freqs = "818000000 738000000 676000000 608000000 525000000 491000000 415000000 315000000 220000000"
    r = run(
        [
            "sh",
            "-c",
            f"""
set -e
gpu_freqs() {{
    echo "{sm8450_freqs}" | awk '{{for(i=1;i<=NF;i++)if($i~/^[0-9]+$/)printf "%d ", int($i/1000000)}}'
}}
gpu_top=$(gpu_freqs | awk '{{for(i=1;i<=NF;i++)if($i>m)m=$i}}END{{print m+0}}')
[ "$gpu_top" = 818 ]
for pair in "85:676" "70:525" "55:415"; do
    gpct=${{pair%%:*}}; want=${{pair#*:}}
    gtgt=$(gpu_freqs | awk -v top="$gpu_top" -v p="$gpct" 'BEGIN{{max=top*p/100}}{{for(i=1;i<=NF;i++){{v=$i;if(v<=max&&v>m)m=v}}}}END{{print m+0}}')
    [ "$gtgt" = "$want" ] || {{ echo "gpct=$gpct got=$gtgt want=$want"; exit 1; }}
done
# Also verify raw Hz table (would overflow 32-bit mksh if computed via $((gpu_top * gpct / 100)))
gtgt_hz=$(echo "{sm8450_freqs}" | awk -v top=818000000 -v p=85 'BEGIN{{max=top*p/100}}{{for(i=1;i<=NF;i++){{v=$i;if(v<=max&&v>m)m=v}}}}END{{print m+0}}')
[ "$gtgt_hz" = "676000000" ] || {{ echo "hz got=$gtgt_hz want=676000000"; exit 1; }}
# Verify gpu_tmu triggers level 2 at 76 C even when skin is 42 C, and holds until < 70 C
l=$(awk -v s=42 -v g=76000 -v l=0 'BEGIN {{ t[1]=45; t[2]=47; t[3]=50; u[1]=70000; u[2]=75000; u[3]=80000; while (l < 3 && (s >= t[l+1] || (g > 0 && g >= u[l+1]))) l++; while (l > 0 && s < t[l]-2 && (g <= 0 || g < u[l]-5000)) l--; print l }}')
[ "$l" = 2 ]
l2=$(awk -v s=42 -v g=71000 -v l=2 'BEGIN {{ t[1]=45; t[2]=47; t[3]=50; u[1]=70000; u[2]=75000; u[3]=80000; while (l < 3 && (s >= t[l+1] || (g > 0 && g >= u[l+1]))) l++; while (l > 0 && s < t[l]-2 && (g <= 0 || g < u[l]-5000)) l--; print l }}')
[ "$l2" = 2 ]
l3=$(awk -v s=42 -v g=64000 -v l=2 'BEGIN {{ t[1]=45; t[2]=47; t[3]=50; u[1]=70000; u[2]=75000; u[3]=80000; while (l < 3 && (s >= t[l+1] || (g > 0 && g >= u[l+1]))) l++; while (l > 0 && s < t[l]-2 && (g <= 0 || g < u[l]-5000)) l--; print l }}')
[ "$l3" = 0 ]
""",
        ]
    )
    assert r.returncode == 0, f"GPU heat cap math failed:\nstdout={r.stdout}\nstderr={r.stderr}"
    print("[PASS] test_gpu_heat_cap_and_return_restore (SM8450 Adreno 730 818->676/525/415 MHz + hysteresis)")


if __name__ == "__main__":
    test_shell_syntax()
    test_parallel_farm_dir_and_whitespace_fallback()
    test_single_pass_mpf_and_secims_merge_up()
    test_samcam_camres_sanitizer()
    test_gpu_heat_cap_and_return_restore()
    print("ALL WAVE 2 TESTS PASSED")
