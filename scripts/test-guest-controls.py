#!/usr/bin/env python3
"""Execute the real guest control shell branch against disposable private state."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'switcher/assets/guest_runtime.sh').read_text()
CONTROL=SOURCE[SOURCE.index('control)'):SOURCE.index('baseline)')]
class ControlsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for p in ['oneos/run','modules','modules_update']: (self.root/p).mkdir(parents=True,exist_ok=True)
  (self.root/'oneos/framework').write_text('test_framework\n')
  self.module=self.root/'modules/test_module';self.module.mkdir();(self.module/'module.prop').write_text('id=test_module\nname=Test module\ndescription=A test with spaces\nauthor=Module author\nversion=v2\nversionCode=2\nupdateJson=https://example.org/update.json\n')
  self.script='set -eu\ncase "$1" in\n'+CONTROL.replace('A=/data/adb','A='+str(self.root))+'esac\n'
 def tearDown(self):self.tmp.cleanup()
 def run_control(self,*args):return subprocess.run(['sh','-c',self.script,'control-test','control',*args],capture_output=True,text=True)
 def test_metadata_is_one_hex_encoded_row(self):
  result=self.run_control('list');self.assertEqual(0,result.returncode,result.stderr)
  rows=[l for l in result.stdout.splitlines() if l.startswith('@@RESULT module-info')];self.assertEqual(1,len(rows),result.stdout)
  parts=rows[0].split();self.assertEqual(14,len(parts));self.assertEqual("Module author",bytes.fromhex(parts[9]).decode());self.assertEqual("2",bytes.fromhex(parts[10]).decode());self.assertEqual('Test module',bytes.fromhex(parts[7]).decode());self.assertEqual('A test with spaces',bytes.fromhex(parts[8]).decode())
 def test_toggle_only_changes_private_flag(self):
  self.assertEqual(0,self.run_control('toggle','test_module','off').returncode);self.assertTrue((self.module/'disable').is_file())
  self.assertEqual(0,self.run_control('toggle','test_module','on').returncode);self.assertFalse((self.module/'disable').exists())
 def test_framework_disables_without_uninstall_and_symlink_flags_are_refused(self):
  (self.module/'.oneos-framework').write_text('lsposed\n');self.assertEqual(0,self.run_control('toggle','test_module','off').returncode);self.assertTrue((self.module/'module.prop').is_file());self.assertNotEqual(0,self.run_control('toggle','test_module','on').returncode)
  (self.module/'.oneos-framework').unlink();(self.module/'disable').unlink();target=self.root/'outside';target.write_text('untouched');(self.module/'disable').symlink_to(target)
  self.assertNotEqual(0,self.run_control('toggle','test_module','on').returncode);self.assertEqual('untouched',target.read_text())
 def test_traversal_and_untrusted_import_path_are_refused(self):
  self.assertNotEqual(0,self.run_control('toggle','../outside','off').returncode)
  self.assertNotEqual(0,self.run_control('import','test','/tmp/other.bundle').returncode)
 def test_remove_can_be_cancelled_and_does_not_delete_active_files(self):
  self.assertEqual(0,self.run_control('remove','test_module').returncode);self.assertTrue((self.module/'remove').exists());self.assertTrue((self.module/'module.prop').exists())
  self.assertEqual(0,self.run_control('restore','test_module').returncode);self.assertFalse((self.module/'remove').exists())
 def test_selected_framework_cannot_be_removed(self):
  (self.root/'oneos/framework').write_text('test_module\n')
  self.assertNotEqual(0,self.run_control('remove','test_module').returncode);self.assertFalse((self.module/'remove').exists())
 def test_asset_reads_local_files_but_refuses_escape(self):
  web=self.module/'webroot';web.mkdir();(web/'index.html').write_text('local webui')
  outside=self.root/'secret';outside.write_text('outside');(web/'escape').symlink_to(outside)
  self.assertEqual('local webui',self.run_control('asset','test_module','index.html').stdout)
  self.assertNotEqual(0,self.run_control('asset','test_module','escape').returncode)
  self.assertNotEqual(0,self.run_control('asset','test_module','../module.prop').returncode)
 def test_remove_symlink_cannot_mutate_target(self):
  outside=self.root/'keep';outside.write_text('keep');(self.module/'remove').symlink_to(outside)
  self.assertNotEqual(0,self.run_control('restore','test_module').returncode);self.assertEqual('keep',outside.read_text())
 def test_action_runs_only_installed_module_with_its_directory(self):
  busy=self.root/'busybox';busy.write_text('#!/bin/sh\nif [ "$1" = timeout ]; then shift 2; exec "$@"; fi\n[ "$1" = sh ] && shift\nexec /bin/sh "$@"\n');busy.chmod(0o755)
  self.script=self.script.replace('/data/oneos_bin/busybox',str(busy))
  (self.module/'action.sh').write_text('printf "action:%s" "$MODPATH"\n')
  result=self.run_control('action','test_module');self.assertEqual(0,result.returncode,result.stderr);self.assertIn('action:'+str(self.module),result.stdout)
  (self.module/'remove').touch();self.assertNotEqual(0,self.run_control('action','test_module').returncode)
 def test_restart_uses_only_the_guarded_request_property(self):
  self.script='setprop() { printf "%s=%s" "$1" "$2"; }\n'+self.script
  result=self.run_control('restart');self.assertEqual(0,result.returncode,result.stderr);self.assertEqual('oneos.guest.powerctl=ksud:soft-reboot',result.stdout)
if __name__=='__main__':unittest.main()
