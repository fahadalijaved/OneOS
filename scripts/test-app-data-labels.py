#!/usr/bin/env python3
"""app_data_labels (guest_prepare.sh): which app folders keep the guest's label and which get their own categories."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
FUNCTION = 'app_data_labels() {' + SOURCE.split('\napp_data_labels() {', 1)[1].split('\n}\n', 1)[0] + '\n}\n'
A = 'u:object_r:app_data_file:'
PACKAGES = [
    ('com.reg', 10123, 'default:targetSdkVersion=34'),
    ('com.reset', 10124, 'default:targetSdkVersion=36'),
    ('com.moved', 10200, 'default:targetSdkVersion=34'),
    ('com.priv', 10050, 'default:privapp:targetSdkVersion=34'),
    ('com.old', 10300, 'default:targetSdkVersion=26'),
    ('com.sysuid', 1000, 'platform:privapp:targetSdkVersion=36'),
]
FOLDERS = [
    (A + 's0:c123,c256,c512,c768', 'com.reg'),                      # the guest's own label: kept
    ('u:object_r:privapp_data_file:s0:c512,c768', 'com.priv'),      # kept, not turned into app_data_file
    ('u:object_r:system_app_data_file:s0', 'com.sysuid'),           # kept
    (A + 's0:c9,c256,c512,c768', 'com.gone'),                       # no longer installed: kept as it is
    (A + 's0:c44,c256,c512,c768', 'com.moved'),                     # another uid's categories: its own again
    (A + 's0', 'com.old'),                                          # bare: the level of an older app
    ('u:object_r:system_data_file:s0', 'com.reset'),                # reset or staged: its own
    ('u:object_r:shell_data_file:s0', 'com.unknown'),               # not installed: bare
    (A + 's0', 'odd name'),                                         # a space: a line of its own
]


def labels():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); (root / 'data/system').mkdir(parents=True)
        (root / 'data/system/packages.list').write_text(''.join(f'{n} {u} 0 /data/user/0/{n} {s} none 0 1 1 @null\n' for n, u, s in PACKAGES))
        (root / 'ls').write_text(''.join(f'{l} /st/{p}\n' for l, p in FOLDERS))
        out = subprocess.run(['/bin/sh', '-c', 'ls() { cat "$STAGE/ls"; }\n' + FUNCTION + 'app_data_labels /st'],
                             env=dict(os.environ, STAGE=str(root)), check=True, capture_output=True, text=True).stdout
    got = {}; counts = None
    for line in out.splitlines():
        kind, rest = line.split(' ', 1)
        if kind == '#': counts = rest
        elif kind == 'n':
            label, *paths = rest.split(' ')
            for p in paths: got[p[4:]] = label
        else:
            label, path = rest.split(' ', 1); got[path[4:]] = label
    return got, counts


class AppDataLabels(unittest.TestCase):
    def test_labels(self):
        got, counts = labels()
        self.assertEqual({
            'com.reg': A + 's0:c123,c256,c512,c768',
            'com.priv': 'u:object_r:privapp_data_file:s0:c512,c768',
            'com.sysuid': 'u:object_r:system_app_data_file:s0',
            'com.gone': A + 's0:c9,c256,c512,c768',
            'com.moved': A + 's0:c200,c256,c512,c768',
            'com.old': A + 's0:c512,c768',
            'com.reset': A + 's0:c124,c256,c512,c768',
            'com.unknown': A + 's0',
            'odd name': A + 's0',
        }, got)
        self.assertEqual('4 3', counts)


if __name__ == '__main__':
    unittest.main()
