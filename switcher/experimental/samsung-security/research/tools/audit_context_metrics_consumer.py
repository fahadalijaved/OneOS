"""Bounded original metrics-consumer source and preservation-plan audit.

No runtime helper, DEX derivative, carrier, boot selection or OEM execution.
--report verifies fixed source/input pins and emits derived metadata only.
"""
import argparse,hashlib,json
from pathlib import Path
PROJECT=Path(__file__).resolve().parent.parent
PARENT=PROJECT.parent
SOURCES = [{'raw': 'firmware/context-metrics-consumer/20261105T210820875441Z-ca4cbb839dec416b85198c8500c6654d.jsonl',
  'rawSha256': '1a5d1c7ca7c4a1656000f9b78f73f42418f6b9f3b11ff91129e8aa78c8224e41',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210820875441Z-ca4cbb839dec416b85198c8500c6654d/receipt.json',
  'receiptSha256': 'b869eeae448acf018861cdb0e2e50f822f5896699d880ccb8a9ab80c23f2bc82'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210821629579Z-3673aa1f21444c608a74ad871e7d4df4.jsonl',
  'rawSha256': 'a2e584f2240abf072c36e223282571bb86e2adcce0a594a1aaa3c9943d2373d7',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210821629579Z-3673aa1f21444c608a74ad871e7d4df4/receipt.json',
  'receiptSha256': '0d475f4812889c47d5deabe41557f85ca289eff9d843fdba9d707740d3e2ed45'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210822447219Z-f906f23db0ab43c5ad0037658d9573f6.jsonl',
  'rawSha256': 'ee975a24505da44351918499c32a8a79510c4d91dac22906b135edfa5a803a40',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210822447219Z-f906f23db0ab43c5ad0037658d9573f6/receipt.json',
  'receiptSha256': 'b49324485b49e2bdbfc873d894f91d7e0b1c7e4540f9175c416ee309d5e52414'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210823252349Z-f3b067469d06448cad04c5a1949cd124.jsonl',
  'rawSha256': '718db5d8056f486b79c548de8824294a20ef304b3155ae3db3c398170f8df14c',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210823252349Z-f3b067469d06448cad04c5a1949cd124/receipt.json',
  'receiptSha256': '40bf3dd8460642c541e2446183b4a78895f0e44cac6e97b2be90e911ce52c8f7'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210824016958Z-1a660750c29b443c846c2eb5c79e6ca7.jsonl',
  'rawSha256': '45486d255d078c6cb41481565a212bbc20df910ac62e377bac136b61346302b6',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210824016958Z-1a660750c29b443c846c2eb5c79e6ca7/receipt.json',
  'receiptSha256': '885377856449bf30a031906a7f24d79095e00751029dd55d4d8c9c24f1f176d3'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210824799087Z-d71278cf7bfe40459a00739ce50fe0ab.jsonl',
  'rawSha256': '779122bfc404123e631fc05595f72a485fbf74865ce2ab9dd9f0a0b7478e7c81',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210824799087Z-d71278cf7bfe40459a00739ce50fe0ab/receipt.json',
  'receiptSha256': '027d8483473cd8514dec2b3d45f50021545014c0a39533527346c20128bdc8ed'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210920488865Z-e71fd54f6e5c4f44b5836a56b265bb0e.jsonl',
  'rawSha256': '8500650c4e5fd54d40e5628d5f46b6a2a1c7ebeb2a554b59937eec2fa3dfe363',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210920488865Z-e71fd54f6e5c4f44b5836a56b265bb0e/receipt.json',
  'receiptSha256': '4f01e742661a92f7cddc247409160c628c6e266afc8f9236b72e39b30e888529'},
 {'raw': 'firmware/context-metrics-consumer/20261105T210921239006Z-ef087688719748e9a08cc2829dd7f75d.jsonl',
  'rawSha256': 'e4e0c3515c33c0f1f7550ffac757365ed61c69685bd01100bb7dd20eaacaa012',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T210921239006Z-ef087688719748e9a08cc2829dd7f75d/receipt.json',
  'receiptSha256': 'bffd528918ef008671051c52bfee9d5d300b2a7638ef773be05aca97db0b399a'},
 {'raw': 'firmware/context-display-contract/20261105T194622852339Z-3efb22d1dc6c4a1d89b6bd466e42f6a6.jsonl',
  'rawSha256': '3d8c254b90c0bbf0bf65591eac4a6b21e297a9c5d32f7c612d3332458e387ec2',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T194622852339Z-3efb22d1dc6c4a1d89b6bd466e42f6a6/receipt.json',
  'receiptSha256': 'c7c4b8ec25e18d3e9a2678f6318f2ce5849645b033c6846c5f8b44b73c3054af',
  'select': ['getDisplayInfoInternal(I)Landroid/view/DisplayInfo;']},
 {'raw': 'firmware/context-display-contract/20261105T194644858309Z-32fd837e668043e280372b191a51323e.jsonl',
  'rawSha256': '0bad95aafc74769cc974a7835f0b80822e640a1b12eae20469c490db638f1c57',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T194644858309Z-32fd837e668043e280372b191a51323e/receipt.json',
  'receiptSha256': 'c6fee9a8ab226e3a8ee8fc5aed5b11030dcec6acadd594989f2380c22ae13e2b',
  'select': ['applyDisplaySandboxingIfNeeded(Landroid/view/DisplayInfo;)V']},
 {'raw': 'firmware/context-display-contract/20261105T195440124913Z-75599f76a5784b0aa4ba88116c54ee09.jsonl',
  'rawSha256': '9e956b1b6718cf161fdb213011cd615e7f02a6959e98e32faebae0c8f17be898',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T195440124913Z-75599f76a5784b0aa4ba88116c54ee09/receipt.json',
  'receiptSha256': '6001416bdab9ab6606a313b66dd92a3245aca51e46ae02d414735b735f5194b4',
  'select': ['getMetricsWithSize(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;II)V',
             'getAppMetrics(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;)V']},
 {'raw': 'firmware/authority-bootstrap-runtime/20261105T184435745232Z-0d61e68780894c568b45a02d3d532ec7.jsonl',
  'rawSha256': '765d6498307a534af6ae1a535fd4fcb6c940ccb9ea67113ae75f44f306054357',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T184435745232Z-0d61e68780894c568b45a02d3d532ec7/receipt.json',
  'receiptSha256': '40216d7fcdf4859400b34d94671688634560bf36ca31cd85c707686a6e1a11d5',
  'select': ['createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;']},
 {'raw': 'firmware/authority-bootstrap-runtime/20261105T185317614405Z-43eb2bc2017041198aeaebce05b83c7d.jsonl',
  'rawSha256': 'd4854f6f9505ac3ea5c52123ae3fd7fba8654f5fe43867e49da1726c6326b46b',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185317614405Z-43eb2bc2017041198aeaebce05b83c7d/receipt.json',
  'receiptSha256': '8328884605cf298f8c5f008abc2e21bb7043c99d20c48b20e9938aaa44ee97a3',
  'select': ['getDisplayMetrics()Landroid/util/DisplayMetrics;',
             'getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;']},
 {'raw': 'firmware/authority-bootstrap-runtime/20261105T185348796990Z-0b6e6667123c416598370a0049681368.jsonl',
  'rawSha256': 'ca8c6c365dd8e36e85f9b2f0682f6ce0a78f1594322d9d2d50db729d841c5a5b',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T185348796990Z-0b6e6667123c416598370a0049681368/receipt.json',
  'receiptSha256': '3d323abebdd40bdeb9011f1bbf582dd241e3e4da4e30b885b87bdc1f8b2beaa0',
  'select': ['getDisplayInfo(I)Landroid/view/DisplayInfo;']},
 {'raw': 'firmware/context-metrics-consumer/20261105T212208297948Z-ec1164aa5f4d471da5af69187c08eaed.jsonl',
  'rawSha256': 'ffbca3d076dbf8844915e1a66d4da08ec70e6bc3421900abc400d29f27e8e4f5',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T212208297948Z-ec1164aa5f4d471da5af69187c08eaed/receipt.json',
  'receiptSha256': '40afb402f8dcf52a72944bb6fb75c7edc94df008b3cc03815b887615748912e8'},
 {'raw': 'firmware/context-metrics-consumer/20261105T212223434388Z-fca843fc45c34bbf83b26a69a0de3323.jsonl',
  'rawSha256': 'a927b719ca6cda66bbe270094dcd818d1f716693f7b5b3698fadfcfc76647d0b',
  'archive': 'firmware/samsung/framework.jar',
  'archiveSha256': '8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe',
  'receipt': 'out/tooling/20261105T212223434388Z-fca843fc45c34bbf83b26a69a0de3323/receipt.json',
  'receiptSha256': '1dc6805f381e55ea1b5bc6cd22d89cee8b76e617806d92c581f30c773af23c50'}]

SF='8095a9aeda27b790756c31a015ccf3cbf4668f823e3ee9efb11363ac42ce71fe'
RM='Landroid/app/ResourcesManager;'
CI='Landroid/app/ContextImpl;'
DI='Landroid/view/DisplayInfo;'
SB='Lcom/samsung/android/core/CompatSandbox;'
AT='Landroid/app/ActivityThread;'
ADJ='Landroid/view/DisplayAdjustments;'
COMP='Landroid/content/res/CompatibilityInfo;'
WC='Landroid/app/WindowConfiguration;'
DMG='Landroid/hardware/display/DisplayManagerGlobal;'
METRICS='getMetricsWithSize(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;II)V'
APP='getAppMetrics(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;)V'
SANDBOX='applyDisplaySandboxingIfNeeded(Landroid/view/DisplayInfo;)V'
OVERLOAD='getDisplayMetrics(ILandroid/view/DisplayAdjustments;)Landroid/util/DisplayMetrics;'
INNER='createSystemContextInner(Landroid/app/ActivityThread;Landroid/app/LoadedApk;)Landroid/app/ContextImpl;'
INPUTS={'inventory/context-display-contract.json':'89c6320f961e7cd1cceb0d519ed79c5515c29b2e6f8e2493ad529fb82f505069','inventory/guest-metrics-producer.json':'0995fcd8238ca88e674cc7e6ef8d54e0e3b2433c0d84d864e0c795822d4161f9','compat/android/com/appleexploit/oneos/security/authority/PreparedGuestMetricsProducer.java':'72b0f4cdbb984c4d3b59724fd4c671771f8bf7e81c48184351e9ce77aa27b8f7','inventory/guest-metrics-producer-build.json':'cc4a619a9835ab409274887121ccacd19f2ab91516866234df8a3e3ab1af9d21'}

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def report():
    for path,pin in INPUTS.items():assert digest(PROJECT/path)==pin,path
    methods={};decl={}
    for src in SOURCES:
        assert digest(PARENT/src['archive'])==src['archiveSha256']
        assert digest(PROJECT/src['raw'])==src['rawSha256']
        assert digest(PROJECT/src['receipt'])==src['receiptSha256']
        receipt=json.loads((PROJECT/src['receipt']).read_text())
        assert receipt['readerExitCode']==0 and receipt['archiveAndToolPinsVerifiedBeforeAndAfter'] and not receipt['oemCodeExecuted']
        for line in (PROJECT/src['raw']).open(encoding='utf-8'):
            r=json.loads(line)
            if r['record']=='class':decl[r['descriptor']]=r
            elif r['record']=='method':
                b=r['body']
                if src.get('select') is not None and b['signature'] not in src['select']:continue
                key=(b['owner'],b['signature'])
                if key in methods:assert methods[key]['normalizedBodySha256']==r['normalizedBodySha256']
                methods[key]={**r,'raw':src['raw']}
    def method(owner,sig):return methods[(owner,sig)]
    def body(owner,sig):return method(owner,sig)['body']
    def at(owner,sig,pc):return next(i for i in body(owner,sig)['instructions'] if i['pc']==pc)
    def a(owner,sig,*checks):
        r=method(owner,sig);out=[]
        for pc,kind,wanted in checks:
            value=at(owner,sig,pc).get(kind)
            assert (wanted in value if isinstance(wanted,str) else wanted==value),(owner,sig,pc,value,wanted)
            out.append({'pc':pc,kind:value})
        return {'owner':owner,'signature':sig,'bodySha256':r['normalizedBodySha256'],'raw':r['raw'],'checks':out}
    facts=[]
    def f(identity,claim,*evidence):facts.append({'id':identity,'classification':'observed-source','claim':claim,'evidence':list(evidence)})
    f('M01','The exact context-only seam is decimal38/hex26, after original RM Configuration read and before original Resources.updateConfiguration.',
      a(CI,INNER,(32,'reference','ResourcesManager;->getConfiguration'),(38,'reference','ResourcesManager;->getDisplayMetrics()'),(38,'registers',[2]),(38,'codeUnits',3),(42,'reference','Resources;->updateConfiguration')))
    f('M02','Original noarg RM selects its actual display ID/default adjustments; overload reads actual adjustments and selects current RM config only under both original predicates.',
      a(RM,'getDisplayMetrics()Landroid/util/DisplayMetrics;',(0,'reference','mResDisplayId'),(2,'reference','DEFAULT_DISPLAY_ADJUSTMENTS')),
      a(RM,OVERLOAD,(19,'reference','getConfiguration'),(23,'reference','getCompatibilityInfo'),(27,'reference','mResDisplayId'),(29,'targetPc',41),(31,'reference','Configuration;->EMPTY'),(33,'reference','Configuration;->equals'),(37,'targetPc',41),(39,'reference','mResConfiguration'),(41,'reference','DisplayInfo;->getAppMetrics')))
    f('M03','Acquisition/allocation/policy ordering and genuine null fallback are source behavior; errors are not a null/default license.',
      a(RM,OVERLOAD,(0,'reference','DisplayManagerGlobal;->getInstance'),(4,'reference','DisplayMetrics;'),(6,'reference','DisplayMetrics;-><init>'),(11,'reference','getDisplayInfo'),(17,'targetPc',45),(19,'reference','getConfiguration'),(45,'reference','DisplayMetrics;->setToDefaults')))
    f('M04','Public DMG local-owner branch returns directly; only fallback getDisplayInfoInternal reaches selected CompatSandbox/callback work.',
      a(DMG,'getDisplayInfo(I)Landroid/view/DisplayInfo;',(0,'reference','mDmInternal'),(2,'targetPc',39),(34,'reference','DisplayManagerInternal;->getDisplayInfo'),(38,'opcode','RETURN_OBJECT'),(39,'reference','getDisplayInfoInternal')),
      a(DMG,'getDisplayInfoInternal(I)Landroid/view/DisplayInfo;',(66,'reference','CompatSandbox;->applyDisplaySandboxingIfNeeded'),(69,'reference','registerCallbackIfNeeded')))
    f('M05','Sandbox uses the real ActivityThread Configuration and private flag helper, and writes all four source dimension fields.',
      a(SB,SANDBOX,(0,'reference','ActivityThread;->currentActivityThread'),(6,'reference','ActivityThread;->getConfiguration'),(14,'literal',2),(15,'reference','hasCompatSandboxFlags'),(32,'reference','DisplayInfo;->appWidth'),(38,'reference','DisplayInfo;->appHeight'),(50,'reference','DisplayInfo;->logicalWidth'),(56,'reference','DisplayInfo;->logicalHeight')))
    f('M06','Original Configuration and bounds getters return actual owner aliases, not synthesized snapshots/default policy.',
      a(AT,'getConfiguration()Landroid/content/res/Configuration;',(2,'reference','ConfigurationController;->getConfiguration')),
      a('Landroid/app/ConfigurationController;','getConfiguration()Landroid/content/res/Configuration;',(0,'reference','mConfiguration')),
      a(RM,'getConfiguration()Landroid/content/res/Configuration;',(0,'reference','mResConfiguration')),
      a(WC,'getCompatSandboxFlags()I',(0,'reference','mCompatSandboxFlags')),
      a(WC,'getAppBounds()Landroid/graphics/Rect;',(0,'reference','mAppBounds')),
      a(WC,'getMaxBounds()Landroid/graphics/Rect;',(0,'reference','mMaxBounds')))
    f('M09','Invoking an additive static DisplayInfo helper still requires the original class initialization; selected initializer creates only the real Parcelable Creator, not a full DisplayInfo.',
      a(DI,'<clinit>()V',(0,'reference','DisplayInfo$1;'),(2,'reference','DisplayInfo$1;-><init>()V'),(5,'reference','DisplayInfo;->CREATOR')),
      a('Landroid/view/DisplayInfo$1;','<init>()V',(0,'reference','Object;-><init>()V')))
    m=body(DI,METRICS);app=body(DI,APP);sandbox=body(SB,SANDBOX)
    this_reads=[i for i in m['instructions'] if i['opcode'].startswith('IGET') and i.get('reference','').startswith(DI+'->')]
    assert [(i['pc'],i['reference'].split('->')[1],i['registers']) for i in this_reads]==[(0,'logicalDensityDpi:I',[0,2]),(6,'logicalDensityDpi:I',[0,2]),(38,'physicalXDpi:F',[0,2]),(44,'physicalYDpi:F',[2,2])]
    writes=[i for i in m['instructions'] if i['opcode'].startswith('IPUT')]
    assert len(writes)==14 and all(i['reference'].startswith('Landroid/util/DisplayMetrics;->') for i in writes)
    f('M07','Scalar algorithm has four receiver reads of three distinct fields; original config/font/bounds/compatibility and all14 output stores remain required.',
      a(DI,METRICS,(0,'reference','logicalDensityDpi'),(6,'reference','logicalDensityDpi'),(9,'literal',1003277517),(19,'reference','Configuration;->fontScale'),(29,'literal',1065353216),(38,'reference','physicalXDpi'),(44,'reference','physicalYDpi'),(54,'reference','WindowConfiguration;->getAppBounds'),(87,'reference','CompatibilityInfo;->applyDisplayMetricsIfNeeded')),
      a(DI,APP,(0,'reference','appWidth'),(2,'reference','appHeight'),(8,'reference','getMetricsWithSize')))
    f('M08','The retained original CompatibilityInfo method preserves global inverse scale AND inverse density scale, default comparison and per-app adjustment.',
      a(COMP,'applyDisplayMetricsIfNeeded(Landroid/util/DisplayMetrics;Z)V',(0,'reference','hasOverrideScale'),(6,'reference','sOverrideInvertedScale'),(8,'reference','sOverrideDensityInvertScale'),(10,'reference','scaleDisplayMetrics'),(14,'reference','DEFAULT_COMPATIBILITY_INFO'),(16,'reference','equals'),(22,'reference','applyToDisplayMetrics')))
    assert m['registerCount']==8 and m['accessFlags']==2 and app['registerCount']==10
    assert all(i['pc'] in [0,6,38] for i in m['instructions'] if i['pc']<44 and 2 in i.get('registers',[]))
    # This is a prototype/register arithmetic check, not generated DEX or an algorithm implementation.
    old_explicit={'metrics':3,'compatibility':4,'configuration':5,'width':6,'height':7}
    proposed_words=8;proposed_registers=11;new_first=proposed_registers-proposed_words
    assert new_first==3 and [new_first+i for i in range(5)]==list(old_explicit.values())
    scalar_edits=[]
    for i,source_reg in zip(this_reads,[8,8,9,10]):
        assert i['codeUnits']==2 and max(i['registers'][0],source_reg)<=15
        scalar_edits.append({'sourcePc':i['pc'],'sourceOpcode':i['opcode'],'sourceField':i['reference'],'sourceRegisters':i['registers'],'plannedReplacement':'MOVE (12x,1codeUnit) + NOP (1codeUnit)','destinationRegister':i['registers'][0],'scalarArgumentRegister':source_reg,'codeUnitsPreserved':2})
    # Sandbox data receiver reads nothing; preserve all four stores through new field refs.
    assert not any(i['opcode'].startswith('IGET') and i.get('reference','').startswith(DI+'->') for i in sandbox['instructions'])
    sandbox_writes=[i for i in sandbox['instructions'] if i['opcode'].startswith('IPUT') and i.get('reference','').startswith(DI+'->')]
    assert [(i['pc'],i['reference'].split('->')[1]) for i in sandbox_writes]==[(32,'appWidth:I'),(38,'appHeight:I'),(50,'logicalWidth:I'),(56,'logicalHeight:I')]
    assert not m['catches'] and not app['catches'] and not sandbox['catches']
    assert at(DI,APP,8)['opcode']=='INVOKE_DIRECT_RANGE' and at(DI,APP,8)['registerStart']==0 and at(DI,APP,8)['registerCount']==6
    # Existing moves save carrier/metrics/compat/config before the proposed staging overwrites v6..8.
    assert [at(DI,APP,pc)['registers'] for pc in [4,5,6,7]]==[[0,6],[1,7],[2,8],[3,9]]
    assert list(range(1,9))==[1,2,3,4,5,6,7,8] and max(range(1,9))<app['registerCount']
    def member(owner,kind,name):
        items=decl[owner]['methods' if kind=='method' else 'fields']
        x=next(x for x in items if (x['signature']==name if kind=='method' else x['name']==name))
        return {'owner':owner,'kind':kind,**x}
    members=[member(RM,'field','mResDisplayId'),member(RM,'field','mResConfiguration'),member(SB,'method','hasCompatSandboxFlags(Landroid/content/res/Configuration;I)Z'),member(DI,'method',METRICS),member(DI,'method',APP),member(RM,'method',OVERLOAD),member(AT,'method','getConfiguration()Landroid/content/res/Configuration;'),member(AT,'method','currentActivityThread()Landroid/app/ActivityThread;'),member(ADJ,'field','DEFAULT_DISPLAY_ADJUSTMENTS'),member(COMP,'method','applyDisplayMetricsIfNeeded(Landroid/util/DisplayMetrics;Z)V'),member(DMG,'field','mDmInternal')]
    assert members[0]['accessFlags']==2 and members[1]['accessFlags']==18 and members[2]['accessFlags']==10 and members[3]['accessFlags']==2
    plan={'status':'declarative-source-preservation-plan-not-implemented','noRuntimeCodeOrDexGenerated':True,'carrier':{'location':'Root-reviewed new public boot-visible primitive work-frame type, exact owner/name not selected','inputFields':['appWidth:I','appHeight:I','logicalDensityDpi:I','physicalXDpi:F','physicalYDpi:F'],'scratchWritesOnly':['sandboxLogicalWidth:I','sandboxLogicalHeight:I'],'scratchInputValuesRequired':False,'scratchNeverClaimsDisplayInfoPolicy':True,'visibility':'Cross-package field access needs public typed fields; constructor/factory can remain owned/package-scoped under reviewed loader API','lifetime':'One owned call/frame only; no guest Sample import, full DisplayInfo, publication or provenance claim'},'sandboxDerivative':{'declaringOwner':SB,'flags':'public static, same as source','parameterWords':1,'registerCount':sandbox['registerCount'],'onlySourceBodyEdits':[{'pc':i['pc'],'sourceField':i['reference'],'replacementField':'Root-reviewed work-frame.'+({'logicalWidth':'sandboxLogicalWidth','logicalHeight':'sandboxLogicalHeight'}.get(i['reference'].split('->')[1].split(':')[0],i['reference'].split('->')[1].split(':')[0]))+':I'} for i in sandbox_writes],'retainedPrivateHelper':'hasCompatSandboxFlags(Configuration,int)','preserveAllBranchesReferencesAndExceptions':True},'scalarDerivative':{'declaringOwner':DI,'flags':'private static (new member only)','proposedParameterDescriptors':['Landroid/util/DisplayMetrics;','Landroid/content/res/CompatibilityInfo;','Landroid/content/res/Configuration;','I','I','I','F','F'],'registerCount':proposed_registers,'parameterWordCount':proposed_words,'firstParameterRegister':new_first,'originalExplicitParameterRegistersPreserved':old_explicit,'rawArguments':{'logicalDensityDpi':8,'physicalXDpi':9,'physicalYDpi':10},'oldThisRegister2BecomesLocal':'No remaining read before first write atPC44; no fake/null/unused receiver needed','edits':scalar_edits,'remainingBodyAndBranchPcsMustRemainExact':True},'appWrapperDerivative':{'declaringOwner':DI,'flags':'public static (new member only)','incomingWords':'Real work-frame + original metrics/compat/config','registerCount':10,'sourceAppWidthHeightReads':'Retarget only PCs0/2 to actual work-frame fields','existingMovesRetainedAtPcs':[4,5,6,7],'stageRawFieldsAfterMoves':['v6 <- frame(v0).logicalDensityDpi','v7 <- frame(v0).physicalXDpi','v8 <- frame(v0).physicalYDpi'],'newInvoke':'INVOKE_STATIC_RANGE v1..v8 to scalar derivative (8words)','sourceInvokePc':8,'newInvokePcIfThree2CUReadsInserted':14,'branchAndTryRelocation':'Source wrapper has none; still require actual emitted/inverse proof'},'rmDerivative':{'declaringOwner':RM,'contextStaticEntry':'New owned static helper(ResourcesManager) with original noarg source body/prototype receiver transformed to first parameter; regcount3','overloadStaticEntry':'New owned static helper(ResourcesManager,int,DisplayAdjustments); regcount7, original owner/config register positions retained','privateAccessRetainedByOwner':True,'exactPolicyBodyRetained':'RM display/adjustments/config equals selection, allocation/null/default and original algorithm ordering','acquisitionChoiceOpen':['Retain real DMG.getInstance/null/local-vs-remote branch and project actual admitted owner(s); substituted getter must not claim old cache/callback effects','Explicitly replace acquisition with admitted scoped RAW source; preserve calculation order and genuine absence/error distinctions, while recording omitted/changed DMG/cache/callback construction obligations'],'applySandbox':'Only under the admitted original branch; finish it before RM adjustments/config selection, not after metrics'},'contextRetarget':{'owner':CI,'signature':INNER,'pcDecimal':38,'pcHex':'0x26','oldInvoke':'INVOKE_VIRTUAL ResourcesManager.getDisplayMetrics()','plannedInvoke':'INVOKE_STATIC owned ResourcesManager helper(ResourcesManager)','registers':[2],'instructionWidthCodeUnits':3,'sourceConfigurationRead32AndResourcesUpdate42Retained':True},'futureProofsRequired':['Exact input/header/constant-pool/member/class placement and boot loader admission','Originals preserved except bounded Context callsite; original metric/Sandbox/RM members remain intact alongside new derivatives','All old instruction/reference/branch/try/debug/body guards and all-method aliases/payload preservation','Exact additive derivative prototypes/register types and verifier/build/OAT constraints','Actual emitted inverse/roundtrip and direct-caller closure; none performed by this source design','Independent reentry/lifetime/subject/config generation/null/exception review before selection']}
    proof=[];sets=[]
    for (owner,sig),r in sorted(methods.items()):
        b=r['body'];proof.append({'owner':owner,'signature':sig,'bodySha256':r['normalizedBodySha256'],'accessFlags':b['accessFlags'],'registerCount':b['registerCount'],'instructionCount':len(b['instructions']),'physicalDex':r['physicalDex'],'logicalHeaderOffset':r['logicalHeaderOffset'],'raw':r['raw']})
        if (owner,sig) in [(DI,METRICS),(DI,APP),(SB,SANDBOX),(RM,OVERLOAD)]:
            sets.append({'owner':owner,'signature':sig,'fieldReads':[{'pc':i['pc'],'reference':i['reference']} for i in b['instructions'] if i['opcode'].startswith(('IGET','SGET'))],'fieldWrites':[{'pc':i['pc'],'reference':i['reference']} for i in b['instructions'] if i['opcode'].startswith(('IPUT','SPUT'))],'invokedReferences':[{'pc':i['pc'],'reference':i['reference']} for i in b['instructions'] if i['opcode'].startswith('INVOKE')],'exceptionHandlers':b['catches']})
    result={'schema':'context-metrics-consumer/v1','status':'source-design-awaiting-root-api-review','selected':False,'runtimeHelpersImplemented':False,'derivativeDexGenerated':False,'bootArtifactSelected':False,'oemExecuted':False,'phoneActions':False,'inputPins':INPUTS,'sources':SOURCES,'sourceAssertions':facts,'selectedMethodProofs':proof,'methodCount':len(proof),'directReadWriteReferenceSets':sets,'memberAccessEvidence':members,'sourceDerivedPlan':plan,'rawProducerContract':{'data':'Exactly five real guest quantities; DPI inputs are Java float-value raw-bit encodings, not native/wire bytes','decoderRequirement':'Mechanical intBitsToFloat at typed target boundary; no scaling, sanitizing, fabricated defaults or already-scaled guest Resources metrics','loader':'Do not reference private guest Sample from target boot classes; only reviewed RAW control/API values','admission':'Actual endpoint/source/display/caller/generation/use/retirement ownership remains external'},'algorithmOrder':['Context reads original RM configuration at32','RM selects actual display/default adjustments','Original acquisition owner obtained before DisplayMetrics allocation; raw owner substitution needs explicit review','Non-null selected fallback info passes original ActivityThread CompatSandbox before RM adjustment getters','RM reads DisplayAdjustments Configuration then CompatibilityInfo and performs exact display/EMPTY selection','Original getAppMetrics uses resulting app dimensions; scalar algorithm writes density,font-scale,DPI,actual appBounds dimensions then original CompatibilityInfo adjustment exactly once','Context updates actual Resources at42 using its earlier configuration reference and resulting metrics'],'unresolved':['Original local-DMI versus fallback path and acquisition-owner API choice; DMG.mDmInternal is private final, so RM cannot inspect it directly','Actual ActivityThread/ConfigurationController, RM/DisplayAdjustments/CompatibilityInfo ownership and updates; returned Configuration/Rect values are aliases','Boot-visible carrier and additive method class/member placement; child-loader same-package name is insufficient','RAW endpoint source/display/caller/generation/currentness and all retained callback/native/cache obligations','Actual thrown/absence outcome and publication admission; missing provider/error never becomes genuine absent display/default readiness','Original DisplayInfo class initialization/link timing must be admitted even without full object construction; do not silently shift required pre-Sandbox initialization','No emitted derivative, register verifier, inverse/all-method preservation or Android/OAT/runtime proof yet'],'limits':['Only selected direct source method/ref/access closure; no handported policy','No guessed Samsung/OPPO-only full DisplayInfo fields or fake full DisplayInfo','Three distinct receiver fields mean FOUR instruction edits','No new null/dummy/ready flag or new policy default supplied','Narrow Context projection is not a global DisplayManager replacement or complete security/Context bootstrap']}
    out=PROJECT/'inventory/context-metrics-consumer.json';out.write_text(json.dumps(result,indent=2)+'\n')
    work=PROJECT/'out/context-metrics-consumer';(work/'verification.json').write_text(json.dumps({'inventorySha256':digest(out),'toolSha256':digest(Path(__file__)),'sourceAssertionGroups':len(facts),'selectedMethods':len(proof),'scalarReadSites':len(this_reads),'distinctScalarFields':3,'metricOutputStores':len(writes),'sandboxOutputStores':len(sandbox_writes),'staticLayoutArithmeticVerified':True,'runtimeCodeGenerated':False,'oemExecuted':False},indent=2)+'\n')
    print(json.dumps({'inventorySha256':digest(out),'sourceGroups':len(facts),'methods':len(proof),'scalarReadSites':len(this_reads),'runtimeCodeGenerated':False}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',required=True,action='store_true');p.parse_args();report()
