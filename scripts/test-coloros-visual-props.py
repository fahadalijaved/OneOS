#!/usr/bin/env python3
import os,subprocess,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_props.sh').read_text()
CODE=s[s.index('    AL=persist.sys.oplus.anim_level;'):s.index('    # One UI\'s color mode')]
class VisualPropsTest(unittest.TestCase):
 def run_case(self,image,host,props):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'.oneos_stage').write_text('{"image": "'+image+'"}')
   for name,text in [('host',host),('new',props),('override',''),('calls','')]: (root/name).write_text(text)
   rp=root/'rp';rp.write_text('#!/bin/sh\nprintf "%s %s %s\\n" "$1" "$2" "$3" >> "$CALL_LOG"\n');rp.chmod(0o755)
   prefix='getprop() { case "$1" in ro.launcher.blur.appLaunch) echo 0 ;; esac; }\n'
   if sys.platform == 'darwin': prefix='sed() { if [ "$1" = -i ]; then shift; command sed -i "" "$@"; else command sed "$@"; fi; }\n'+prefix
   env={**os.environ,'STAGE':d,'HOST':str(root/'host'),'NEW':str(root/'new'),'OVR':str(root/'override'),'RP':str(rp),'CALL_LOG':str(root/'calls'),'ROOTFS':d,'GSE':d}
   subprocess.run(['sh','-ec',prefix+CODE],env=env,check=True,capture_output=True)
   return tuple((root/name).read_text() for name in ['new','override','calls'])
 def test_empty_host_animation_tier_is_overridden_and_restorable(self):
  new,overrides,calls=self.run_case('coloros17-findn6','persist.sys.oplus.anim_level\nro.launcher.blur.appLaunch\n','')
  self.assertIn('-n persist.sys.oplus.anim_level 1',calls);self.assertIn('persist.sys.oplus.anim_level=\n',overrides)
  self.assertIn('-n ro.launcher.blur.appLaunch 1',calls);self.assertIn('ro.launcher.blur.appLaunch=0',overrides)
 def test_empty_guest_property_is_replaced(self):
  new,_,_=self.run_case('coloros17-findn6','','persist.sys.oplus.anim_level=\nro.launcher.blur.appLaunch=0\n')
  self.assertEqual(1,new.count('persist.sys.oplus.anim_level=1'));self.assertNotIn('ro.launcher.blur.appLaunch=0',new);self.assertIn('ro.oplus.animationlevel=3',new);self.assertIn('ro.oplus.gaussianlevel=3',new)
 def test_other_images_unchanged(self):
  original='persist.sys.oplus.anim_level=\n';new,overrides,calls=self.run_case('pixel11fold-yogi','',original)
  self.assertEqual(original,new);self.assertEqual('',overrides);self.assertEqual('',calls)
if __name__=='__main__':unittest.main()
