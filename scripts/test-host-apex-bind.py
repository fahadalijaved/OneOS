#!/usr/bin/env python3
"""One UI's /system/apex is bound into the guest whatever is mounted at that path (0.4.93).

Galaxy S22 Ultra (Exynos) and A33, guest root on, 0.4.85 to 0.4.92: every switch ended at the logo.
On kernels without overlayfs, guest root's missing /system/xbin comes from a copy of the system top
level with every entry of the image bound into it, so the image's own apex folder is a mount on
$ROOTFS/system/apex. guest_prepare.sh took any mount at that path for One UI's folder and left the
bind out; apexd (One UI's) reports One UI's files, and the guest's system_server died in its APEX
scan ("Unable to parse: /system/apex/com.android.bt.apex").

Here: the block as it is in the script, with One UI's folder at a test path, a recorded mount tool
and a mount table that lists a mount at $ROOTFS/system/apex.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPARE = (ROOT / 'switcher/assets/guest_prepare.sh').read_text()


def block():
    body = PREPARE.split("# Payload extractions above used the GSI's own /system/apex files.", 1)[1]
    body = body.split('\n', 1)[1].split('\necho "=== 9. ', 1)[0]
    body = '\n'.join(l for l in body.split('\n') if not l.lstrip().startswith('#'))
    # One UI's folder wherever the code names it, never "$ROOTFS/system/apex".
    body, n = re.subn(r'(?<=\s)/system/apex(?=[\s;)])', '$HOST_APEX', body)
    assert n >= 2, n
    return body


class HostApexBindTest(unittest.TestCase):
    def run_block(self, d, same, mounted):
        d = Path(d)
        host = d / 'host/system/apex'
        host.mkdir(parents=True)
        rootfs = d / 'rootfs'
        if same:
            # The guest path resolves to One UI's folder itself, as after the bind.
            rootfs.mkdir()
            (rootfs / 'system').symlink_to(d / 'host/system')
        else:
            (rootfs / 'system/apex').mkdir(parents=True)
        log = d / 'bb.log'
        bb = d / 'busybox'
        bb.write_text('#!/bin/sh\necho "$*" >> "%s"\nexit 0\n' % log)
        bb.chmod(0o755)
        table = d / 'mounts'
        table.write_text('/dev/block/loop9 on %s/system/apex type erofs (ro)\n' % rootfs if mounted else
                         '/dev/block/loop9 on %s/system type erofs (ro)\n' % rootfs)
        script = 'mount() { cat "%s"; }\n%s\n' % (table, block())
        run = subprocess.run(['sh', '-c', script], timeout=30, text=True,
                             env={**os.environ, 'HOST_APEX': str(host), 'ROOTFS': str(rootfs), 'BB': str(bb)},
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(run.returncode, 0, run.stdout)
        calls = log.read_text().split('\n') if log.exists() else []
        return [c for c in calls if c], run.stdout, host, rootfs

    def test_the_images_own_folder_mounted_there_does_not_stop_the_bind(self):
        with tempfile.TemporaryDirectory() as d:
            calls, out, host, rootfs = self.run_block(d, same=False, mounted=True)
            self.assertEqual(calls, ['mount --bind %s %s/system/apex' % (host, rootfs)])
            self.assertIn("bound over the image's own folder", out)

    def test_nothing_mounted_there_binds_as_before(self):
        with tempfile.TemporaryDirectory() as d:
            calls, out, host, rootfs = self.run_block(d, same=False, mounted=False)
            self.assertEqual(calls, ['mount --bind %s %s/system/apex' % (host, rootfs)])
            self.assertEqual(out, '')

    def test_one_uis_folder_already_there_is_not_bound_again(self):
        with tempfile.TemporaryDirectory() as d:
            calls, out, host, rootfs = self.run_block(d, same=True, mounted=True)
            self.assertEqual(calls, [])
            self.assertEqual(out, '')

    def test_the_bind_is_not_decided_by_the_mount_table_alone(self):
        text = block()
        self.assertNotIn('grep -q "$ROOTFS/system/apex " ||', text)
        self.assertIn('stat -c %d:%i "$ROOTFS/system/apex"', text)


if __name__ == '__main__':
    unittest.main()
