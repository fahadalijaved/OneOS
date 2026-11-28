"""Exercise the file-stage identity and sequence gates with inert shell replies."""

from datetime import datetime, timezone
import json
import shlex
import unittest
from unittest.mock import patch

import check_file_stage_device_preflight as preflight
import review_file_stage_sequence as sequence


BEGIN = 'inventory_identity|begin'
END = 'inventory_identity|end'
SCHEMA = 'oneos-file-stage-read-only-preflight/v4'
SERIAL = 'authored-fixture-transport'
IDENTITY = [preflight.MODEL, preflight.BUILD, preflight.FINGERPRINT, '37',
            "6.12.69-android16-6-inert'quote", '0', '0', '0', '0', 'Enforcing',
            '7e000000-0000-0000-0000-000000000000', 'mnt:[42]']


def inventory_rows():
    present = {
        'data': ('41f9', '771', 1000, 1000, 4096),
        'local': ('41e9', '751', 0, 0, 4096),
        'tmp': ('41f9', '771', 2000, 2000, 4096),
        'system': ('41fd', '775', 1000, 1000, 4096),
        'dev': ('41ed', '755', 0, 0, 4096),
        'host_permit_dir': ('41e8', '750', 0, 1000, 4096),
        'host_permit': ('8120', '440', 0, 1000, len(preflight.HOST_PERMIT_MARKER)),
    }
    rows = []
    for name in preflight.PATHS:
        if name not in present:
            rows.append(f'path|{name}|absent')
        else:
            mode, perms, uid, gid, size = present[name]
            rows.append(f'path|{name}|present|{mode}|{perms}|{uid}|{gid}|1|{size}|1|2|3|4')
    rows.extend(f'hash|{name}|unobserved' for name in ('controller', 'profile', *preflight.DROP_ARTIFACTS))
    rows.extend(f'hash|{name}|not_listed_any_user' for name in preflight.PACKAGES)
    rows.extend([f'hash|host_permit|{preflight.HOST_PERMIT_SHA}',
                 f'space|{preflight.MIN_FREE // 4096 + 1}|4096|f2f52010',
                 'data_mount|rw,nosuid|f2fs|/dev/block/dm-1|rw', 'features|/dev/block/dm-1|verity',
                 'nested_mounts|0', 'drop_mounts|0', 'parent_mounts|0'])
    return rows


class PreflightIdentityTest(unittest.TestCase):
    def setUp(self):
        guard = patch.object(preflight.socket, 'create_connection', side_effect=AssertionError('fixture socket access'))
        guard.start()
        self.addCleanup(guard.stop)

    def observe(self, response):
        with patch.object(preflight, 'devices', return_value=[SERIAL]) as devices, patch.object(
                preflight, 'shell', side_effect=[IDENTITY.copy(), response]) as shell:
            try:
                return preflight.observe()
            finally:
                devices.assert_called_once_with()
                self.assertEqual(shell.call_count, 2, 'one identity shell and one bracketed inventory shell')
                self.assertEqual(shell.call_args_list[0].args, (SERIAL, preflight.IDENTITY))
                serial, command = shell.call_args_list[1].args
                self.assertEqual(serial, SERIAL)
                self.assertIn('expected_identity=' + shlex.quote('\n'.join(IDENTITY)) + '\n', command)
                self.assertIn('observed_identity=$(' + preflight.IDENTITY + ')', command)
                self.assertIn('[ "$observed_identity" = "$expected_identity" ] || exit 2', command)
                self.assertLess(command.index('check_identity begin\n'), command.index('\nobserve data '))
                self.assertTrue(command.endswith('\ncheck_identity end'))

    def test_complete_bracket_is_attributed_and_reviewable(self):
        result = self.observe([BEGIN, *inventory_rows(), END])
        self.assertEqual(preflight.SCHEMA, SCHEMA)
        self.assertIs(result['inventoryIdentityBound'], True)
        self.assertEqual(result['status'], 'READ_ONLY_PREFLIGHT_REVIEW_REQUIRED')
        self.assertEqual(result['contents']['host_permit'], 'exact_bytes')
        self.assertEqual(result['paths'].keys(), preflight.PATHS.keys())
        serialized = json.dumps(result)
        for internal in (SERIAL, IDENTITY[-2], IDENTITY[-1], BEGIN, END):
            self.assertNotIn(internal, serialized)

        receipt = self.review_receipt(result)
        cohort = {'modeled': 'local cohort review only'}
        with patch.object(sequence, 'verify_local_cohort', return_value=cohort) as verify:
            review = sequence.review(receipt)
        verify.assert_called_once_with()
        self.assertEqual(review['status'], 'FRESH_SEQUENCE_FOR_OPERATOR_REVIEW')
        self.assertIs(review['mayExecute'], False)
        self.assertEqual(review['localCohort'], cohort)

    def test_bad_brackets_refuse(self):
        rows = inventory_rows()
        for name, response in {
            'missing begin': [*rows, END], 'missing end': [BEGIN, *rows],
            'misordered': [END, *rows, BEGIN], 'duplicate begin': [BEGIN, BEGIN, *rows, END],
            'duplicate end': [BEGIN, *rows, END, END],
            'misplaced markers': [rows[0], BEGIN, *rows[1:], END],
        }.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.observe(response)

    def test_remote_refusal_for_changed_identity_has_no_inventory(self):
        # Mock the error shell() reports for a nonzero remote exit. No shell is run.
        with patch.object(preflight, 'inventory', side_effect=AssertionError('refused evidence parsed')):
            with self.assertRaisesRegex(ValueError, 'Read-only shell observation refused'):
                self.observe(ValueError('Read-only shell observation refused or incomplete'))

    @staticmethod
    def review_receipt(result):
        return result | {'schema': SCHEMA, 'deviceEligible': False,
                         'observedUtc': datetime.now(timezone.utc).isoformat(timespec='seconds')}

    def test_review_requires_current_schema_and_literal_true(self):
        receipt = self.review_receipt(self.observe([BEGIN, *inventory_rows(), END]))
        missing = {name: value for name, value in receipt.items() if name != 'inventoryIdentityBound'}
        for name, candidate in {
            'old schema': receipt | {'schema': 'oneos-file-stage-read-only-preflight/v3'},
            'missing binding': missing, 'false binding': receipt | {'inventoryIdentityBound': False},
            'numeric binding': receipt | {'inventoryIdentityBound': 1},
        }.items():
            with self.subTest(name=name), patch.object(sequence, 'verify_local_cohort',
                    side_effect=AssertionError('unbound evidence reached cohort lookup')):
                review = sequence.review(candidate)
                self.assertEqual(review['status'], 'HELD')
                self.assertIs(review['mayExecute'], False)
                self.assertEqual(review['orderedSteps'], [])


if __name__ == '__main__':
    unittest.main()
