#!/usr/bin/env python3
"""Retained APK activation must stay scoped and fail closed on unknown bundles."""
from pathlib import Path
import json,os,subprocess,tempfile,unittest
SCRIPT=Path(__file__).resolve().parents[1]/'switcher/assets/fold8_coloros.sh'
class Activation(unittest.TestCase):
 def invoke(self,profile='f8',image='coloros17-findn6',fileset='n6-f8',bundle=False):
  with tempfile.TemporaryDirectory() as tmp:
   stage=Path(tmp);(stage/'.oneos_stage').write_text(json.dumps(dict(image=image,set=fileset,created=0),indent=2)+'\n')
   # 0.4.38: selected only where the patched SystemUI is staged (here: the Fold8's).
   if profile=='f8':(stage/'Fold8SystemUI.apk').write_bytes(b'')
   if bundle:
    d=stage/'verified_addons';d.mkdir();(d/'overlays.list').write_text('untrusted manifest\n')
   return subprocess.run(['sh',str(SCRIPT),'addons-verify'],env=dict(os.environ,STAGE=tmp,BB='/bin/sh',ONEOS_PROFILE=profile),capture_output=True).returncode
 def test_stock_stage_without_saved_bundle_is_unchanged(self):self.assertEqual(0,self.invoke())
 def test_unknown_bundle_is_refused(self):self.assertNotEqual(0,self.invoke(bundle=True))
 def test_other_profiles_and_guests_do_not_activate(self):
  for profile,image,fileset in [('f8u','coloros17-findn6','n6-f8u'),('f8','pixel11fold-yogi','pixel-f8')]:
   self.assertEqual(0,self.invoke(profile,image,fileset,True))
 def test_unknown_photos_apk_is_refused_before_mounting(self):
  with tempfile.TemporaryDirectory() as tmp:
   stage=Path(tmp);(stage/'.oneos_stage').write_text(json.dumps(dict(image='coloros17-findn6',set='n6-f8',created=0),indent=2)+'\n')
   (stage/'Fold8SystemUI.apk').write_bytes(b'')
   d=stage/'verified_addons';d.mkdir();(d/'PhotosGlobal.apk').write_bytes(b'wrong donor')
   result=subprocess.run(['sh',str(SCRIPT),'prepare'],env=dict(os.environ,STAGE=tmp,BB='/does/not/exist',ONEOS_PROFILE='f8'),capture_output=True)
   self.assertNotEqual(0,result.returncode)
   self.assertFalse((stage/'rootfs').exists())
if __name__=='__main__':unittest.main()
