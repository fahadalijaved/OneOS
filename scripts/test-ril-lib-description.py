#!/usr/bin/env python3
"""What libsec-ril-patch.sh logs about a library that has neither SMS queue sequence (describe_lib)."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/libsec-ril-patch.sh').read_text()
CODE = ('readn() {' + SOURCE.split('readn() {', 1)[1].split('restart_ril() {', 1)[0]).replace('/system/bin/grep', 'grep') + 'describe_lib\n'
BB = shutil.which('busybox')
NOP = bytes.fromhex('1f2003d5')
MILLION = bytes.fromhex('08488852e801a072')          # mov w8, #0x4240; movk w8, #0xf, lsl #16
MILLION_W9 = bytes.fromhex('09488852e901a072')
CMP = bytes.fromhex('9f03086b')


@unittest.skipUnless(BB, 'no busybox on this machine')
class RilLibDescription(unittest.TestCase):
    def describe(self, data):
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d) / 'libsec-ril.so'; lib.write_bytes(data)
            e = {**os.environ, 'BB': BB, 'LIB': str(lib), 'LC_ALL': 'C'}
            out = subprocess.run(['sh', '-c', CODE], env=e, check=True, capture_output=True, text=True).stdout.splitlines()
            return [l.replace(str(lib), 'LIB') for l in out]

    def test_only_flag_checks_before_the_compare_are_shown(self):
        other = bytes.fromhex('880640f9' '29054439' '49000036')   # ldr x8,[x20,#8]; ldrb w9,[x9,#0x101]; tbz w9,#0
        data = (NOP * 16
                + other + NOP + MILLION_W9 + CMP + NOP            # 64: a flag check with other registers, shown
                + NOP * 4 + MILLION + CMP + NOP                   # 96: the constant with nothing before it, counted only
                + b'\x00' + MILLION + NOP * 2 + b'\x00\x00\x00'   # not on an instruction boundary
                + bytes.fromhex('08488852') + NOP * 3)            # the first word alone
        self.assertEqual(0, len(data) % 4)
        self.assertEqual([
            f'inbound SMS: LIB is {len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()}',
            'inbound SMS: flag check before a compare with 1000000 at 80: 880640f929054439490000361f2003d5 | 09488852e901a0729f03086b1f2003d5',
            'inbound SMS: 2 loads of 1000000 looked at, 1 with a flag check before them',
        ], self.describe(data))

    def test_a_library_without_the_constant(self):
        data = NOP * 64
        self.assertEqual([f'inbound SMS: LIB is 256 bytes, sha256 {hashlib.sha256(data).hexdigest()}',
                          'inbound SMS: 0 loads of 1000000 looked at, 0 with a flag check before them'], self.describe(data))

    def test_at_most_eight_places_are_shown(self):
        place = bytes.fromhex('08054439' 'a8010034') + NOP * 2 + MILLION
        lines = self.describe(NOP * 4 + place * 12 + NOP * 4)
        self.assertEqual(8, sum('flag check before a compare' in l for l in lines))
        self.assertEqual('inbound SMS: 12 loads of 1000000 looked at, 8 with a flag check before them', lines[-1])


if __name__ == '__main__':
    unittest.main()
