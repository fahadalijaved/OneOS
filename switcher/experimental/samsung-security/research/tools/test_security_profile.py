"""Local-only adversarial collector checks; never invokes adb or a phone."""
import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location('profile_collector', Path(__file__).with_name('collect_security_profile.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProfileSafety(unittest.TestCase):
    def test_zero_ambiguous_and_nontrusted_transports_refused(self):
        for payload in (b'', b'a\tdevice\nb\tdevice\n', b'a\toffline\n', b'a\tunauthorized\n', b'a\tno permissions\n'):
            with self.subTest(payload=payload), self.assertRaises(p.ProfileError):
                p.select_device(p.parse_devices(payload))

    def test_explicit_serial_never_selects_other_transport(self):
        rows = p.parse_devices(b'first\tdevice product:x\nsecond\tdevice\n')
        self.assertEqual(p.select_device(rows, 'second'), 'second')
        with self.assertRaises(p.ProfileError):
            p.select_device(rows, 'missing')

    def test_duplicate_injected_or_oversized_devices_refused(self):
        for payload in (b'a\tdevice\na\tdevice', b'bad;command\tdevice', b'x'*65536):
            with self.subTest(payload=payload[:30]), self.assertRaises(p.ProfileError):
                p.parse_devices(payload)

    def test_pid_list_has_hard_scope(self):
        self.assertEqual(p.parse_pids('98 3\n'), ['3', '98'])
        for text in ('', '1 2 3', '1 1', '0', '-1', '5;id', '99999999'):
            with self.subTest(text=text), self.assertRaises(p.ProfileError):
                p.parse_pids(text)

    def test_pid_starttime_and_name_are_actual_identity_fields(self):
        text = '123 (system_server) S '+' '.join(str(n) for n in range(4, 53))
        self.assertEqual(p.parse_pid_stat(text, '123'), {'pid': '123', 'starttimeTicks': '22'})
        for altered in (text.replace('123 ', '124 ', 1), text.replace('system_server', 'other'), '123 (system_server) S'):
            with self.assertRaises(p.ProfileError):
                p.parse_pid_stat(altered, '123')

    def test_unknown_secret_and_arbitrary_pid_paths_refused(self):
        for path in ('/data/system/locksettings.db', '/metadata/password_slots/slot_map', '/proc/123/root/data/system/locksettings.db', '/proc/123/environ', '/system/framework/../build.prop'):
            with self.subTest(path=path), self.assertRaises(p.ProfileError):
                p.hash_command(path)
        self.assertIn('sha256sum', p.hash_command('/proc/123/root/system/framework/services.jar'))

    def test_profile_mismatch_cannot_become_acceptance(self):
        good = {'ro.product.model': 'SM-S948U1', 'ro.build.version.sdk': '37', 'ro.build.display.id': 'CP2A.260605.016.S948U1UES4BZIG', 'ro.build.fingerprint': 'samsung/device/build'}
        p.validate_profile(good)
        for key, value in [('ro.product.model', 'other'), ('ro.build.version.sdk', '36'), ('ro.build.display.id', 'future'), ('ro.build.fingerprint', '')]:
            with self.subTest(key=key), self.assertRaises(p.ProfileError):
                p.validate_profile(dict(good, **{key:value}))

    def test_strict_collection_stops_on_guest_or_unknown_property_view(self):
        for props in ({}, {'ro.product.model':'ColorOS'}, {'ro.product.model':'SM-S948U1','ro.build.version.sdk':'37','ro.build.display.id':'guest-build'}):
            with self.subTest(props=props), self.assertRaises(p.ProfileError):
                p.assess_profile(props, inspection=False)

    def test_inspection_preserves_negative_admission_classification(self):
        result = p.assess_profile({'ro.product.model':'guest'}, inspection=True)
        self.assertFalse(result['recordedPropertySubsetMatches'])
        self.assertFalse(result['profileAdmitted'])
        self.assertIn('not supported-profile', result['classification'])
        good = {'ro.product.model':'SM-S948U1','ro.build.version.sdk':'37','ro.build.display.id':'CP2A.260605.016.S948U1UES4BZIG','ro.build.fingerprint':'samsung/device/build'}
        result = p.assess_profile(good, inspection=True)
        self.assertTrue(result['recordedPropertySubsetMatches'])
        self.assertFalse(result['profileAdmitted'])

    def test_inspection_cannot_use_automatic_or_conflicting_selection(self):
        self.assertEqual(p.request_mode(inspection_serial='trusted:5555'), ('inspection-only','trusted:5555'))
        for kwargs in ({'inspection_serial':''}, {'inspection_serial':'bad;id'}, {'inspection_serial':'trusted','collect':True}, {'inspection_serial':'trusted','serial':'other'}, {'serial':'trusted'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(p.ProfileError):
                p.request_mode(**kwargs)

    def test_actual_child_failure_is_not_output_success(self):
        with self.assertRaisesRegex(p.ProfileError, 'failed'):
            p.bounded_command([sys.executable, '-I', '-S', '-c', 'print("plausible"); raise SystemExit(7)'], 1024)

    def test_actual_child_stderr_is_unresolved(self):
        with self.assertRaisesRegex(p.ProfileError, 'stderr'):
            p.bounded_command([sys.executable, '-I', '-S', '-c', 'import sys;print("warning",file=sys.stderr)'], 1024)

    def test_actual_child_output_is_bounded(self):
        with self.assertRaisesRegex(p.ProfileError, 'bound'):
            p.bounded_command([sys.executable, '-I', '-S', '-c', 'print("x"*200000)'], 1024)

    def test_actual_child_timeout_is_refused(self):
        with self.assertRaisesRegex(p.ProfileError, 'timed out'):
            p.bounded_command([sys.executable, '-I', '-S', '-c', 'import time; time.sleep(3)'], 1024, timeout=.1)


if __name__ == '__main__':
    unittest.main()
