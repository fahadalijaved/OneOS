#!/usr/bin/env python3
"""The guest's audio policy copy with Bluetooth A2DP outputs (guest_prepare.sh) and the Bluetooth audio
bridge's answer on a HIDL-only phone (oneos_switch.sh), against vendor fixtures written here.

Mounts are a stand-in: $BB is a script that writes down mount, umount and chcon and runs everything
else, and mount without arguments prints what the stand-in "mounted".
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PREPARE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
SWITCH = (ROOT / 'switcher/assets/oneos_switch.sh').read_text()


def between(text, start, end):
    return start + text.split(start, 1)[1].split(end, 1)[0]


def local(block):
    return block.replace('/vendor/etc/', '$V/etc/')


COPY = local(between(PREPARE, 'apm_copy() {\n', "# HyperOS: Xiaomi's miui-services.jar"))
HYPEROS = local(between(PREPARE, '    APM_X="${ONEOS_GUEST_APM_XML:-}"\n', '\n# The other systems read AOSP'))
OTHER = local(between(PREPARE, 'GAPM=/vendor/etc/audio_policy_configuration.xml\n', '\n# ims-ext-common.jar with a 60 s'))
BRIDGE = local(between(SWITCH, 'BT_WHY=""\nBT_FRAG=', 'BT_COPY="$STAGE/oneos_bt_vintf.xml"'))

PROFILE = ('<profile name="" format="AUDIO_FORMAT_PCM_16_BIT" samplingRates="48000" '
           'channelMasks="AUDIO_CHANNEL_OUT_STEREO"/>')
SPEAKER_PORT = '<devicePort role="sink" tagName="Speaker" type="AUDIO_DEVICE_OUT_SPEAKER">'
SPEAKER_ROUTE = '<route sink="Speaker" sources="primary-out,fast, deep-buffer,mmap_no_irq_out" type="mix" />'
PLAIN = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<audioPolicyConfiguration version="1.0" xmlns:xi="http://www.w3.org/2001/XInclude">
    <globalConfiguration speaker_drc_enabled="true"/>
    <modules>
        <module name="primary" halVersion="3.0">
            <attachedDevices>
                <item>Earpiece</item>
                <item>Speaker</item>
                <item>Built-In Mic</item>
            </attachedDevices>
            <defaultOutputDevice>Speaker</defaultOutputDevice>
            <mixPorts>
                <mixPort name="primary-out" role="source" flags="AUDIO_OUTPUT_FLAG_PRIMARY">
                    {PROFILE}
                </mixPort>
                <mixPort name="fast" role="source" flags="AUDIO_OUTPUT_FLAG_FAST">
                    {PROFILE}
                </mixPort>
                <mixPort name="deep-buffer" role="source" flags="AUDIO_OUTPUT_FLAG_DEEP_BUFFER">
                    {PROFILE}
                </mixPort>
                <mixPort name="mmap_no_irq_out" role="source" flags="AUDIO_OUTPUT_FLAG_DIRECT|AUDIO_OUTPUT_FLAG_MMAP_NOIRQ">
                    {PROFILE}
                </mixPort>
                <mixPort name="primary-in" role="sink">
                    <profile name="" format="AUDIO_FORMAT_PCM_16_BIT" samplingRates="48000" channelMasks="AUDIO_CHANNEL_IN_STEREO"/>
                </mixPort>
            </mixPorts>
            <devicePorts>
                <devicePort role="sink" tagName="Earpiece" type="AUDIO_DEVICE_OUT_EARPIECE">
                    {PROFILE}
                </devicePort>
                {SPEAKER_PORT}
                    {PROFILE}
                </devicePort>
                <devicePort role="sink" tagName="Wired Headset" type="AUDIO_DEVICE_OUT_WIRED_HEADSET">
                    {PROFILE}
                </devicePort>
                <devicePort role="sink" tagName="BT SCO" type="AUDIO_DEVICE_OUT_BLUETOOTH_SCO">
                    {PROFILE}
                </devicePort>
                <devicePort role="source" tagName="Built-In Mic" type="AUDIO_DEVICE_IN_BUILTIN_MIC">
                    <profile name="" format="AUDIO_FORMAT_PCM_16_BIT" samplingRates="48000" channelMasks="AUDIO_CHANNEL_IN_STEREO"/>
                </devicePort>
            </devicePorts>
            <routes>
                <!-- <route sink="Speaker" sources="old-out" type="mix" /> -->
                <route sink="Earpiece" sources="primary-out,fast" type="mix" />
                {SPEAKER_ROUTE}
                <route sink="Wired Headset" sources="primary-out,fast,deep-buffer" type="mix" />
                <route sink="BT SCO" sources="primary-out,fast" type="mix" />
                <route sink="primary-in" sources="Built-In Mic" type="mix" />
            </routes>
        </module>
        <xi:include href="a2dpsink_audio_policy_configuration.xml"/>
        <xi:include href="/system/etc/r_submix_audio_policy_configuration.xml"/>
    </modules>
    <xi:include href="audio_policy_volumes.xml"/>
    <xi:include href="default_volume_tables.xml"/>
</audioPolicyConfiguration>
'''
A2DP_SINK = '''<module name="a2dpsink" halVersion="2.0">
    <devicePorts>
        <devicePort tagName="BT A2DP In" type="AUDIO_DEVICE_IN_BLUETOOTH_A2DP" role="source"/>
    </devicePorts>
</module>
'''
BT_MODULE = '''<module name="bluetooth" halVersion="2.0">
    <devicePorts>
        <devicePort tagName="BT A2DP Out" type="AUDIO_DEVICE_OUT_BLUETOOTH_A2DP" role="sink"/>
    </devicePorts>
</module>
'''
# One UI's own file: the Samsung-only microphone type and A2DP in the primary module.
SEC = '''<audioPolicyConfiguration version="1.0">
    <modules>
        <module name="primary" halVersion="2.0">
            <devicePorts>
                <devicePort tagName="BT A2DP Out" type="AUDIO_DEVICE_OUT_BLUETOOTH_A2DP" role="sink">
                    <profile name="" format="AUDIO_FORMAT_PCM_16_BIT"
                             samplingRates="48000" channelMasks="AUDIO_CHANNEL_OUT_STEREO"/>
                </devicePort>
                <devicePort tagName="Built-In 2 Mic" type="AUDIO_DEVICE_IN_2MIC" role="source"/>
            </devicePorts>
        </module>
    </modules>
</audioPolicyConfiguration>
'''
AIDL_BT = '''<manifest version="1.0" type="device">
    <hal format="aidl">
        <name>vendor.samsung.hardware.bluetooth.audio</name>
        <version>1</version>
        <fqname>ISehBluetoothAudioProviderFactory/default</fqname>
    </hal>
</manifest>
'''
HIDL_BT = '''<manifest version="1.0" type="device">
    <hal format="hidl">
        <name>vendor.samsung.hardware.bluetooth.audio</name>
        <transport>hwbinder</transport>
        <version>2.0</version>
        <interface>
            <name>ISehBluetoothAudioProvidersFactory</name>
            <instance>default</instance>
        </interface>
        <fqname>@2.0::ISehBluetoothAudioProvidersFactory/default</fqname>
    </hal>
</manifest>
'''
HIDL_AUDIO = '''<manifest version="1.0" type="device">
    <hal format="hidl">
        <name>android.hardware.audio</name>
        <fqname>@7.1::IDevicesFactory/default</fqname>
    </hal>
</manifest>
'''
AIDL_AUDIO = HIDL_AUDIO.replace('android.hardware.audio<', 'android.hardware.audio.core<')

BB = '''#!/bin/sh
case "$1" in
    mount)
        echo "$*" >> "$R/bb.log"
        [ "$2 $3" = "-t tmpfs" ] && echo "tmpfs $7 tmpfs rw 0 0" >> "$R/mounts"
        [ "$2" = --bind ] && [ -n "$BIND_REFUSED" ] && exit 1
        exit 0 ;;
    umount|chcon) echo "$*" >> "$R/bb.log" ;;
    *) exec "$@" ;;
esac
'''
PRELUDE = '''
BB=$R/bin/bb
mount() { cat "$R/mounts" 2>/dev/null; }
chown() { :; }
getprop() { command echo "$SKU_PROP"; }
'''
ADDED = ['OneOS BT A2DP Out', 'OneOS BT A2DP Headphones', 'OneOS BT A2DP Speaker']
TYPES = ['AUDIO_DEVICE_OUT_BLUETOOTH_A2DP', 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP_HEADPHONES',
         'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP_SPEAKER']


def shape(root):
    return [(e.tag, sorted(e.attrib.items()), (e.text or '').strip()) for e in root.iter()]


class Fixture:
    def __init__(self, t, plain=PLAIN, sec=SEC, base=None, bt=AIDL_BT, audio=HIDL_AUDIO, includes=None, sku=None,
                 hyperos=False, odm=False):
        self.r = r = Path(t)
        self.v = v = r / 'vendor'
        self.stage = r / 'stage'
        self.rootfs = self.stage / 'rootfs'
        self.guest_etc = Path(str(self.rootfs) + str(v)) / 'etc'
        (v / 'etc/vintf/manifest').mkdir(parents=True)
        (self.guest_etc / 'audio').mkdir(parents=True)
        (r / 'bin').mkdir()
        (r / 'bin/bb').write_text(BB)
        os.chmod(r / 'bin/bb', 0o755)
        if plain is not None:
            (v / 'etc/audio_policy_configuration.xml').write_text(plain)
            (self.guest_etc / 'audio_policy_configuration.xml').write_text(plain)
        if sec is not None:
            (v / 'etc/audio_policy_configuration_sec.xml').write_text(sec)
        if base is not None:
            (v / 'etc/audio_policy_configuration_base.xml').write_text(base)
        for name, text in {'a2dpsink_audio_policy_configuration.xml': A2DP_SINK, **(includes or {})}.items():
            (v / 'etc' / name).write_text(text)
        if bt is not None:
            (v / 'etc/vintf/manifest/bluetooth_audio.xml').write_text(bt)
        (v / 'etc/vintf/manifest.xml').write_text(audio)
        if sku:
            for d in (v / 'etc/audio' / f'sku_{sku}', self.guest_etc / 'audio' / f'sku_{sku}'):
                d.mkdir(parents=True)
                (d / 'audio_policy_configuration.xml').write_text(PLAIN.replace('primary-out', 'sku-out'))
        self.miui = self.rootfs / 'system_ext/framework'
        self.miui.mkdir(parents=True)
        if hyperos:
            (self.miui / 'miui-services.jar').write_text('x')
        if odm:
            (self.rootfs / 'odm/etc').mkdir(parents=True)
            (self.rootfs / 'odm/etc/audio_policy_configuration.xml').write_text(plain)

    def run(self, code, env=None, awk=None):
        e = dict(os.environ, R=str(self.r), V=str(self.v), STAGE=str(self.stage), ROOTFS=str(self.rootfs),
                 MIUI_FW=str(self.miui), SKU_PROP='')
        e.update(env or {})
        if awk:
            (self.r / 'awkbin').mkdir(exist_ok=True)
            (self.r / 'awkbin/awk').write_text(f'#!/bin/sh\nexec {awk} "$@"\n')
            os.chmod(self.r / 'awkbin/awk', 0o755)
            e['PATH'] = f'{self.r}/awkbin:' + e['PATH']
        out = subprocess.run(['/bin/sh', '-c', PRELUDE + code], env=e, capture_output=True, text=True, timeout=60)
        self.err = out.stderr
        return out.stdout.splitlines()

    def log(self):
        f = self.r / 'bb.log'
        return f.read_text().splitlines() if f.exists() else []


AWKS = [None] + ([f'{shutil.which("busybox")} awk'] if shutil.which('busybox') else [])


class Copy(unittest.TestCase):
    def copy(self, may='1', env=None, awk=None, **kw):
        with tempfile.TemporaryDirectory() as t:
            f = Fixture(t, **kw)
            src = f.v / 'etc/audio_policy_configuration.xml'
            lines = f.run(COPY + f'apm_copy "{src}" "$R/out.xml" {may}; echo "rc=$? note=$APM_NOTE"\n', env=env, awk=awk)
            self.assertEqual('', f.err)
            self.assertEqual(1, len(lines), lines)
            self.assertFalse((f.r / 'out.xml.a2dp').exists())
            text = (f.r / 'out.xml').read_text() if (f.r / 'out.xml').exists() else None
            return lines[0], text, str(f.v / 'etc')

    def absolute(self, text, etc):
        return text.replace('href="a2dpsink', f'href="{etc}/a2dpsink').replace('href="audio_policy_volumes', f'href="{etc}/audio_policy_volumes') \
            .replace('href="default_volume', f'href="{etc}/default_volume').replace('href="bluetooth_audio', f'href="{etc}/bluetooth_audio')

    def assert_added(self, text, plain, etc, sources='primary-out,fast,deep-buffer'):
        root = ET.fromstring(text)
        mod = root.find("modules/module[@name='primary']")
        ports = list(mod.find('devicePorts'))[-3:]
        self.assertEqual(ADDED, [p.get('tagName') for p in ports])
        self.assertEqual(TYPES, [p.get('type') for p in ports])
        for p in ports:
            self.assertEqual({'tagName', 'type', 'role'}, set(p.attrib))
            self.assertEqual('sink', p.get('role'))
            self.assertEqual([{'name': '', 'format': 'AUDIO_FORMAT_PCM_16_BIT', 'samplingRates': '48000',
                               'channelMasks': 'AUDIO_CHANNEL_OUT_STEREO'}], [dict(c.attrib) for c in p])
        routes = list(mod.find('routes'))[-3:]
        self.assertEqual([{'type': 'mix', 'sink': n, 'sources': sources} for n in ADDED], [dict(r.attrib) for r in routes])
        # Every source is an output mix port of the module, and nothing else in the file moved.
        mixes = {m.get('name') for m in mod.find('mixPorts') if m.get('role') == 'source'}
        self.assertLessEqual(set(sources.split(',')), mixes)
        for p in ports:
            mod.find('devicePorts').remove(p)
        for r in routes:
            mod.find('routes').remove(r)
        self.assertEqual(shape(ET.fromstring(self.absolute(plain, etc))), shape(root))
        self.assertEqual(3, text.count('OneOS BT A2DP') // 2)
        self.assertIn('<!-- OneOS: Bluetooth A2DP through the primary module', text)

    def test_the_a2dp_outputs_go_on_the_speakers_mix_ports(self):
        for awk in AWKS:
            with self.subTest(awk):
                line, text, etc = self.copy(awk=awk)
                self.assertEqual('rc=0 note=Bluetooth A2DP outputs added on primary-out,fast,deep-buffer', line)
                self.assert_added(text, PLAIN, etc)
                self.assertIn(f'<xi:include href="{etc}/audio_policy_volumes.xml"/>', text)
                self.assertIn('<xi:include href="/system/etc/r_submix_audio_policy_configuration.xml"/>', text)

    def test_tags_over_several_lines_and_in_another_order(self):
        plain = PLAIN.replace(SPEAKER_PORT, '<devicePort tagName = "Speaker"\n                            role="sink"\n'
                                            '                            type="AUDIO_DEVICE_OUT_SPEAKER"\n                >') \
            .replace(SPEAKER_ROUTE, '<route type="mix" sink="Speaker"\n                       sources="fast,\n  primary-out"/>')
        self.assertNotEqual(PLAIN, plain)
        for awk in AWKS:
            with self.subTest(awk):
                line, text, etc = self.copy(plain=plain, awk=awk)
                self.assertEqual('rc=0 note=Bluetooth A2DP outputs added on fast,primary-out', line)
                self.assert_added(text, plain, etc, sources='fast,primary-out')

    def test_a_file_with_a2dp_of_its_own_is_only_copied(self):
        own = PLAIN.replace('<devicePort role="sink" tagName="BT SCO"', '<devicePort role="sink" tagName="BT A2DP Out" '
                            'type="AUDIO_DEVICE_OUT_BLUETOOTH_A2DP"/>\n<devicePort role="sink" tagName="BT SCO"')
        line, text, etc = self.copy(plain=own)
        self.assertEqual(('rc=0 note=it has A2DP outputs of its own', self.absolute(own, etc)), (line, text))
        # In a module it includes: the href is followed.
        inc = PLAIN.replace('<xi:include href="a2dpsink', '<xi:include href="bluetooth_audio_policy_configuration.xml"/>\n<xi:include href="a2dpsink')
        line, text, etc = self.copy(plain=inc, includes={'bluetooth_audio_policy_configuration.xml': BT_MODULE})
        self.assertEqual(('rc=0 note=it has A2DP outputs of its own', self.absolute(inc, etc)), (line, text))

    def test_only_where_one_uis_own_file_has_a2dp(self):
        for kw in ({'sec': None}, {'sec': SEC.replace('OUT_BLUETOOTH_A2DP"', 'OUT_BLUETOOTH_SCO"')}):
            line, text, etc = self.copy(**kw)
            self.assertEqual(("rc=0 note=no A2DP outputs added (One UI's own policy file has none)", self.absolute(PLAIN, etc)), (line, text))
        line, text, etc = self.copy(sec=None, base=SEC)
        self.assertEqual('rc=0 note=Bluetooth A2DP outputs added on primary-out,fast,deep-buffer', line)

    def test_only_with_an_aidl_bluetooth_audio_factory(self):
        for bt in (HIDL_BT, None):
            line, text, etc = self.copy(bt=bt)
            self.assertEqual(('rc=0 note=no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone)', self.absolute(PLAIN, etc)),
                             (line, text))
        line, text, etc = self.copy(bt=AIDL_BT.replace('vendor.samsung.hardware.bluetooth.audio', 'android.hardware.bluetooth.audio')
                                    .replace('ISehBluetoothAudioProviderFactory', 'IBluetoothAudioProviderFactory'))
        self.assertEqual('rc=0 note=Bluetooth A2DP outputs added on primary-out,fast,deep-buffer', line)

    def test_the_switch_and_a_plain_copy(self):
        line, text, etc = self.copy(env={'ONEOS_GUEST_APM_A2DP': '0'})
        self.assertEqual(('rc=0 note=no A2DP outputs added (ONEOS_GUEST_APM_A2DP=0)', self.absolute(PLAIN, etc)), (line, text))
        line, text, etc = self.copy(may='0')
        self.assertEqual(('rc=0 note=', self.absolute(PLAIN, etc)), (line, text))

    def test_a_layout_it_does_not_know_is_left_as_it_is(self):
        odd = {
            'no speaker': PLAIN.replace('AUDIO_DEVICE_OUT_SPEAKER', 'AUDIO_DEVICE_OUT_SPEAKER_SAFE'),
            'no speaker route': PLAIN.replace(SPEAKER_ROUTE, ''),
            'a source that is no mix port': PLAIN.replace('sources="primary-out,fast, deep-buffer,mmap_no_irq_out"', 'sources="primary-out,other"'),
            'a source that is an input': PLAIN.replace('sources="primary-out,fast, deep-buffer,mmap_no_irq_out"', 'sources="primary-in"'),
            'mmap only': PLAIN.replace('sources="primary-out,fast, deep-buffer,mmap_no_irq_out"', 'sources="mmap_no_irq_out"'),
            'no primary module': PLAIN.replace('<module name="primary"', '<module name="main"'),
            'routes before the ports': PLAIN.replace('<devicePorts>', '<x>').replace('</devicePorts>', '</x>')
                                            .replace('</module>', '<devicePorts></devicePorts></module>', 1).replace('<x>', '<y>', 1),
            'an open comment': PLAIN.replace('</routes>', '</routes><!-- '),
            'single quotes': PLAIN.replace(SPEAKER_PORT, SPEAKER_PORT.replace('"', "'")),
        }
        for awk in AWKS:
            for name, plain in odd.items():
                with self.subTest(name, awk=awk):
                    self.assertNotEqual(PLAIN, plain)
                    line, text, etc = self.copy(plain=plain, awk=awk)
                    self.assertEqual(f'rc=0 note=no A2DP outputs added (the layout of {etc}/audio_policy_configuration.xml '
                                     'is not one this knows)', line)
                    self.assertEqual(self.absolute(plain, etc), text)

    def test_a_missing_file_fails(self):
        line, text, etc = self.copy(plain=None)
        self.assertEqual(('rc=1 note=', None), (line, text))


class HyperOS(unittest.TestCase):
    def prepare(self, env=None, **kw):
        with tempfile.TemporaryDirectory() as t:
            f = Fixture(t, hyperos=True, **kw)
            lines = f.run(COPY + HYPEROS, env=env)
            mi = f.stage / 'hyperos_apm/up/audio_policy_configuration_mi.xml'
            self.overlay = f'mount -t overlay overlay -o ro,lowerdir={f.stage}/hyperos_apm/up:{f.guest_etc}/audio {f.guest_etc}/audio'
            return lines, (mi.read_text() if mi.exists() else None), f.log(), str(f.v / 'etc'), str(f.guest_etc)

    def test_the_plain_file_comes_before_samsungs_own(self):
        lines, mi, log, etc, guest = self.prepare()
        self.assertEqual([f'HyperOS audio policy: {etc}/audio_policy_configuration.xml as {etc}/audio/audio_policy_configuration_mi.xml '
                          '(no AIDL audio HAL); Bluetooth A2DP outputs added on primary-out,fast,deep-buffer'], lines)
        self.assertEqual(3, mi.count('tagName="OneOS BT A2DP '))
        self.assertNotIn('AUDIO_DEVICE_IN_2MIC', mi)
        self.assertEqual(self.overlay, log[-1])

    def test_a_sku_file_stays_first_and_is_only_copied(self):
        lines, mi, log, etc, guest = self.prepare(sku='kalama', env={'SKU_PROP': 'kalama'})
        self.assertEqual([f'HyperOS audio policy: {etc}/audio/sku_kalama/audio_policy_configuration.xml as '
                          f'{etc}/audio/audio_policy_configuration_mi.xml (no AIDL audio HAL)'], lines)
        self.assertIn('sku-out', mi)
        self.assertNotIn('OneOS BT A2DP', mi)
        self.assertIn(f'href="{etc}/audio/sku_kalama/audio_policy_volumes.xml"', mi)

    def test_samsungs_own_file_is_the_last_resort(self):
        lines, mi, log, etc, guest = self.prepare(plain=None)
        self.assertEqual([f'HyperOS audio policy: {etc}/audio_policy_configuration_sec.xml as {etc}/audio/audio_policy_configuration_mi.xml '
                          '(no AIDL audio HAL)'], lines)
        self.assertEqual(SEC, mi)

    def test_a_named_file_is_only_copied(self):
        with tempfile.TemporaryDirectory() as t:
            f = Fixture(t, hyperos=True)
            lines = f.run(COPY + HYPEROS, env={'ONEOS_GUEST_APM_XML': str(f.v / 'etc/audio_policy_configuration.xml')})
            self.assertEqual(1, len(lines))
            self.assertTrue(lines[0].endswith('(no AIDL audio HAL)'), lines)
            self.assertNotIn('OneOS BT A2DP', (f.stage / 'hyperos_apm/up/audio_policy_configuration_mi.xml').read_text())

    def test_an_aidl_audio_hal_reads_no_file(self):
        lines, mi, log, etc, guest = self.prepare(audio=AIDL_AUDIO)
        self.assertEqual(([], None, []), (lines, mi, log))


class OtherGuests(unittest.TestCase):
    def prepare(self, env=None, **kw):
        with tempfile.TemporaryDirectory() as t:
            f = Fixture(t, **kw)
            lines = f.run(COPY + OTHER, env=env)
            self.assertEqual('', f.err)
            c = f.stage / 'guest_apm/audio_policy_configuration.xml'
            return lines, (c.read_text() if c.exists() else None), f.log(), str(f.v / 'etc'), f

    def test_the_copy_is_bound_over_the_guests_file(self):
        lines, copy, log, etc, f = self.prepare()
        self.assertEqual([f'Guest audio policy: {etc}/audio_policy_configuration.xml with Bluetooth A2DP outputs added on '
                          'primary-out,fast,deep-buffer (no AIDL audio HAL)'], lines)
        self.assertEqual(3, copy.count('tagName="OneOS BT A2DP '))
        target = f'{f.guest_etc}/audio_policy_configuration.xml'
        self.assertEqual([f'mount -t tmpfs -o size=2m,mode=755 tmpfs {f.stage}/guest_apm', f'mount --make-private {f.stage}/guest_apm',
                          f'chcon u:object_r:vendor_configs_file:s0 {f.stage}/guest_apm/audio_policy_configuration.xml',
                          f'mount --bind {f.stage}/guest_apm/audio_policy_configuration.xml {target}',
                          f'mount -o remount,ro,bind {target}'], log)

    def test_nothing_to_add_binds_nothing(self):
        for kw, why in (({'bt': HIDL_BT}, 'no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone)'),
                        ({'sec': None}, "no A2DP outputs added (One UI's own policy file has none)")):
            lines, copy, log, etc, f = self.prepare(**kw)
            self.assertEqual([f'Guest audio policy: {etc}/audio_policy_configuration.xml left as it is: {why}'], lines)
            self.assertFalse(any('--bind' in l for l in log), log)

    def test_a_file_the_guest_reads_first_is_left_alone(self):
        lines, copy, log, etc, f = self.prepare(odm=True)
        self.assertEqual((['Guest audio policy: the guest reads /odm/etc/audio_policy_configuration.xml; left alone'], []), (lines, log))
        lines, copy, log, etc, f = self.prepare(sku='s5e8845', env={'SKU_PROP': 's5e8845'})
        self.assertEqual(([f'Guest audio policy: the guest reads {etc}/audio/sku_s5e8845/audio_policy_configuration.xml; left alone'], []),
                         (lines, log))

    def test_not_for_hyperos_an_aidl_audio_hal_or_the_switch(self):
        for kw, env in (({'hyperos': True}, None), ({'audio': AIDL_AUDIO}, None), ({}, {'ONEOS_GUEST_APM_A2DP': '0'}), ({'plain': None}, None)):
            lines, copy, log, etc, f = self.prepare(env=env, **kw)
            self.assertEqual(([], None, []), (lines, copy, log))

    def test_a_refused_bind_is_said(self):
        lines, copy, log, etc, f = self.prepare(env={'BIND_REFUSED': '1'})
        self.assertEqual([f"!!! WARNING: guest audio policy: the bind on {etc}/audio_policy_configuration.xml was refused; "
                          "the guest keeps the vendor's file (no Bluetooth audio)"], lines)


BRIDGE_PRELUDE = '''
timeout() { shift; "$@"; }
sleep() { command echo s >> "$R/sleeps"; }
service() { command echo "$*" >> "$R/service"; if [ -n "$FOUND" ]; then command echo "Service $2: found"; else command echo "Service $2: not found"; fi; }
'''


class Bridge(unittest.TestCase):
    def why(self, bt, found=''):
        with tempfile.TemporaryDirectory() as t:
            f = Fixture(t, bt=bt)
            f.stage.mkdir(exist_ok=True)
            (f.stage / 'oneos_btaudio').write_text('#!/bin/sh\n[ "$1" = --declared ] && echo 0\n')
            lines = f.run(BRIDGE_PRELUDE + BRIDGE + 'command echo "why=$BT_WHY"\n', env={'FOUND': found})
            self.assertEqual('', f.err)
            count = lambda n: len((f.r / n).read_text().splitlines()) if (f.r / n).exists() else 0
            return lines[-1], count('sleeps'), count('service')

    def test_the_hidl_factory_is_named_without_a_wait(self):
        self.assertEqual(("why=not started: Samsung's Bluetooth audio HAL on this phone is the older HIDL one, which the bridge "
                          'cannot serve (no Bluetooth audio in the guest)', 0, 0), self.why(HIDL_BT))

    def test_the_aidl_factory_is_waited_for_as_before(self):
        self.assertEqual(('why=', 0, 2), self.why(AIDL_BT, found='1'))
        self.assertEqual(("why=Samsung's factory was not registered 15 s after the audio HAL restart; not started", 30, 31), self.why(AIDL_BT))
        # Both in one fragment, or a form this does not know: the wait decides.
        self.assertEqual(('why=', 0, 2), self.why(HIDL_BT + AIDL_BT.replace('<manifest version="1.0" type="device">\n', '')
                                                  .replace('</manifest>\n', ''), found='1')[0:3])
        odd = HIDL_BT.replace('ISehBluetoothAudioProvidersFactory', 'ISehOther')
        self.assertEqual(30, self.why(odd)[1])


if __name__ == '__main__':
    unittest.main()
