"""Prepare/read bounded nonsecret authority topology. Default is PC-only plan.

--collect is for a later root-coordinated existing trusted transport. No root,
connect/pair/server-start command, OEM service call or device mutation exists.
"""
import argparse,hashlib,json,re,runpy,socket,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;OUT=ROOT/'out/authority-topology-capture'
PROFILE=ROOT/'tools/collect_security_profile.py';PROFILE_SHA='1da6a75fa2301865bcf42a36c82bc99de2b7d37063696fcc21fce512a25d1fac'
ADB=PARENT/'out/toolchain/android-sdk/platform-tools/adb.exe';ADB_SHA='b4a6b455702684652cccf7b46258b29e653538904359a58fd4931cf3ef286b3f'
FP_RC=ROOT/'firmware/fingerprint/mounted/vendor/etc/init/vendor.samsung.hardware.biometrics.fingerprint-service.rc'
FP_SHA='a30e7ac20cb1d593437bc4c8eee4baa94783d73267bca1667ef197b65443244a'
PORT=5038;MAX_PIDS=32;MAX_THREADS=512;MAX_VIEWS=4;MAX_QUERIES=512;TOTAL_SECONDS=180;TOTAL_BYTES=8*1024*1024
ROLES={'init':('init',),'zygote':('zygote','zygote64','zygote_secondary','zygote_next','app_process64'),
       'system_server':('system_server',),'vold':('vold',),'keystore2':('keystore2',),
       'servicemanager':('servicemanager','hwservicemanager'),
       'fingerprint_hal':('vendor.samsung.hardware.biometrics.fingerprint-service',)}
PROPS=('ro.product.model','ro.build.version.sdk','ro.build.display.id','ro.build.fingerprint','ro.zygote',
       'init.svc.zygote','init.svc.zygote_secondary','init.svc.zygote_next','init.svc.vold','init.svc.keystore2',
       'init.svc.servicemanager','init.svc.vendor.fingerprint-default')
MOUNTS=('/','/system','/apex','/data','/data/system','/data/user','/data/user_de','/linkerconfig','/metadata')
VIEW_PATHS=('/system/framework/framework.jar','/system/framework/services.jar','/system/bin/vold',
            '/apex/com.android.art/lib64/libart.so','/linkerconfig/ld.config.txt','/data')
NUM=re.compile(r'[1-9][0-9]{0,6}\Z');NS=re.compile(r'mnt:\[[1-9][0-9]*\]\Z')
class TopologyError(ValueError):pass
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pins():
 for p,wanted in[(PROFILE,PROFILE_SHA),(ADB,ADB_SHA),(FP_RC,FP_SHA)]:
  if digest(p)!=wanted:raise TopologyError('Pinned PC/input source changed: '+p.name)
 if ADB.read_bytes()[6456317:6456317+5]!=b'-t ID':raise TopologyError('Pinned adb transport-id help anchor changed')
 return {'profileToolSha256':PROFILE_SHA,'adbSha256':ADB_SHA,'fingerprintRcSha256':FP_SHA}
def numeric(x):
 x=str(x)
 if not NUM.fullmatch(x):raise TopologyError('Invalid bounded numeric PID/TID')
 return x
def command(kind,*,name=None,pid=None,tid=None,key=None,path=None):
 """Only fixed operation templates; no arbitrary command/path/serial input."""
 if kind=='discover':
  if name not in {n for names in ROLES.values()for n in names}:raise TopologyError('Unknown owner name')
  return "if p=$(pidof '"+name+"'); then printf '%s\\n' \"$p\"; else r=$?; if [ \"$r\" = 1 ]; then printf '__NO_MATCH__\\n'; else exit \"$r\"; fi; fi",4096
 if kind=='property':
  if key not in PROPS:raise TopologyError('Unknown public property')
  return 'getprop '+key,1024
 if kind=='boot_id':return 'cat /proc/sys/kernel/random/boot_id',128
 if kind=='identity':return 'id -u',128
 p=numeric(pid);base='/proc/'+p
 if kind=='stat':return 'cat '+base+'/stat',4096
 if kind=='status':return "awk '/^(Name|Tgid|Pid|PPid|Uid|Gid|Threads):/ {print}' "+base+'/status',4096
 if kind=='exe':return 'readlink '+base+'/exe',1024
 if kind=='threads':
  # Numeric /proc task glob only, explicit cap. No per-thread name/environ/FD/stack.
  return "n=0; for t in "+base+"/task/[0-9]*; do [ -d \"$t\" ] || continue; n=$((n+1)); if [ \"$n\" -gt "+str(MAX_THREADS)+" ]; then printf '__THREAD_CAP__\\n'; break; fi; a=$(readlink \"$t/ns/mnt\" 2>/dev/null); ar=$?; b=$(stat -L -c '%d:%i' \"$t/root\" 2>/dev/null); br=$?; printf '%s|%s|%s|%s|%s\\n' \"${t##*/}\" \"$ar\" \"$a\" \"$br\" \"$b\"; done",131072
 t=numeric(tid);base+='/task/'+t
 if kind=='task_stat':return 'cat '+base+'/stat',4096
 if kind=='cgroup':return 'cat '+base+'/cgroup',8192
 if kind=='namespace':return 'readlink '+base+'/ns/mnt',128
 if kind=='mounts':
  condition=' || '.join('$5 == "'+m+'"'for m in MOUNTS)
  # Deliberately omit mount options, filesystem sources and superblock options.
  return "awk '"+condition+" {printf \"%s %s %s %s %s\",$1,$2,$3,$4,$5; for(i=7;i<=NF && $i!=\"-\";i++) if($i ~ /^(shared|master|propagate_from):[0-9]+$/ || $i==\"unbindable\") printf \" %s\",$i; printf \"\\n\"}' "+base+'/mountinfo',65536
 if kind=='view':
  if path not in VIEW_PATHS:raise TopologyError('Unknown fixed OS metadata path')
  return "stat -L -c '%d:%i:%s' "+base+'/root'+path,128
 raise TopologyError('Unknown read-only operation')
def parse_pids(data):
 text=data.decode('ascii','strict').strip()
 if text=='__NO_MATCH__':return []
 values=text.split()
 if not values or len(values)>MAX_PIDS or len(set(values))!=len(values):raise TopologyError('Malformed/duplicate/excess PID list')
 return sorted([int(numeric(v))for v in values])
def parse_stat(data,pid):
 text=data.decode('utf8','strict').strip();m=re.fullmatch(r'([1-9][0-9]{0,6}) \(([^\r\n]*)\) ([A-Za-z]) (.*)',text)
 if not m or int(m[1])!=int(pid):raise TopologyError('PID/stat identity mismatch')
 fields=m[4].split()
 if len(fields)<19 or not fields[0].isdigit()or not fields[18].isdigit():raise TopologyError('Malformed stat parent/starttime')
 return {'pid':int(pid),'comm':m[2],'state':m[3],'ppid':int(fields[0]),'starttimeTicks':int(fields[18])}
def parse_status(data,pid):
 rows={}
 for line in data.decode('utf8','strict').splitlines():
  if ':'not in line:raise TopologyError('Malformed status')
  key,value=line.split(':',1)
  if key not in('Name','Tgid','Pid','PPid','Uid','Gid','Threads')or key in rows:raise TopologyError('Unexpected/duplicate status key')
  rows[key]=value.strip()
 if set(rows)!=set(('Name','Tgid','Pid','PPid','Uid','Gid','Threads')):raise TopologyError('Incomplete status')
 for key,count in[('Uid',4),('Gid',4),('Tgid',1),('Pid',1),('PPid',1),('Threads',1)]:
  values=rows[key].split()
  if len(values)!=count or any(not re.fullmatch(r'[0-9]{1,10}',v)for v in values):raise TopologyError('Invalid status scalar')
  rows[key]=[int(v)for v in values]if count==4 else int(values[0])
 if rows['Pid']!=int(pid)or rows['Tgid']!=int(pid):raise TopologyError('Status PID/TGID mismatch')
 return rows
def parse_threads(data):
 rows=[];capped=False;seen=set()
 for line in data.decode('ascii','strict').splitlines():
  if line=='__THREAD_CAP__':capped=True;continue
  if capped:raise TopologyError('Rows after thread cap')
  parts=line.split('|')
  if len(parts)!=5:raise TopologyError('Malformed thread row')
  tid,nsrc,ns,rootrc,root=parts;numeric(tid)
  if tid in seen or len(rows)>=MAX_THREADS:raise TopologyError('Duplicate/excess thread')
  seen.add(tid)
  if not nsrc.isdigit()or not rootrc.isdigit()or int(nsrc)>255 or int(rootrc)>255:raise TopologyError('Invalid thread read exit')
  if int(nsrc)==0 and not NS.fullmatch(ns):raise TopologyError('Invalid mount namespace')
  if int(rootrc)==0 and not re.fullmatch(r'[0-9]+:[0-9]+',root):raise TopologyError('Invalid root metadata')
  rows.append({'tid':int(tid),'namespace':ns if int(nsrc)==0 else None,'namespaceReadExit':int(nsrc),'rootDeviceInode':root if int(rootrc)==0 else None,'rootReadExit':int(rootrc)})
 if not rows:raise TopologyError('No readable task rows; exit/denial unresolved')
 return {'rows':rows,'capped':capped,'completeEnumerationClaim':False,'enumerationLimit':'Task glob/reads race with creation, exit and view changes; uncapped does not mean atomic complete state','readErrors':any(r['namespaceReadExit']or r['rootReadExit']for r in rows),'distinctNamespaces':sorted({r['namespace']for r in rows if r['namespace']})}
def select_views(threads,pid):
 rows=threads['rows'];chosen=[]
 main=next((r for r in rows if r['tid']==pid),None)
 if main:chosen.append(main['tid'])
 groups=sorted({(r['namespace'],r['rootDeviceInode'])for r in rows},key=str)
 for group in groups:
  if not any(r['tid']in chosen and(r['namespace'],r['rootDeviceInode'])==group for r in rows):chosen.append(min(r['tid']for r in rows if(r['namespace'],r['rootDeviceInode'])==group))
 return chosen[:MAX_VIEWS],len(chosen)>MAX_VIEWS
def parse_value(kind,data):
 text=data.decode('utf8','strict').strip()
 if kind=='namespace':
  if not NS.fullmatch(text):raise TopologyError('Invalid namespace value')
 elif kind=='view':
  if not re.fullmatch(r'[0-9]+:[0-9]+:[0-9]+',text):raise TopologyError('Invalid OS stat metadata')
 elif kind=='cgroup':
  if not text or any(not re.fullmatch(r'[0-9]+:[A-Za-z0-9_,=.-]*:/[^\x00-\x1f]*',line)for line in text.splitlines()):raise TopologyError('Invalid cgroup records')
 elif kind=='mounts':
  if not text:raise TopologyError('No selected mount rows')
  for line in text.splitlines():
   fields=line.split()
   if len(fields)<5 or fields[4]not in MOUNTS or not fields[0].isdigit()or not fields[1].isdigit()or not re.fullmatch(r'[0-9]+:[0-9]+',fields[2])or not fields[3].startswith('/')or any(not re.fullmatch(r'(shared|master|propagate_from):[0-9]+|unbindable',f)for f in fields[5:]):raise TopologyError('Unexpected mount projection')
 elif kind=='boot_id':
  if not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',text):raise TopologyError('Invalid boot session ID')
 elif kind=='identity':
  if not re.fullmatch(r'[0-9]{1,10}',text):raise TopologyError('Invalid transport UID')
 elif kind=='property':
  if not text or len(text)>512 or any(ord(c)<32 for c in text):raise TopologyError('Missing/invalid public property')
 elif kind=='exe':
  if not text.startswith('/')or len(text)>768 or any(ord(c)<32 for c in text):raise TopologyError('Missing/invalid executable link')
 else:raise TopologyError('Unknown parser')
 return text.splitlines()if kind in('mounts','cgroup')else text
def save(p,obj):
 if not p.resolve().is_relative_to(ROOT.resolve()):raise TopologyError('PC output escaped nested repository')
 content=json.dumps(obj,indent=2)+'\n'
 if len(content.encode('utf8'))>32*1024*1024:raise TopologyError('PC artifact exceeds32MiB bound')
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf8')
def profile_module():
 if digest(PROFILE)!=PROFILE_SHA:raise TopologyError('Profile module drift')
 return runpy.run_path(str(PROFILE))
class Reader:
 def __init__(self,transport,profile):
  if not re.fullmatch(r'[1-9][0-9]{0,5}',str(transport)):raise TopologyError('Explicit existing numeric transport ID required')
  self.transport=str(transport);self.profile=profile;self.deadline=time.monotonic()+TOTAL_SECONDS;self.count=0;self.bytes=0;self.log=[]
 def run(self,kind,**kw):
  cmd,cap=command(kind,**kw);remaining=self.deadline-time.monotonic()
  if remaining<=0 or self.count>=MAX_QUERIES or self.bytes>=TOTAL_BYTES:raise TopologyError('Global collection budget reached')
  self.count+=1;entry={'kind':kind,**kw,'limit':cap};self.log.append(entry)
  try:
   data=self.profile['bounded_command']([str(ADB),'-P',str(PORT),'-t',self.transport,'shell',cmd],min(cap,TOTAL_BYTES-self.bytes),timeout=min(20,remaining))
   self.bytes+=len(data);entry['status']='returned';entry['bytes']=len(data);return data
  except(OSError,ValueError)as e:
   charge=min(cap,TOTAL_BYTES-self.bytes);self.bytes+=charge;entry['status']='unresolved';entry['error']=str(e);entry['conservativeByteCharge']=charge;raise
 def get(self,kind,**kw):
  try:
   data=self.run(kind,**kw)
   if kind=='discover':value=parse_pids(data)
   elif kind=='stat':value=parse_stat(data,kw['pid'])
   elif kind=='task_stat':value=parse_stat(data,kw['tid'])
   elif kind=='status':value=parse_status(data,kw['pid'])
   elif kind=='threads':value=parse_threads(data)
   else:value=parse_value(kind,data)
   if kind=='discover'and not value:return {'status':'no_match_returned','value':[],'limit':'No pidof match returned; not proof that an owner is absent or readable'}
   return {'status':'observed','value':value}
  except(OSError,ValueError)as e:return {'status':'unresolved','reason':str(e)}
def collect(transport,label):
 if not re.fullmatch(r'[1-9][0-9]{0,5}',str(transport)):raise TopologyError('Explicit existing numeric transport ID required')
 p=pins();module=profile_module()
 # Existing-server-only precheck, as in existing profile tool. The normal adb
 # client can still auto-start after a server-exit race; this is not atomic.
 with socket.create_connection(('127.0.0.1',PORT),timeout=2):pass
 data=module['bounded_command']([str(ADB),'-P',str(PORT),'-t',str(transport),'get-state'],128,timeout=5)
 if data.strip()!=b'device':raise TopologyError('Existing transport not in device state')
 reader=Reader(transport,module);report={'schema':'authority-topology-observation/v1','label':label,'startedUtc':datetime.now(timezone.utc).isoformat(),'port':PORT,'sourcePins':p,'deviceMutation':False,'runtimeAccepted':False,'profileAdmitted':False,'atomicSnapshot':False,'parentDeathSignalObserved':False,'survivalOrConcurrencyProved':False,'facts':{},'roles':{},'processes':{}}
 report['facts']['bootBefore']=reader.get('boot_id');report['facts']['transportUid']=reader.get('identity')
 report['facts']['properties']={k:reader.get('property',key=k)for k in PROPS}
 props={k:v['value']for k,v in report['facts']['properties'].items()if v['status']=='observed'}
 report['profileAssessment']=module['assess_profile'](props,inspection=True)
 pids={1};before={}
 for role,names in ROLES.items():
  found={name:reader.get('discover',name=name)for name in names};before[role]=found
  for v in found.values():
   if v['status']=='observed':pids.update(v['value'])
  report['roles'][role]={'candidateLookups':found,'classification':'comm/name candidates only; not authenticated Binder/native endpoint owner'}
 if len(pids)>MAX_PIDS:report['processBudgetError']='All returned candidates recorded, but total exceeds bound; none inspected'
 else:
  for pid in sorted(pids):
   row={'statBefore':reader.get('stat',pid=pid),'status':reader.get('status',pid=pid),'exe':reader.get('exe',pid=pid),'threadsBefore':reader.get('threads',pid=pid),'selectedThreadViews':{}}
   if row['threadsBefore']['status']=='observed':
    tids,capped=select_views(row['threadsBefore']['value'],pid);row['selectedViewCapReached']=capped
    for tid in tids:
     view={'taskStatBefore':reader.get('task_stat',pid=pid,tid=tid),'namespaceBefore':reader.get('namespace',pid=pid,tid=tid),'cgroup':reader.get('cgroup',pid=pid,tid=tid),'selectedMounts':reader.get('mounts',pid=pid,tid=tid),'osMetadata':{path:reader.get('view',pid=pid,tid=tid,path=path)for path in VIEW_PATHS},'namespaceAfter':reader.get('namespace',pid=pid,tid=tid),'taskStatAfter':reader.get('task_stat',pid=pid,tid=tid)}
     a=view['taskStatBefore'];b=view['taskStatAfter'];n=view['namespaceBefore'];m=view['namespaceAfter']
     view['taskIdentityAndNamespaceMatchAtEndpoints']=a['status']==b['status']==n['status']==m['status']=='observed'and a['value']['pid']==b['value']['pid']and a['value']['starttimeTicks']==b['value']['starttimeTicks']and n['value']==m['value']
     view['coherentViewAdmitted']=False;row['selectedThreadViews'][str(tid)]=view
   row['threadsAfter']=reader.get('threads',pid=pid);row['statAfter']=reader.get('stat',pid=pid)
   a=row['statBefore'];b=row['statAfter'];row['identityStableAtEndpoints']=a['status']==b['status']=='observed'and all(a['value'][k]==b['value'][k]for k in('pid','comm','ppid','starttimeTicks'))
   row['threadSnapshotsEqual']=row['threadsBefore']==row['threadsAfter'];row['classification']='bounded sampled facts only; unresolved/races retained; no owner admission'
   report['processes'][str(pid)]=row
 report['roleLookupsAfter']={role:{name:reader.get('discover',name=name)for name in names}for role,names in ROLES.items()}
 report['rawRoleResultsEqual']=before==report['roleLookupsAfter'];report['facts']['bootAfter']=reader.get('boot_id');report['bootSnapshotsEqual']=report['facts']['bootBefore']['status']==report['facts']['bootAfter']['status']=='observed'and report['facts']['bootBefore']['value']==report['facts']['bootAfter']['value']
 report['queries']=reader.log;report['completedUtc']=datetime.now(timezone.utc).isoformat();report['sourcePinsAfter']=pins();assert report['sourcePinsAfter']==p
 report['incompleteOrMovingSamples']=bool(report.get('processBudgetError'))or any(not row['identityStableAtEndpoints']or not row['threadSnapshotsEqual']or row.get('selectedViewCapReached',False)or any(not v['taskIdentityAndNamespaceMatchAtEndpoints']for v in row['selectedThreadViews'].values())or any(row[k]['status']=='observed'and(row[k]['value']['capped']or row[k]['value']['readErrors'])for k in('threadsBefore','threadsAfter'))for row in report['processes'].values())
 work=OUT/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex);save(work/'observation.json',report)
 def unresolved(value):
  if isinstance(value,dict):return int(value.get('status')=='unresolved')+sum(unresolved(v)for v in value.values())
  if isinstance(value,list):return sum(unresolved(v)for v in value)
  return 0
 count=unresolved(report);print(json.dumps({'observation':str((work/'observation.json').relative_to(ROOT)),'unresolvedResults':count,'profileAdmitted':False,'runtimeAccepted':False,'snapshotOnly':True}))
 return 2 if count or report['incompleteOrMovingSamples']or not report['bootSnapshotsEqual']or not report['rawRoleResultsEqual']else 0
def plan():
 source=pins()
 ops={'discover':{'names':ROLES},'property':{'keys':PROPS},'boot_id':{},'identity':{},'stat':{},'status':{},'exe':{},'threads':{},'task_stat':{},'cgroup':{},'namespace':{},'mounts':{'mountpoints':MOUNTS},'view':{'metadataOnlyPaths':VIEW_PATHS}}
 return {'schema':'authority-topology-prepared-plan/v1','status':'PC_ONLY_PREPARATION; no ADB invocation or socket probe performed by plan/self-test','sourcePins':source,'port':PORT,'requiresExplicitExistingTransportId':True,'collectsSerialOrDevicesList':False,'operations':ops,'remoteCommandPrograms':['pidof','getprop','cat','id','readlink','stat','awk','printf','shell fixed conditionals/for/arithmetic'],
         'limits':{'distinctPids':MAX_PIDS,'threadsPerPid':MAX_THREADS,'selectedThreadViewsPerPid':MAX_VIEWS,'queries':MAX_QUERIES,'collectionSeconds':TOTAL_SECONDS,'perQuerySeconds':20,'successfulAndConservativelyChargedFailureBytes':TOTAL_BYTES,'largestQueryBytes':131072},
         'outputs':'repo-local out/authority-topology-capture/<timestamp-uuid>/observation.json only','runtimeAccepted':False,'profileAdmitted':False,'parentDeathSignalObservableHere':False,'noClaims':['No PID/name/native endpoint authority authentication','No atomic snapshot, survival, one-writer, concurrency or drain proof','No loaded-code or credential/native-state read','No actual inherited parent-death signal observation','No complete selected-view proof for every thread; all capped/failed/changed facts remain unresolved'],
         'transportFlagEvidence':{'binarySha256':ADB_SHA,'helpStringOffset':6456317,'literal':'-t ID                    use device with given transport id','scope':'Static pinned PC binary help-string evidence; adb not executed'},
         'transportLimit':'Same existing profile-tool localhost5038 precheck/normal adb client behavior; precheck cannot exclude server-exit/autostart race. No connect/pair/root/start/reset command.',
         'oneosSourceContext':'Retained control card pins v0.4.57. Reused legacy profile module contributes bounded child I/O and inspection-only property assessment; its older OneOS source-pins/list/serial/collection flow is not executed.'}
def self_test():
 checks=[]
 def yes(name,condition):
  if not condition:raise AssertionError(name)
  checks.append(name)
 def refuses(name,fn):
  try:fn()
  except(ValueError,UnicodeError):checks.append(name);return
  raise AssertionError(name+' accepted')
 yes('all matching PIDs retained and sorted',parse_pids(b'99 2 7\n')==[2,7,99]);yes('no match is empty without authority assertion',parse_pids(b'__NO_MATCH__\n')==[])
 for name,data in [('duplicate PID',b'1 1'),('command PID injection',b'2;id'),('negative PID',b'-1'),('oversized PID count',' '.join(str(i)for i in range(1,34)).encode()),('invalid encoding',b'\xff')]:refuses(name,lambda data=data:parse_pids(data))
 stat=b'5 (system_server) S '+' '.join(str(n)for n in range(4,53)).encode();v=parse_stat(stat,5)
 yes('correct stat PPid and field22 starttime',v['ppid']==4 and v['starttimeTicks']==22)
 refuses('PID reuse/stat mismatch',lambda:parse_stat(stat,6));refuses('short stat',lambda:parse_stat(b'5 (x) S 1',5))
 status=b'Name:\tsystem_server\nTgid:\t5\nPid:\t5\nPPid:\t4\nUid:\t1000 1000 1000 1000\nGid:\t1000 1000 1000 1000\nThreads:\t8\n'
 yes('real/effective/saved/fs uid retained',parse_status(status,5)['Uid']==[1000]*4)
 refuses('extra private status field',lambda:parse_status(status+b'Private: data\n',5));refuses('status pid mismatch',lambda:parse_status(status,4))
 tr=parse_threads(b'5|0|mnt:[1]|0|1:2\n8|0|mnt:[2]|0|1:3\n9|1||1|\n')
 yes('thread namespace differences explicit',tr['distinctNamespaces']==['mnt:[1]','mnt:[2]']);yes('thread read error explicit',tr['readErrors']);chosen,_=select_views(tr,5);yes('main plus distinct namespace/root representatives',chosen[0]==5 and set(chosen)=={5,8,9})
 same_ns=parse_threads(b'5|0|mnt:[1]|0|1:2\n8|0|mnt:[1]|0|1:3\n');yes('same namespace different roots not conflated',select_views(same_ns,5)==([5,8],False))
 yes('thread cap explicit',parse_threads(b'5|0|mnt:[1]|0|1:2\n__THREAD_CAP__\n')['capped'])
 refuses('duplicate TID',lambda:parse_threads(b'5|0|mnt:[1]|0|1:2\n5|0|mnt:[1]|0|1:2\n'));refuses('bad namespace grammar',lambda:parse_threads(b'5|0|garbage|0|1:2\n'));refuses('no task rows not success',lambda:parse_threads(b''))
 for path in('/data/system/locksettings.db','/data/system/users/0/fpdata','/proc/1/environ','/system/../data/secret'):
  refuses('private/arbitrary path refused '+path,lambda path=path:command('view',pid=1,tid=1,path=path))
 for kind in('kill','mount','su','dumpsys','service','logcat','shell'):
  refuses('unlisted command refused '+kind,lambda kind=kind:command(kind,pid=1,tid=1))
 refuses('arbitrary property refused',lambda:command('property',key='ro.serialno'));refuses('arbitrary name refused',lambda:command('discover',name='com.android.settings'));refuses('numeric injection refused',lambda:command('stat',pid='1;id'))
 refuses('cgroup malformed',lambda:parse_value('cgroup',b'bad'));yes('cgroup controllers retained',parse_value('cgroup',b'0::/system\n')==['0::/system'])
 refuses('private mountpoint not admitted',lambda:parse_value('mounts',b'1 2 0:1 / /data/user/0/private'))
 yes('selected mount projection permits propagation only',parse_value('mounts',b'1 2 0:1 / /data shared:9 master:2')==['1 2 0:1 / /data shared:9 master:2'])
 refuses('filesystem source/options not retained',lambda:parse_value('mounts',b'1 2 0:1 / /data rw - ext4 /dev/x secret=bad'))
 calls=[];module={'bounded_command':lambda argv,limit,timeout:(calls.append((argv,limit,timeout))or b'__NO_MATCH__\n')}
 r=Reader(7,module);q=r.get('discover',name='vold');yes('no match recorded explicitly',q['status']=='no_match_returned')
 yes('fixed5038/transportid shell only',calls[0][0][1:6]==['-P','5038','-t','7','shell']);yes('no serial selector/devices',not any(x in calls[0][0]for x in('-s','devices','connect','root')))
 r.count=MAX_QUERIES;yes('query cap unresolved not success',r.get('discover',name='vold')['status']=='unresolved');yes('budget cap sends no extra command',len(calls)==1)
 def failed(*a,**kw):raise ValueError('fixture capped/failed output')
 r=Reader(7,{'bounded_command':failed});r.bytes=TOTAL_BYTES-128;yes('failed read remains unresolved',r.get('discover',name='vold')['status']=='unresolved');yes('failed read conservatively respects remaining byte budget',r.bytes==TOTAL_BYTES and r.log[-1]['conservativeByteCharge']==128)
 refuses('invalid transport numeric refused',lambda:Reader('7;id',module))
 many=parse_threads('\n'.join(str(n)+'|0|mnt:['+str(n)+']|0|1:'+str(n)for n in range(5,11)).encode());chosen,capped=select_views(many,5);yes('view cap explicit and main retained',len(chosen)==MAX_VIEWS and chosen[0]==5 and capped)
 # Guard actual phone/network entry points during the complete static plan path.
 old=socket.create_connection
 def forbidden(*a,**kw):raise AssertionError('Static path opened network')
 socket.create_connection=forbidden
 try:
  p=plan();yes('default plan is unselected and serial-free',not p['runtimeAccepted']and not p['collectsSerialOrDevicesList'])
  assess=profile_module()['assess_profile'];yes('actual reused mismatch assessment never admits',not assess({},inspection=True)['profileAdmitted'])
  assessed=assess({'ro.product.model':'SM-S948U1','ro.build.version.sdk':'37','ro.build.display.id':'CP2A.260605.016.S948U1UES4BZIG','ro.build.fingerprint':'authored/model'},inspection=True);yes('actual reused matching subset still never admits',assessed['recordedPropertySubsetMatches']and not assessed['profileAdmitted'])
 finally:socket.create_connection=old
 save(OUT/'plan.json',p);save(OUT/'static-checks.json',{'pass':True,'checks':checks,'count':len(checks),'adbInvoked':False,'networkProbed':False,'deviceInspected':False,'modelOnly':True})
 inventory={'schema':'authority-topology-capture-preparation/v1','status':'STAGED_PC_ONLY; not run against a phone','tool':'tools/collect_authority_topology.py','toolSha256':digest(Path(__file__)),'plan':p,'staticChecks':{'path':'out/authority-topology-capture/static-checks.json','sha256':digest(OUT/'static-checks.json'),'count':len(checks)},'actualObservation':None,'adbInvoked':False,'deviceInspected':False,'runtimeAccepted':False}
 save(ROOT/'inventory/authority-topology-capture.json',inventory)
 paths=[Path(__file__),ROOT/'docs/authority-topology-capture.md',ROOT/'inventory/authority-topology-capture.json',OUT/'plan.json',OUT/'static-checks.json']
 save(OUT/'FROZEN-MANIFEST.json',{'adbInvoked':False,'deviceInspected':False,'runtimeAccepted':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p)}for p in paths]})
 print(json.dumps({'pass':True,'staticChecks':len(checks),'adbInvoked':False,'deviceInspected':False}))
def main():
 ap=argparse.ArgumentParser(description=__doc__);g=ap.add_mutually_exclusive_group();g.add_argument('--collect',action='store_true');g.add_argument('--self-test',action='store_true');g.add_argument('--plan',action='store_true');ap.add_argument('--transport-id',type=int);ap.add_argument('--label',choices=('host_before','oneos','host_return'),default='host_before');a=ap.parse_args()
 if a.collect:
  if a.transport_id is None:ap.error('--collect requires an existing trusted numeric --transport-id')
  try:raise SystemExit(collect(a.transport_id,a.label))
  except(OSError,ValueError)as e:
   work=OUT/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex)
   save(work/'failure.json',{'status':'unresolved','reason':str(e),'port':PORT,'profileAdmitted':False,'runtimeAccepted':False,'noObservationCompleted':True})
   print(json.dumps({'failure':str((work/'failure.json').relative_to(ROOT)),'status':'unresolved'}));raise SystemExit(2)
 elif a.transport_id is not None:ap.error('--transport-id requires --collect')
 elif a.self_test:self_test()
 else:
  save(OUT/'plan.json',plan());print(json.dumps({'plan':'out/authority-topology-capture/plan.json','adbInvoked':False,'deviceInspected':False}))
if __name__=='__main__':main()
