#!/usr/bin/env python3
"""Port Pixel hinge input and lock-screen double-tap gestures to the pinned Lineage donor.
The supplied adapter DEX is used; its Java and compilation-only stubs are in source/.
A rebuilt APK needs its SHA-256 pin updated in enable/undo scripts before use.
"""
import argparse, copy, hashlib, pathlib, shutil, struct, subprocess, tempfile, zipfile
ROOT=pathlib.Path(__file__).resolve().parent
PIXEL=ROOT.parent/'fold8-pixel'
# apktool on PATH, else the repository's own (mysticgsi/tools/apktool, as the camera builds use).
APKTOOL=['apktool'] if shutil.which('apktool') else ['java','-jar',str(sorted((ROOT.parents[2]/'mysticgsi/tools/apktool').glob('*.jar'))[0])]
# Double tap to sleep (dt2s/, 0.4.59): helper classes added to classes2.
ADDED={'com.android.systemui.unfold.updates.hinge.PixelFold8Hinge','oneos.sysui.OneOSDt2s','oneos.sysui.OneOSDt2s$1'}
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('donor',type=pathlib.Path)
p.add_argument('--zipalign',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args(); a.donor=a.donor.resolve();a.output=a.output.resolve()
assert hashlib.sha256(a.donor.read_bytes()).hexdigest()=='aa22961855b1f8a9d3dbbbc643922f9b216f6d411313e12eb8b70086287b84c3','Different donor'
with tempfile.TemporaryDirectory(prefix='oneos-pixel-hinge-') as tmp:
 w=pathlib.Path(tmp);decoded=w/'decoded'
 subprocess.run(APKTOOL+['d','-f','-r','-o',str(decoded),str(a.donor)],check=True)
 base=decoded/'smali_classes2/com/android/systemui/unfold/updates/hinge'
 provider=base/'HingeSensorAngleProvider$stop$1.smali'
 text=provider.read_text()
 for value,method in [('v0','start'),('v1','stop')]:
  needle=f'    iput-boolean {value}, p0, Lcom/android/systemui/unfold/updates/hinge/HingeSensorAngleProvider;->started:Z'
  assert text.count(needle)==1
  text=text.replace(needle,needle+f'\n\n    invoke-static {{p0}}, Lcom/android/systemui/unfold/updates/hinge/PixelFold8Hinge;->{method}(Lcom/android/systemui/unfold/updates/hinge/HingeSensorAngleProvider;)V')
 provider.write_text(text)
 listener=base/'HingeSensorAngleProvider$HingeAngleSensorListener.smali'
 text=listener.read_text();a0=text.index('.method public final onSensorChanged(');b0=text.index('.end method',a0)+len('.end method')
 body=""".method public final onSensorChanged(Landroid/hardware/SensorEvent;)V
    .locals 2
    iget-object v0, p0, Lcom/android/systemui/unfold/updates/hinge/HingeSensorAngleProvider$HingeAngleSensorListener;->this$0:Lcom/android/systemui/unfold/updates/hinge/HingeSensorAngleProvider;
    iget-object v1, p1, Landroid/hardware/SensorEvent;->values:[F
    const/4 p1, 0x0
    aget v1, v1, p1
    invoke-static {v0, v1}, Lcom/android/systemui/unfold/updates/hinge/PixelFold8Hinge;->onPublicAngle(Lcom/android/systemui/unfold/updates/hinge/HingeSensorAngleProvider;F)V
    return-void
.end method"""
 listener.write_text(text[:a0]+body+text[b0:])
 # Recompute Quick Settings header heights on a panel/configuration switch, preserving Lineage resource ids.
 header=decoded/'smali_classes2/com/android/systemui/shade/ShadeHeaderController$configurationControllerListener$1.smali'
 text=header.read_text();start=text.index('.method public final onConfigChanged(');end=text.index('.end method',start)
 body=text[start:end];assert body.count('    .locals 4')==1 and body.count('    return-void')==1
 body=body.replace('    .locals 4','    .locals 5\n\n    move-object v4, p0')
 body=body.replace('    return-void','    invoke-virtual {v4}, Lcom/android/systemui/shade/ShadeHeaderController$configurationControllerListener$1;->onDensityOrFontScaleChanged()V\n\n    return-void')
 header.write_text(text[:start]+body+text[end:])
 import re
 view=decoded/'smali_classes2/com/android/systemui/shade/NotificationShadeWindowView.smali'
 text=view.read_text()
 for signature,call in [('dispatchTouchEvent\\(Landroid/view/MotionEvent;\\)Z','invoke-static/range {p0 .. p1}, Loneos/sysui/OneOSDt2s;->shadeTouch(Landroid/view/View;Landroid/view/MotionEvent;)V'),('onAttachedToWindow\\(\\)V','invoke-static {p0}, Loneos/sysui/OneOSDt2s;->register(Landroid/view/View;)V')]:
  rx=re.compile(r'(^\.method [^\n]*'+signature+r'\n    \.locals \d+\n)',re.M)
  text,n=rx.subn(lambda m:m[0]+'\n    '+call+'\n',text);assert n==1,(signature,n)
 view.write_text(text)
 for helper in (PIXEL/'dt2s/smali').rglob('*.smali'):
  dest=decoded/'smali_classes2'/helper.relative_to(PIXEL/'dt2s/smali');assert not dest.exists(),dest
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(helper,dest)
 subprocess.run(APKTOOL+['b','-o',str(w/'rebuilt.apk'),str(decoded)],check=True)
 replacement=(decoded/'build/apk/classes2.dex').read_bytes()
 with a.donor.open('rb') as raw,zipfile.ZipFile(a.donor) as src,zipfile.ZipFile(w/'raw.apk','w') as dst:
  assert 'classes4.dex' not in src.namelist()
  for info in src.infolist():
   if info.filename=='classes2.dex':dst.writestr(info.filename,replacement,compress_type=zipfile.ZIP_STORED);continue
   raw.seek(info.header_offset);header=raw.read(30);assert header[:4]==b'PK\x03\x04'
   nl,el=struct.unpack_from('<HH',header,26);body=raw.read(nl+el+info.compress_size);desc=b''
   if info.flag_bits&8:
    desc=raw.read(4);desc+=raw.read(12 if desc==b'PK\x07\x08' else 8)
   entry=copy.copy(info);entry.header_offset=dst.fp.tell();dst.fp.write(header+body+desc)
   dst.filelist.append(entry);dst.NameToInfo[entry.filename]=entry;dst.start_dir=dst.fp.tell();dst._didModify=True
  dst.writestr('classes4.dex',(PIXEL/'PixelFold8Hinge.dex').read_bytes(),compress_type=zipfile.ZIP_STORED)
 subprocess.run([str(a.zipalign),'-f','-P','16','4',str(w/'raw.apk'),str(w/'aligned.apk')],check=True)
 # Preserve the donor's certificate metadata for a trusted system-directory
 # replacement. This does NOT create a content-valid OEM APK signature.
 original=a.donor.read_bytes();e=original.rfind(b'PK\x05\x06');cd=struct.unpack_from('<I',original,e+16)[0]
 assert original[cd-16:cd]==b'APK Sig Block 42'
 size=struct.unpack_from('<Q',original,cd-24)[0];block=original[cd-size-8:cd]
 assert struct.unpack_from('<Q',block)[0]==size
 result=(w/'aligned.apk').read_bytes();e=result.rfind(b'PK\x05\x06');cd=struct.unpack_from('<I',result,e+16)[0]
 result=bytearray(result[:cd]+block+result[cd:]);struct.pack_into('<I',result,e+len(block)+16,cd+len(block))
 a.output.write_bytes(result)
 with zipfile.ZipFile(a.donor) as src,zipfile.ZipFile(a.output) as dst:
  assert set(dst.namelist())-set(src.namelist())=={'classes4.dex'}
  for name in src.namelist():
   if name!='classes2.dex':assert src.read(name)==dst.read(name),name
 def classes(path):return subprocess.check_output(['python3',str(PIXEL/'list_dex_classes.py'),str(path),'.']).decode().splitlines()
 before,after=classes(a.donor),classes(a.output)
 assert len(after)==len(set(after)) and set(before).issubset(after)
 assert set(after)-set(before)==ADDED,set(after)-set(before)
print(hashlib.sha256(a.output.read_bytes()).hexdigest(),a.output)
