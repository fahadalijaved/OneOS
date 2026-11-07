#!/usr/bin/env python3
"""Exercise the actual customize environment with standard root-module calls."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_runtime.sh').read_text()
CODE=s[s.index('\ncustomize)')+len('\ncustomize)'):s.index('\nlate)')].rsplit(';;',1)[0]
class InstallerTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.module=self.root/'module with spaces';self.module.mkdir();(self.module/'module.prop').write_text('id=test\n');(self.module/'service.sh').write_text('exit 0\n')
  self.prefix='chown() { printf "chown:%s:%s:%s\\n" "$1" "$2" "${3-}" >> "$CALL_LOG"; }\nchcon() { printf "chcon:%s:%s:%s\\n" "$1" "$2" "${3-}" >> "$CALL_LOG"; }\n'
 def tearDown(self):self.tmp.cleanup()
 def run_custom(self,script):
  (self.module/'customize.sh').write_text(script)
  return subprocess.run(['sh','-ec',self.prefix+CODE,'installer-test','customize',str(self.module)],env={**os.environ,'MODPATH':str(self.module),'CALL_LOG':str(self.root/'calls')},capture_output=True,text=True)
 def test_standard_pixelxpert_set_perm_order(self):
  result=self.run_custom('set_perm "$MODPATH/service.sh" 0 0 0755\n')
  self.assertEqual(0,result.returncode,result.stderr);self.assertEqual(0o755,(self.module/'service.sh').stat().st_mode&0o777)
  calls=(self.root/'calls').read_text();self.assertIn('chown:0:0:'+str(self.module/'service.sh'),calls);self.assertIn('chcon:u:object_r:system_file:s0:',calls)
 def test_recursive_modes_and_explicit_context(self):
  tree=self.module/'nested dir';tree.mkdir();(tree/'file name').touch()
  result=self.run_custom('set_perm_recursive "$MODPATH/nested dir" 0 0 0750 0640 u:object_r:system_file:s0\n')
  self.assertEqual(0,result.returncode,result.stderr);self.assertEqual(0o750,tree.stat().st_mode&0o777);self.assertEqual(0o640,(tree/'file name').stat().st_mode&0o777)
 def test_customizers_do_not_inherit_errexit_or_nounset(self):
  result=self.run_custom('false\nprintf "%s" "$UNDEFINED_MODULE_OPTION"\nui_print done\n');self.assertEqual(0,result.returncode,result.stderr);self.assertIn('done',result.stdout)
 def test_explicit_abort_still_fails(self):
  result=self.run_custom('abort "unsupported ROM"\nui_print must-not-run\n');self.assertNotEqual(0,result.returncode);self.assertNotIn('must-not-run',result.stdout)
 def test_package_install_can_defer_when_the_guest_framework_is_stopped(self):
  service=self.root/'service';service.write_text('#!/bin/sh\necho "Service package: not found"\n');service.chmod(0o755)
  global CODE
  original=CODE
  try:
   CODE=CODE.replace('/system/bin/service',str(service))
   result=self.run_custom('pm install -r "$MODPATH/test.apk" >/dev/null 2>&1\nif [ $? -ne 0 ]; then touch "$MODPATH/install_needed"; fi\nui_print deferred\n')
   self.assertEqual(0,result.returncode,result.stderr);self.assertTrue((self.module/'install_needed').exists())
  finally:CODE=original
if __name__=='__main__':unittest.main()
