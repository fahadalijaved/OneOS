#!/usr/bin/env python3
"""When the guest gets the empty system_ext/bin/hwservicemanager marker (guest_prepare.sh).

The decision block is run with stand-ins for the vendor manifest folder, pidof, getprop and One UI's
`service` and `lshal`.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
START = 'HWSM=0\nHWSM_WHY=""\n'
END = "# --- Samsung's IMS stack in the guest"
RAW = START + SOURCE.split(START, 1)[1].split(END, 1)[0]
BLOCK = (RAW.replace('/vendor/etc/vintf/', '$R/vintf/').replace('/system/bin/service', '$R/service')
         .replace('/system/bin/lshal', '$R/lshal').replace('timeout 10 ', 'timeout 2 '))

AIDL_MANIFEST = '''<manifest version="1.0" type="device">
    <hal format="aidl"><name>android.hardware.graphics.composer3</name><fqname>IComposer/default</fqname></hal>
    <hal format="aidl"><name>android.hardware.audio.core</name><fqname>IModule/default</fqname></hal>
%s</manifest>
'''
RADIO_AIDL = '    <hal format="aidl"><name>android.hardware.radio.sim</name><fqname>IRadioSim/slot1</fqname></hal>\n'
RADIO_HIDL = ('    <hal format="hidl"><name>android.hardware.radio</name><transport>hwbinder</transport>'
              '<fqname>@1.6::IRadio/slot1</fqname></hal>\n')
LSHAL_HEAD = '| All HIDL binderized services (registered with hwservicemanager)\nInterface\n'
LSHAL_OTHER = 'android.hidl.manager@1.2::IServiceManager/default\nvendor.samsung.hardware.thing@1.0::IThing/default\n'
LSHAL_RADIO = 'android.hardware.radio@1.0::IRadio/slot1\nandroid.hardware.radio@1.6::IRadio/slot1\n'
SERVICE = '''#!/bin/sh
echo "$*" >> "$R/service_args"
case "$AIDL" in
    yes) echo "Service $2: found" ;;
    no) echo "Service $2: not found" ;;
esac
'''
LSHAL = '''#!/bin/sh
echo "$*" >> "$R/lshal_args"
[ -z "$SLOW" ] || exec sleep 30
cat "$R/lshal_out"
'''


class HidlMarker(unittest.TestCase):
    def run_block(self, manifests=(AIDL_MANIFEST % '',), aidl='no', lshal=LSHAL_HEAD + LSHAL_OTHER + LSHAL_RADIO,
                  host_hwsm='607', rild='running', image=(), slow=''):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            (r / 'bin').mkdir(); (r / 'vintf/manifest').mkdir(parents=True)
            rootfs = r / 'rootfs'
            (rootfs / 'system/system_ext/bin').mkdir(parents=True); (rootfs / 'system/bin').mkdir(parents=True)
            for i, text in enumerate(manifests):
                (r / 'vintf' / ('manifest.xml' if i == 0 else f'manifest/extra{i}.xml')).write_text(text)
            for path in image:
                if path.endswith('@'):
                    (rootfs / path[:-1]).symlink_to('/system/system_ext/bin/hwservicemanager')
                else:
                    (rootfs / path).write_text('x')
            (r / 'bb').write_text('#!/bin/sh\nexec "$@"\n')
            (r / 'service').write_text(SERVICE)
            (r / 'lshal').write_text(LSHAL)
            (r / 'lshal_out').write_text(lshal)
            (r / 'bin/pidof').write_text('#!/bin/sh\n[ "$1" = hwservicemanager ] && [ -n "$HOST_HWSM" ] && echo "$HOST_HWSM"\n')
            (r / 'bin/getprop').write_text('#!/bin/sh\n[ "$1" = init.svc.ril-daemon ] && echo "$RILD"\n')
            for f in ('bb', 'service', 'lshal', 'bin/pidof', 'bin/getprop'):
                os.chmod(r / f, 0o755)
            env = dict(os.environ, R=str(r), BB=str(r / 'bb'), ROOTFS=str(rootfs), GUEST_SYSTEM_EXT=str(rootfs / 'system/system_ext'),
                       AIDL=aidl, HOST_HWSM=host_hwsm, RILD=rild, SLOW=slow, PATH=f'{r}/bin:' + os.environ['PATH'])
            began = time.time()
            out = subprocess.run(['/bin/sh', '-c', BLOCK + '\necho "HWSM=$HWSM WHY=$HWSM_WHY"\n'], env=env, capture_output=True,
                                 text=True, timeout=60)
            self.assertEqual('', out.stderr)
            asked = [n for n in ('service_args', 'lshal_args') if (r / n).exists()]
            lines = out.stdout.splitlines()
            return {'lines': lines[:-1], 'end': lines[-1], 'asked': asked, 'took': time.time() - began}

    def test_the_source_keeps_the_ten_second_limit(self):
        self.assertIn('"$BB" timeout 10 /system/bin/lshal list -i --types=b', RAW)

    def test_a_hidl_radio_the_manifest_test_did_not_see(self):
        # A07 721f435a, A15 be9415c0 (0.4.83): AIDL display and audio, the radio only with hwservicemanager.
        # Whatever the manifest folder says: nothing about the radio, or both kinds (a file for another model).
        for manifests, said in (((AIDL_MANIFEST % '',), 'AIDL no, HIDL no'),
                                ((AIDL_MANIFEST % RADIO_HIDL, AIDL_MANIFEST % RADIO_AIDL), 'AIDL yes, HIDL yes')):
            with self.subTest(said):
                got = self.run_block(manifests=manifests)
                self.assertEqual('HWSM=1 WHY=radio HAL', got['end'])
                self.assertEqual(['HIDL: this image has no hwservicemanager and One UI runs one. Radio by its services: AIDL no, '
                                  f'HIDL yes; by the vendor manifest: {said} (HIDL-only: the marker is set)'], got['lines'])
                self.assertEqual(['service_args', 'lshal_args'], got['asked'])

    def test_an_aidl_radio_gets_no_marker(self):
        got = self.run_block(manifests=(AIDL_MANIFEST % RADIO_AIDL,), aidl='yes')
        self.assertEqual('HWSM=0 WHY=', got['end'])
        self.assertEqual(['HIDL: this image has no hwservicemanager and One UI runs one. Radio by its services: AIDL yes, '
                          'HIDL unknown; by the vendor manifest: AIDL yes, HIDL no'], got['lines'])
        self.assertEqual(['service_args'], got['asked'])

    def test_no_radio_service_of_either_kind(self):
        # hwservicemanager answers and lists no IRadio (a tablet, or rild down): nothing to reach.
        got = self.run_block(lshal=LSHAL_HEAD + LSHAL_OTHER)
        self.assertEqual('HWSM=0 WHY=', got['end'])
        self.assertIn('AIDL no, HIDL no;', got['lines'][0])
        # The radio extension of the vendor is not the radio.
        got = self.run_block(lshal=LSHAL_HEAD + 'vendor.samsung.hardware.radio@2.2::ISehRadio/slot1\n')
        self.assertEqual('HWSM=0 WHY=', got['end'])

    def test_lshal_without_a_list(self):
        for lshal, slow in (('', ''), (LSHAL_HEAD, ''), (LSHAL_HEAD + LSHAL_RADIO, '1')):
            with self.subTest((lshal, slow)):
                got = self.run_block(lshal=lshal, slow=slow)
                self.assertEqual('HWSM=1 WHY=radio HAL', got['end'])
                self.assertIn('AIDL no, HIDL unknown;', got['lines'][0])
                self.assertLess(got['took'], 15)
                got = self.run_block(lshal=lshal, slow=slow, rild='stopped')
                self.assertEqual('HWSM=0 WHY=', got['end'])

    def test_a_service_tool_that_says_nothing_changes_nothing(self):
        got = self.run_block(aidl='silent')
        self.assertEqual(('HWSM=0 WHY=', ['service_args']), (got['end'], got['asked']))
        self.assertIn('AIDL unknown, HIDL unknown;', got['lines'][0])

    def test_the_manifest_reasons_ask_nobody(self):
        for manifests, why in (((AIDL_MANIFEST % RADIO_HIDL,), 'radio HAL'),
                               (('<manifest><hal><name>android.hardware.audio.core</name></hal></manifest>\n',), 'display composer'),
                               (('<manifest><hal><name>android.hardware.graphics.composer3</name></hal>%s</manifest>\n' % RADIO_HIDL,),
                                'audio HAL and radio HAL')):
            with self.subTest(why):
                got = self.run_block(manifests=manifests, aidl='yes')
                self.assertEqual((f'HWSM=1 WHY={why}', [], []), (got['end'], got['lines'], got['asked']))

    def test_an_image_with_its_own_hwservicemanager_or_a_phone_without_one(self):
        for kw in ({'image': ('system/system_ext/bin/hwservicemanager',)}, {'image': ('system/bin/hwservicemanager',)},
                   {'host_hwsm': ''}):
            with self.subTest(kw):
                got = self.run_block(**kw)
                self.assertEqual(('HWSM=0 WHY=', [], []), (got['end'], got['lines'], got['asked']))
                # A manifest reason does not change that.
                got = self.run_block(manifests=(AIDL_MANIFEST % RADIO_HIDL,), **kw)
                self.assertEqual(('HWSM=0', []), (got['end'].split()[0], got['asked']))
        # system/bin/hwservicemanager as a link into system_ext (where the image has none) still counts as none.
        got = self.run_block(image=('system/bin/hwservicemanager@',))
        self.assertEqual('HWSM=1 WHY=radio HAL', got['end'])


if __name__ == '__main__':
    unittest.main()
