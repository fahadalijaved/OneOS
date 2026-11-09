#!/usr/bin/env python3
"""Run the actual guest-su and file-bind setup snippets in isolated fixtures."""
from pathlib import Path
import os, subprocess, tempfile, unittest, sys
ROOT=Path(__file__).resolve().parents[1]
class SetupTest(unittest.TestCase):
 def test_native_broker_is_copied_without_a_host_su_file(self):
  script=(ROOT/'switcher/assets/guest_prepare.sh').read_text()
  snippet=script.split('echo "=== 6. Setting up /system/xbin/su (KernelSU Bridge) ==="',1)[1].split('echo "=== 7.',1)[0]
  with tempfile.TemporaryDirectory() as d:
   stage=Path(d); (stage/'data/oneos_root').mkdir(parents=True);(stage/'data/oneos_root/enabled').touch();(stage/'rootfs/system/xbin').mkdir(parents=True)
   broker=stage/'guest_root';broker.write_bytes(b'guest broker fixture')
   bb=stage/'busybox';bb.write_text('#!/bin/sh\n[ "$1" = mount ] && exit 0\nexit 1\n');bb.chmod(0o755)
   subprocess.run(['sh','-c',snippet],env={**os.environ,'STAGE':d,'ROOTFS':str(stage/'rootfs'),'BB':str(bb)},check=True)
   actual=stage/'rootfs/system/xbin/su';self.assertEqual(actual.read_bytes(),broker.read_bytes());self.assertTrue(actual.stat().st_mode & 0o111)
 def test_missing_xbin_is_added_only_to_enabled_guests_overlay(self):
  script=(ROOT/'switcher/assets/guest_prepare.sh').read_text()
  helper=script[script.index('guest_root_mountpoint() {'):script.index('if [ -d "$SAMCAM_SRC" ] && [ $SAMCAM_IMAGE = 0 ]; then')]
  with tempfile.TemporaryDirectory() as d:
   stage=Path(d);(stage/'rootfs/system').mkdir(parents=True);(stage/'data/oneos_root').mkdir(parents=True);up=stage/'overlay';up.mkdir()
   env={**os.environ,'STAGE':d,'ROOTFS':str(stage/'rootfs')}
   subprocess.run(['sh','-ec',helper+'\nguest_root_mountpoint "'+str(up)+'"'],env=env,check=True)
   self.assertFalse((up/'xbin').exists())
   (stage/'data/oneos_root/enabled').touch()
   subprocess.run(['sh','-ec',helper+'\nguest_root_mountpoint "'+str(up)+'"'],env=env,check=True)
   self.assertTrue((up/'xbin').is_dir());self.assertFalse((stage/'rootfs/system/xbin').exists())
 def test_bind_remount_has_explicit_source_and_target(self):
  script=(ROOT/'switcher/assets/guest_runtime.sh').read_text()
  snippet=script.split('    if [ -f /data/adb/ksu/.allowlist ]',1)[1].split('\n    fi',1)[0]
  # Run only the real remount/cleanup branch, substituting a fixture target.
  snippet=snippet[snippet.index('        if ! "$busy" mount -o remount,bind,ro'):]
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);(base/'allowlist.saved').write_text('preserved grants')
   busy=base/'busybox';busy.write_text('#!/bin/sh\n[ "$#" = 5 ] && [ "$1" = mount ] && [ "$2" = -o ] && [ "$3" = remount,bind,ro ]\n');busy.chmod(0o755)
   subprocess.run(['sh','-ec',snippet.replace('/data/adb/ksu/.allowlist',str(base/'target'))],env={**os.environ,'B':d,'busy':str(busy)},check=True)
   self.assertTrue((base/'allowlist.protected').exists())
class PrivateBindTest(unittest.TestCase):
 def check_bind(self,kind):
  script=(ROOT/'switcher/assets/guest_runtime.sh').read_text()
  start=script.index('verify_private_adb_bind() {')
  function=script[start:script.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);private=base/'private';(private/'modules').mkdir(parents=True)
   root=base/'rootfs';(root/'data').mkdir(parents=True)
   if kind=='wrong-root':(root/'data/adb').mkdir()
   else:(root/'data/adb').symlink_to(private)
   foreign=base/'foreign';foreign.mkdir()
   busy=base/'busybox'
   busy.write_text('#!'+sys.executable+'\nimport os,sys\nassert sys.argv[1:5]==["stat","-L","-c","%d:%i"]\np=sys.argv[-1]\nif os.getenv("BAD_MODULE_BIND") and p.endswith("/rootfs/data/adb/modules"):p=os.environ["FOREIGN"]\ns=os.stat(p)\nprint(str(s.st_dev)+":"+str(s.st_ino))\n');busy.chmod(0o755)
   env={**os.environ,'B':str(busy),'A':str(private),'R':str(root),'FOREIGN':str(foreign)}
   if kind=='wrong-modules':env['BAD_MODULE_BIND']='1'
   result=subprocess.run(['sh','-ec',function+'\nverify_private_adb_bind'],env=env,capture_output=True,text=True)
   self.assertEqual(kind=='valid',result.returncode==0,result.stderr)
 def test_private_root_and_modules_match(self):self.check_bind('valid')
 def test_host_adb_view_is_rejected(self):self.check_bind('wrong-root')
 def test_nested_modules_overmount_is_rejected(self):self.check_bind('wrong-modules')
if __name__=='__main__': unittest.main()
