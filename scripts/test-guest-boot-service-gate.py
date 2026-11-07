#!/usr/bin/env python3
"""Execute the handoff reset against a stale shared host boot-completed flag."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_start.sh').read_text()
RESET=s[s.index('# Properties are shared: One UI left boot_completed=1.'):s.index('echo "[Pivoted Root] Launching guest Zygote')]
class BootGateTest(unittest.TestCase):
 def test_host_completion_is_cleared_before_guest_services_start(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for key in ['sys.boot_completed','dev.bootcomplete']:(root/key).write_text('1')
   code='setprop() { printf "%s" "$2" > "$STATE/$1"; }\n'+RESET
   result=subprocess.run(['sh','-ec',code],env={**os.environ,'STATE':d},capture_output=True,text=True)
   self.assertEqual(0,result.returncode,result.stderr)
   for key in ['sys.boot_completed','dev.bootcomplete']:self.assertEqual('0',(root/key).read_text())
   self.assertLess(s.index(RESET),s.index('/data/oneos_runtime.sh late'))
if __name__=='__main__':unittest.main()
