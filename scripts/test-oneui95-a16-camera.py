#!/usr/bin/env python3
"""Tests for One UI 9.5 camera fixes on One UI 8.0 hosts (Galaxy S22):
- VENDOR_LIB_INFO rewrite/filter in guest_prepare.sh (image_codec.samsung.v1 -> v2,
  missing ai_clear_zoom / super_night.mpi libs)
- /data/sec/camera setup and symlink guards across guest_prepare.sh, guest_start.sh, oneos_switch.sh
- GUARD_JARS and guards.txt verification for One UI 8.0/8.5 camera overlays
- pixel_camera_native.py One UI 8.0 ABI patching (COMPAT_AS_INT, jump-table BTI-safe Bn ignore)
- oneui8_patch_camera_client() fail-closed guards and shell syntax across modified scripts
"""
from pathlib import Path
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUEST_PREPARE = ROOT / 'switcher/assets/guest_prepare.sh'
GUEST_START = ROOT / 'switcher/assets/guest_start.sh'
ONEOS_SWITCH = ROOT / 'switcher/assets/oneos_switch.sh'
PATCH_NATIVE_SH = ROOT / 'scripts/patch-camera-native.sh'
PATCH_NATIVE_PY = ROOT / 'switcher/patches/pixel_camera_native.py'

sys.path.insert(0, str(ROOT / 'switcher/patches'))
import pixel_camera_native as pcn


def extract_sh_func(source: str, name: str) -> str:
    m = re.search(rf'(?m)^([ \t]*){re.escape(name)}\(\) \{{', source)
    if not m:
        raise AssertionError(f'{name}() not found')
    indent = m.group(1)
    start = m.start()
    end = re.search(rf'(?m)^{re.escape(indent)}\}}$', source[m.end():])
    if not end:
        raise AssertionError(f'{name}() closing brace not found')
    return source[start:m.end() + end.end()] + '\n'


class ShellSyntaxAndGuards(unittest.TestCase):
    def test_shell_scripts_parse_cleanly(self):
        for p in (GUEST_PREPARE, GUEST_START, ONEOS_SWITCH, PATCH_NATIVE_SH):
            with self.subTest(script=p.name):
                r = subprocess.run(['sh', '-n', str(p)], capture_output=True, text=True)
                self.assertEqual(0, r.returncode, r.stderr)

    def test_sec_camera_wiring_and_symlink_protection(self):
        gp = GUEST_PREPARE.read_text()
        gs = GUEST_START.read_text()
        sw = ONEOS_SWITCH.read_text()
        self.assertIn('sec sec/camera', gp)
        self.assertIn('touch "$STAGE/data/oneos_sec_camera"', gp)
        self.assertIn('[ -f /data/oneos_sec_camera ]', gs)
        self.assertIn('[ -f $STAGE/data/oneos_sec_camera ]', sw)
        # OneOSGalleryStub grant block in guest_start.sh must remain SAMCAM-only.
        gallery_block = gs.split('Grant Gallery Bridge', 1)[1][:220]
        self.assertIn('[ -f /data/oneos_samcam ]', gallery_block)
        self.assertNotIn('oneos_sec_camera', gallery_block)

    def test_guard_lists_include_oneui8_and_85_camera_overlays(self):
        gp = GUEST_PREPARE.read_text()
        sw = ONEOS_SWITCH.read_text()
        for name in (
            'framework_patched_oneui8.jar',
            'framework_patched_oneui85.jar',
            'libcamera_client_patched.so',
            'libcameracompatbilityinfo_patched.so',
            'libcamera_client_patched_oneui95.so',
            'libcamera_client_patched_oneui8.so',
            'libcamera_client_patched_oneui85.so',
        ):
            with self.subTest(overlay=name):
                self.assertIn(f'$2 == "{name}"', gp)
                self.assertIn(f'$2 == "{name}"', sw)

    def test_session_native_camera_binary_lives_under_session_subdir(self):
        gp = GUEST_PREPARE.read_text()
        self.assertIn('CAM_CL="session/libcamera_client.oneui8.session.so"', gp)
        self.assertNotIn('$STAGE/libcamera_client.oneui8.session.so', gp)
        self.assertIn('CAM_FW="session/framework.oneui8.session.jar"', gp)
        self.assertNotIn('$STAGE/framework.oneui8.session.jar', gp)


class OneUiVendorLibInfoFilter(unittest.TestCase):
    FUNC = extract_sh_func(GUEST_PREPARE.read_text(), 'oneui_filter_vendor_lib_info')

    def run_filter(self, xml: str, libs=(), filter_on: str = '1'):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rootfs = root / 'rootfs'
            (rootfs / 'system/lib64').mkdir(parents=True)
            for lib in libs:
                (rootfs / 'system/lib64' / lib).write_bytes(b'elf')
            ff = root / 'oneos_floating_feature.xml'
            ff.write_text(xml)
            env = dict(
                os.environ,
                ROOTFS=str(rootfs),
                ONEOS_GUEST_SAMCAM_NODE_FILTER=filter_on,
            )
            r = subprocess.run(
                ['/bin/sh', '-c', self.FUNC + 'oneui_filter_vendor_lib_info "$1"', 'sh', str(ff)],
                env=env, capture_output=True, text=True,
            )
            return r.returncode, ff.read_text(), r.stdout, r.stderr

    def test_renames_image_codec_v1_and_drops_missing_node_libs(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<SecFloatingFeatureSet>\n'
            '    <SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>'
            'beauty.samsung.v4,ai_clear_zoom.arcsoft.v2,super_night.mpi.v2,super_night.samsung.v3,image_codec.samsung.v1,dual_bokeh.samsung.v1'
            '</SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>\n'
            '</SecFloatingFeatureSet>\n'
        )
        code, out_xml, stdout, stderr = self.run_filter(xml)
        self.assertEqual(0, code, stderr)
        self.assertIn(
            '<SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>'
            'beauty.samsung.v4,super_night.samsung.v3,image_codec.samsung.v2,dual_bokeh.samsung.v1'
            '</SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>',
            out_xml,
        )
        self.assertIn('ai_clear_zoom.arcsoft.v2', stdout)
        self.assertIn('super_night.mpi.v2', stdout)
        self.assertIn('image_codec.samsung.v1->image_codec.samsung.v2', stdout)

    def test_keeps_node_features_when_guest_libs_exist(self):
        xml = (
            '<SecFloatingFeatureSet>\n'
            '    <SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>'
            'ai_clear_zoom.arcsoft.v2,super_night.mpi.v2,image_codec.samsung.v1'
            '</SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>\n'
            '</SecFloatingFeatureSet>\n'
        )
        code, out_xml, stdout, _ = self.run_filter(
            xml,
            libs=('libdtsr_wrapper_v1.camera.samsung.so', 'libAIQSolution_MPI.camera.samsung.so'),
        )
        self.assertEqual(0, code)
        self.assertIn(
            'ai_clear_zoom.arcsoft.v2,super_night.mpi.v2,image_codec.samsung.v2',
            out_xml,
        )
        self.assertNotIn('ai_clear_zoom.arcsoft.v2,', stdout)

    def test_escape_hatch_disables_filter(self):
        xml = (
            '<SecFloatingFeatureSet>\n'
            '    <SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>'
            'ai_clear_zoom.arcsoft.v2,image_codec.samsung.v1'
            '</SEC_FLOATING_FEATURE_CAMERA_CONFIG_VENDOR_LIB_INFO>\n'
            '</SecFloatingFeatureSet>\n'
        )
        code, out_xml, _, _ = self.run_filter(xml, filter_on='0')
        self.assertEqual(0, code)
        self.assertEqual(xml, out_xml)


class SessionNativeCameraPatch(unittest.TestCase):
    FUNC = extract_sh_func(GUEST_PREPARE.read_text(), 'oneui8_patch_camera_client')
    FW_FUNC = extract_sh_func(GUEST_PREPARE.read_text(), 'oneui8_patch_framework_jar')

    def test_refuses_unknown_binary_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bb = root / 'bb'
            bb.write_text('#!/bin/sh\nexec "$@"\n')
            bb.chmod(0o755)
            bad = root / 'bad.so'
            bad.write_bytes(b'not the pinned library')
            link = root / 'link.so'
            link.symlink_to(bad)
            dst = root / 'out.so'
            for fn_name, fn_body in (
                ('oneui8_patch_camera_client', self.FUNC),
                ('oneui8_patch_framework_jar', self.FW_FUNC),
            ):
                for src in (bad, link):
                    with self.subTest(fn=fn_name, src=src.name):
                        r = subprocess.run(
                            ['/bin/sh', '-c', fn_body + f'{fn_name} "$1" "$2"', 'sh', str(src), str(dst)],
                            env=dict(os.environ, BB=str(bb)), capture_output=True, text=True,
                        )
                        self.assertNotEqual(0, r.returncode)
                        self.assertFalse(dst.exists())


class CaptureResultExtrasAndCallbacks(unittest.TestCase):
    def test_a16_camera_wires_result_extras_patch(self):
        src = (ROOT / 'switcher/patches/a16_camera.py').read_text()
        self.assertIn('a16_camera_result_extras.py', src)

    def test_a16_camera_result_extras_patches_smali_and_is_idempotent(self):
        smali = (
            '.class public Landroid/hardware/camera2/impl/CaptureResultExtras;\n'
            '.method public readFromParcel(Landroid/os/Parcel;)V\n'
            '    .locals 2\n'
            '    .line 126\n'
            '    sget-object v0, Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;->CREATOR:Landroid/os/Parcelable$Creator;\n\n'
            '    invoke-virtual {p1, v0}, Landroid/os/Parcel;->createTypedArray(Landroid/os/Parcelable$Creator;)[Ljava/lang/Object;\n\n'
            '    move-result-object p1\n\n'
            '    check-cast p1, [Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;\n\n'
            '    iput-object p1, p0, Landroid/hardware/camera2/impl/CaptureResultExtras;->multiResConcurrentReadersStartInfo:[Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;\n'
            '    return-void\n'
            '.end method\n'
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'smali_classes2/android/hardware/camera2/impl/CaptureResultExtras.smali'
            p.parent.mkdir(parents=True)
            p.write_text(smali)
            script = str(ROOT / 'switcher/patches/a16_camera_result_extras.py')
            r = subprocess.run(['python3', script, d], capture_output=True, text=True)
            self.assertEqual(0, r.returncode, r.stderr)
            self.assertEqual('smali_classes2', r.stdout.strip())
            patched = p.read_text()
            self.assertIn('const/4 v0, 0x0', patched)
            self.assertIn('new-array p1, v0, [Landroid/hardware/camera2/impl/MultiResConcurrentReadersStartInfo;', patched)
            self.assertNotIn('createTypedArray', patched)
            # Idempotent second run.
            r2 = subprocess.run(['python3', script, d], capture_output=True, text=True)
            self.assertEqual(0, r2.returncode, r2.stderr)
            self.assertEqual('', r2.stdout.strip())

    def test_pixel_camera_abi_remaps_shifted_samsung_listener_callback(self):
        import pixel_camera_abi as pca
        stub = (
            '.method public onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z\n'
            '    packed-switch p1, :pswitch_data_0\n'
            '    invoke-super {p0, p1, p2, p3, p4}, Landroid/os/Binder;->onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z\n'
            '    return v0\n'
            '    :pswitch_data_0\n'
            '    .packed-switch 0x1\n'
            '        :pswitch_1\n'
            '        :pswitch_2\n'
            '        :pswitch_3\n'
            '        :pswitch_4\n'
            '        :pswitch_5\n'
            '        :pswitch_6\n'
            '        :pswitch_7\n'
            '        :pswitch_8\n'
            '        :pswitch_9\n'
            '        :pswitch_10\n'
            '    .end packed-switch\n'
            '.end method\n'
        )
        host = pca.read_table(str(ROOT / 'switcher/patches/host_camera_oneui8.txt'))['android.hardware.ICameraServiceListener']
        # One UI 9.5 guest: code 9 is onStatusChangedBatched, code 10 is onCameraDeviceStateChanged (same sig as host 9).
        guest_oneui95 = dict(host)
        guest_oneui95['onStatusChangedBatched'] = (9, '([Landroid/hardware/CameraStatus;[Landroid/hardware/TorchStatus;)V')
        guest_oneui95['onCameraDeviceStateChanged'] = (10, host['onCameraDeviceStateChanged'][1])
        changed = []
        out, n = pca.patch_stub_switch(stub, 'android.hardware.ICameraServiceListener', host, guest_oneui95, changed)
        self.assertEqual(2, n)
        # Code 9 remaps to :pswitch_10 (onCameraDeviceStateChanged), and trailing stale code 10 falls off the switch!
        self.assertIn(':pswitch_8\n        :pswitch_10\n    .end packed-switch', out)
        self.assertNotIn(':pswitch_9', out)
        # Pixel guest (no onCameraDeviceStateChanged at all): code 9 falls off cleanly.
        guest_pixel = {k: v for k, v in host.items() if k != 'onCameraDeviceStateChanged'}
        guest_pixel['onStatusChangedBatched'] = (9, '([Landroid/hardware/CameraStatus;[Landroid/hardware/TorchStatus;)V')
        stub9 = stub.replace('        :pswitch_10\n', '')
        changed2 = []
        out2, n2 = pca.patch_stub_switch(stub9, 'android.hardware.ICameraServiceListener', host, guest_pixel, changed2)
        self.assertEqual(1, n2)
        self.assertNotIn(':pswitch_9', out2)


class PixelCameraNativeLogic(unittest.TestCase):
    def test_oneui8_table_methods_covered(self):
        host8 = pcn.read_table(str(ROOT / 'switcher/patches/host_camera_oneui8.txt'))
        self.assertEqual(10, host8['android.hardware.camera2.ICameraDeviceUser']['createStream'][0])
        self.assertEqual(27, host8['android.hardware.ICameraService']['isHiddenIdPermittedPackage'][0])
        self.assertNotIn('warmUp', host8['android.hardware.ICameraService'])
        self.assertNotIn('configureStreams', host8['android.hardware.camera2.ICameraDeviceUser'])
        self.assertIn('warmUp', pcn.GUEST_ONLY_VOID)
        self.assertIn('updateOutputConfigurations', pcn.GUEST_ONLY_VOID)
        self.assertIn('configureStreams', pcn.GUEST_ONLY_STATUS)

    def test_jump_table_decoder_and_b_encoding(self):
        # Exact instruction pattern from One UI 9.5 BnCameraServiceListener::onTransact (0x60da4..0x60dd0).
        ws = [
            (0x60da4, 0x60da4, 0x51000428),  # sub w8, w1, #1
            (0x60da8, 0x60da8, 0xaa0303f3),  # mov x19, x3
            (0x60dac, 0x60dac, 0xaa0203f6),  # mov x22, x2
            (0x60db0, 0x60db0, 0x7100251f),  # cmp w8, #9
            (0x60db4, 0x60db4, 0xaa0003f4),  # mov x20, x0
            (0x60db8, 0x60db8, 0x540040a8),  # b.hi 0x615cc
            (0x60dbc, 0x60dbc, 0xd503201f),  # nop
            (0x60dc0, 0x60dc0, 0x50e86289),  # adr x9, 0x31a12
            (0x60dc4, 0x60dc4, 0x1000008a),  # adr x10, 0x60dd4
            (0x60dc8, 0x60dc8, 0x7868792b),  # ldrh w11, [x9, x8, lsl #1]
            (0x60dcc, 0x60dcc, 0x8b0b094a),  # add x10, x10, x11, lsl #2
            (0x60dd0, 0x60dd0, 0xd61f0140),  # br x10
        ]
        self.assertEqual((1, 9, 0x615cc, 0x31a12, 0x60dd4), pcn.find_jump_table(ws))
        # Direct branch from 0x61620 (right after bti j at 0x6161c) -> 0x615cc.
        self.assertEqual(0x17FFFFEB, pcn.encode_b(0x61620, 0x615cc))
        # BL round-trip check.
        bl = pcn.encode_bl(0x4c5d4, 0x4c5d4 + 0x19a7d * 4)
        self.assertEqual(0x94019a7d, bl)
        self.assertEqual(0x4c5d4 + 0x19a7d * 4, pcn.decode_bl(0x4c5d4, bl))


if __name__ == '__main__':
    unittest.main()
