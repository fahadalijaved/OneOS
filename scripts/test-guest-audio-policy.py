#!/usr/bin/env python3
"""The guest's audio policy copy with Bluetooth A2DP and USB outputs (guest_prepare.sh) and the Bluetooth
audio bridge's answer on a HIDL-only phone (oneos_switch.sh), against vendor fixtures written here.

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
    return block.replace('/vendor/etc/', '$V/etc/').replace('/vendor/lib', '$V/lib').replace('/odm/lib', '$V/odm/lib')


COPY = local(between(PREPARE, 'apm_hw_lib() {\n', "# HyperOS: Xiaomi's miui-services.jar"))
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
# Android's module files as a vendor ships them next to its policy file: the Bluetooth one in both formats
# (lists with commas, and with spaces for a 7.x policy file) and the USB one.
BT_MODULE_7 = BT_MODULE.replace('role="sink"/>', 'role="sink" encodedFormats="AUDIO_FORMAT_SBC AUDIO_FORMAT_AAC"/>')
USB_MODULE = '''<module name="usb" halVersion="2.0">
    <mixPorts>
        <mixPort name="usb_device output" role="source"/>
    </mixPorts>
    <devicePorts>
        <devicePort tagName="USB Device Out" type="AUDIO_DEVICE_OUT_USB_DEVICE" role="sink"/>
        <devicePort tagName="USB Headset Out" type="AUDIO_DEVICE_OUT_USB_HEADSET" role="sink"/>
    </devicePorts>
    <routes>
        <route type="mix" sink="USB Device Out" sources="usb_device output"/>
        <route type="mix" sink="USB Headset Out" sources="usb_device output"/>
    </routes>
</module>
'''
BT_FILE = 'bluetooth_audio_policy_configuration.xml'
BT_FILE_7 = 'bluetooth_audio_policy_configuration_7_0.xml'
USB_FILE = 'usb_audio_policy_configuration.xml'
BT_LIB = 'lib/hw/audio.bluetooth.default.so'
USB_LIB = 'lib64/hw/audio.usb.default.so'
# The Galaxy A35's vendor as the user's own fix found it: both module files and both libraries, Samsung's AIDL factory.
A35 = {'includes': {BT_FILE: BT_MODULE, USB_FILE: USB_MODULE}, 'libs': (BT_LIB, USB_LIB)}
BT_ONLY = {'includes': {BT_FILE: BT_MODULE}, 'libs': (BT_LIB,)}
USB_ONLY = {'includes': {USB_FILE: USB_MODULE}, 'libs': (USB_LIB,)}
XI = '{http://www.w3.org/2001/XInclude}include'
BT_SAID = "Bluetooth A2DP outputs added with the vendor's Bluetooth module (bluetooth_audio_policy_configuration.xml)"
USB_SAID = "USB outputs added with the vendor's usb module (usb_audio_policy_configuration.xml)"
PRIMARY_SAID = 'Bluetooth A2DP outputs added on primary-out,fast,deep-buffer'

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
getprop() { case "$1" in ro.soc.manufacturer) command echo "$SOC_PROP" ;; *) command echo "$SKU_PROP" ;; esac; }
'''
ADDED = ['OneOS BT A2DP Out', 'OneOS BT A2DP Headphones', 'OneOS BT A2DP Speaker']
TYPES = ['AUDIO_DEVICE_OUT_BLUETOOTH_A2DP', 'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP_HEADPHONES',
         'AUDIO_DEVICE_OUT_BLUETOOTH_A2DP_SPEAKER']


def shape(root):
    return [(e.tag, sorted(e.attrib.items()), (e.text or '').strip()) for e in root.iter()]


class Fixture:
    def __init__(self, t, plain=PLAIN, sec=SEC, base=None, bt=AIDL_BT, audio=HIDL_AUDIO, includes=None, sku=None,
                 hyperos=False, odm=False, libs=()):
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
        for lib in libs:
            (v / lib).parent.mkdir(parents=True, exist_ok=True)
            (v / lib).write_text('x')
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
                 MIUI_FW=str(self.miui), SKU_PROP='', SOC_PROP='S.LSI')
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
    def copy(self, may='1', env=None, awk=None, more=False, **kw):
        """more: the line also says what was done for USB and whether the copy has more in it than the vendor's file."""
        with tempfile.TemporaryDirectory() as t:
            f = Fixture(t, **kw)
            src = f.v / 'etc/audio_policy_configuration.xml'
            said = 'rc=$? note=$APM_NOTE' + (' usb=$APM_USB added=$APM_ADDED' if more else '')
            lines = f.run(COPY + f'apm_copy "{src}" "$R/out.xml" {may}; echo "{said}"\n', env=env, awk=awk)
            self.assertEqual('', f.err)
            self.assertEqual(1, len(lines), lines)
            self.assertFalse((f.r / 'out.xml.a2dp').exists())
            self.assertFalse((f.r / 'out.xml.inc').exists())
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

    def assert_included(self, text, plain, etc, names):
        """The module files are the last children of <modules>, in this order, and nothing else in the file moved."""
        root = ET.fromstring(text)
        mods = root.find('modules')
        got = list(mods)[len(mods) - len(names):]
        self.assertEqual([(XI, f'{etc}/{n}') for n in names], [(e.tag, e.get('href')) for e in got])
        for e in got:
            mods.remove(e)
        self.assertEqual(shape(ET.fromstring(self.absolute(plain, etc))), shape(root))
        self.assertNotIn('OneOS BT A2DP', text)
        self.assertEqual(len(names), text.count('<!-- OneOS: '))
        # Each on a line of its own, indented as the modules are.
        for n in names:
            self.assertIn(f'\n        <xi:include href="{etc}/{n}"/>\n', text)
        self.assertTrue(text.rstrip().endswith('</audioPolicyConfiguration>'))

    def test_the_vendors_own_bluetooth_and_usb_modules_are_included(self):
        for awk in AWKS:
            with self.subTest(awk):
                line, text, etc = self.copy(awk=awk, more=True, **A35)
                self.assertEqual(f'rc=0 note={BT_SAID} usb={USB_SAID} added=1', line)
                self.assert_included(text, PLAIN, etc, [BT_FILE, USB_FILE])
                self.assertIn("<!-- OneOS: Bluetooth A2DP through the vendor's own Bluetooth audio module -->", text)
                self.assertIn("<!-- OneOS: USB headphones through the vendor's own usb audio module -->", text)
                self.assertIn(f'<xi:include href="{etc}/{USB_FILE}"/>\n    </modules>', text)
        # Libraries in the other folders the audio HAL loads from.
        for lib in ('lib64/hw/audio.bluetooth.default.so', 'odm/lib/hw/audio.bluetooth.default.so', 'odm/lib64/hw/audio.bluetooth.s5e8835.so'):
            line, text, etc = self.copy(includes={BT_FILE: BT_MODULE}, libs=(lib,))
            self.assertEqual(f'rc=0 note={BT_SAID}', line)

    def test_a_7x_policy_file_gets_the_7_0_bluetooth_file(self):
        seven = PLAIN.replace('<audioPolicyConfiguration version="1.0"', '<audioPolicyConfiguration\n\tversion="7.0"')
        self.assertNotEqual(PLAIN, seven)
        both = {BT_FILE: BT_MODULE, BT_FILE_7: BT_MODULE_7}
        line, text, etc = self.copy(plain=seven, includes=both, libs=(BT_LIB,))
        self.assertEqual(f'rc=0 note={BT_SAID.replace(BT_FILE, BT_FILE_7)}', line)
        self.assert_included(text, seven, etc, [BT_FILE_7])
        # No 7_0 file, or one without an A2DP output: the file the user's fix took.
        for inc in ({BT_FILE: BT_MODULE}, {BT_FILE: BT_MODULE, BT_FILE_7: A2DP_SINK}):
            line, text, etc = self.copy(plain=seven, includes=inc, libs=(BT_LIB,))
            self.assertEqual(f'rc=0 note={BT_SAID}', line)
        # A 1.0 file keeps the 1.0 module file.
        line, text, etc = self.copy(includes=both, libs=(BT_LIB,))
        self.assertEqual(f'rc=0 note={BT_SAID}', line)
        self.assert_included(text, PLAIN, etc, [BT_FILE])

    def test_qualcomm_and_the_switch_keep_the_primary_module_way(self):
        for env in ({'SOC_PROP': 'QTI'}, {'ONEOS_GUEST_APM_BT_MODULE': '0'}):
            line, text, etc = self.copy(env=env, more=True, **BT_ONLY)
            self.assertEqual(f'rc=0 note={PRIMARY_SAID} usb= added=1', line)
            self.assert_added(text, PLAIN, etc)
            self.assertNotIn(BT_FILE, text)
        line, text, etc = self.copy(env={'SOC_PROP': 'QTI', 'ONEOS_GUEST_APM_BT_MODULE': '1'}, **BT_ONLY)
        self.assertEqual(f'rc=0 note={BT_SAID}', line)
        line, text, etc = self.copy(env={'ONEOS_GUEST_APM_BT_MODULE': 'auto'}, **BT_ONLY)
        self.assertEqual(f'rc=0 note={BT_SAID}', line)

    def test_no_bluetooth_module_without_its_file_its_library_or_a_place_for_it(self):
        no_xi = '\n'.join(l for l in PLAIN.splitlines() if 'xi:include' not in l).replace(' xmlns:xi="http://www.w3.org/2001/XInclude"', '') + '\n'
        for name, kw in {
            'no library': {'includes': {BT_FILE: BT_MODULE}},
            'another library': {'includes': {BT_FILE: BT_MODULE}, 'libs': ('lib/hw/audio.a2dp.default.so', 'lib/audio.bluetooth.default.so')},
            'no file': {'libs': (BT_LIB,)},
            'a file without an A2DP output': {'includes': {BT_FILE: A2DP_SINK}, 'libs': (BT_LIB,)},
            'no xi: in the policy file': {'plain': no_xi, **BT_ONLY},
        }.items():
            with self.subTest(name):
                plain = kw.get('plain', PLAIN)
                line, text, etc = self.copy(more=True, **kw)
                self.assertEqual(f'rc=0 note={PRIMARY_SAID} usb= added=1', line)
                self.assert_added(text, plain, etc)
                self.assertNotIn(BT_FILE, text)
        # Without an AIDL factory there is no session for either way.
        for bt in (HIDL_BT, None):
            line, text, etc = self.copy(bt=bt, more=True, **BT_ONLY)
            self.assertEqual(('rc=0 note=no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone) usb= added=0',
                              self.absolute(PLAIN, etc)), (line, text))
        # The switch for A2DP is for both ways.
        line, text, etc = self.copy(env={'ONEOS_GUEST_APM_A2DP': '0'}, more=True, **BT_ONLY)
        self.assertEqual(('rc=0 note=no A2DP outputs added (ONEOS_GUEST_APM_A2DP=0) usb= added=0', self.absolute(PLAIN, etc)), (line, text))

    def test_the_include_goes_before_the_real_end_of_the_modules(self):
        for awk in AWKS:
            with self.subTest(awk):
                # One in a comment does not count, and one that shares its line gets lines of its own.
                commented = PLAIN.replace('<modules>', '<modules>\n        <!-- <modules> </modules> -->')
                line, text, etc = self.copy(plain=commented, awk=awk, **BT_ONLY)
                self.assertEqual(f'rc=0 note={BT_SAID}', line)
                self.assert_included(text, commented, etc, [BT_FILE])
                shared = PLAIN.replace('\n    </modules>', '</modules>')
                self.assertNotEqual(PLAIN, shared)
                line, text, etc = self.copy(plain=shared, awk=awk, more=True, **A35)
                self.assertEqual(f'rc=0 note={BT_SAID} usb={USB_SAID} added=1', line)
                self.assert_included(text, shared, etc, [BT_FILE, USB_FILE])

    def test_usb_outputs_only_where_the_file_has_none(self):
        line, text, etc = self.copy(more=True, **USB_ONLY)
        self.assertEqual(f'rc=0 note={PRIMARY_SAID} usb={USB_SAID} added=1', line)
        self.assertEqual([(XI, f'{etc}/{USB_FILE}')], [(e.tag, e.get('href')) for e in list(ET.fromstring(text).find('modules'))[-1:]])
        self.assertEqual(3, text.count('tagName="OneOS BT A2DP '))
        # Its own switch, and the one for A2DP leaves it alone.
        line, text, etc = self.copy(env={'ONEOS_GUEST_APM_USB': '0'}, more=True, **A35)
        self.assertEqual(f'rc=0 note={BT_SAID} usb= added=1', line)
        self.assert_included(text, PLAIN, etc, [BT_FILE])
        line, text, etc = self.copy(env={'ONEOS_GUEST_APM_A2DP': '0'}, more=True, **A35)
        self.assertEqual(f'rc=0 note=no A2DP outputs added (ONEOS_GUEST_APM_A2DP=0) usb={USB_SAID} added=1', line)
        self.assert_included(text, PLAIN, etc, [USB_FILE])
        # A file that has USB outputs, in itself or in a module it includes, keeps them.
        own = PLAIN.replace('<devicePort role="sink" tagName="BT SCO"', '<devicePort role="sink" tagName="USB Headset Out" '
                            'type="AUDIO_DEVICE_OUT_USB_HEADSET"/>\n<devicePort role="sink" tagName="BT SCO"')
        inc = PLAIN.replace('<xi:include href="a2dpsink', '<xi:include href="usb_audio_policy_configuration.xml"/>\n<xi:include href="a2dpsink')
        for plain in (own, inc):
            self.assertNotEqual(PLAIN, plain)
            line, text, etc = self.copy(plain=plain, bt=HIDL_BT, more=True, **USB_ONLY)
            self.assertEqual(('rc=0 note=no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone) usb= added=0',
                              self.absolute(plain, etc).replace('href="usb_audio', f'href="{etc}/usb_audio')), (line, text))
        # No library for the module, no file, or a file without a USB output: nothing.
        for kw in ({'includes': {USB_FILE: USB_MODULE}}, {'libs': (USB_LIB,)}, {'includes': {USB_FILE: A2DP_SINK}, 'libs': (USB_LIB,)},
                   {'includes': {USB_FILE: USB_MODULE}, 'libs': ('lib64/audio.usb.default.so',)}):
            line, text, etc = self.copy(bt=HIDL_BT, more=True, **kw)
            self.assertEqual(('rc=0 note=no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone) usb= added=0',
                              self.absolute(PLAIN, etc)), (line, text))
        # A plain copy stays one.
        line, text, etc = self.copy(may='0', more=True, **A35)
        self.assertEqual(('rc=0 note= usb= added=0', self.absolute(PLAIN, etc)), (line, text))

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

    def test_the_vendors_modules_are_said_on_the_line(self):
        lines, mi, log, etc, guest = self.prepare(**A35)
        self.assertEqual([f'HyperOS audio policy: {etc}/audio_policy_configuration.xml as {etc}/audio/audio_policy_configuration_mi.xml '
                          f'(no AIDL audio HAL); {BT_SAID}; {USB_SAID}'], lines)
        self.assertEqual([f'{etc}/{BT_FILE}', f'{etc}/{USB_FILE}'], [e.get('href') for e in list(ET.fromstring(mi).find('modules'))[-2:]])
        self.assertNotIn('OneOS BT A2DP', mi)
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

    def test_the_vendors_modules_are_bound_the_same_way(self):
        lines, copy, log, etc, f = self.prepare(**A35)
        self.assertEqual([f'Guest audio policy: {etc}/audio_policy_configuration.xml with {BT_SAID}; {USB_SAID} (no AIDL audio HAL)'], lines)
        self.assertEqual([f'{etc}/{BT_FILE}', f'{etc}/{USB_FILE}'], [e.get('href') for e in list(ET.fromstring(copy).find('modules'))[-2:]])
        self.assertNotIn('OneOS BT A2DP', copy)
        target = f'{f.guest_etc}/audio_policy_configuration.xml'
        self.assertEqual([f'mount --bind {f.stage}/guest_apm/audio_policy_configuration.xml {target}', f'mount -o remount,ro,bind {target}'], log[-2:])
        # USB alone is reason enough for the copy: after the primary module way, with no Bluetooth to add, with A2DP switched off.
        for kw, env, said in (
                (USB_ONLY, None, f'{PRIMARY_SAID}; {USB_SAID}'),
                ({'bt': HIDL_BT, **USB_ONLY}, None, f'{USB_SAID}; no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone)'),
                (A35, {'ONEOS_GUEST_APM_A2DP': '0'}, f'{USB_SAID}; no A2DP outputs added (ONEOS_GUEST_APM_A2DP=0)')):
            lines, copy, log, etc, f = self.prepare(env=env, **kw)
            self.assertEqual([f'Guest audio policy: {etc}/audio_policy_configuration.xml with {said} (no AIDL audio HAL)'], lines)
            self.assertEqual(f'{etc}/{USB_FILE}', list(ET.fromstring(copy).find('modules'))[-1].get('href'))
            self.assertTrue(any('--bind' in l for l in log), log)

    def test_nothing_to_add_binds_nothing(self):
        for kw, why in (({'bt': HIDL_BT}, 'no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone)'),
                        ({'sec': None}, "no A2DP outputs added (One UI's own policy file has none)"),
                        ({'env': {'ONEOS_GUEST_APM_A2DP': '0'}}, 'no A2DP outputs added (ONEOS_GUEST_APM_A2DP=0)'),
                        ({'env': {'ONEOS_GUEST_APM_USB': '0'}, 'bt': HIDL_BT, **USB_ONLY},
                         'no A2DP outputs added (no AIDL Bluetooth audio HAL on this phone)')):
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
        both_off = {'ONEOS_GUEST_APM_A2DP': '0', 'ONEOS_GUEST_APM_USB': '0'}
        for kw, env in (({'hyperos': True, **A35}, None), ({'audio': AIDL_AUDIO, **A35}, None), (A35, both_off), ({'plain': None}, None)):
            lines, copy, log, etc, f = self.prepare(env=env, **kw)
            self.assertEqual(([], None, []), (lines, copy, log))

    def test_a_refused_bind_is_said(self):
        lines, copy, log, etc, f = self.prepare(env={'BIND_REFUSED': '1'})
        self.assertEqual([f"!!! WARNING: guest audio policy: the bind on {etc}/audio_policy_configuration.xml was refused; "
                          "the guest keeps the vendor's file (no Bluetooth audio)"], lines)
        for kw, lost in ((A35, 'no Bluetooth audio, no USB audio'), ({'bt': HIDL_BT, **USB_ONLY}, 'no USB audio')):
            lines, copy, log, etc, f = self.prepare(env={'BIND_REFUSED': '1'}, **kw)
            self.assertEqual([f"!!! WARNING: guest audio policy: the bind on {etc}/audio_policy_configuration.xml was refused; "
                              f"the guest keeps the vendor's file ({lost})"], lines)


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
