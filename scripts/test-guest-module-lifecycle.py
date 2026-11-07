#!/usr/bin/env python3
"""Execute actual module promotion/removal logic without any device or mounts."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_prepare.sh').read_text()
LOGIC=s[s.index('# Cleanup scripts run in the guest root'):s.index("# The image's folder for a path")]
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
if __name__=='__main__':unittest.main()
