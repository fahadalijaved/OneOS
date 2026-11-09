#!/usr/bin/env python3
"""Check restoration of module property overrides for a guest-only restart."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_runtime.sh').read_text()
RESTORE=s[s.index('restore-props)')+len('restore-props)'):s.index('uninstall)')].rsplit(';;',1)[0]
class ModulePropsTest(unittest.TestCase):
 def test_existing_empty_and_new_properties_restore_without_shell_evaluation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'oneos/run').mkdir(parents=True);(root/'ksu/bin').mkdir(parents=True)
   snap=root/'oneos/run/module-props';snap.write_text('ro.test.present|1|original value\nro.test.empty|1|\nro.test.added|0|\nro.test.quoted|1|$(touch /tmp/oneos-must-not-exist)|literal\n')
   rp=root/'ksu/bin/resetprop';rp.write_text('#!/bin/sh\nprintf "[%s][%s][%s]\\n" "$1" "$2" "${3-}" >> "$CALL_LOG"\n');rp.chmod(0o755)
   result=subprocess.run(['sh','-ec',RESTORE.replace('A=/data/adb','A='+d)],env={**os.environ,'CALL_LOG':str(root/'calls')},capture_output=True,text=True)
   self.assertEqual(0,result.returncode,result.stderr);calls=(root/'calls').read_text()
   self.assertIn('[-n][ro.test.present][original value]',calls);self.assertIn('[-n][ro.test.empty][]',calls);self.assertIn('[--delete][ro.test.added][]',calls)
   self.assertIn('$(touch /tmp/oneos-must-not-exist)|literal',calls);self.assertFalse(snap.exists())
if __name__=='__main__':unittest.main()
