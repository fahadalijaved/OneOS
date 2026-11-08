"""Bounded captured ELF disassembly only; never load or execute OEM code."""
from pathlib import Path
import hashlib,json,lzma,re,runpy,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'firmware/guest-native-service-manager'
OUT=ROOT/'out/guest-native-service-manager'
PARSER='tools/audit_security_native_linkage.py'
PARSER_SHA='33c005e05b884ce03f4b57d3e288a62211abb78a2203ee8f3834bdce8a7d9831'
SOURCES={
 'binder':('../firmware/donor/extracted/system/lib64/libbinder.so','471001204af7c226bb104dcbf9aae7e74be431f4542f389bcc574489428ff8ad'),
 'ndk':('../firmware/donor/extracted/system/lib64/libbinder_ndk.so','70ebb035814a7b0ac8996804dadd74b94ab2ed53ad402ee293f7efe78b374047'),
 'runtime':('../firmware/donor/extracted/system/lib64/libandroid_runtime.so','edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279')}
WANTED={
 'binder':['defaultServiceManagerEv','setDefaultServiceManagerE','getBackendUnifiedServiceManagerEv','ProcessState16getContextObject','ProcessState23getStrongProxyForHandle','ProcessState4initE','ProcessState13childPostFork','getJavaServicemanagerImplPrivate','BackendUnifiedServiceManagerC1E','CppBackendShim10onAsBinder','CppBackendShim10getServiceE','CppBackendShim12checkServiceE','CppBackendShim14realGetService','CppBackendShim14waitForServiceE','CppBackendShim10addServiceE','CppBackendShim12listServicesE','CppBackendShim24registerForNotificationsE','CppBackendShim26unregisterForNotificationsE','CppBackendShim19getServiceDebugInfoE','CppBackendShim18checkServiceAccess','BackendUnifiedServiceManager18checkServiceAccess','BackendUnifiedServiceManager13checkService2','BackendUnifiedServiceManager11getService2','BackendUnifiedServiceManager14returnIfCached','BackendUnifiedServiceManager11updateCache','BackendUnifiedServiceManager10addServiceE','BackendUnifiedServiceManager24registerForNotificationsE','BackendUnifiedServiceManager26unregisterForNotificationsE'],
 'ndk':['AServiceManager_getService','AServiceManager_checkService','AServiceManager_waitForService','AServiceManager_addService','AServiceManager_addServiceWithFlags','AServiceManager_registerForServiceNotifications','AServiceManager_NotificationRegistration_delete','AServiceManager_registerLazyServiceWithFlags','AServiceManager_NotificationRegistration21onServiceRegistration'],
 'runtime':['android_os_ServiceManager_waitForServiceNative','Java_android_os_ServiceManagerProxy_getNativeServiceManager','android_os_BinderInternal_getContextObject']}
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
 if sha((ROOT/PARSER).read_bytes())!=PARSER_SHA:raise ValueError('Frozen parser mismatch')
 elf=runpy.run_path(str(ROOT/PARSER))['elf']
 sys.path.insert(0,str(ROOT/'out/security-native/static-disassembler'))
 import capstone
 cs=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);cs.detail=True
 allproof={}
 for label,(path,pin) in SOURCES.items():
  blob=(ROOT/path).read_bytes()
  if sha(blob)!=pin:raise ValueError('Exact captured source mismatch '+label)
  parsed=elf(blob);sections=parsed['sections'];symbols=list(parsed['dynamicSymbols'])
  debug=[s for s in sections if s['name']=='.gnu_debugdata']
  if len(debug)!=1:raise ValueError('One bounded mini-debug required')
  d=debug[0];mini=lzma.decompress(blob[d['offset']:d['offset']+d['bytes']],memlimit=64*1024*1024)
  if len(mini)>16*1024*1024:raise ValueError('Mini debug bound')
  symbols+=elf(mini)['dynamicSymbols']
  def offset(addr,size):
   s,=[s for s in sections if s['type']!=8 and s['address']<=addr and addr+size<=s['address']+s['bytes']]
   return s['offset']+addr-s['address']
  plt,=[s for s in sections if s['name']=='.plt'];slots=[r for r in parsed['rela'] if r['type']==1026]
  def resolve(addr):
   names=[s['name'] for s in symbols if s['sectionIndex'] and s['value']==addr]
   if names:return names[0]
   if plt['address']+32<=addr<plt['address']+plt['bytes'] and (addr-plt['address']-32)%24==0:
    index=(addr-plt['address']-32)//24
    if index>=len(slots):raise ValueError('PLT bound')
    rel=slots[index];stub=list(cs.disasm(blob[offset(addr,24):offset(addr,24)+24],addr))
    adrp=next(i for i in stub if i.mnemonic=='adrp' and i.op_str.startswith('x16,'));load=next(i for i in stub if i.mnemonic=='ldr' and i.op_str.startswith('x17,'))
    disp=re.search(r'#(0x[0-9a-f]+|[0-9]+)',load.op_str)
    if int(adrp.op_str.split('#')[1],16)+(int(disp.group(1),0) if disp else 0)!=rel['target']:raise ValueError('PLT relocation mismatch')
    return parsed['dynamicSymbols'][rel['symbolIndex']]['name']
   return None
  functions=[];seen=set();total=0
  for sym in symbols:
   name=sym['name']
   if not sym['sectionIndex'] or sym['type']!=2 or not sym['size'] or sym['value'] in seen or not any(k in name for k in WANTED[label]):continue
   # Exclude generic std library clones; retain exactly the two once callbacks.
   if name.startswith('_ZNSt3') and not ('defaultServiceManagerEvE3$_0' in name or 'setDefaultServiceManager' in name):continue
   if sym['size']>8192:raise ValueError('Function bound '+name)
   seen.add(sym['value']);total+=sym['size']
   if total>131072:raise ValueError('Selected text bound')
   off=offset(sym['value'],sym['size']);code=blob[off:off+sym['size']];instructions=[]
   for ins in cs.disasm(code,sym['value']):
    row={'pc':ins.address,'bytes':ins.bytes.hex(),'mnemonic':ins.mnemonic,'operands':ins.op_str}
    if ins.mnemonic in ('b','bl') and ins.op_str.startswith('#0x'):
     target=int(ins.op_str[1:],16);row['targetPc']=target;resolved=resolve(target)
     if resolved:row['targetSymbol']=resolved
    instructions.append(row)
   if len(instructions)*4!=len(code):raise ValueError('Incomplete fixed ARM64 decode')
   functions.append({'symbol':name,'address':sym['value'],'fileOffset':off,'bytes':len(code),'sha256':sha(code),'instructions':instructions})
  if not functions:raise ValueError('Missing selections')
  value={'source':path,'sourceSha256':pin,'miniDebugSha256':sha(mini),'functions':functions,'oemExecuted':False,'sourceScope':'original captured donor; staged/loaded library identity unproved'}
  save(RAW/(label+'.json'),value)
  allproof[label]={'source':path,'sourceSha256':pin,'raw':str((RAW/(label+'.json')).relative_to(ROOT)).replace('\\','/'),'rawSha256':sha((RAW/(label+'.json')).read_bytes()),'functions':[{k:v for k,v in f.items() if k!='instructions'} for f in functions],'instructionCount':sum(len(f['instructions']) for f in functions)}
  if sha((ROOT/path).read_bytes())!=pin:raise ValueError('Source changed')
 save(OUT/'capture.json',{'schema':'guest-native-sm-capture/v1','inputs':allproof,'parserSha256':PARSER_SHA,'capstoneVersion':capstone.__version__,'oemExecuted':False})
 print(json.dumps({k:{'functions':len(v['functions']),'instructions':v['instructionCount']} for k,v in allproof.items()}))
def verify_saved():
 capture=json.loads((OUT/'capture.json').read_text(encoding='utf-8'));records={};checks=[]
 def require(condition,label):
  if not condition:raise ValueError(label)
  checks.append(label)
 require(sha((ROOT/PARSER).read_bytes())==PARSER_SHA,'frozen ELF parser identity')
 for label,(path,pin) in SOURCES.items():
  blob=(ROOT/path).read_bytes();require(sha(blob)==pin,label+' actual captured source identity')
  entry=capture['inputs'][label];raw=(ROOT/entry['raw']).read_bytes()
  require(sha(raw)==entry['rawSha256'],label+' raw record identity')
  value=json.loads(raw)
  for f in value['functions']:
   code=blob[f['fileOffset']:f['fileOffset']+f['bytes']]
   require(sha(code)==f['sha256'] and b''.join(bytes.fromhex(i['bytes']) for i in f['instructions'])==code,label+' exact bytes '+f['symbol'])
   for i in f['instructions']:records[label,i['pc']]=i
 def edge(label,pc,suffix):
  require(records[label,pc].get('targetSymbol','').endswith(suffix),label+' actual call '+hex(pc)+' '+suffix)
 def op(label,pc,mnemonic,operands):
  i=records[label,pc];require(i['mnemonic']==mnemonic and i['operands']==operands,label+' exact instruction '+hex(pc))
 edge('runtime',0x13a2e4,'defaultServiceManagerEv')
 op('runtime',0x13a2f4,'ldr','x9, [x8, #0x40]')
 op('runtime',0x13a2fc,'blr','x9')
 edge('runtime',0x13a3b4,'getJavaServicemanagerImplPrivateDoNotUseExceptInTheOnePlaceItIsUsedEv')
 edge('binder',0x9921c,'getBackendUnifiedServiceManagerEv')
 edge('binder',0x886e0,'getBackendUnifiedServiceManagerEv')
 edge('binder',0x932c0,'__call_onceERVmPvPFvS2_E')
 edge('binder',0x932f0,'__android_log_assert')
 op('binder',0x6beec,'mov','w1, wzr')
 edge('binder',0x6befc,'ProcessState23getStrongProxyForHandleEi')
 edge('binder',0x6b14c,'getContextObjectERKNS_2spINS_7IBinderEEE')
 edge('binder',0x6b158,'IServiceManager11asInterfaceERKNS_2spINS_7IBinderEEE')
 edge('binder',0x6b1ec,'BackendUnifiedServiceManagerC1ERKNS_2spINS_2os15IServiceManagerEEE')
 edge('binder',0x799f0,'returnIfCachedERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEEPNS_2os7ServiceE')
 edge('binder',0x79ee8,'returnIfCachedERKNSt3__112basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEEPNS_2os7ServiceE')
 for pc in [0x1605c,0x16768,0x246b4,0x247e0]:edge('ndk',pc,'defaultServiceManagerEv')
 op('binder',0x992b0,'strb','w9, [x8, #0xf8]')
 edge('binder',0x992b4,'close')
 save(OUT/'audit.json',{'status':'PASS_BOUNDED_SOURCE_EDGES_ONLY','checks':checks,'count':len(checks),'captureSha256':sha((OUT/'capture.json').read_bytes()),'toolSha256':sha(Path(__file__).read_bytes()),'oemExecuted':False,'runtimeAcceptance':False})
 print(json.dumps({'status':'PASS_BOUNDED_SOURCE_EDGES_ONLY','checks':len(checks),'oemExecuted':False}))
if __name__=='__main__':
 if sys.argv[1:]==['--verify']:verify_saved()
 elif sys.argv[1:]:raise SystemExit('Only --verify or source capture without arguments')
 else:main()
