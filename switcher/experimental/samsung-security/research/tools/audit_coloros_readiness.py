"""Bounded offline ColorOS unavailable-authority consumer audit. No OEM execution.

--collect adds only fixed, named source queries; default verifies saved receipts
and derives authored metadata. All source bodies stay in ignored firmware/.
"""
import argparse, hashlib, json, runpy, sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'out/coloros-readiness'
LPU = 'Lcom/android/internal/widget/LockPatternUtils;'
ARCHIVES = {
 'framework': ('firmware/donor/extracted/system/framework/framework.jar', 'd5c6b7fd79f0466831e1d2b52714df5900685862e0c51dc0c02e5f488355bcd2'),
 'systemui': ('firmware/donor/extracted/system/system_ext/priv-app/SystemUI/SystemUI.apk', '0e253fad7ce9a08fae656121cd907d8432b67b84bc37ae84a12e56fe01b8ef77'),
 'settings': ('firmware/donor/extracted/system/system_ext/priv-app/Settings/Settings.apk', '33b0173ba206bc75a25cfba765d96f64fb3a29db7bca02fcb2b9c28f6744838b')}
TARGETS = [
 ('framework', 'com.android.internal.widget.LockPatternUtils', ['credentialTypeToPasswordQuality', 'invalidateCredentialTypeCache', 'invalidateLockoutEndTimeCache']),
 ('framework', 'android.app.PropertyInvalidatedCache', ['query', 'recompute']),
 ('framework', 'com.android.internal.widget.LockPatternUtils$1', ['apply']),
 ('framework', 'com.android.internal.widget.LockPatternUtils$2', ['apply']),
 ('systemui', 'com.android.keyguard.KeyguardSecurityModel', ['getSecurityMode']),
 ('systemui', 'com.android.keyguard.KeyguardSecurityModel$$ExternalSyntheticLambda2', ['get']),
 ('systemui', 'com.oplus.systemui.keyguard.OplusKeyguardBouncerExImpl', ['getSecurityMode']),
 ('systemui', 'com.oplus.keyguard.security.OplusKeyguardSecurityModel', ['getSecurityMode']),
 ('systemui', 'com.android.keyguard.KeyguardSecurityContainerController', ['showPrimarySecurityScreen', 'showNextSecurityScreenOrFinish']),
 ('systemui', 'com.android.keyguard.KeyguardSecurityContainerController$$ExternalSyntheticLambda8', ['get']),
 ('systemui', 'com.oplus.keyguard.security.view.OplusKeyguardAbsKeyInputViewController', ['onResume', 'onPasswordChecked', 'shouldLockout']),
 ('settings', 'com.oplus.settings.feature.password.OplusScreenLockSettings$ScreenLockSettingsFragment', ['currentKeyguardQuality', 'launchChooseOrConfirmLock', 'launchConfirmationActivity']),
 ('settings', 'com.oplus.settings.feature.password.ConfirmLockPasswordFragment', ['onResume', 'onPasswordChecked']),
 ('settings', 'com.android.settings.password.ChooseLockSettingsHelper', ['launch', 'launchConfirmationActivity', 'determineAppropriateActivityClass', 'passwordQualityToLockTypes']),
 ('settings', 'com.android.settings.password.ChooseLockSettingsHelper$Builder', ['show']),
 ('systemui', 'com.android.systemui.DejankUtils', ['whitelistIpcs'])]

def sha(path):
 with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path, value):
 Path(path).parent.mkdir(parents=True, exist_ok=True)
 Path(path).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

def collect():
 read = runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive']
 path = OUT/'reads.json'
 ledger = load(path) if path.exists() else []
 def query(role, owner, methods=(), reference=None):
  key = {'role': role, 'owner': owner, 'methods': list(methods)}
  if reference:key['reference']=reference
  old = next((r for r in ledger if r['key'] == key), None)
  if old:
   if sha(ROOT/old['raw']) != old['rawSha256']: raise ValueError('Raw drift')
   return old
  archive, pin = ARCHIVES[role]
  result = read(ROOT.parent/archive, pin, owner, methods, reference, stream='coloros-readiness')
  if result['readerExitCode'] != 0: raise ValueError('Reader failed')
  result['key'] = key; ledger.append(result); save(path, ledger)
  print('saved', role, owner, len(methods), flush=True)
  return result
 for role, owner, names in TARGETS:
  declared = query(role, owner)['selectedClassDeclarations']
  if len(declared) != 1: raise ValueError('Class absent/ambiguous: '+owner)
  methods = [m['signature'] for m in declared[0]['methods'] if m['signature'].split('(')[0] in names]
  if set(names) != {m.split('(')[0] for m in methods}: raise ValueError('Missing method: '+owner+' '+str(names))
  query(role, owner, methods)
 for suffix,ret in [('1','Ljava/lang/Integer;'),('2','Ljava/time/Duration;')]:
  query('framework', None, reference=LPU[:-1]+'$'+suffix+';->apply(Ljava/lang/Integer;)'+ret)

def evidence():
 rows = load(OUT/'reads.json')
 for name in ['lockpattern-bodies','type-cache','lockout-cache','systemui-lockpattern-refs','settings-lockpattern-refs']:
  row=load(ROOT/('out/construction-protocol/'+name+'.json'));row['inheritedReceipt']='out/construction-protocol/'+name+'.json';rows.append(row)
 inherited=load(ROOT/'inventory/coloros-frontend.json')['selectedUiProofs']
 rows += inherited
 records=[]
 for row in rows:
  if sha(ROOT/row['raw']) != row['rawSha256']:raise ValueError('Raw proof drift: '+row['raw'])
  for line in (ROOT/row['raw']).read_text(encoding='utf-8').splitlines():
   r=json.loads(line)
   if r.get('record') in ['method','reference']:
    records.append((row,r))
 return rows,records

def analyse():
 rows,records=evidence()
 for archive,pin in ARCHIVES.values():
  if sha(ROOT.parent/archive)!=pin:raise ValueError('Input archive drift')
 methods={}
 for row,r in records:
  if r.get('record')!='method':continue
  b=r['body'];key=b['owner']+'->'+b['signature']
  if key in methods and methods[key][1]['normalizedBodySha256']!=r['normalizedBodySha256']:raise ValueError('Ambiguous body '+key)
  methods[key]=(row,r)
 def body(owner,name):
  found=[r['body']for k,(_,r)in methods.items()if k.startswith(owner+'->'+name+'(')]
  if len(found)!=1:raise ValueError('Unique selected method: '+owner+' '+name)
  return found[0]
 def at(b,pc,ending):
  i=next(i for i in b['instructions']if i['pc']==pc)
  assert i.get('reference','').endswith(ending)
  return i
 core_names={'getCredentialTypeForUser','getKeyguardStoredPasswordQuality','getActivePasswordQuality','getLockoutEndTime','isSecure','isLockScreenDisabled','credentialTypeToPasswordQuality','invalidateCredentialTypeCache','invalidateLockoutEndTimeCache'}
 selected=[]
 for key,(row,r) in methods.items():
  b=r['body']
  if b['owner']==LPU and b['signature'].split('(')[0]not in core_names:continue
  # Publish only bounded derived sites and source pins, never OEM instruction bodies.
  selected.append({'method':key,'physicalDex':r['physicalDex'],'logicalHeaderOffset':r['logicalHeaderOffset'],'normalizedBodySha256':r['normalizedBodySha256'],'raw':row['raw'],'rawSha256':row['rawSha256'],'catchRegions':b['catches'],'sites':[{'pc':i['pc'],'opcode':i['opcode'],'reference':i['reference']} for i in b['instructions'] if 'reference' in i and (i.get('referenceKind') in ['method','field'])],'branchSites':[{'pc':i['pc'],**{k:v for k,v in i.items()if k in ['opcode','targetPc','switchElements']}}for i in b['instructions']if 'targetPc'in i or 'switchElements'in i]})
 for owner,ret,pin in [('1','Ljava/lang/Integer;','04b5a5473b4c8c0c6ea03ba00e93542deb4cd1018b3ae493a461c0580a50e2bc'),('2','Ljava/time/Duration;','e2bf187e88f264ab5f984e790d21282f04b2853808880ca89c0381589853e4a8')]:
  _,r=methods[LPU[:-1]+'$'+owner+';->apply(Ljava/lang/Integer;)'+ret]
  assert r['normalizedBodySha256']==pin
  ins={i['pc']:i for i in r['body']['instructions']}
  assert ins[19]['opcode']=='MOVE_EXCEPTION' and ins[19]['registers']==[0]
  assert ins[24]['registers']==[1,2,0]
  assert r['body']['catches']==[{'startPc':0,'codeUnits':18,'exceptionType':'Landroid/os/RemoteException;','handlerPc':19}]
 query=body('Landroid/app/PropertyInvalidatedCache;','query')
 for pc in [54,109]:
  at(query,pc,'->recompute(Ljava/lang/Object;)Ljava/lang/Object;')
  assert not any(c['startPc']<=pc<c['startPc']+c['codeUnits']for c in query['catches'])
 at(query,70,'->get(Ljava/lang/Object;)Ljava/lang/Object;');at(query,139,'->put(Ljava/lang/Object;Ljava/lang/Object;)V')
 assert next(i for i in query['instructions']if i['pc']==108)['opcode']=='RETURN_OBJECT'
 assert body('Landroid/app/PropertyInvalidatedCache;','recompute')['catches']==[]
 for name in ['getCredentialTypeForUser','getKeyguardStoredPasswordQuality','getActivePasswordQuality','getLockoutEndTime','isSecure']:
  assert body(LPU,name)['catches']==[]
 container='Lcom/android/keyguard/KeyguardSecurityContainerController;'
 finish=body(container,'showNextSecurityScreenOrFinish');assert finish['catches']==[]
 for pc in [210,261,357]:at(finish,pc,'->getSecurityMode(I)Lcom/android/keyguard/KeyguardSecurityModel$SecurityMode;')
 at(finish,391,'->isSecureLockDeviceEnabled()Lkotlinx/coroutines/flow/StateFlow;');at(finish,413,'->isAuthenticatedButPendingDismissal()Lkotlinx/coroutines/flow/StateFlow;');at(finish,602,'->finish(I)V')
 confirm=body('Lcom/oplus/settings/feature/password/ConfirmLockPasswordFragment;','onResume')
 assert confirm['catches']==[]
 at(confirm,7,'->getLockoutEndTime(I)Ljava/time/Duration;');at(confirm,95,'->mLockInput:Z');at(confirm,106,'->updateUi(Lcom/oplus/settings/feature/password/ConfirmLockPasswordFragment$Stage;)V')
 xrefs=[]
 for row,r in records:
  if r.get('record')=='reference'and row.get('key',{}).get('reference'):
   xrefs.append({'query':row['key']['reference'],'caller':r['caller'],'pc':r['instruction']['pc'],'raw':row['raw']})
 assert len(xrefs)==2 and all(x['pc']==2 and '->apply(Ljava/lang/Object;)'in x['caller']for x in xrefs)
 leafpath=OUT/'leaf-receipt.json';leaf=load(leafpath)if leafpath.exists()else None
 if leaf:
  for k in ['outputArchive','outputDex']:
   if sha(ROOT/leaf[k])!=leaf[k+'Sha256']:raise ValueError('Cold leaf drift')
  for r in leaf['reads']:
   if sha(ROOT/r['raw'])!=r['rawSha256']:raise ValueError('Cold leaf read drift')
  assert leaf['selected']is False and leaf['coldStartOnly']is True
  assert isinstance(leaf['requiredSelectionConditions'],list)and len(leaf['requiredSelectionConditions'])==8
  assert leaf['producerSha256']==sha(ROOT/'tools/build_coloros_readiness_leaf.py')
 report={'schema':'coloros-failure-readiness/v1','status':'SOURCE_ONLY_UNSELECTED; higher recovery and authority owner unassembled','inputs':{k:{'path':v[0],'sha256':v[1]}for k,v in ARCHIVES.items()},'toolSha256':sha(__file__),'sourceMethods':selected,'sourceMethodCount':len(selected),'receipts':[{'raw':r['raw'],'rawSha256':r['rawSha256'],'receipt':r.get('receipt',r.get('inheritedReceipt'))}for r in rows],'typedApplyDirectCallers':xrefs,'coldLeaf':None if not leaf else {'receipt':leafpath.relative_to(ROOT).as_posix(),'receiptSha256':sha(leafpath),'archive':leaf['outputArchive'],'archiveSha256':leaf['outputArchiveSha256'],'selected':False},'checks':{'twoExactCatchRegisterAndHandlerProofs':True,'queryRecomputeOutsideCatchAndHitReturnProved':True,'coreCacheConsumersNoCatchProved':True,'finishOriginalModeFactorAndFinishSitesProved':True,'settingsZeroClearAndUiSitesProved':True,'typedApplyOnlyBridgeDirectCallers':True,'allThreeSourceArchivesVerified':True},'requiredUnassembledOwnership':['Actual selected-user/current-authority generation admission before mode, confirmation, resume and finish','Invalidation/readback of both original PropertyInvalidatedCache keys on authority death/replacement/user/commit transitions; no stale-hit success','Owned protected unknown-state presentation and safe return, including queued input/progress/death/drain; throwing alone is not recovery','Actual StrongAuth/additional-factor policy applied before original finish; never initial false or fake credential type','Native Settings abort/retain on unavailability and uncertain write reconciliation, not no-credential creation or retry','Coherent source composition with other unselected leaves and installed-profile/ART/runtime validation'],'runtimeAccepted':False,'oemCodeExecuted':False,'phoneActions':0}
 if leaf:
  report.update({k:leaf[k]for k in ['sourceArchive','sourceArchiveSha256','patchedArchive','patchedArchiveSha256','selected','coldStartOnly','requiredSelectionConditions']})
 save(ROOT/'inventory/coloros-readiness.json',report)
 print('verified',len(selected),'method bodies; metadata inventory written')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');args=p.parse_args()
 if args.collect:collect()
 analyse()
