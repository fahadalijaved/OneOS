#!/usr/bin/env python3
"""Execute actual module promotion/removal logic without any device or mounts."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_prepare.sh').read_text()
LOGIC=s[s.index('# Cleanup scripts run in the guest root'):s.index("# The image's folder for a path")]
r=(ROOT/'switcher/assets/guest_runtime.sh').read_text();r=r[r.index('\nuninstall)'):]
UNINSTALL=r[r.index('    for m in "$A/modules/"*; do'):r.index('    ;;')]
class ModuleLifecycleTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.m=self.root/'modules';self.u=self.root/'modules_update';self.m.mkdir();self.u.mkdir()
  self.bb=self.root/'busybox';self.bb.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOOK_LOG"\n');self.bb.chmod(0o755)
  (self.root/'data/oneos_root').mkdir(parents=True);(self.root/'data/oneos_root/enabled').touch()
 def tearDown(self):self.tmp.cleanup()
 def run_logic(self):
  return subprocess.run(['sh','-ec',LOGIC],env={**os.environ,'S':str(self.root),'R':str(self.root/'rootfs'),'M':str(self.m),'U':str(self.u),'BB':str(self.bb),'HOOK_LOG':str(self.root/'hooks')},capture_output=True,text=True)
 def test_remove_wins_over_update_and_cleanup_is_guest_chrooted(self):
  old=self.m/'example';new=self.u/'example';old.mkdir();new.mkdir();(old/'remove').touch();(new/'module.prop').write_text('new')
  result=self.run_logic();self.assertEqual(0,result.returncode,result.stderr);self.assertFalse(old.exists());self.assertFalse(new.exists())
  self.assertEqual(f'chroot {self.root}/rootfs /system/bin/sh /data/oneos_runtime.sh uninstall\n',(self.root/'hooks').read_text())
 def test_update_promotes_only_matching_private_module(self):
  old=self.m/'example';new=self.u/'example';old.mkdir();new.mkdir();(old/'old').touch();(new/'new').touch()
  other=self.m/'other';other.mkdir();(other/'keep').touch()
  result=self.run_logic();self.assertEqual(0,result.returncode,result.stderr);self.assertTrue((old/'new').exists());self.assertFalse((old/'old').exists());self.assertTrue((other/'keep').exists())
 def test_symlink_destination_cannot_delete_outside_state(self):
  outside=self.root/'outside';outside.mkdir();(outside/'keep').touch();(self.m/'example').symlink_to(outside,target_is_directory=True);(self.u/'example').mkdir()
  self.assertNotEqual(0,self.run_logic().returncode);self.assertTrue((outside/'keep').exists())
 def run_uninstall(self,a):
  sh=self.root/'bbsh';sh.write_text('#!/bin/sh\nshift\nexec sh "$@"\n');sh.chmod(0o755)
  return subprocess.run(['sh','-eu','-c',UNINSTALL.replace('/data/oneos_bin/busybox',str(sh))],env={**os.environ,'A':str(a)},capture_output=True,text=True)
 def test_framework_removal_never_runs_its_uninstall_on_the_bound_state(self):
  # A36 d2de5297: Vector/LSPosed's uninstall.sh "rm -rf /data/adb/lspd" hit the selected framework's bound state
  a=self.root/'adb';(a/'oneos/run').mkdir(parents=True);(a/'oneos/framework').write_text('zygisk_vector\n')
  for i in ('zygisk_lsposed','zygisk_vector'):
   m=a/'modules'/i;m.mkdir(parents=True);(m/'.oneos-framework').write_text('lsposed\n');(m/'uninstall.sh').write_text('rm -rf "$LSPD"\nexit 1\n')
   (a/'oneos/framework-state'/i/'lspd').mkdir(parents=True);(a/'oneos/framework-state'/i/'lspd/config').touch()
  (a/'modules/zygisk_lsposed/remove').touch();(a/'modules/zygisk_vector/remove').touch()
  hma=a/'modules/hma';hma.mkdir();(hma/'remove').touch();(hma/'uninstall.sh').write_text('touch "$MODPATH/ran"\nexit 3\n')
  result=self.run_uninstall(a);self.assertEqual(0,result.returncode,result.stderr)
  self.assertFalse((a/'oneos/framework-state/zygisk_lsposed').exists());self.assertTrue((a/'oneos/framework-state/zygisk_vector/lspd/config').exists())
  self.assertTrue((hma/'ran').exists());self.assertIn("hma's uninstall.sh failed (exit 3); removed anyway",result.stdout)
if __name__=='__main__':unittest.main()
