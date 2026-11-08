"""Three source-derived Samsung security resource lookups versus supplied ColorOS.

Only one hash-indexed regular tar member may be selectively copied. No links,
metadata restoration, OEM execution, phone access or reader-source mutation.
"""
from datetime import datetime,timezone
import gzip,hashlib,json,os,re,struct,subprocess,tarfile,uuid,zipfile
from pathlib import Path

R=Path(__file__).resolve().parent.parent;P=R.parent
SAMSUNG='86049c09ad8b1c6b955e681093915b4bd7d8b3aa9447066440034a46eb8ce290'
COLOROS='52c3fd4e8b251a861b5b0412f62af11749408fcd4561fdbb56b1df1b4bc7cd5e'
SERVICES='def967fbcb9498d530614b31b9c535540cb24ca5e6f20caf95f874bbe29639f6'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def table(path):
    entries={};current=None
    for line in path.read_text(encoding='utf-8').splitlines():
        m=re.match(r'^\s*resource (0x[0-9a-fA-F]+) (\S+)',line)
        if m:
            ident=int(m[1],16)
            if ident in entries:raise ValueError('Duplicate resource ID in framework table')
            current={'id':ident,'hex':f'0x{ident:08x}','name':m[2],'values':[]};entries[ident]=current
        elif current and (m:=re.match(r'^\s*\(([^)]*)\)\s+(.*)$',line)):current['values'].append({'qualifier':m[1],'literal':m[2]})
    if not entries:raise ValueError('No resource entries parsed')
    return entries
def summarize(entry):
    if entry is None:return None
    defaults=[v['literal'] for v in entry['values'] if not v['qualifier']]
    if len(defaults)!=1:raise ValueError('Expected one explicit default scalar for selected resource')
    literal=defaults[0]
    value=False if literal=='false' else True if literal=='true' else json.loads(literal) if literal.startswith('"') else literal
    return {'id':entry['id'],'hex':entry['hex'],'name':entry['name'],'type':entry['name'].split('/',1)[0],'defaultValue':value,'defaultAaptLiteral':literal,
        'configurationCount':len(entry['values']),'allConfigurationLiteralsSha256':hashlib.sha256(json.dumps(entry['values'],sort_keys=True).encode()).hexdigest()}
def acquire():
    report_path=P/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/report.json';report=json.loads(report_path.read_text())
    if sha(report_path)!='c1785505f9f01ac922c48dc31e3fd8e2489630a9730489fc5bd27dcfaf9a8733':raise ValueError('Independent parent manifest report changed')
    manifest=report_path.parent/'samsung-manifest.jsonl.gz'
    if sha(manifest)!=report['outputs'][manifest.name]:raise ValueError('Parent physical file map changed')
    with gzip.open(manifest,'rt',encoding='utf-8') as f:members=[row for line in f if (row:=json.loads(line))['path']=='system/framework/framework-res.apk']
    if len(members)!=1 or members[0]['kind']!='file' or members[0]['sha256']!=SAMSUNG:raise ValueError('Exact regular framework-res source record required')
    record=members[0];raw=R/'firmware/resource-compat';raw.mkdir(parents=True,exist_ok=True);dest=raw/'samsung-framework-res.apk';archive=P/report['samsungArchive']
    if archive.stat().st_size!=20434769920:raise ValueError('Named immutable source archive size changed')
    if not dest.exists():
        partial=raw/('framework-res-'+uuid.uuid4().hex+'.partial')
        with tarfile.open(archive,'r:') as tar:
            selected=[item for item in tar if item.name.rstrip('/')==record['originalPath']]
            if len(selected)!=1 or not selected[0].isfile() or selected[0].size!=record['size']:raise ValueError('Only exact unique regular member may be read')
            with tar.extractfile(selected[0]) as source,partial.open('xb') as output:
                while data:=source.read(1024*1024):output.write(data)
        if sha(partial)!=SAMSUNG or partial.stat().st_size!=record['size']:raise ValueError('Selected regular member hash/length differs')
        partial.rename(dest)
    if sha(dest)!=SAMSUNG:raise ValueError('Selective framework-res bytes changed')
    color=P/'firmware/donor/extracted/system/framework/framework-res.apk'
    if sha(color)!=COLOROS:raise ValueError('Supplied ColorOS framework-res identity differs')
    return dest,color,{'manifestReport':str(report_path),'manifestReportSha256':sha(report_path),'physicalManifestSha256':sha(manifest),'selectedRegularMember':record,
        'sourceTar':str(archive),'sourceTarDeclaredSha256':report['samsungArchiveSha256'],'sourceTarWholeHashFreshlyRecomputed':False,'selectedMemberHashFreshlyVerified':True,'symlinkExtraction':False}
def callsites():
    definitions=[('out/tooling/20261105T123610183210Z-3ae13072e1c8485f8b85ebc47565732e/receipt.json','Lcom/android/server/biometrics/SemUtils;','isKeyguard(Landroid/content/Context;Ljava/lang/String;)Z',18,17040392,'getString'),
        ('out/tooling/20261105T123454212027Z-7bee1deb9d7c403087492c4d788a2cd6/receipt.json','Lcom/android/server/locksettings/LockSettingsService;','<init>(Lcom/android/server/locksettings/LockSettingsService$Injector;)V',0x1c2,17891991,'getBoolean'),
        ('out/tooling/20261105T123454212027Z-7bee1deb9d7c403087492c4d788a2cd6/receipt.json','Lcom/android/server/locksettings/LockSettingsService;','migrateUserToSpWithBoundKeysLocked(I)V',0x59,17891665,'getBoolean')]
    out=[]
    for name,owner,signature,pc,ident,getter in definitions:
        receipt=R/name;receipt_pin=sha(receipt);proof=json.loads(receipt.read_text());raw=R/proof['raw'];raw_pin=sha(raw)
        if proof['archiveSha256']!=SERVICES or sha(Path(proof['archive']))!=SERVICES or sha(raw)!=proof['rawSha256']:raise ValueError('Exact source/raw callsite identity differs')
        rows=[r for l in raw.read_text(encoding='utf-8').splitlines() if (r:=json.loads(l))['record']=='method' and r['body']['owner']==owner and r['body']['signature']==signature]
        if len(rows)!=1:raise ValueError('Selected original method ambiguous/absent')
        row=rows[0];instructions=row['body']['instructions'];literal=[i for i in instructions if i['pc']==pc]
        if len(literal)!=1 or literal[0].get('literal')!=ident or literal[0]['opcode']!='CONST':raise ValueError('Original resource literal changed')
        target=[i for i in instructions if i['pc']==pc+3]
        expected='Landroid/content/res/Resources;->'+('getString(I)Ljava/lang/String;' if getter=='getString' else 'getBoolean(I)Z')
        if len(target)!=1 or target[0].get('reference')!=expected or target[0]['registers'][-1]!=literal[0]['registers'][0]:raise ValueError('Literal/getter direct register edge changed')
        # Independent raw byte check of the actual literal at the full-container
        # code_item selected by exact method signature. No source decoder mutation.
        import runpy
        RawDex=runpy.run_path(str(R/'out/tooling/verify_actual.py'))['RawDex']
        with zipfile.ZipFile(proof['archive']) as archive:data=archive.read(row['physicalDex'])
        decoder=RawDex(data,row['logicalHeaderOffset']);_,code=decoder.declared(owner)[signature]
        if struct.unpack_from('<i',data,code+16+pc*2+2)[0]!=ident:raise ValueError('Independent original literal bytes differ')
        callee_index=struct.unpack_from('<H',data,code+16+(pc+3)*2+2)[0]
        if decoder.method(callee_index)!=expected:raise ValueError('Independent original getter reference bytes differ')
        if sha(receipt)!=receipt_pin or sha(raw)!=raw_pin:raise ValueError('Callsite proof changed during audit')
        out.append({'evidenceKind':'observed-source-fact','owner':owner,'signature':signature,'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],
            'literalPcCodeUnits':pc,'literalPcHex':hex(pc),'resourceId':ident,'resourceIdHex':f'0x{ident:08x}','getterPcCodeUnits':pc+3,'getter':expected,
            'directRegisterEdgeVerified':True,'independentLiteralAndGetterBytesVerified':True,'receiptRawPinsVerifiedBeforeAndAfter':True,'normalizedBodySha256':row['normalizedBodySha256'],'receipt':name,'receiptSha256':receipt_pin,'raw':proof['raw'],'rawSha256':proof['rawSha256'],
            'internalBiometricPermissionStringPresent':'string=android.permission.USE_BIOMETRIC_INTERNAL' in [i.get('reference') for i in instructions]})
    return out
def main():
    samsung,coloros,acquisition=acquire();aapt=P/'out/toolchain/android-sdk/build-tools/37.0.0/aapt2.exe'
    if sha(aapt)!='4b09f89d449cc4498fcf5076a4ad6b28f079e565d2737f7881a674580960c8df':raise ValueError('Existing AAPT2 source identity differs')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex;rawdir=R/'firmware/resource-compat'/stamp;rawdir.mkdir(exist_ok=False);work=R/'out/resource-compat'/stamp;work.mkdir(parents=True);temp=work/'tmp';temp.mkdir();tables={};dumps={}
    pins={str(path):sha(path) for path in [samsung,coloros,aapt,Path(__file__).resolve(),R/'tools/static_security_reader.py',R/'tools/SecurityDexReader.java']}
    for side,path in [('samsung',samsung),('coloros',coloros)]:
        output=rawdir/(side+'-resources.txt')
        with output.open('xb') as f:result=subprocess.run([str(aapt),'dump','resources',str(path)],stdout=f,stderr=subprocess.PIPE,env=dict(os.environ,TMP=str(temp),TEMP=str(temp)),creationflags=subprocess.CREATE_NO_WINDOW)
        (work/(side+'-stderr.txt')).write_bytes(result.stderr)
        if result.returncode:raise RuntimeError('AAPT2 refused actual resource table')
        tables[side]=table(output);dumps[side]={'raw':output.relative_to(R).as_posix(),'sha256':sha(output),'resourceCount':len(tables[side])}
    sites=callsites();comparisons=[]
    for site in sites:
        ident=site['resourceId'];s=tables['samsung'].get(ident);c=tables['coloros'].get(ident)
        if s is None:raise ValueError('Actual Samsung literal has no source table entry')
        same_name=[v for v in tables['coloros'].values() if v['name']==s['name']]
        if len(same_name)!=1:raise ValueError('Expected one same-named ColorOS policy resource')
        ss,cc,nn=summarize(s),summarize(c),summarize(same_name[0])
        comparisons.append({'evidenceKind':'observed-resource-table-fact','callsite':site,'samsung':ss,'colorosSameNumericId':cc,'colorosSameName':nn,
            'sameIdNameMatches':ss['name']==cc['name'] if cc else False,'sameIdTypeMatches':ss['type']==cc['type'] if cc else False,
            'sameIdDefaultValueMatches':ss['defaultValue']==cc['defaultValue'] if cc else False,'sameNameIdMatches':ss['id']==nn['id'],'sameNameDefaultValueMatches':ss['defaultValue']==nn['defaultValue']})
    if any(sha(Path(name))!=h for name,h in pins.items()):raise ValueError('Input/tool changed during audit')
    record={'schema':'security-resource-compat/v1','scope':'Three observed Samsung service callsites and base APK resource tables only','acquisition':acquisition,'archives':{'samsungFrameworkRes':{'path':samsung.relative_to(R).as_posix(),'sha256':SAMSUNG,'bytes':samsung.stat().st_size},'colorosFrameworkRes':{'path':str(coloros),'sha256':COLOROS,'bytes':coloros.stat().st_size},'samsungServicesSha256':SERVICES},
        'sourceAndToolPinsVerifiedBeforeAndAfter':pins,'rawResourceDumps':dumps,'comparisons':comparisons,'selectedSites':3,'numericIdNameMismatches':sum(not c['sameIdNameMatches'] for c in comparisons),'sameNameBaseValueMismatches':sum(not c['sameNameDefaultValueMatches'] for c in comparisons),
        'inference':'Executing these unchanged Samsung compiled IDs against the supplied ColorOS base Resources is not resource-compatible. Two valid same-type IDs name unrelated entries, so type correctness is insufficient. One same-name policy default also differs; name-only ID remapping does not preserve the Samsung base configuration.',
        'missingEvidence':['Effective runtime RRO/idmap/AssetManager/configuration values were not queried','The supplied ColorOS resource APK is not proof of current installed guest resource state','A complete Samsung-service transitive resource contract and owned resource-compatible Context are not implemented','Resource compatibility does not establish caller/permission identity, HAL/credential/lockout/key namespace or runtime security acceptance'],
        'oemCodeExecuted':False,'androidExecuted':False,'phoneActions':False,'readerSourcesModified':False}
    (R/'inventory/resource-compat.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'selectedSites':3,'numericIdNameMismatches':record['numericIdNameMismatches'],'sameNameBaseValueMismatches':record['sameNameBaseValueMismatches'],'inventory':'inventory/resource-compat.json'}))
if __name__=='__main__':main()
