#!/usr/bin/env python3
"""Exercise the actual guest preparation selector and its failure boundaries."""
import hashlib, json, os, pathlib, subprocess, tempfile, unittest
R=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=R/'switcher/assets/fold8_pixel.sh'
class PrepareBoundaryTest(unittest.TestCase):
 def run_prepare(self,profile='f8',image='pixel11fold-yogi',fileset='pixel-f8',donor=True,symlink=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);stage=root/'stage';stage.mkdir()
   (stage/'.oneos_stage').write_text(json.dumps(dict(image=image,set=fileset,created=0),indent=2)+'\n')
   apk='SystemUI/SystemUI.apk' if image in ('lineage24-infiniti','infinityx41-findx9u') else 'SystemUIGoogle/SystemUIGoogle.apk'
   target=stage/'rootfs/system/system_ext/priv-app'/apk
   target.parent.mkdir(parents=True);target.write_bytes(b'donor' if donor else b'wrong')
   (stage/'data').mkdir();outside=root/'outside';outside.mkdir()
   (stage/'Fold8AngleRelay.dex').write_bytes(b'dex');(stage/'fold8_pixel.sh').write_text('#')
   if symlink:(stage/'data/oneos_pixel_hinge').symlink_to(outside,target_is_directory=True)
   bb=root/'busybox';bb.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\nexit 0\n');bb.chmod(0o755)
   # Use a tiny fake donor while retaining all script branches and filesystem checks.
   script=root/'prepare.sh';script.write_text(SCRIPT.read_text().replace('9934d2dac326f56290f459b9e649185cd5531e1b6ae1f5a72b11e88f865f8b03',hashlib.sha256(b'donor').hexdigest()).replace('aa22961855b1f8a9d3dbbbc643922f9b216f6d411313e12eb8b70086287b84c3',hashlib.sha256(b'donor').hexdigest()).replace('6a99684e831f9635738189d39667debe0f8b798012fa4eb622a7cb87ad9b1ddf',hashlib.sha256(b'donor').hexdigest()))
   tools=root/'tools';tools.mkdir()
   for t in ('chown','chcon'):(tools/t).write_text('#!/bin/sh\nexit 0\n');(tools/t).chmod(0o755)
   calls=root/'calls';env=dict(os.environ,STAGE=str(stage),BB=str(bb),ONEOS_PROFILE=profile,CALLS=str(calls),PATH=str(tools)+':'+os.environ['PATH'])
   p=subprocess.run(['sh',str(script),'prepare'],env=env,capture_output=True,text=True)
   return p,calls.read_text() if calls.exists() else '',list(outside.iterdir())
 def test_other_devices_and_images_have_no_mounts(self):
  for p,i,s in [('f8','coloros17-findn6','n6-f8'),('f8u','coloros17-findn6','n6-f8u'),('f8','pixel11fold-yogi','pixel-f8u'),('f8u','pixel11fold-yogi','pixel-f8'),('s-8850','pixel11pro-kodiak','pixel-sultra')]:
   result,calls,_=self.run_prepare(p,i,s);self.assertEqual(0,result.returncode);self.assertEqual('',calls)
 def test_fold8_and_fold8_ultra_bind_the_patched_systemui(self):
  for p,s in [('f8','pixel-f8'),('f8u','pixel-f8u')]:
   result,calls,_=self.run_prepare(p,'pixel11fold-yogi',s);self.assertEqual(0,result.returncode,result.stderr);self.assertIn('mount --bind',calls)
 def test_lineage_is_scoped_to_fold8_and_exact_donor(self):
  result,calls,_=self.run_prepare('f8','lineage24-infiniti','lineage');self.assertEqual(0,result.returncode,result.stderr);self.assertIn('Fold8LineageSystemUI.apk',calls)
  result,calls,_=self.run_prepare('f8u','lineage24-infiniti','lineage');self.assertEqual(0,result.returncode);self.assertNotIn('mount --bind',calls)
  result,calls,_=self.run_prepare('f8','lineage24-infiniti','lineage',donor=False);self.assertEqual(3,result.returncode);self.assertNotIn('mount --bind',calls)
  result,_,outside=self.run_prepare('f8','lineage24-infiniti','lineage',symlink=True);self.assertEqual(3,result.returncode);self.assertEqual([],outside)
 def test_infinity_is_scoped_to_fold8_and_exact_image_set_and_donor(self):
  result,calls,_=self.run_prepare('f8','infinityx41-findx9u','infinityx');self.assertEqual(0,result.returncode,result.stderr);self.assertIn('Fold8InfinitySystemUI.apk',calls)
  for profile,fileset in [('f8u','infinityx'),('f8','lineage')]:
   result,calls,_=self.run_prepare(profile,'infinityx41-findx9u',fileset);self.assertEqual(0,result.returncode);self.assertNotIn('mount --bind',calls)
  result,calls,_=self.run_prepare('f8','infinityx41-findx9u','infinityx',donor=False);self.assertEqual(3,result.returncode);self.assertNotIn('mount --bind',calls)
  result,_,outside=self.run_prepare('f8','infinityx41-findx9u','infinityx',symlink=True);self.assertEqual(3,result.returncode);self.assertEqual([],outside)
 def test_unknown_donor_refuses_before_bind(self):
  result,calls,_=self.run_prepare(donor=False);self.assertEqual(3,result.returncode);self.assertNotIn('mount --bind',calls)
 def test_guest_symlink_cannot_redirect_payload_writes(self):
  result,_,outside=self.run_prepare(symlink=True);self.assertEqual(3,result.returncode);self.assertEqual([],outside)
if __name__=='__main__':unittest.main()
