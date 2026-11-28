"""Bounded static storage adapter cut; never reads state or executes OEM code."""
import argparse,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'out/storage-contract-adapter'
FIELD='Lcom/android/server/locksettings/LockSettingsService;->mStorageManagerInternal:Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;'
LSS='Lcom/android/server/locksettings/LockSettingsService;'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collect',action='store_true');args=parser.parse_args()
 prior=json.loads((ROOT/'inventory/construction-storage-linkage.json').read_text())
 for source in prior['inputs'].values():
  if sha(ROOT/source['path'])!=source['sha256']:raise ValueError('Source archive drift')
 WORK.mkdir(parents=True,exist_ok=True);ledger=WORK/'receipts.json'
 receipts=json.loads(ledger.read_text()) if ledger.exists() else {}
 read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
 def query(key,side,**selector):
  source=prior['inputs'][side];path=ROOT/source['path']
  if sha(path)!=source['sha256']:raise ValueError('Input archive drift')
  if key not in receipts:
   if not args.collect:raise ValueError('Missing bounded receipt '+key)
   receipts[key]=read(path,source['sha256'],stream='storage-contract-adapter',**selector)
   ledger.write_text(json.dumps(receipts,indent=2)+'\n')
  r=receipts[key]
  if r['archiveSha256']!=source['sha256'] or r['readerExitCode']!=0 or not r['archiveAndToolPinsVerifiedBeforeAndAfter']:raise ValueError('Receipt source identity differs')
  if r['query']['exactMethods']!=selector.get('methods',[]) or r['query']['reference']!=selector.get('reference'):raise ValueError('Cached selector differs')
  if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Raw changed')
  return r
 query('exact-public-field-references','samsung-services',reference=FIELD)
 query('exact-framework-public-field-references','samsung-framework',reference=FIELD)
 for side in ('samsung-framework','coloros-framework'):
  query(side+':RemoteException',side,class_name='android.os.RemoteException',methods=['rethrowAsRuntimeException()Ljava/lang/RuntimeException;'])
 query('samsung-framework:ArrayUtils','samsung-framework',class_name='com.android.internal.util.ArrayUtils',methods=['isEmpty([B)Z'])
 hexentry=query('samsung-framework:HexDump-entry','samsung-framework',class_name='com.android.internal.util.HexDump',methods=['toHexString([B)Ljava/lang/String;'])
 query('samsung-framework:HexDump-digits','samsung-framework',class_name='com.android.internal.util.HexDump',methods=['<clinit>()V'])
 query('samsung-framework:IVold-status','samsung-framework',class_name='android.os.IVold$Stub$Proxy',methods=['getUnlockedUsers()[I'])
 pending=set()
 for row in map(json.loads,(ROOT/hexentry['raw']).read_text(encoding='utf-8').splitlines()):
  if row['record']=='method':pending.update(i['reference'].split('->')[1] for i in row['body']['instructions'] if i.get('reference','').startswith('Lcom/android/internal/util/HexDump;->toHexString('))
 for depth in range(3):
  if not pending:break
  hexnext=query('samsung-framework:HexDump-reached-'+str(depth),'samsung-framework',class_name='com.android.internal.util.HexDump',methods=sorted(pending))
  known=set(pending);pending=set()
  for row in map(json.loads,(ROOT/hexnext['raw']).read_text(encoding='utf-8').splitlines()):
   if row['record']=='method':pending.update(i['reference'].split('->')[1] for i in row['body']['instructions'] if i.get('reference','').startswith('Lcom/android/internal/util/HexDump;->toHexString('))
  pending-=known
 bodies={};proofs={}
 for e in prior['evidence']:
  r=json.loads((ROOT/e['receipt']).read_text())
  if sha(ROOT/e['receipt'])!=e['receiptSha256'] or sha(ROOT/e['raw'])!=e['rawSha256']:raise ValueError('Frozen evidence changed')
  for row in map(json.loads,(ROOT/e['raw']).read_text(encoding='utf-8').splitlines()):
   if row['record']!='method':continue
   b=row['body'];key=e['input']+':'+b['owner']+'->'+b['signature']
   if key in bodies and bodies[key]['normalizedBodySha256']!=row['normalizedBodySha256']:raise ValueError('Method conflict')
   bodies[key]=row;proofs[key]={'bodySha256':row['normalizedBodySha256'],'raw':e['raw'],'rawSha256':e['rawSha256'],'receipt':e['receipt']}
 for key,r in receipts.items():
  for row in map(json.loads,(ROOT/r['raw']).read_text(encoding='utf-8').splitlines()):
   if row['record']!='method':continue
   b=row['body'];name=key.split(':')[0]+':'+b['owner']+'->'+b['signature'];bodies[name]=row
   proofs[name]={'bodySha256':row['normalizedBodySha256'],'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':r['receipt']}
 selected={k:v for k,v in bodies.items() if k.startswith('samsung-services:'+LSS+'->') and v['body']['signature'].split('(')[0] in ('<init>','setCeStorageProtection','unlockCeStorage','isCeStorageUnlocked')}
 def method(owner,name):
  matches=[(k,r) for k,r in bodies.items() if k.startswith('samsung-services:'+owner+'->') and r['body']['signature'].split('(')[0]==name]
  if len(matches)!=1:raise ValueError('Exact method ambiguity '+name)
  return matches[0]
 field=receipts['exact-public-field-references']
 refs=[x for x in map(json.loads,(ROOT/field['raw']).read_text(encoding='utf-8').splitlines()) if x['record']=='reference']
 if len(refs)!=5 or any(not r['caller'].startswith(LSS+'->') for r in refs):raise ValueError('Additional public field users require expanded retarget')
 if sorted(r['instruction']['pc'] for r in refs)!=[83,105,163,177,651]:raise ValueError('Field reference scope changed')
 if receipts['exact-framework-public-field-references']['referenceMatchCount']!=0:raise ValueError('Framework field readers require expanded retarget')
 changes=[]
 contract='Lcom/appleexploit/oneos/security/storage/PreparedStorageContract;'
 newField=LSS+'->mStorageManagerInternal:'+contract
 for _,row in selected.items():
  b=row['body']
  ranges=[]
  if b['signature'].startswith('<init>'):ranges=[(643,645),(649,651),(651,653)]
  elif b['signature'].startswith('setCeStorageProtection'):ranges=[(83,85),(88,97),(105,107),(110,119)]
  elif b['signature'].startswith('unlockCeStorage'):ranges=[(163,165),(165,168),(177,179),(180,183)]
  elif b['signature'].startswith('isCeStorageUnlocked'):ranges=[(0,2),(2,5)]
  code=b['instructions'];by_pc={i['pc']:i for i in code}
  for start,end in ranges:
   instructions=[i for i in code if start<=i['pc']<end]
   if sum(i['codeUnits'] for i in instructions)!=end-start:raise ValueError('Noncontiguous replacement span')
   if any(start<i.get('targetPc',-1)<end for i in code):raise ValueError('Interior branch target needs a different rewrite')
   for c in b['catches']:
    if any(start<p<end for p in [c['startPc'],c['startPc']+c['codeUnits'],c['handlerPc']]):raise ValueError('Interior try/handler boundary needs a different rewrite')
   if b['signature'].startswith('<init>') and start in (643,649):
    proposed={'opcode':by_pc[start]['opcode'],'registers':by_pc[start]['registers'],'reference':contract}
   elif by_pc[start]['opcode'] in ('IGET_OBJECT','IPUT_OBJECT') and end-start==2:
    proposed={'opcode':by_pc[start]['opcode'],'registers':by_pc[start]['registers'],'reference':newField}
   elif b['signature'].startswith('setCeStorageProtection'):
    proposed={'opcode':'INVOKE_INTERFACE','registers':[3,4,0 if start==88 else 5],'reference':contract+'->setCeStorageProtection(I[B)V','trailingSingleUnitNops':6}
   else:
    proposed={'opcode':'INVOKE_INTERFACE','registers':by_pc[start]['registers'],'reference':contract+'->'+('isCeStorageUnlocked(I)Z' if start==2 else 'unlockCeStorage(I[B[B)V')}
   if proposed['opcode']=='INVOKE_INTERFACE':
    if len(proposed['registers'])>5 or any(not 0<=r<=15 for r in proposed['registers']):raise ValueError('Proposed invoke requires a different register encoding')
    if 3+proposed.get('trailingSingleUnitNops',0)!=end-start:raise ValueError('Proposed invoke/padding budget differs')
   changes.append({'method':b['signature'],'startPc':start,'endPcExclusive':end,'codeUnits':end-start,'sourceBodySha256':row['normalizedBodySha256'],'replacesOpcodes':[i['opcode'] for i in instructions],'proposalOnly':proposed})
 checks=['Frozen storage evidence/archives/raw receipts verified','Exact whole-services public field scan closes all five uses, with no foreign direct field readers','Planned same-size replacement spans are contiguous, with no interior branch/try/handler boundaries']
 checks[1]='Exact public field scan: five uses in Samsung services, all LSS; zero in Samsung framework; reflection/JNI/other archives not closed'
 for side in ('samsung-framework','coloros-framework'):
  key=side+':Landroid/os/RemoteException;->rethrowAsRuntimeException()Ljava/lang/RuntimeException;'
  code=bodies[key]['body']['instructions']
  if not any(i['opcode']=='THROW' for i in code) or any(i['opcode'].startswith('RETURN') for i in code):raise ValueError('Rethrow method does not unconditionally throw')
 checks.append('Both actual canonical RemoteException.rethrowAsRuntimeException bodies throw, with no normal return')
 protected=method(LSS,'setCeStorageProtection')[1]['body'];unlock=method(LSS,'unlockCeStorage')[1]['body']
 if [i['pc'] for i in protected['instructions'] if '->zeroize(' in i.get('reference','')]!=[124,128]:raise ValueError('Protection cleanup moved')
 if [i['pc'] for i in unlock['instructions'] if '->zeroize(' in i.get('reference','')]!=[213,233,237]:raise ValueError('Unlock cleanup moved')
 checks.append('Original secret selection and cleanup bodies remain source-pinned; adapter is not a new derivation or async owner')
 selectedKeys=set(selected)
 for owner,name in [('Lcom/android/server/StorageManagerService$StorageManagerInternalImpl;','unlockCeStorage'),('Lcom/android/server/StorageManagerService;','isCeStorageUnlocked')]:selectedKeys.add(method(owner,name)[0])
 selectedKeys.update(k for k in proofs if 'RemoteException;->rethrowAsRuntimeException' in k)
 selectedKeys.update(k for k in proofs if k.startswith(('samsung-framework:Lcom/android/internal/util/ArrayUtils;->isEmpty([B)','samsung-framework:Lcom/android/internal/util/HexDump;->toHexString(')))
 selectedKeys.update(k for k in proofs if k.startswith('samsung-framework:Lcom/android/internal/util/HexDump;-><clinit>'))
 selectedKeys.add('samsung-services:Lcom/android/server/StorageManagerService$Lifecycle;->onStart()V')
 for side in ('samsung-framework','coloros-framework'):
  selectedKeys.update(k for k in proofs if k.startswith(side+':Landroid/os/IVold$Stub$Proxy;->'))
 wire=[]
 for key in sorted(selectedKeys):
  if not key.startswith('samsung-framework:Landroid/os/IVold$Stub$Proxy;->'):continue
  b=bodies[key]['body'];code=b['instructions'];transact=next(i for i in code if 'IBinder;->transact(' in i.get('reference',''));reg=transact['registers'][4]
  flags=next(i['literal'] for i in reversed(code[:code.index(transact)]) if i.get('registers')==[reg] and 'literal' in i)
  if b['signature']!='getUnlockedUsers()[I' and (flags!=32 or not any('Parcel;->markSensitive()' in i.get('reference','') for i in code)):raise ValueError('Native sensitive transport contract differs')
  codeReg=transact['registers'][1]
  transaction=next(i['literal'] for i in reversed(code[:code.index(transact)]) if i.get('registers')==[codeReg] and 'literal' in i)
  wire.append({'method':b['signature'],'transactionCode':transaction,'transactionFlags':flags,'sensitive':any('Parcel;->markSensitive()' in i.get('reference','') for i in code),'readsReplyException':any('Parcel;->readException()' in i.get('reference','') for i in code),'bodySha256':bodies[key]['normalizedBodySha256']})
 checks.append('Actual Samsung native storage proxies mark sensitive and use flags32, then read reply exceptions')
 result={'schema':'storage-contract-adapter/v1','status':'source-to-code preparation; no helper/DEX/backend selected','sourceInventory':{'path':'inventory/construction-storage-linkage.json','sha256':sha(ROOT/'inventory/construction-storage-linkage.json')},'inputs':prior['inputs'],'checks':checks,'minimumContractProposal':{'descriptor':'Lcom/appleexploit/oneos/security/storage/PreparedStorageContract;','methods':['setCeStorageProtection(I[B)V','unlockCeStorage(I[B[B)V','isCeStorageUnlocked(I)Z'],'purpose':'genuine internal original-selected-secret transport and coherent status; not public IPC or default backend','checkedExceptionPolicy':{'setCeStorageProtection':'canonical android.os.RemoteException reaches unchanged LSS handler','unlockCeStorage':'native RemoteException rethrown as RuntimeException as original concrete method','isCeStorageUnlocked':'canonical RemoteException reaches unchanged LSS false/log handler; uncertainty separately blocks integration admission'}},'originalConcreteEdges':prior['locksettingsConcreteEdges'],'originalField':prior['locksettingsOwnedStorageField'],'exactWholeArchiveFieldReferences':[{'caller':r['caller'],'pc':r['instruction']['pc'],'target':r['instruction']['reference']} for r in refs],'rewriteSpans':changes,'methodProofs':{k:proofs[k] for k in sorted(selectedKeys)},'nativeWire':prior['ivoldProxyProofs'],'samsungNativeWireLifetime':wire,'receipts':'out/storage-contract-adapter/receipts.json','receiptsSha256':sha(ledger),'toolSha256':sha(Path(__file__)),'androidExecuted':False,'oemExecuted':False,'privateStateRead':False,'phoneActions':False,'adapterImplemented':False,'dexRetargetApplied':False,'missing':['Root-reviewed helper ABI/publication and same-loader Class identity','Genuine Samsung native endpoint/HSUM/encryption/user/writer/generation authority','Aligned current status/cache invalidation and native/listener/lock/reset reconciliation','Synchronous borrowed-secret/HAT consumption and actual completion/uncertain-commit recovery','Actual DEX inverse/roundtrip/type/caller preservation and device acceptance']}
 result['branchContract']={'protection':{'virtualUser':'original return before derivation/native call','ordinarySecret':'SP FBE derive at9, register5','dualDarOuterSecret':'only genuine DualDAR non-device-owner fetch at73, register0 used at94','noEncryptionShortcut':True,'zeroize':'derived register5 at124/128; do not assert original wipes outer key or HAT'},'unlock':{'virtualOrAlreadyUnlocked':'original early returns at6/29','secret':'SP derive48 into register2; genuine non-DO DualDAR can replace register2 at119','verifyChallenge':'same SP/user verify at131 retained even when chosen native HAT is null','hatCondition':'firstApiLevel<=30 AND (user==0 OR enterprise-and-not-SecureFolder) AND response!=null','hatNull':'selected HAT-bearing branch rejects null at161/169; nonnull empty is not rejected here; other branch passes explicit null179','wireHat':'null or empty -> !; otherwise original uppercase HexDump over full input','zeroize':'current register2 at213/233/237; not a new wipe guarantee for discarded derived array or HAT'},'backend':{'protect':'direct Samsung native operation, actual HSUM, RemoteException remains checked until original LSS handler','unlock':'actual encryption gate; Samsung proxy ack then update current owned unlocked view/invalidate caches; RemoteException becomes RuntimeException before update','status':'same authoritative subject/generation; existing Java membership cache is not native proof; getUnlockedUsers59 is a source-backed candidate for fresh encrypted-backend view','failure':'LSS unlock catches RuntimeException and logs/returns void; native commit/uncertainty cannot be inferred from void return'}}
 result['publicationProposal']={'registry':'one canonical LocalServices registry; exact same private Contract Class object at publication and LSS const-class/cast','constructorAbi':'unchanged; constructor key643/cast649/field651 changes only','field':'same public-final name/access flags17, new interface descriptor, all five old references retargeted; status adds one deliberate new read','precondition':'real prepared owner and source/state/user/native/loader admission BEFORE any eager LSS construction; nullable registry lookup is not readiness','noDefaultBackend':'no arbitrary HSUM/encryption/ready getters or no-op methods; root reviews actual interface/publication before shared source edits','lifetime':'real process owner retains native endpoint, code and status/control dependencies through calls, callbacks and uncertain progress; dispatch-call count is not drain'}
 result['fieldReferenceScope']={'samsungServices':5,'samsungFramework':0,'limits':'exact direct code references in supplied two archives only; no reflection/JNI or arbitrary external loader closure'}
 result['futureProducerProofs']=['one original LSS class edited; exact field metadata plus four selected method bodies only','actual index/register/verifier/loader bounds and same-class contract publication','all untouched branches/catches/zeroize PCs and constructor ABI preserved','all foreign definitions preserved; exact inverse reconstructs original class/source bytes','DEX041 container/header/table/checksum and direct caller/ref closure on actual emitted artifact','no proof or counter here authorizes native execution or a phone candidate']
 for source in prior['inputs'].values():
  if sha(ROOT/source['path'])!=source['sha256']:raise ValueError('Archive drift after audit')
 (ROOT/'inventory/storage-contract-adapter.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'pass':True,'checks':len(checks),'exactFieldUses':len(refs),'rewriteSpans':len(changes),'newBoundedQueries':len(receipts),'sourceMethods':len(selectedKeys),'adapterImplemented':False,'dexRetargetApplied':False}))
if __name__=='__main__':main()
