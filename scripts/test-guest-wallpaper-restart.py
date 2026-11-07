#!/usr/bin/env python3
"""Run the actual startup repair against Pixel's indented saved metadata."""
import os, subprocess, tempfile, unittest, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'switcher/assets/guest_start.sh').read_text()
CODE=s[s.index("# Pixel 17's WallpaperDataParser"):s.index('# Properties are shared:')]
XML='''<?xml version="1.0"?>
<wp component="example.wallpaper/.Live">
  <description component="example.wallpaper/.Live" title="Tidal &amp; Swirl">
    <content><string name="text">keep  these spaces</string></content>
  </description>
</wp>
'''
class WallpaperRestartTest(unittest.TestCase):
 def run_repair(self,root):
  code=CODE.replace('/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk',str(root/'pixel.apk')).replace('/data/',str(root)+'/')
  r=subprocess.run(['sh','-c','bb() { "$@"; }; BB=bb\n'+code],capture_output=True,text=True)
  self.assertEqual(0,r.returncode,r.stderr)
 def test_preserves_selected_component_and_content_on_every_start(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'pixel.apk').touch();p=root/'system/users/0/wallpaper_info.xml';p.parent.mkdir(parents=True);p.write_text(XML)
   self.run_repair(root)
   expected=ET.fromstring(XML);actual=ET.fromstring(p.read_text())
   self.assertEqual(expected.attrib,actual.attrib)
   self.assertEqual(expected.find('description').attrib,actual.find('description').attrib)
   self.assertEqual('keep  these spaces',actual.find('.//string').text)
   self.assertNotRegex(p.read_text(),r'>\s+<');self.assertEqual(XML,Path(str(p)+'.oneos-spacing-backup').read_text())
   before=p.read_bytes();self.run_repair(root);self.assertEqual(before,p.read_bytes())
 def test_symlink_is_untouched(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'pixel.apk').touch();p=root/'system/users/0/wallpaper_info.xml';p.parent.mkdir(parents=True)
   target=root/'original';target.write_text(XML);p.symlink_to(target);self.run_repair(root)
   self.assertEqual(XML,target.read_text());self.assertTrue(p.is_symlink())
if __name__=='__main__':unittest.main()
