"""Finite original-vold bootstrap evidence; no device, state or OEM execution."""
import argparse,hashlib,json,lzma,re,runpy,struct,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'out/authority-bootstrap-storage'
RAW=ROOT/'firmware/authority-bootstrap-storage'
VOLD=ROOT/'firmware/storage-keys/system/bin/vold'
VOLD_SHA='0b00f386f2056aebd3e0824f67cba35614fdc6e2d2b11414ae34d5a2c33bebb7'
WHEEL=ROOT.parent/'out/toolchain/ghidra-12.1.4/ghidra_12.1.4_PUBLIC/Ghidra/Debug/Debugger-agent-dbgeng/pypkg/dist/capstone-5.0.6-py3-none-win_amd64.whl'
WHEEL_SHA='761c3deae00b22ac697081cdae1383bb90659dd0d79387a09cf5bdbb22b17064'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def relr_targets(entries):
 cursor=None;targets=[]
 for entry in entries:
  if entry&1:
   if cursor is None:raise ValueError('RELR bitmap before direct address')
   targets.extend(cursor+8*n for n in range(63) if entry&(1<<(n+1)))
   cursor+=63*8
  else:
   if entry%8:raise ValueError('RELR address alignment')
   targets.append(entry);cursor=entry+8
  if len(targets)>1000000:raise ValueError('RELR count bound')
 return targets
def native_probe():
 if sha(VOLD)!=VOLD_SHA or sha(WHEEL)!=WHEEL_SHA:raise ValueError('Frozen input/tool differs')
 WORK.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
 package=WORK/'static-disassembler';package.mkdir(exist_ok=True)
 with zipfile.ZipFile(WHEEL) as archive:
  for item in archive.infolist():
   if not item.filename.startswith('capstone/') or item.is_dir():continue
   target=package/item.filename
   if not target.resolve().is_relative_to(package.resolve()) or item.file_size>32*1024*1024:raise ValueError('PC disassembler bounds')
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(item))
 sys.path.insert(0,str(package));import capstone
 elf=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf']
 data=VOLD.read_bytes();parsed=elf(data);debug=next(s for s in parsed['sections'] if s['name']=='.gnu_debugdata')
 mini=lzma.decompress(data[debug['offset']:debug['offset']+debug['bytes']])
 if len(mini)>16*1024*1024:raise ValueError('Mini-debug bound')
 mini_path=RAW/'vold.debug.elf';mini_path.write_bytes(mini)
 symbols=[s for s in [*elf(mini)['dynamicSymbols'],*parsed['dynamicSymbols']] if s['sectionIndex']!=0]
 def offset(address,length):
  matches=[s for s in parsed['sections'] if s['type']!=8 and s['address']<=address and address+length<=s['address']+s['bytes']]
  if len(matches)!=1:raise ValueError('File-backed range ambiguity')
  return matches[0]['offset']+address-matches[0]['address']
 dis=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
 def function(s):
  if not 0<s['size']<=32768:raise ValueError('Selected native function bound')
  off=offset(s['value'],s['size']);raw=data[off:off+s['size']]
  ins=[{'address':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str} for i in dis.disasm(raw,s['value'])]
  if sum(len(bytes.fromhex(i['bytes'])) for i in ins)!=len(raw):raise ValueError('Incomplete ARM64 disassembly')
  return {'symbol':s['name'],'address':s['value'],'fileOffset':off,'bytes':s['size'],'sha256':hashlib.sha256(raw).hexdigest(),'instructions':ins}
 wanted=['VoldNativeService16getUnlockedUsers','VoldNativeService22setCeStorageProtection','VoldNativeService15unlockCeStorage',
         '_Z26fscrypt_get_unlocked_usersv','_ZN7android4vold14CheckUidOrRootEj','_Z12IsFbeEnabledv',
         '_Z25fscrypt_unlock_ce_storage','_Z29fscrypt_set_ce_key_protection','_Z23fscrypt_lock_ce_storage',
         '_ZN7android2os6BnVold10onTransact','VoldNativeService5startEv']
 selected=[s for s in symbols if s['type']==2 and any(n in s['name'] for n in wanted)]
 if len(selected)!=11:raise ValueError('Eleven bounded native wrapper/status/policy/dispatch functions required')
 functions=[function(s) for s in selected]
 by_address={s['value']:s for s in symbols if s['type']==2}
 def resolve(target):
  if target in by_address:return {'symbol':by_address[target]['name'],'resolution':'mini-debug/defined'}
  plt=next(s for s in parsed['sections'] if s['name']=='.plt')
  if not plt['address']<=target<plt['address']+plt['bytes']:return {'symbol':None,'resolution':'unresolved'}
  off=offset(target,24);stub=list(dis.disasm(data[off:off+24],target))
  adrp=next(i for i in stub if i.mnemonic=='adrp' and i.op_str.startswith('x16,'))
  load=next(i for i in stub if i.mnemonic=='ldr' and i.op_str.startswith('x17, [x16'))
  if not any(i.mnemonic=='br' and i.op_str=='x17' for i in stub):raise ValueError('Unproved PLT branch')
  disp=re.search(r'#(0x[0-9a-f]+|\d+)',load.op_str);got=int(adrp.op_str.split('#')[1],16)+(int(disp.group(1),0) if disp else 0)
  reloc=[r for r in parsed['rela'] if r['type']==1026 and r['target']==got]
  if len(reloc)!=1:raise ValueError('PLT/relocation disagreement')
  return {'symbol':parsed['dynamicSymbols'][reloc[0]['symbolIndex']]['name'],'resolution':'PLT instructions + JUMP_SLOT','gotAddress':got}
 calls=[]
 for f in functions:
  for ins in f['instructions']:
   if ins['mnemonic']=='bl':
    target=int(ins['operands'].lstrip('#'),16)
    calls.append({'caller':f['symbol'],'pc':ins['address'],'target':target,**resolve(target)})
 relr=next(s for s in parsed['sections'] if s['name']=='.relr.dyn')
 if relr['bytes']%8:raise ValueError('RELR table alignment')
 relrset=set(relr_targets([struct.unpack_from('<Q',data,p)[0] for p in range(relr['offset'],relr['offset']+relr['bytes'],8)]))
 # Captured start's GOT load -> three installed NativeService address points.
 got=0x1609d8
 if got not in relrset:raise ValueError('NativeService vtable GOT lacks relative relocation')
 vtable=struct.unpack_from('<Q',data,offset(got,8))[0];address_point=vtable+0x18
 start=next(f for f in functions if 'VoldNativeService5startEv' in f['symbol']);startpc={i['address']:i for i in start['instructions']}
 for pc,op,operand in [(0x97d7c,'adrp','x8, #0x160000'),(0x97d88,'ldr','x8, [x8, #0x9d8]'),(0x97d8c,'add','x9, x8, #0x18'),(0x97d98,'str','x9, [x20]')]:
  if (startpc[pc]['mnemonic'],startpc[pc]['operands'])!=(op,operand):raise ValueError('NativeService installed vtable provenance differs')
 routes=[];dispatcher=next(f for f in functions if 'BnVold10onTransact' in f['symbol'])
 bypc={i['address']:i for i in dispatcher['instructions']}
 for pc,op,args in [(0x107e5c,'sub','w8, w1, #1'),(0x107e78,'adr','x9, #0x2947c'),(0x107e7c,'adr','x10, #0x107e8c'),(0x107e80,'ldrh','w11, [x9, x8, lsl #1]'),(0x107e84,'add','x10, x10, x11, lsl #2')]:
  if (bypc[pc]['mnemonic'],bypc[pc]['operands'])!=(op,args):raise ValueError('Native dispatch table interpretation differs')
 for code,entry,slot,tail,slotpc,callpc,fragment in [(46,0x10a7f4,0x188,0x10c644,0x10c680,0x10c688,'VoldNativeService22setCeStorageProtection'),(59,0x109338,0x1f0,None,0x109378,0x109380,'VoldNativeService16getUnlockedUsers'),(60,0x10ae7c,0x1f8,0x10c7c4,0x10c800,0x10c80c,'VoldNativeService15unlockCeStorage')]:
  target=0x107e8c+4*struct.unpack_from('<H',data,offset(0x2947c,2*125)+2*(code-1))[0]
  if target!=entry or bypc[entry]['mnemonic']!='bti':raise ValueError('Actual native Binder case differs')
  if bypc[slotpc]['mnemonic']!='ldr' or bypc[slotpc]['operands']!='x9, [x8, #'+hex(slot)+']' or (bypc[callpc]['mnemonic'],bypc[callpc]['operands'])!=('blr','x9'):raise ValueError('Native virtual dispatch slot differs')
  if tail and not any(i['operands'].endswith('#'+hex(tail)) for i in dispatcher['instructions'] if entry<=i['address']<entry+164):raise ValueError('Case does not reach selected decode tail')
  pointer=address_point+slot
  expected=next(f for f in functions if fragment in f['symbol'])
  if pointer not in relrset or struct.unpack_from('<Q',data,offset(pointer,8))[0]!=expected['address']:raise ValueError('Case virtual slot does not bind actual NativeService wrapper')
  start=entry;end=next(i['address'] for i in dispatcher['instructions'] if i['address']>start and i['mnemonic']=='bti')
  windows=[{'start':start,'bytes':end-start,'sha256':hashlib.sha256(data[offset(start,end-start):offset(start,end-start)+end-start]).hexdigest()}]
  if tail:windows.append({'start':tail,'bytes':96,'sha256':hashlib.sha256(data[offset(tail,96):offset(tail,96)+96]).hexdigest()})
  routes.append({'code':code,'jumpTable':0x2947c,'jumpBase':0x107e8c,'caseEntry':entry,'virtualSlotOffset':slot,'nativeVtableAddressPoint':address_point,'relocatedPointerAddress':pointer,'target':expected['address'],'targetSymbol':expected['symbol'],'caseWindows':windows})
 result={'source':{'path':VOLD.relative_to(ROOT).as_posix(),'sha256':VOLD_SHA,'bytes':len(data)},'miniDebugSha256':sha(mini_path),'pcDisassemblerSha256':WHEEL_SHA,'functions':functions,'calls':calls,'nativeBinderRoutes':routes,'nativeServiceVtableGot':{'address':got,'relrVerified':True,'table':vtable,'addressPoint':address_point},'selectedSymbols':[s for s in symbols if any(n in s['name'].lower() for n in ['ce_key','ce_storage','unlocked_users','ce_policies'])],'oemExecuted':False}
 path=RAW/'vold-selected.json';path.write_text(json.dumps(result,indent=2)+'\n')
 (WORK/'native-receipt.json').write_text(json.dumps({'raw':path.relative_to(ROOT).as_posix(),'rawSha256':sha(path),'miniDebug':mini_path.relative_to(ROOT).as_posix(),'miniDebugSha256':sha(mini_path),'inputSha256':sha(VOLD),'pcToolSha256':sha(WHEEL),'toolSha256':sha(Path(__file__))},indent=2)+'\n')
 print(json.dumps({'nativeFunctions':len(functions),'resolvedDirectCalls':sum(c['symbol'] is not None for c in calls),'unresolvedDirectCalls':sum(c['symbol'] is None for c in calls)}))
def java_probe():
 WORK.mkdir(parents=True,exist_ok=True)
 read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
 archive=ROOT.parent/'firmware/samsung/framework.jar';pin='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
 ledger=WORK/'java-receipts.json';queries=json.loads(ledger.read_text()) if ledger.exists() else {}
 for key,owner,methods in [('samsung-file-encryption','android.os.storage.StorageManager',['isFileEncrypted()Z']),
                          ('samsung-encryption-state','android.os.storage.StorageManager',['isEncrypted()Z']),
                          ('samsung-ro-system-properties','com.android.internal.os.RoSystemProperties',['<clinit>()V']),
                          ('samsung-crypto-properties','android.sysprop.CryptoProperties',['type()Ljava/util/Optional;','state()Ljava/util/Optional;'])]:
  if key in queries:
   r=queries[key]
   if sha(ROOT/r['raw'])!=r['rawSha256'] or r['archiveSha256']!=pin:raise ValueError('Cached Java source differs')
   continue
  r=read(archive,pin,class_name=owner,methods=methods,stream='authority-bootstrap-storage');queries[key]=r
  ledger.write_text(json.dumps(queries,indent=2)+'\n')
 print(json.dumps({'javaQueries':len(queries),'methods':sum(len(r['selectedMethodProofs']) for r in queries.values())}))
def report():
 WORK.mkdir(parents=True,exist_ok=True)
 nr=json.loads((WORK/'native-receipt.json').read_text());native=json.loads((ROOT/nr['raw']).read_text())
 if sha(VOLD)!=VOLD_SHA or sha(ROOT/nr['raw'])!=nr['rawSha256'] or sha(ROOT/nr['miniDebug'])!=nr['miniDebugSha256'] or sha(WHEEL)!=WHEEL_SHA:raise ValueError('Native evidence differs')
 data=VOLD.read_bytes();elf=runpy.run_path(str(ROOT/'tools/audit_security_native_linkage.py'))['elf'];parsed=elf(data)
 def literal(address):
  sections=[s for s in parsed['sections'] if s['type']!=8 and s['address']<=address<s['address']+s['bytes']]
  if len(sections)!=1:raise ValueError('Native literal outside unique section')
  s=sections[0];off=s['offset']+address-s['address'];end=data.find(b'\0',off,off+512)
  if end<0:raise ValueError('Unterminated native literal')
  return data[off:end].decode('ascii')
 for f in native['functions']:
  if hashlib.sha256(data[f['fileOffset']:f['fileOffset']+f['bytes']]).hexdigest()!=f['sha256']:raise ValueError('Native function changed')
 checks=[]
 def check(name,value):
  if not value:raise ValueError('Source check failed: '+name)
  checks.append(name)
 check('Native source/current selected ranges and three Binder dispatch targets verified',len(native['nativeBinderRoutes'])==3 and all(r['target']==next(f['address'] for f in native['functions'] if f['symbol']==r['targetSymbol']) for r in native['nativeBinderRoutes']))
 check('Original native registration name and FBE property/default bytes',literal(0x11ee8)=='vold' and literal(0x18729)=='ro.crypto.type' and literal(0x1f9fd)=='none')
 def fn(fragment):return next(f for f in native['functions'] if fragment in f['symbol'])
 def op(fragment,address,mnemonic,operands):
  return any(i['address']==address and i['mnemonic']==mnemonic and i['operands']==operands for i in fn(fragment)['instructions'])
 check('Native status reads native policy tree keys and no authentication result',op('fscrypt_get_unlocked_users',0x76fec,'adr','x8, #0x164a10') and op('fscrypt_get_unlocked_users',0x77028,'ldr','w28, [x27, #0x20]') and op('fscrypt_get_unlocked_users',0x77034,'str','w28, [x26], #4'))
 check('Native status, unlock and lock operate on same native policy tree',op('fscrypt_unlock_ce_storage',0x772e4,'ldr','x9, [x8, #0xa10]') and op('fscrypt_lock_ce_storage',0x7764c,'adr','x0, #0x164a10'))
 calls=native['calls']
 check('Native Binder source enforces system UID/root and takes VolumeManager mutex',all(any(c['caller']==fn(n)['symbol'] and 'CheckUidOrRoot' in c['symbol'] for c in calls) and any(c['caller']==fn(n)['symbol'] and 'mutex4lock' in c['symbol'] for c in calls) for n in ['VoldNativeService16getUnlockedUsers','VoldNativeService22setCeStorageProtection','VoldNativeService15unlockCeStorage']))
 check('Caller check uses real Binder calling UID and root branch',any('IPCThreadState13getCallingUid' in c['symbol'] for c in calls if 'CheckUidOrRoot' in c['caller']) and op('CheckUidOrRoot',0xd4148,'cbz','w0, #0xd41c0'))
 check('Native unlock accepts empty or exclamation token, otherwise service error minus22',op('VoldNativeService15unlock',0x9d52c,'cbz','x9, #0x9d550') and op('VoldNativeService15unlock',0x9d530,'cmp','x9, #1') and op('VoldNativeService15unlock',0x9d548,'cmp','w8, #0x21') and op('VoldNativeService15unlock',0x9d5b4,'mov','w0, #-0x16'))
 check('Native fscrypt mutation receives actual secret and HSUM, not a fabricated token success',op('VoldNativeService15unlock',0x9d550,'and','w2, w22, #1') and op('VoldNativeService15unlock',0x9d558,'mov','x1, x21') and any('fscrypt_unlock_ce_storage' in c['symbol'] for c in calls if 'VoldNativeService15unlock' in c['caller']))
 prior=json.loads((ROOT/'inventory/storage-contract-adapter.json').read_text());methods=dict(prior['methodProofs'])
 java=json.loads((WORK/'java-receipts.json').read_text())
 for r in java.values():
  if sha(ROOT/r['raw'])!=r['rawSha256'] or sha(r['archive'])!=r['archiveSha256']:raise ValueError('Java source differs')
  for row in map(json.loads,(ROOT/r['raw']).read_text(encoding='utf-8').splitlines()):
   if row['record']=='method':methods['samsung-framework:'+row['body']['owner']+'->'+row['body']['signature']]={'bodySha256':row['normalizedBodySha256'],'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':r['receipt']}
 user=json.loads((ROOT/'inventory/security-user-binding.json').read_text())
 for key in ['samsung-framework:Landroid/os/UserManager;->isHeadlessSystemUserMode()Z','samsung-services:Lcom/android/server/pm/UserManagerService;->isHeadlessSystemUserMode()Z','samsung-framework:Landroid/content/pm/UserInfo;->isFull()Z']:
  methods[key]=user['methodProofs'][key]
 for m in methods.values():
  if sha(ROOT/m['raw'])!=m['rawSha256']:raise ValueError('Reused method pin differs')
 check('Original proxy source preserves sensitive flags32 and exact native46/59/60',sorted((w['transactionCode'],w['transactionFlags'],w['sensitive']) for w in prior['samsungNativeWireLifetime'])==[(46,32,True),(59,32,True),(60,32,True)])
 oneos=json.loads((ROOT/'inventory/inputs.json').read_text());scripts=[]
 for name,spans in [('guest_start.sh',[[645,759],[1208,1217]]),('guest_prepare.sh',[[1242,1266]])]:
  item=next(f for f in oneos['files'] if f['path'].endswith('/'+name));path=ROOT.parent/item['path']
  if sha(path)!=item['sha256']:raise ValueError('OneOS source differs')
  scripts.append({'path':'../'+item['path'],'sha256':item['sha256'],'linesInclusive':spans,'installedBehaviorVerified':False})
 check('Conditional OneOS host-vold/gvld source pins verified',len(scripts)==2)
 result={'schema':'authority-bootstrap-storage/v1','gate':'D','status':'SOURCE_CUT_CLOSED__BLOCKED_GENUINE_LIVE_STORAGE_PROVIDER','helperImplemented':False,'marshallerImplemented':False,'nativeCodeExecuted':False,'androidExecuted':False,'phoneActions':False,'privateStateRead':False,'checks':checks,'sourceInventories':{p:sha(ROOT/p) for p in ['inventory/storage-contract-adapter.json','inventory/storage-keys.json','inventory/security-user-binding.json']},'methodProofs':methods,'native':{'receipt':'out/authority-bootstrap-storage/native-receipt.json','receiptSha256':sha(WORK/'native-receipt.json'),'raw':nr['raw'],'rawSha256':nr['rawSha256'],'input':native['source'],'pcDisassemblerSha256':WHEEL_SHA,'nativeBinderRoutes':native['nativeBinderRoutes'],'functions':[{k:v for k,v in f.items() if k!='instructions'} for f in native['functions']]},'oneos':{'commit':oneos['oneosCommit'],'scripts':scripts,'scope':'Source-selected gvld branch preserves original vold names with PID checks; fallback can register guest under vold; live marker/bytes/PIDs/handles were not acquired'},'preparedContract':prior['minimumContractProposal'],'sourceDisposition':{'status':'keys of daemon-local tracked UserPolicies tree under VolumeManager lock; same tree touched by installation/eviction; no live map values acquired','notProvedByStatus':['fresh credential/HAT','new protector/secret protection committed','CE file usability','Keystore/KeyMint acceptance','durability or rollback','whole writer/native drain'],'nativeHat':'Original native accepts token String empty or !; other text fails with service-specific minus22 before fscrypt unlock. Preserve original Java HAT branch and admit actual firstAPI; do not force null as workaround.','nativeCaller':'kernel Binder calling UID must equal1000 or0; both OS system UID may be1000, so this is not user/policy/source provenance'},'genuineInputs':{'endpoint':'Original vold IBinder/proxy captured by an actual trusted bootstrap before guest name replacement, bound to verified original process/image/mount/generation and retained through real drain; name/descriptor/ping/UID alone insufficient','user':'same authoritative user/profile/serial/state owner as LSS/SPM and native physical CE/key namespace; not native map integer membership or guessed user0','hsum':'actual original UserManagerService derives !UserInfo(user0).isFull under users lock; framework caches global user Binder result; no defaultfalse or guest-view substitution','encryption':'original Java isEncrypted AND RoSystemProperties.CRYPTO_FILE_ENCRYPTED; CryptoProperties reads ro.crypto.state/type with unsupported/none fallbacks. Native IsFbeEnabled reads ro.crypto.type defaultnone and compares file. Must bind same original property view/profile/generation; unknown/default is not admission.','firstApi':'Original LSS reads ro.product.first_api_level; HAT-native compatibility depends on this input; no guessed default or force-null policy','status':'same original daemon/current user generation plus explicit guest/cache alignment; native59 not universal reconciliation and must not be sent as a probe to an unidentified endpoint'},'explicitBlockers':['No actual trusted provider currently mints original native endpoint+user+HSUM/FBE/firstAPI binding before eager LSS work','Installed OneOS guarded branch, native identity, service handle/process generation and physical key/data namespace remain unverified','No owned cache/public-status alignment, original lifecycle/writer handoff and native/error disposition integration','Protection/response-loss uncertainty has no universal readonly getter/atomic rollback proof; native user membership alone cannot resolve it'],'nextAdmissionEvidence':['Implement/review trusted bootstrap acquisition owned by selected real process/runtime/user authority, never caller-supplied readiness receipts','Admit exact original-vold process/image/namespace/generation before even status59; reject guest/fallback or death/replacement','Capture original policy at its genuine owner and match same physical user/registry/key state; retain actual endpoint/code/control owners','Define quiesce/status/cache/error reconciliation with no auto retry/reset/secret backup; then root may approve exact contract implementation'],'rootDirection':'source/API-only; another unselected low-level marshaller is not a bootstrap binding','toolSha256':sha(Path(__file__))}
 result['crossGateDependencies']={'B':'endpoint/alias evidence does not mint registry or policy','C':'genuine user registry/lifecycle/state owner','F':'applicable genuine policy/Context owner','D':'original-vold identity/status and storage binding; no live provider supplied'}
 (ROOT/'inventory/authority-bootstrap-storage.json').write_text(json.dumps(result,indent=2)+'\n')
 (WORK/'verification.json').write_text(json.dumps({'sourceChecks':len(checks),'nativeFunctions':len(native['functions']),'nativeProtocolCases':len(native['nativeBinderRoutes']),'javaNewBodies':sum(len(r['selectedMethodProofs']) for r in java.values()),'liveProvider':'missing','oemExecuted':False,'phoneActions':False},indent=2)+'\n')
 print((WORK/'verification.json').read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',action='store_true');p.add_argument('--java',action='store_true');a=p.parse_args()
 if a.native:native_probe()
 if a.java:java_probe()
 if not(a.native or a.java):report()
if __name__=='__main__':main()
