#!/usr/bin/env python3
"""One UI's persist properties after a session (guest_props.sh restore-persist): what is deleted, blanked and put back."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_props.sh').read_text()
START = '    NOW="$STAGE/persist_props.now"\n'
END = '    rm -f "$BLANKED.persist" "$NOW" "$plan"\n'

# One UI's values when the session began, and what the phone holds at the return.
SNAPSHOT = {
    'persist.sys.usb.config': 'mtp',
    'persist.sys.timezone': 'Asia/Karachi',
    'persist.sys.locale': 'en-US',
    'persist.sys.boot.reason': 'reboot',
    'persist.trail': 'two words ',
    'persist.gone': '1',
    'persist.sys.x': 'same',
}
NOW = {
    'persist.sys.usb.config': 'mtp',
    'persist.sys.timezone': 'Europe/Berlin',
    'persist.sys.locale': 'zh-CN',
    'persist.sys.boot.reason': 'hard',
    'persist.trail': 'x',
    'persist.sys.x': 'same',
    'persist.oplus.display': '1',
    'persist.sys.new.oneui': '1',
    'persist.sys.boot.reason.history': 'h',
    'persist.blank.me': '',
    'persist.empty.new': '',
    'persist.vendor.softdog': '0',
    'persistXsysXx': 'not a persist property',
    'ro.build.id': 'ignored',
}
BLANKED = ['persist.blank.me']


def block(source=SOURCE, start=START, end=END):
    return start + source.split(start, 1)[1].split(end, 1)[0] + end


def run(mode='', store=0, code=None, rp_fails=False):
    """The calls made to the property tool, as sorted tuples, and the files left behind."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); stage = root / 'stage'; stage.mkdir()
        (root / 'getprop').write_text(''.join(f'[{k}]: [{v}]\n' for k, v in NOW.items()))
        (stage / 'snap').write_text(''.join(f'{k}={v}\n' for k, v in SNAPSHOT.items()))
        (stage / 'blanked').write_text(''.join(k + '\n' for k in BLANKED))
        rp = root / 'rp'
        rp.write_text('#!/bin/sh\nfor a in "$@"; do printf "%s\\037" "$a"; done >> "$CALLS"; printf "\\n" >> "$CALLS"\n' + ('exit 1\n' if rp_fails else ''))
        rp.chmod(0o755)
        pre = ('getprop() { cat "$FIX/getprop"; }\nset -- restore-persist "$MODE"\n'
               'SNAP="$STAGE/snap"; BLANKED="$STAGE/blanked"; BOOT_ID=boot-1\n')
        post = '\necho "counts $deleted ${blanked_p:-0} $restored $failed"\n'
        env = dict(os.environ, FIX=str(root), STAGE=str(stage), MODE=mode, STORE_SESSION=str(store), RP=str(rp), CALLS=str(root / 'calls'))
        out = subprocess.run(['/bin/sh', '-c', pre + (code or block()) + post], env=env, check=True, capture_output=True, text=True)
        calls = (root / 'calls').read_text().splitlines() if (root / 'calls').exists() else []
        return {
            'calls': sorted(tuple(c.split('\x1f')[:-1]) for c in calls),
            'counts': out.stdout.strip().splitlines()[-1],
            'blanked': sorted((stage / 'blanked').read_text().split()),
            'left': sorted(p.name for p in stage.iterdir()),
        }


def delete(k): return ('-p', '--delete', k)
def restore(k): return ('-p', k, SNAPSHOT[k])
def blank(k): return ('-n', k, '')


ADDED = ['persist.oplus.display', 'persist.sys.new.oneui', 'persist.sys.boot.reason.history', 'persist.empty.new',
         'persist.vendor.softdog']
CHANGED = ['persist.sys.timezone', 'persist.sys.locale', 'persist.sys.boot.reason', 'persist.trail', 'persist.gone']


class PersistRestore(unittest.TestCase):
    def test_the_return_deletes_what_the_guest_added_and_puts_one_uis_values_back(self):
        r = run()
        self.assertEqual(sorted([delete(k) for k in ADDED] + [restore(k) for k in CHANGED]), r['calls'])
        self.assertEqual('counts 5 0 5 0', r['counts'])
        # A value goes back exactly, its trailing space included.
        self.assertIn(('-p', 'persist.trail', 'two words '), r['calls'])
        self.assertEqual(['blanked', 'snap'], r['left'])

    def test_with_the_sessions_own_store_added_ones_are_blanked_and_listed(self):
        r = run(store=1)
        self.assertEqual(sorted([blank(k) for k in ADDED] + [restore(k) for k in CHANGED]), r['calls'])
        self.assertEqual('counts 0 5 5 0', r['counts'])
        self.assertEqual(sorted(BLANKED + ADDED), r['blanked'])
        self.assertIn('blanked.boot', r['left'])

    def test_recover_touches_only_the_guests_own_names_and_leaves_the_boot_reason(self):
        r = run('--recover')
        self.assertEqual(sorted([delete('persist.oplus.display'), delete('persist.vendor.softdog'), restore('persist.sys.locale')]), r['calls'])

    def test_added_only_restores_nothing(self):
        r = run('--added-only')
        self.assertEqual(sorted(delete(k) for k in ADDED), r['calls'])

    def test_a_failed_write_is_counted(self):
        self.assertEqual('counts 0 0 0 10', run(rp_fails=True)['counts'])


if __name__ == '__main__':
    unittest.main()
