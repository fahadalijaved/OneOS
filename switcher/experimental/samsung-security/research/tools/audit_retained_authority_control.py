"""Pinned OneOS retained-authority control comparison. Static reads only."""
import argparse,gzip,hashlib,json,sys,tarfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
RAW=ROOT/'firmware/retained-authority-control';OUT=ROOT/'out/retained-authority-control'
COMMIT='1f2c2aa45ab8a7dc81384f6b67962d1e9cf7fefe'
DIFF=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84'
TAR=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
MEMBERS={'system/etc/init/hw/init.zygote64.rc':'55d71c63fcccb7b84664593f0bb1aebe7b54b07a04cea32b84427657b733debc','system/etc/init/init.sysfw.rc':'db9688ba524c09d891f3498efacb0b1a8d303409df510164de0197f76e0475d9'}
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def extract():
 manifest=DIFF/'samsung-manifest.jsonl.gz';assert sha(manifest)=='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
 with gzip.open(manifest,'rt')as f:rows={r['path']:r for line in f if(r:=json.loads(line))['path']in MEMBERS}
 assert set(rows)==set(MEMBERS)and TAR.stat().st_size==20434769920
 wanted=set(MEMBERS);proof=[]
 for name in list(wanted):
  path=RAW/'captured'/name
  if path.exists():assert sha(path)==MEMBERS[name];wanted.remove(name)
 if not wanted:return
 with tarfile.open(TAR,'r:')as tar:
  for member in tar:
   name=member.name.removeprefix('./')
   if name not in wanted:continue
   row=rows[name];assert member.isfile()and row['kind']=='file'and member.size==row['size']and member.size<16384 and row['sha256']==MEMBERS[name]
   data=tar.extractfile(member).read(member.size+1);assert len(data)==member.size and hashlib.sha256(data).hexdigest()==MEMBERS[name]
   path=RAW/'captured'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
   proof.append({'member':name,'headerOffset':member.offset,'dataOffset':member.offset_data,'bytes':len(data),'sha256':MEMBERS[name]});wanted.remove(name)
   if not wanted:break
 assert not wanted
 save(OUT/'acquisition.json',{'sourceTar':str(TAR),'tarBytes':TAR.stat().st_size,'priorStrictReceipt':str(DIFF/'report.json'),'priorStrictReceiptSha256':sha(DIFF/'report.json'),'wholeTarRehashed':False,'members':proof,'sourceExecuted':False})
def audit():
 g=ROOT/'inventory/authority-bootstrap-handoff.json';assert sha(g)=='0ac74af1bdeb1d2da3f0bc88e55b92ac8aaa6aad225a3d2a4178a21feaa36798'
 j=json.loads(g.read_text());assert j['oneosCommit']==COMMIT and len(j['inputs'])==15
 files={};inputs=[]
 for item in j['inputs']:
  p=ROOT/item['path'];assert sha(p)==item['sha256'];files[item['sourceRelativePath']]=p.read_text(encoding='utf8').splitlines();inputs.append(item)
 for name,pin in MEMBERS.items():
  p=RAW/'captured'/name;assert sha(p)==pin;files[name]=p.read_text().splitlines();inputs.append({'sourceRelativePath':name,'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':pin})
 sw='switcher/assets/oneos_switch.sh';prep='switcher/assets/guest_prepare.sh';start='switcher/assets/guest_start.sh';ret='switcher/assets/return_to_oneui.sh';facts=[];slices=[]
 def fact(id,file,a,b,text,need):
  block='\n'.join(files[file][a-1:b]);assert all(token in block for token in need),(id,need)
  facts.append({'id':id,'sourceRelativePath':file,'firstLine':a,'lastLine':b,'lineSliceSha256':hashlib.sha256(block.encode()).hexdigest(),'classification':'observed source commands/declarations; execution not observed','fact':text})
  slices.append({'id':id,'sourceRelativePath':file,'firstLine':a,'text':block})
 fact('init-view',sw,68,81,'Switch re-executes into init mount namespace when needed; no per-thread retained original-server view is prepared.',['nsenter','-t 1 -m'])
 fact('shell-cgroup',sw,281,286,'Move/oom writes concern the switch shell and inherited descendants; no source command moves or attests the pre-existing original server.',['echo $$ > /sys/fs/cgroup/cgroup.procs','/proc/$$/oom_score_adj'])
 fact('primary-secondary-stop',sw,971,979,'Primary zygote stopped; secondary is conditionally stopped. Skipping explicit server kill does not remove these service-control requests.',['setprop ctl.stop zygote','setprop ctl.stop zygote_secondary'])
 fact('explicit-kills',sw,993,999,'Name-selected app_process64, zygote_exec, zygotes and system_server are SIGKILLed; no retained-owner exception.',['pidof app_process64','pidof zygote64','pidof system_server'])
 fact('keeper',sw,1000,1012,'A recurring keeper stops running primary/secondary zygotes and selected host UI/audio services.',['nohup','ctl.stop zygote','ctl.stop zygote_secondary','sleep 0.2'])
 fact('watchdog-close',sw,1013,1028,'Writes magic-close values to watchdog/softdog nodes based on the stopped-server design. Retained FD/heartbeat ownership is not verified.',['printf V','/dev/watchdog','/dev/softdog'])
 fact('watchdog-property',sw,1043,1049,'Conditional property change requests Samsung softdog disable; not a drain or retention mechanism.',['persist.vendor.softdog off','SOFTDOG_V'])
 fact('prepare-window',sw,1086,1105,'Host-view preparation runs before guest mount namespace launch; failure/APEX drift invokes existing return.',['guest_prepare.sh','return_to_oneui.sh','host_apex.after'])
 fact('shared-properties',sw,1148,1149,'Calls guest property injection after preparation; a private mount namespace does not substitute for a property authority plan.',['guest_props.sh',' add '])
 fact('guest-mount-launch',sw,1417,1429,'New takeover process gets unshare -m, then recorded namespace/root device; this does not migrate the pre-existing server.',['unshare -m','guest_mntns','guest_rootdev'])
 fact('zygote-socket-pins',sw,1443,1464,'Bind-pins canonical zygote/usap socket paths; separate live host/guest zygote sockets and client routes are unassembled.',['for s in zygote usap_pool_primary','mount --bind','protect_zygote_sockets'])
 fact('first-server-helper',sw,2598,2609,'Sampler selects first global system_server and enters its mount view; two servers make this selector unsuitable as guest identity.',['pidof system_server','nsenter -t','oneos_genv.sh'])
 fact('guest-liveness',sw,3012,3021,'Any matching system_server or zygote64 resets guest death counter; retained host can mask guest failure.',['if pidof system_server','pidof zygote64','dead=0','return_to_oneui.sh'])
 fact('feeder',prep,186,237,'Generated recurring watchdog feeder attempts software-watchdog writes every two seconds; it does not attest retained server/watchdog ownership.',['oneos_wdog_feeder.sh','while true','printf V','sleep 2'])
 fact('host-bridges',prep,3240,3258,'Guest staged copies are bound over selected host /data paths before launch; existing server path lookup must retain correct original view.',['for pair in $BRIDGES','mount --bind','All host data trees bridged'])
 fact('bridge-list','switcher/assets/bridges.sh',1,15,'Bridge list includes user/user_de/app/dalvik-cache/profiles/media/resource-cache; it is not a blanket credentials-directory bind.',['BRIDGES=','user:user','user_de:user_de','misc/profiles','resource-cache'])
 fact('guest-pivot',start,12,48,'Guest makes its mount tree rprivate, pivots root and detaches old host root; existing original server is not the command target.',['mount --make-rprivate /','pivot_root','umount -l /postinstall'])
 fact('vold-mode',prep,1257,1281,'Guarded matched gvld branch preserves host vold names; unguarded fallback gives guest vold the global vold name.',['vold_patched','echo gvld','guest vold takes vold'])
 fact('vold-preflight',start,679,709,'gvld branch validates selected patched consumers and host vold; no actual live branch/native generation is observed here.',['VOLD_NAME=gvld','host_vold_lost','getprop init.svc_debug_pid.vold','Not starting the guest'])
 fact('native-name-baseline',ret,70,98,'Baseline checks only five named endpoints including vold/keystore2/installd/gatekeeper; no original Java authority or FP/Weaver/KeyMint operation generation.',['HOST_NAMES=','android.system.keystore2','android.service.gatekeeper','svcpid'])
 fact('return-name-kills',ret,215,229,'Return broad-kills keeper, zygote launcher, every matching system_server and zygote64.',['pkill -9 -f "system_server"','pkill -9 -x zygote64','ctl.stop zygote'])
 fact('return-namespace-kills',ret,256,285,'Return repeatedly kills by guest mount namespace or root device; moving retained authority into guest classification is not safe.',['GUEST_NS','GUEST_DEV','kill -9 "$pid"'])
 fact('return-mode',ret,418,440,'Default return mode is reboot; in-place is conditional, not a guaranteed retained-process resume.',['MODE=${ONEOS_RETURN_MODE:-reboot}','baseline','MODE=reboot'])
 fact('return-native-gate',ret,689,709,'Return compares named native endpoint PIDs, rejects guest survivors and explicitly rejects existing system_server/running zygote.',['now=$(svc_pid','One UI\'s vold restarted','! pidof system_server'])
 fact('return-properties-policy',ret,710,753,'Return restores guest/persistent properties and baseline SELinux before stock startup; retained server would already have observed the session.',['guest_props.sh remove','restore-persist','setenforce 1'])
 fact('return-stock-start',ret,876,907,'Return aborts FUSE, may restart zygote_next, restarts netd and starts stock zygotes; not an existing-server resume protocol.',['vdc volume abort_fuse','ctl.restart zygote_next','ctl.restart netd','ctl.start zygote'])
 fact('return-postcheck',ret,910,943,'Postcheck selects a system_server PID and waits user0/launcher stability, not credential/FP one-owner acceptance.',['ss=$(pidof system_server)','RUNNING_UNLOCKED','up + 30'])
 fact('original-zygote-command','system/etc/init/hw/init.zygote64.rc',1,21,'Captured init service command creates zygote with start-system-server; declared restart actions affect FUSE/audio/camera/media/network and task profiles.',['--start-system-server','onrestart exec_background','abort_fuse','onrestart restart netd','task_profiles','critical window='])
 fact('original-softdog-init','system/etc/init/init.sysfw.rc',1,6,'Captured Samsung init initializes/enables softdog with timeout100; node FD/current state is unobserved.',['softdog init','softdog settimeout 100'])
 fact('original-softdog-stop','system/etc/init/init.sysfw.rc',65,80,'Captured init reacts to stopped zygote and softdog-off properties by disabling softdog, with resetreason action.',['on property:init.svc.zygote=stopped','restart resetreason','softdog disable','on property:persist.vendor.softdog=off'])
 preserved={'inventory/method-review-upstream.json':'38864ad6669e9cdd340dd1ca200893ca1a0adea34537eab81f32fdc59b982648','docs/authority-boot-framework.md':'498c2fc83901a8a34d6902b7135d771f8d5e46f8a72d8a8192ff8a6472b742fc','docs/authority-vm-options.md':'6a844f305d30877f3bae7e1fb79d04db32f84c1b2a48a5c5ae0634fffc353d18','docs/authority-art-option-selection.md':'3598c91fbdc33fbc4098516572aee7a5409f44660248ba4a3d501ac69cd99be8','docs/security-authority-quiescence.md':'946604e673df1c989e552b2e915e5ddeb3977ac834f64abc558e37e09a8f9da3'}
 for path,pin in preserved.items():assert sha(ROOT/path)==pin
 save(RAW/'source-slices.json',slices)
 cuts=[{'before':'oneos_switch971','need':'A real existing-server/zygote/init process-group/parent and watchdog control contract; replace coherent stop/kill/keeper/socket/liveness selectors, not a rename or SIGSTOP.'},
       {'before':'oneos_switch1087 / guest_prepare3244','need':'Keep every real security worker and native dependency on the original Samsung source/state view; investigate separating guest-only preparation, not assumed migration of a multithreaded initialized server.'},
       {'before':'guest framework creation/publication','need':'One Samsung writer and native/session owner; guest producer suppression/local lifecycle adapters; canonical host security endpoints and separately routed guest framework endpoints; real UID/user/policy/physical display/input integration.'},
       {'before':'return_to_oneui193-229','need':'Actual guest drain and atomic retained-resume OR retired-and-reconstruct branch; adapt kill/absence/start controls coherently; never launch another stock LSS alongside retained original.'}]
 inv={'schema':'retained-authority-control-source/v1','status':'ARCHITECTURE_COMPARISON_ONLY; no pivot, retainer, process exemption or ready handoff implemented','selected':False,'sourceExecuted':False,'oemExecuted':False,'deviceInspected':False,'oneosCommit':COMMIT,'release':'v0.4.57','inputs':inputs,'sourceFacts':facts,'rawSlices':{'path':'firmware/retained-authority-control/source-slices.json','sha256':sha(RAW/'source-slices.json')},'acquisition':{'path':'out/retained-authority-control/acquisition.json','sha256':sha(OUT/'acquisition.json')},'proposedCoordinatedCuts':cuts,
      'unknownLiveFacts':['Original server PID/starttime/boot identity and exact parent/zygote relationship','init process-group/cgroup membership and stop/reap/zygote death-signal behavior for this captured build','Per-thread mount/root/source/state view, open files, native socket/Binder generations and watchdog FD/heartbeat owners','Actual installed guarded gvld profile/native surviving PIDs and fingerprint/Weaver/KeyMint sessions','Current global service publications/cached handles, physical display/input ownership, user/UID/package-policy integration','An admitted rooted control hook plus real worker/native drain and rollback/return contract'],
      'peerCritique':{'worker':'sol_power_backend','report':'docs/retained-authority-dependencies.md','scope':'Independent companion dependency card, not assumed frozen input','acceptedConstraints':['Preserve real AM/UMS/DPM/Supervision/StrongAuth handler-alarm/native callbacks; freezing whole server defeats service','Native reconnect paths/global service names and fresh path resolution remain active','Physical fingerprint/display/input and guest identity/policy integration remain required']},'preservedPins':[{'path':p,'sha256':v}for p,v in preserved.items()]}
 dest=ROOT/'inventory/retained-authority-control.json';save(dest,inv);save(OUT/'checks.json',{'pass':True,'immutableUpstreamInputs':15,'capturedRcFiles':2,'sourceCards':len(facts),'selected':False,'sourceExecuted':False})
 paths=[ROOT/'docs/retained-authority-control.md',dest,Path(__file__),OUT/'checks.json',OUT/'acquisition.json',RAW/'source-slices.json']
 save(OUT/'FROZEN-MANIFEST.json',{'selected':False,'sourceExecuted':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in paths]})
 print(json.dumps({'pass':True,'upstreamInputs':15,'capturedRcFiles':2,'sourceCards':len(facts),'selected':False,'sourceExecuted':False}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--extract',action='store_true');a=ap.parse_args()
 if a.extract:extract()
 else:audit()
