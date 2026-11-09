#!/usr/bin/env python3
"""Run the real framework selection/loading branches without starting Android."""
from pathlib import Path
import os,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_runtime.sh').read_text()
PRE=s[s.index('    selected=$(cat "$A/oneos/framework")',s.index('\npre)')):s.index('    "$A/oneos/bin/zygiskd"',s.index('\npre)'))]
PREP=s[s.index('    for base in modules modules_update;',s.index('\nprepare)')):s.index('    mkdir -p "$A/oneos/framework-state',s.index('\nprepare)'))]
class FrameworkSwitchTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.a=Path(self.tmp.name)
  for p in ['oneos/bin','oneos/run','modules/provider/zygisk','modules/other','modules_update']: (self.a/p).mkdir(parents=True,exist_ok=True)
  self.provider=self.a/'modules/provider';(self.a/'oneos/framework').write_text('provider\n');(self.provider/'.oneos-framework').write_text('vector\n');(self.a/'modules/other/.oneos-framework').write_text('lsposed\n');(self.provider/'zygisk/arm64-v8a.so').touch()
  helper=self.a/'oneos/bin/su';helper.write_text('#!/bin/sh\nprintf started > "$MARKER"\n');helper.chmod(0o755)
 def tearDown(self):self.tmp.cleanup()
 def run_branch(self,code):return subprocess.run(['sh','-ec',code+'\nwait\n'],env={**os.environ,'A':str(self.a),'selected':'provider','MARKER':str(self.a/'started')},capture_output=True,text=True)
 def test_disabled_provider_is_kept_but_daemon_does_not_start(self):
  (self.provider/'disable').touch();result=self.run_branch(PRE);self.assertEqual(0,result.returncode,result.stderr);self.assertFalse((self.a/'started').exists());self.assertTrue((self.provider/'.oneos-framework').exists())
 def test_enabled_provider_starts(self):
  result=self.run_branch(PRE);self.assertEqual(0,result.returncode,result.stderr);self.assertTrue((self.a/'started').exists())
 def test_preparation_does_not_reenable_explicitly_disabled_selection(self):
  (self.provider/'disable').touch();result=self.run_branch(PREP);self.assertEqual(0,result.returncode,result.stderr);self.assertTrue((self.provider/'disable').exists());self.assertTrue((self.a/'modules/other/disable').exists())
if __name__=='__main__':unittest.main()
