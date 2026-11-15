#!/usr/bin/env python3
"""samcam_bind (guest_prepare.sh): the same binds with a busybox that has a parallel xargs and with one that has not."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()
FUNCTION = 'samcam_bind() {' + SOURCE.split('\nsamcam_bind() {', 1)[1].split('\n}\n', 1)[0] + '\n}\n'
BUSYBOX = '''#!/bin/sh
cmd=$1; shift
case "$cmd" in
    nproc) echo 4 ;;
    xargs)
        if [ "$NO_PARALLEL" = 1 ]; then
            case " $* " in *" -P "*) echo "xargs: invalid option -- P" >&2; exit 1 ;; esac
        fi
        exec xargs "$@" ;;
    mount)
        echo "$*" >> "$CALLS"
        [ "$1" = --bind ] && [ "$2" = "$FAIL_SOURCE" ] && exit 1
        exit 0 ;;
esac
'''
SYS = [('etc/permissions/a.xml', '/src/a.xml'), ('priv-app/Cam/Cam.apk', '/src/Cam.apk'), ('cameradata', '/src/cameradata'),
       ('lib64/one.so', '/src/one.so'), ('lib64/two.so', '/src/two.so')]
SYSEXT = [('etc/b.xml', '/src/b.xml')]


def bind(kind='sys', parallel=True, missing=None, fail=None):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); mp = root / 'mp'
        for target, _ in SYS + SYSEXT:
            if target != missing:
                (mp / target).parent.mkdir(parents=True, exist_ok=True); (mp / target).write_text('')
        (root / 'list').write_text(''.join(f'sys {t} {s}\n' for t, s in SYS) + ''.join(f'sysext {t} {s}\n' for t, s in SYSEXT))
        bb = root / 'bb'; bb.write_text(BUSYBOX); bb.chmod(0o755)
        env = dict(os.environ, BB=str(bb), SAMCAM_LIST=str(root / 'list'), SAMCAM_SH='/bin/sh', CALLS=str(root / 'calls'),
                   NO_PARALLEL='0' if parallel else '1', FAIL_SOURCE=fail or '-')
        out = subprocess.run(['/bin/sh', '-c', FUNCTION + 'samcam_bind "$1" "$2"', 'sh', kind, str(mp)], env=env, capture_output=True, text=True)
        calls = (root / 'calls').read_text().replace(str(mp) + '/', 'MP/').splitlines() if (root / 'calls').exists() else []
        return out.returncode, sorted(calls), out.stdout


def expected(entries):
    return sorted([f'--bind {s} MP/{t}' for t, s in entries] + [f'--make-rslave MP/{t}' for t, _ in entries])


class SamsungCameraBind(unittest.TestCase):
    def test_both_ways_bind_every_entry_of_the_kind_and_no_other(self):
        for parallel, how in ((True, 'with 4 workers'), (False, 'one by one (this busybox has no parallel xargs)')):
            with self.subTest(parallel=parallel):
                code, calls, out = bind(parallel=parallel)
                self.assertEqual((0, expected(SYS)), (code, calls))
                self.assertIn('Samsung Camera: binding 5 onto', out)
                self.assertIn(how, out)
                self.assertIn('Samsung Camera in the guest: 5 files and folders bound onto', out)
                self.assertEqual((0, expected(SYSEXT)), bind('sysext', parallel)[:2])

    def test_a_missing_mount_point_or_a_failed_bind_fails_the_step(self):
        for parallel in (True, False):
            with self.subTest(parallel=parallel):
                code, _, out = bind(parallel=parallel, missing='lib64/one.so')
                self.assertEqual(1, code)
                self.assertNotIn('files and folders bound', out)
                code, _, out = bind(parallel=parallel, fail='/src/Cam.apk')
                self.assertEqual(1, code)
                self.assertNotIn('files and folders bound', out)

    def test_a_kind_with_no_entry_binds_nothing(self):
        code, calls, out = bind('other')
        self.assertEqual((0, []), (code, calls))
        self.assertIn('0 files and folders bound', out)


if __name__ == '__main__':
    unittest.main()
