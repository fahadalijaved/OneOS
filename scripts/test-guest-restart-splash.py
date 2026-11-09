#!/usr/bin/env python3
"""Run the actual restart splash generation with inert local Android paths."""
import os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'switcher/assets/boot_status.sh').read_text()
class RestartSplashTest(unittest.TestCase):
 def run_case(self,saved,override=None):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'verbose').write_text(saved+'\n');(root/'events.log').write_text('previous events\n');(root/'stage').write_text('{"image":"pixel11fold-yogi"}');(root/'icon').write_text('icon')
   source=SOURCE.replace('/data/local/tmp/oneos/.oneos_stage',str(root/'stage')).replace('/data/local/tmp/oneos/oneos_boot_icon.png',str(root/'icon')).replace('/system/bin/sh /data/local/tmp/oneos/boot_status.sh supervise','/usr/bin/true')
   env={k:v for k,v in os.environ.items() if k!='ONEOS_VERBOSE_BOOT'};env['ONEOS_BOOT_DIR']=d
   if override is not None:env['ONEOS_VERBOSE_BOOT']=override
   result=subprocess.run(['sh','-c',source+'\noneos_boot_begin restart\noneos_boot_event "Preparing guest modules"\nwait\n','splash-test'],env=env,capture_output=True,text=True)
   self.assertEqual(0,result.returncode,result.stderr)
   return {name:(root/name).read_text() for name in ['verbose','title','status','events.log']}
 def test_saved_verbose_mode_is_respected(self):
  state=self.run_case('1');self.assertEqual('1\n',state['verbose']);self.assertEqual('Restarting Pixel\n',state['title']);self.assertIn('Preparing guest modules',state['events.log'])
 def test_quiet_mode_keeps_the_splash_without_verbose_events(self):
  state=self.run_case('0');self.assertEqual('0\n',state['verbose']);self.assertEqual('Restarting Pixel\n',state['title']);self.assertEqual('previous events\n',state['events.log'])
 def test_session_setting_can_override_the_saved_value(self):
  state=self.run_case('1','0');self.assertEqual('0\n',state['verbose']);self.assertEqual('previous events\n',state['events.log'])
if __name__=='__main__':unittest.main()
