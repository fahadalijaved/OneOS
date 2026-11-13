"""Offline bounded JNI/source/ELF linkage; never load or execute an OEM binary."""
import argparse,gzip,hashlib,json,lzma,re,runpy,struct,sys,tarfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;WORK=ROOT/'out/security-native';RAW=ROOT/'firmware/security-native'
MANIFEST=PARENT/'out/os-comparison-resumed/manifest-diff/20261105T002932626225Z-5567ad3e8a594767a4063bc762a88b84/samsung-manifest.jsonl.gz'
MANIFEST_SHA='6654252d9f7bde941e367fe79eb9af541869f4a1ddb5d1b8a0f0d4d6dde57a7a'
ARCHIVE=PARENT/'firmware/samsung/os-mirror-20261104/mounted-os-20261104T235732022961Z.tar'
MEMBERS=['system/lib64/libandroid_servers.so','system/lib64/libandroid_runtime.so']
MEMBER_PINS={
 'samsung:system/lib64/libandroid_servers.so':'9482076b93ae97db3cb0e4a2c6e45b93c6dc6fd7d264afe2df7e8bdd25d80a16',
 'samsung:system/lib64/libandroid_runtime.so':'f77d49dcfae7271ec3508cb06948218e65bdfbd1dc284797cb650b0db09af57d',
 'coloros:system/lib64/libandroid_servers.so':'dc919b691a30f60a6bf1e17aeff3a67b5226a50ebc699a07924c0bb208c8f651',
 'coloros:system/lib64/libandroid_runtime.so':'edfd170ccbca035d6acd8da1b93a346a7cb438f35cf706ba03037bdc1feb1279',
}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def packed_rela(blob):
    """Bounded APS2 decoding, checked against AOSP bionic relocation iterator."""
    if blob[:4]!=b'APS2':raise ValueError('Android packed RELA magic required')
    cursor=4
    def take():
        nonlocal cursor
        value=0;shift=0
        for _ in range(10):
            if cursor>=len(blob):raise ValueError('Short packed relocation')
            byte=blob[cursor];cursor+=1;value|=(byte&127)<<shift;shift+=7
            if byte&128==0:return value-(1<<shift)if byte&64 else value
        raise ValueError('Oversize SLEB128')
    count=take();offset=take();addend=0;info=0;result=[]
    if not 0<=count<=1000000:raise ValueError('Packed relocation count bound')
    while len(result)<count:
        size=take();flags=take()
        if size<=0 or size>count-len(result)or flags&~15:raise ValueError('Packed relocation group bounds')
        delta=take()if flags&2 else None
        if flags&1:info=take()
        mode=flags&12
        if mode==12:addend+=take()
        elif mode!=8:addend=0
        for _ in range(size):
            offset+=delta if flags&2 else take()
            if not flags&1:info=take()
            if mode==8:addend+=take()
            result.append({'target':offset,'type':info&0xffffffff,'symbolIndex':info>>32,'addend':addend})
    if cursor!=len(blob):raise ValueError('Unconsumed packed relocation bytes')
    return result
def elf(data):
    if data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Exact little-endian ELF64 required')
    off=struct.unpack_from('<Q',data,40)[0];size,count,ni=struct.unpack_from('<HHH',data,58)
    if size!=64 or count>8192 or ni>=count or off+64*count>len(data):raise ValueError('ELF section bounds')
    sec=[struct.unpack_from('<IIQQQQIIQQ',data,off+64*i)for i in range(count)]
    for s in sec:
        if s[1]!=8 and s[4]+s[5]>len(data):raise ValueError('ELF section outside file')
    def string_at(blob,i):
        if i>=len(blob):raise ValueError('ELF string outside table')
        end=blob.find(b'\0',i)
        if end<0:raise ValueError('ELF string is not terminated')
        return blob[i:end].decode('utf-8',errors='replace')
    names=data[sec[ni][4]:sec[ni][4]+sec[ni][5]];sections=[];symbols=[];needed=[];relocations=[]
    for s in sec:
        sections.append({'name':string_at(names,s[0]),'type':s[1],'address':s[3],'offset':s[4],'bytes':s[5]})
        if s[1]in [2,6,11]:
            if s[6]>=count:raise ValueError('ELF linked table outside sections')
            st=sec[s[6]];strings=data[st[4]:st[4]+st[5]]
            if s[1]==6:
                if s[9]!=16 or s[5]%16:raise ValueError('ELF dynamic shape')
                for o in range(s[4],s[4]+s[5],16):
                    tag,val=struct.unpack_from('<qQ',data,o)
                    if tag==1:needed.append(string_at(strings,val))
            else:
                if s[9]!=24 or s[5]%24:raise ValueError('ELF symbol shape')
                for o in range(s[4],s[4]+s[5],24):
                    n,info,other,index,val,sz=struct.unpack_from('<IBBHQQ',data,o)
                    symbols.append({'name':string_at(strings,n),'value':val,'size':sz,'type':info&15,'binding':info>>4,'sectionIndex':index})
        if s[1]==4:
            if s[9]!=24 or s[5]%24:raise ValueError('ELF RELA shape')
            for o in range(s[4],s[4]+s[5],24):
                target,info,addend=struct.unpack_from('<QQq',data,o);relocations.append({'target':target,'type':info&0xffffffff,'symbolIndex':info>>32,'addend':addend})
        if s[1]==0x60000002:relocations.extend(packed_rela(data[s[4]:s[4]+s[5]]))
    literals=[]
    for m in re.finditer(rb'[\x20-\x7e]{4,}\x00',data):
        text=m.group()[:-1].decode('ascii')
        if any(t in text.lower()for t in ['syntheticpassword','nativesid','nativescrypt','nativekdf','nativekbkdf','nativepbkdf','nativerbg','scrypt','jni_onload','register_com_android_server_locksettings','native_onboot']):literals.append({'fileOffset':m.start(),'text':text})
    return {'machine':struct.unpack_from('<H',data,18)[0],'sections':sections,'needed':sorted(set(needed)),'dynamicSymbols':symbols,'rela':relocations,'selectedLiterals':literals}

def collect_members():
    WORK.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True)
    if sha(MANIFEST)!=MANIFEST_SHA or ARCHIVE.stat().st_size!=20434769920:raise ValueError('Capture pin changed')
    rows={v['path']:v for l in gzip.open(MANIFEST,'rt',encoding='utf-8')if (v:=json.loads(l))['kind']=='file'and v['path']in MEMBERS}
    if set(rows)!=set(MEMBERS):raise ValueError('Exact required regular members missing')
    result={};seen=set()
    with tarfile.open(ARCHIVE,'r:')as tar:
        for member in tar:
            name=member.name.removeprefix('./')
            if name not in rows:continue
            expected=rows[name]
            if name in seen or not member.isfile()or member.size!=expected['size']or member.size>16*1024*1024:raise ValueError('Bounded unique regular member required')
            seen.add(name);data=tar.extractfile(member).read(16*1024*1024+1)
            if len(data)!=expected['size']or hashlib.sha256(data).hexdigest()!=expected['sha256']:raise ValueError('Captured member mismatch')
            path=RAW/'samsung'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            result['samsung:'+name]={'path':path.relative_to(ROOT).as_posix(),'sha256':expected['sha256'],'bytes':len(data),'archiveHeaderOffset':member.offset,'archiveDataOffset':member.offset_data}
            if seen==set(MEMBERS):break
    if seen!=set(MEMBERS)or sha(MANIFEST)!=MANIFEST_SHA:raise ValueError('Capture incomplete/drifted')
    donor_manifest=MANIFEST.with_name('coloros-manifest.jsonl.gz')
    donor_rows={v['path']:v for l in gzip.open(donor_manifest,'rt',encoding='utf-8')if (v:=json.loads(l))['kind']=='file'and v['path']in MEMBERS}
    for name,v in donor_rows.items():
        path=PARENT/'firmware/donor/extracted'/v['extractedPath']
        if path.stat().st_size!=v['size']or sha(path)!=v['sha256']:raise ValueError('Exact donor member changed')
        result['coloros:'+name]={'path':'../'+path.relative_to(PARENT).as_posix(),'sha256':v['sha256'],'bytes':v['size']}
    for k,v in result.items():
        if v['sha256']!=MEMBER_PINS[k]:raise ValueError('Explicit captured native identity required')
        parsed=elf((ROOT/v['path']).read_bytes());dest=RAW/(k.split(':')[0]+'-'+Path(k.split(':')[1]).name+'.elf.json');dest.write_text(json.dumps(parsed,indent=2)+'\n');v['staticElf']=dest.relative_to(ROOT).as_posix();v['staticElfSha256']=sha(dest)
    (WORK/'members.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'members':len(result),'oemExecuted':False}))

def collect_java():
    WORK.mkdir(parents=True,exist_ok=True);read=runpy.run_path(str(ROOT/'tools/static_security_reader.py'))['read_archive'];queries=[]
    pins={role:json.loads((PARENT/('out/os-comparison-resumed/archive-index/comparisons/'+role+'/summary.json')).read_text())for role in ['framework','system-server-services']}
    for side in ['samsung','coloros']:
        for role,owner,methods in [('system-server-services','com.android.server.locksettings.SyntheticPasswordManager',['scrypt([B[BIIII)[B']),('framework','android.security.Scrypt',['scrypt([B[BIIII)[B','nativeScrypt([B[BIIII)[B'])]:
            pin=pins[role][side];result=read(PARENT/pin['archive'],pin['archiveSha256'],class_name=owner,methods=methods,stream='security-native');queries.append({'side':side,'role':role,'kind':'exact methods','receipt':result['receipt']})
    pin=pins['system-server-services']['samsung']
    references=['Lcom/android/server/locksettings/SyntheticPasswordCrypto;->'+m for m in ['nativeKBKDF([B[B[BI)[B','nativeKDF([B[B[BI)[B','nativePBKDF2([B[BII)[B','nativeRBG(I)[B']]
    references+=['Lcom/android/server/locksettings/SyntheticPasswordManager;->nativeSidFromPasswordHandle([B)J']
    for ref in references:
        result=read(PARENT/pin['archive'],pin['archiveSha256'],reference=ref,stream='security-native');queries.append({'side':'samsung','role':'system-server-services','kind':'exact direct reference scan','target':ref,'receipt':result['receipt']})
    (WORK/'java-reads.json').write_text(json.dumps(queries,indent=2)+'\n');print(json.dumps({'pass':True,'queries':len(queries),'oemExecuted':False}))

def inspect_elf():
    # Stage the already present PC disassembler in this stream; no pip/install.
    wheel=PARENT/'out/toolchain/ghidra-12.1.4/ghidra_12.1.4_PUBLIC/Ghidra/Debug/Debugger-agent-dbgeng/pypkg/dist/capstone-5.0.6-py3-none-win_amd64.whl'
    if sha(wheel)!='761c3deae00b22ac697081cdae1383bb90659dd0d79387a09cf5bdbb22b17064':raise ValueError('Existing tool pin changed')
    package=WORK/'static-disassembler';package.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(wheel)as z:
        for item in z.infolist():
            if not item.filename.startswith('capstone/')or item.is_dir():continue
            dest=package/item.filename
            if not dest.resolve().is_relative_to(package.resolve())or item.file_size>32*1024*1024:raise ValueError('PC tool staging bounds')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(item))
    sys.path.insert(0,str(package));import capstone
    disassembler=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM);outputs={}
    for key,member in json.loads((WORK/'members.json').read_text()).items():
        path=ROOT/member['path'];data=path.read_bytes()
        if sha(path)!=member['sha256']or member['sha256']!=MEMBER_PINS[key]:raise ValueError('Exact native input changed')
        parsed=elf(data);sections=parsed['sections']
        def map_address(address,length=1):
            matches=[s for s in sections if s['type']!=8 and s['address']<=address and address+length<=s['address']+s['bytes']]
            if len(matches)!=1:raise ValueError('Unique file-backed native range required '+hex(address))
            return matches[0]['offset']+address-matches[0]['address']
        def cstring(address):
            off=map_address(address);end=data.find(b'\0',off)
            if end<off or end-off>1024:raise ValueError('Bounded native string required')
            return data[off:end].decode('ascii')
        debug=next(s for s in sections if s['name']=='.gnu_debugdata');mini=lzma.decompress(data[debug['offset']:debug['offset']+debug['bytes']])
        if len(mini)>16*1024*1024:raise ValueError('Debug metadata expansion bound')
        mini_path=RAW/(key.split(':')[0]+'-'+path.name+'.debug.elf');mini_path.write_bytes(mini);debug_symbols=elf(mini)['dynamicSymbols']
        functions=[];tables=[]
        wanted=['register_android_server_SyntheticPasswordManager','register_android_security_Scrypt','nativeSidFromPasswordHandle','nativeScrypt','JNI_OnLoad','AndroidRuntime8startReg','crypto_scrypt']
        all_symbols={s['name']:s for s in [*debug_symbols,*parsed['dynamicSymbols']]if s['sectionIndex']!=0}
        # Keep function boundaries from mini-debug symbols, even when dynsym is stripped.
        for name,sym in all_symbols.items():
            if sym['type']!=2 or not any(w in name for w in wanted)or sym['size']==0:continue
            off=map_address(sym['value'],sym['size']);instructions=[{'address':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str}for i in disassembler.disasm(data[off:off+sym['size']],sym['value'])]
            functions.append({'symbol':name,'address':sym['value'],'fileOffset':off,'bytes':sym['size'],'sha256':hashlib.sha256(data[off:off+sym['size']]).hexdigest(),'instructions':instructions})
        # Bounded helper immediately called by the exported Scrypt registrar.
        registrar=next((f for f in functions if 'register_android_security_Scrypt'in f['symbol']),None)
        if registrar:
            target=int(next(i['operands'][1:]for i in registrar['instructions']if i['mnemonic']=='bl'),16);off=map_address(target,320)
            functions.append({'symbol':'selected_Scrypt_registration_helper_320_byte_window','address':target,'fileOffset':off,'bytes':320,'sha256':hashlib.sha256(data[off:off+320]).hexdigest(),'instructions':[{'address':i.address,'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str}for i in disassembler.disasm(data[off:off+320],target)],'boundedWindowNotInferredFunctionSize':True})
        plt=next(s for s in sections if s['name']=='.plt');jump_slots=[r for r in parsed['rela']if r['type']==1026]
        def resolve_call(target):
            matches=[s for s in parsed['dynamicSymbols']if s['value']==target and s['sectionIndex']!=0]
            if matches:return {'kind':'defined dynamic symbol','symbol':matches[0]['name'],'target':target}
            if plt['address']+32<=target<plt['address']+plt['bytes'] and (target-plt['address']-32)%24==0:
                slot=(target-plt['address']-32)//24
                if slot>=len(jump_slots):raise ValueError('PLT slot bounds')
                reloc=jump_slots[slot];off=map_address(target,24);stub=list(disassembler.disasm(data[off:off+24],target))
                adrp=next(i for i in stub if i.mnemonic=='adrp'and i.op_str.startswith('x16,'));ldr=next(i for i in stub if i.mnemonic=='ldr'and i.op_str.startswith('x17,'));page=int(adrp.op_str.split('#')[1],16);disp=re.search(r'#(0x[0-9a-f]+|\d+)',ldr.op_str);got=page+(int(disp.group(1),0)if disp else 0)
                if got!=reloc['target']:raise ValueError('PLT instruction/relocation disagreement')
                return {'kind':'PLT verified against R_AARCH64_JUMP_SLOT','symbol':parsed['dynamicSymbols'][reloc['symbolIndex']]['name'],'target':target,'gotAddress':got}
            return {'kind':'internal target not symbol-resolved','target':target}
        call_edges=[]
        for f in functions:
            for ins in f['instructions']:
                if ins['mnemonic']=='bl':call_edges.append({'caller':f['symbol'],'pc':ins['address'],**resolve_call(int(ins['operands'][1:],16))})
        registration_tables=[];registrar_arguments=[]
        start_reg=next((f for f in functions if'AndroidRuntime8startReg'in f['symbol']),None)
        if start_reg:
            table=int(next(i['operands'].split('#')[1]for i in start_reg['instructions']if i['mnemonic']=='adr'and i['operands'].startswith('x21,')),16)
            bound=int(next(i['operands'].split('#')[1]for i in start_reg['instructions']if i['mnemonic']=='cmp'and i['operands'].startswith('x20,')),16)
            for reloc in parsed['rela']:
                if table<=reloc['target']<=table+bound and reloc['symbolIndex']<len(parsed['dynamicSymbols']):
                    symbol=parsed['dynamicSymbols'][reloc['symbolIndex']]['name']
                    if'register_android_security_Scrypt'in symbol:registration_tables.append({'caller':start_reg['symbol'],'tableAddress':table,'lastByteOffset':bound,'entryAddress':reloc['target'],'relocationType':reloc['type'],'symbol':symbol,'addend':reloc['addend']})
            if len(registration_tables)!=1:raise ValueError('Exact Scrypt registration-table entry required')
        for f in functions:
            if not('register_android_server_SyntheticPasswordManager'in f['symbol']or f['symbol']=='selected_Scrypt_registration_helper_320_byte_window'):continue
            registers={};classes=[];method_tables=[]
            for index,i in enumerate(f['instructions']):
                text=i['operands'];match=re.fullmatch(r'(x[12]), #(0x[0-9a-f]+)',text)
                if match and i['mnemonic']in ['adr','adrp']:registers[match.group(1)]=int(match.group(2),16)
                match=re.fullmatch(r'(x[12]), \1, #(0x[0-9a-f]+|\d+)',text)
                if match and i['mnemonic']=='add'and match.group(1)in registers:registers[match.group(1)]+=int(match.group(2),0)
                if i['mnemonic']=='ldr'and text=='x8, [x8, #0x30]'and'x1'in registers:classes.append({'pc':i['address'],'classNameAddress':registers['x1'],'className':cstring(registers['x1'])})
                if i['mnemonic']=='ldr'and text=='x8, [x8, #0x6b8]'and'x2'in registers:
                    count=next((p for p in f['instructions'][index+1:index+4]if p['mnemonic']=='mov'and p['operands'].startswith('w3, #')),None)
                    if count is None:raise ValueError('Exact RegisterNatives count required')
                    method_tables.append({'pc':i['address'],'methodTableAddress':registers['x2'],'methodCount':int(count['operands'].split('#')[1],0),'methodCountPc':count['address']})
            registrar_arguments.append({'registrar':f['symbol'],'findClassArguments':classes,'registerNativesArguments':method_tables})
        for literal in parsed['selectedLiterals']:
            if literal['text']not in ['nativeSidFromPasswordHandle','nativeScrypt']:continue
            sec=next(s for s in sections if s['type']!=8 and s['offset']<=literal['fileOffset']<s['offset']+s['bytes']);address=sec['address']+literal['fileOffset']-sec['offset'];needle=struct.pack('<Q',address);start=0;found=[]
            while(start:=data.find(needle,start))>=0:
                region=next((s for s in sections if s['name']=='.data.rel.ro'and s['offset']<=start and start+24<=s['offset']+s['bytes']),None)
                if region:
                    name,signature,target=struct.unpack_from('<QQQ',data,start);found.append({'name':cstring(name),'signature':cstring(signature),'functionAddress':target,'tableAddress':region['address']+start-region['offset'],'tableFileOffset':start,'targetFileOffset':map_address(target)})
                start+=1
            if len(found)!=1:raise ValueError('Unique selected JNI method triplet required')
            tables.extend(found)
        out=RAW/(key.split(':')[0]+'-'+path.name+'.disassembly.json');out.write_text(json.dumps({'source':member,'functions':functions,'jniMethodTriplets':tables,'registrarArguments':registrar_arguments,'resolvedDirectCalls':call_edges,'runtimeRegistrationTable':registration_tables,'selectedDebugSymbols':[s for s in debug_symbols if any(w.lower()in s['name'].lower()for w in wanted)],'pcDisassemblerSha256':sha(wheel),'oemExecuted':False},indent=2)+'\n');outputs[key]={'raw':out.relative_to(ROOT).as_posix(),'rawSha256':sha(out),'miniDebugSha256':sha(mini_path),'functionProofs':[{k:v for k,v in f.items()if k!='instructions'}for f in functions],'jniMethodTriplets':tables,'registrarArguments':registrar_arguments,'resolvedDirectCalls':call_edges,'runtimeRegistrationTable':registration_tables}
    (WORK/'native-analysis.json').write_text(json.dumps(outputs,indent=2)+'\n');print(json.dumps({'pass':True,'nativeInputs':len(outputs),'functions':sum(len(v['functionProofs'])for v in outputs.values()),'oemExecuted':False}))

def summarize():
    members=json.loads((WORK/'members.json').read_text());native=json.loads((WORK/'native-analysis.json').read_text());native_raw={};checks=[]
    for key,item in members.items():
        if item['sha256']!=MEMBER_PINS[key]or sha(ROOT/item['path'])!=item['sha256']:raise ValueError('Pinned native input changed')
        proof=native[key]
        if sha(ROOT/proof['raw'])!=proof['rawSha256']:raise ValueError('Native disassembly evidence drift')
        native_raw[key]=json.loads((ROOT/proof['raw']).read_text())
    def check(label,value):
        if not value:raise ValueError('Static assertion failed: '+label)
        checks.append({'assertion':label,'pass':True})
    def function(side,library,fragment):return next(f for f in native_raw[side+':system/lib64/'+library]['functions']if fragment in f['symbol'])
    sid=[function(side,'libandroid_servers.so','nativeSidFromPasswordHandle')for side in ['samsung','coloros']]
    check('exact SID native implementation bytes identical',sid[0]['sha256']==sid[1]['sha256']=='5a426f8390432a4986a136ac415d4aa4c401b4a736fb54199b501f6969b4bbc1'and sid[0]['bytes']==sid[1]['bytes']==116)
    jni_header=PARENT/'out/toolchain/jdk-21.0.13+9/include/jni.h'
    if sha(jni_header)!='99e64ebbe749e6df284f852f11b3c73f6ea97baf15120428f40f887fe0616e61':raise ValueError('Existing JNI ABI header changed')
    struct_text=jni_header.read_text().split('struct JNINativeInterface_ {',1)[1].split('\n};',1)[0];jni_slots=['reserved0','reserved1','reserved2','reserved3']+re.findall(r'\(JNICALL \*(\w+)\)',struct_text)
    abi={name:{'slot':jni_slots.index(name),'elf64ByteOffset':8*jni_slots.index(name)}for name in ['FindClass','RegisterNatives','GetPrimitiveArrayCritical','ReleasePrimitiveArrayCritical']}
    check('JNI ABI slots map actual registration and primitive critical calls',[abi[n]['elf64ByteOffset']for n in abi]==[0x30,0x6b8,0x6f0,0x6f8])
    for side,f in zip(['samsung','coloros'],sid):
        instructions={(i['mnemonic'],i['operands'])for i in f['instructions']};check(side+' SID function uses critical-array read at offset1 and abort release',all(v in instructions for v in [('ldr','x8, [x8, #0x6f0]'),('ldur','x21, [x0, #1]'),('mov','w3, #2'),('ldr','x8, [x8, #0x6f8]')])and sum(i['mnemonic']=='blr'for i in f['instructions'])==2 and not any(i['mnemonic']=='bl'for i in f['instructions']))
    for side in ['samsung','coloros']:
        data=native_raw[side+':system/lib64/libandroid_servers.so'];table=data['jniMethodTriplets'];args=data['registrarArguments'][0]
        check(side+' SID JNI triplet exact',len(table)==1 and table[0]['name']=='nativeSidFromPasswordHandle'and table[0]['signature']=='([B)J')
        check(side+' SID table points to inspected byte-identical function',table[0]['functionAddress']==function(side,'libandroid_servers.so','nativeSidFromPasswordHandle')['address'])
        check(side+' SID registrar resolves exact class and one-method table',len(args['findClassArguments'])==1 and args['findClassArguments'][0]['className']=='com/android/server/locksettings/SyntheticPasswordManager'and args['registerNativesArguments'][0]['methodTableAddress']==table[0]['tableAddress']and args['registerNativesArguments'][0]['methodCount']==1)
        check(side+' JNI_OnLoad reaches actual SPM registrar via validated PLT',any(e['caller']=='JNI_OnLoad'and e.get('symbol')=='_ZN7android48register_android_server_SyntheticPasswordManagerEP7_JNIEnv'for e in data['resolvedDirectCalls']))
        data=native_raw[side+':system/lib64/libandroid_runtime.so'];table=data['jniMethodTriplets'];args=data['registrarArguments'][0]
        check(side+' Scrypt JNI triplet and class exact',len(table)==1 and table[0]['name']=='nativeScrypt'and table[0]['signature']=='([B[BIIII)[B'and args['findClassArguments'][0]['className']=='android/security/Scrypt'and args['registerNativesArguments'][0]['methodTableAddress']==table[0]['tableAddress']and args['registerNativesArguments'][0]['methodCount']==1)
        check(side+' Scrypt table points to inspected wrapper',table[0]['functionAddress']==function(side,'libandroid_runtime.so','nativeScrypt')['address'])
        check(side+' runtime startReg table contains actual Scrypt registrar',len(data['runtimeRegistrationTable'])==1)
    # Normalize only checked intra-function branch targets, resolved call symbols,
    # and literal address pairs whose actual zero-terminated bytes are equal.
    def normalized(side,fragment):
        key=side+':system/lib64/libandroid_runtime.so';data=native_raw[key];f=function(side,'libandroid_runtime.so',fragment);instructions=f['instructions'];calls={e['pc']:e for e in data['resolvedDirectCalls']if e['caller']==f['symbol']};binary=(ROOT/members[key]['path']).read_bytes();sections=elf(binary)['sections'];replace={}
        def string_at_va(address):
            sec=next(s for s in sections if s['type']!=8 and s['address']<=address<s['address']+s['bytes']);off=sec['offset']+address-sec['address'];end=binary.find(b'\0',off)
            if end<off or end-off>1024:raise ValueError('Comparison literal bounds')
            return binary[off:end].decode('ascii')
        for index,i in enumerate(instructions[:-1]):
            if i['mnemonic']!='adrp':continue
            match=re.fullmatch(r'(x\d+), #(0x[0-9a-f]+)',i['operands']);following=instructions[index+1]
            if not match or following['mnemonic']!='add':raise ValueError('Unnormalized native address instruction')
            reg=match.group(1);add=re.fullmatch(reg+', '+reg+r', #(0x[0-9a-f]+|\d+)',following['operands'])
            if not add:raise ValueError('Nonliteral native address pair')
            literal=string_at_va(int(match.group(2),16)+int(add.group(1),0));replace[index]=('address-page-of-verified-string',reg,literal);replace[index+1]=('address-offset-of-verified-string',reg,literal)
        result=[]
        for index,i in enumerate(instructions):
            if index in replace:result.append(replace[index]);continue
            op=i['mnemonic'];text=i['operands']
            if op=='bl':
                edge=calls[i['address']]
                if 'symbol'not in edge:raise ValueError('Unresolved called native target')
                text='resolved-symbol:'+edge['symbol']
            elif op=='b'or op.startswith('b.')or op in ['cbz','cbnz','tbz','tbnz']:
                match=re.search(r'#(0x[0-9a-f]+)$',text)
                if not match:raise ValueError('Native branch address shape')
                target=int(match.group(1),16)
                if not f['address']<=target<f['address']+f['bytes']:raise ValueError('Native comparison leaves function')
                text=text[:match.start()]+'relative:'+str(target-f['address'])
            result.append((op,text))
        return result
    comparisons={}
    for fragment in ['nativeScrypt','crypto_scrypt']:
        host=normalized('samsung',fragment);guest=normalized('coloros',fragment);check(fragment+' checked instruction/control-flow/call/literal comparison',host==guest);comparisons[fragment]={'instructions':len(host),'normalizedSha256':hashlib.sha256(json.dumps(host,separators=(',',':')).encode()).hexdigest(),'normalization':'in-function targets, relocation/instruction-verified called symbol names, verified equal literal bytes; all other operands unchanged','underlyingLibcryptoImplementationOrRuntimeNotProved':True}
    java_proofs={};java_bodies={};references=[];receipts={};archive_checked={}
    def reuse(receipt,side,wanted,origin):
        p=ROOT/receipt;meta=json.loads(p.read_text());raw=ROOT/meta['raw']
        if sha(raw)!=meta['rawSha256']:raise ValueError('Saved Java evidence drift')
        if meta['archive']not in archive_checked:archive_checked[meta['archive']]=sha(meta['archive'])
        if archive_checked[meta['archive']]!=meta['archiveSha256']:raise ValueError('Saved Java archive drift')
        receipts[receipt]={'sha256':sha(p),'archiveSha256':meta['archiveSha256'],'raw':meta['raw'],'rawSha256':meta['rawSha256'],'origin':origin}
        for lineno,line in enumerate(raw.read_text().splitlines(),1):
            row=json.loads(line)
            if row['record']=='reference':references.append(dict(row,receipt=receipt))
            if row['record']!='method':continue
            body=row['body'];name=body['owner']+'->'+body['signature']
            if wanted is not None and name not in wanted:continue
            key=side+':'+name;java_bodies[key]=body;java_proofs[key]={'receipt':receipt,'raw':meta['raw'],'rawLine':lineno,'archiveSha256':meta['archiveSha256'],'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'normalizedBodySha256':row['normalizedBodySha256'],'accessFlags':body['accessFlags'],'hasCode':body['hasCode'],'instructionCount':len(body['instructions'])}
    for q in json.loads((WORK/'java-reads.json').read_text()):reuse(q['receipt'],q['side'],None,'this bounded selection')
    old=json.loads((ROOT/'inventory/credentials.json').read_text());spm='Lcom/android/server/locksettings/SyntheticPasswordManager;'
    for key in [side+':'+spm+'->sidFromPasswordHandle([B)J'for side in ['samsung','coloros']]+['samsung:'+spm+'->nativeSidFromPasswordHandle([B)J']:
        reuse(old['methodProofs'][key]['receipt'],key.split(':',1)[0],{key.split(':',1)[1]},'reused frozen credential body')
    crypto=json.loads((ROOT/'inventory/storage-keys.json').read_text())['javaStaticEvidence']['com.android.server.locksettings.SyntheticPasswordCrypto'];reuse(crypto['receipt'],'samsung',{'Lcom/android/server/locksettings/SyntheticPasswordCrypto;->'+p['signature']for p in crypto['methodProofs']},'reused frozen Crypto12 receipt')
    ctor=json.loads((ROOT/'inventory/construction-credentials.json').read_text())['methods']
    for name in [spm+'-><clinit>()V','Lcom/android/server/locksettings/LockSettingsService;-><clinit>()V']:
        if name in ctor:reuse(ctor[name]['receipt'],'samsung',{name},'reused construction initializer')
    for report,key,side,signature in [('startup-import','sharedReaderBodyEvidence','samsung','main([Ljava/lang/String;)V'),('construction-startup','methodEvidence','coloros','run()V')]:
        inventory=json.loads((ROOT/('inventory/'+report+'.json')).read_text());proof=next(p for p in inventory[key]if any(m['owner']=='Lcom/android/server/SystemServer;'and m['signature']==signature for m in p.get('selectedMethods',p.get('methodProofs',[]))))
        reuse(proof['receipt'],side,{'Lcom/android/server/SystemServer;->'+signature},'reused frozen startup library load')
    native_targets=['Lcom/android/server/locksettings/SyntheticPasswordCrypto;->'+m for m in ['nativeKBKDF([B[B[BI)[B','nativeKDF([B[B[BI)[B','nativePBKDF2([B[BII)[B','nativeRBG(I)[B']]
    for target in native_targets:check('no supplied-services direct callers of '+target,not any(v['instruction'].get('reference')==target for v in references))
    check('Samsung public instance SID wrapper',java_proofs['samsung:'+spm+'->sidFromPasswordHandle([B)J']['accessFlags']==1)
    check('guest protected instance SID wrapper',java_proofs['coloros:'+spm+'->sidFromPasswordHandle([B)J']['accessFlags']==4)
    check('Samsung private native instance SID declaration',java_proofs['samsung:'+spm+'->nativeSidFromPasswordHandle([B)J']['accessFlags']==258)
    declaration_evidence={}
    selected_types={spm,'Lcom/android/server/locksettings/SyntheticPasswordCrypto;','Lcom/android/server/locksettings/LockSettingsService;','Landroid/security/Scrypt;','Lcom/android/server/knox/dar/ddar/ta/TZNative;','Lcom/android/server/knox/dar/sdp/SdpManagerImpl;'}
    for role in ['framework','system-server-services']:
        summary=json.loads((PARENT/('out/os-comparison-resumed/archive-index/comparisons/'+role+'/summary.json')).read_text())
        for side in ['samsung','coloros']:
            source=summary[side];index=PARENT/source['declarations']
            if sha(index)!=source['declarationsSha256']:raise ValueError('Frozen native declaration index changed')
            for line in gzip.open(index,'rt',encoding='utf-8'):
                row=json.loads(line)
                if row.get('descriptor')not in selected_types or'methods'not in row:continue
                declaration_evidence[side+':'+row['descriptor']]={'archiveSha256':source['archiveSha256'],'declarations':source['declarations'],'declarationsSha256':source['declarationsSha256'],'physicalDex':row['physicalDex'],'logicalHeaderOffset':row['logicalHeaderOffset'],'methods':[m for m in row['methods']if m['accessFlags']&256 or m['name']=='sidFromPasswordHandle']}
    check('guest private native SID exact declaration',any(m['name']=='nativeSidFromPasswordHandle'and m['descriptor']=='([B)J'and m['accessFlags']==258 for m in declaration_evidence['coloros:'+spm]['methods']))
    for side in ['samsung','coloros']:check(side+' Scrypt package-private native exact descriptor',any(m['name']=='nativeScrypt'and m['descriptor']=='([B[BIIII)[B'and m['accessFlags']==256 for m in declaration_evidence[side+':Landroid/security/Scrypt;']['methods']))
    library_loads=[]
    for key,body in java_bodies.items():
        for index,i in enumerate(body['instructions']):
            if i.get('reference')=='Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V':library_loads.append({'caller':key,'pc':i['pc'],'precedingInstruction':body['instructions'][index-1]})
    check('both original startup loaders select android_servers',len(library_loads)==2 and all(v['precedingInstruction'].get('reference')=='string=android_servers'for v in library_loads))
    for owner in ['Lcom/android/server/locksettings/LockSettingsService;','Lcom/android/server/locksettings/SyntheticPasswordManager;','Lcom/android/server/locksettings/SyntheticPasswordCrypto;']:
        key='samsung:'+owner+'-><clinit>()V'
        if key in java_bodies:check(owner+' selected initializer does not load library',not any(i.get('reference','').startswith('Ljava/lang/System;->load')for i in java_bodies[key]['instructions']))
    result={'schema':'security-native-linkage-static/v1','status':'actual canonical native registration and core ABI source proofs; no private Samsung native binding or runtime acceptance implemented','nativeInputs':members,'nativeEvidence':native,'coreNativeComparison':{'sidByteIdentity':{'bytes':116,'sha256':sid[0]['sha256']},'scrypt':comparisons},'javaMethodProofs':java_proofs,'javaReceipts':receipts,'selectedNativeDeclarations':declaration_evidence,'selectedDirectReferences':references,'javaLibraryLoadSites':library_loads,'unusedNativeDeclarationTargets':native_targets,'sourceAssertions':checks,'sourceAssertionsPass':True,'formatReferences':[{'url':'https://android.googlesource.com/platform/bionic/+/refs/heads/main/linker/linker_reloc_iterators.h','blob':'c6a8cf620ab2f7d3ea1c7e921f12e06743265fa2','use':'APS2 decoder format only; not a claim about captured runtime behavior'},{'url':'https://developer.android.com/ndk/guides/jni-tips','use':'FindClass/JNI_OnLoad class-loader contract; not proof of candidate loader placement'}],'bindingFrontier':{'scrypt':'preserve genuine canonical android.security.Scrypt; exact Java/JNI/table/native call and checked code equivalence support guest delegation without Samsung runtime import; effective native/crypto owner remains runtime-unproved','sid':'both runtimes bind their own canonical SPM private instance native; private imported SPM needs an explicit source-closed callable/registration adapter or deliberate canonical placement before registration. Protected guest wrapper requires actual canonical receiver; none assembled','cryptoNativeDeclarations':'four extra public static native declarations have no direct calls in supplied Samsung services; selected real JNI tables register SID/Scrypt only. External/reflection/JNI references and other native images not excluded','conditionalDar':'separate SDP/TZ native declarations exist in supplied services; their reached feature paths and registration dependencies are outside demonstrated core closure; not blanket disabled or imported','hardware':'native SID format extraction/scrypt are not Gatekeeper verification, signed HAT, storage unlock or protected-key acceptance'},'toolSha256':sha(Path(__file__)),'oemExecuted':False,'jniExecuted':False,'servicesStarted':False,'phoneActions':False,'runtimeBehaviorVerified':False}
    result['jniAbiHeaderProof']={'path':jni_header.relative_to(PARENT).as_posix(),'sha256':sha(jni_header),'slots':abi,'purpose':'existing PC header confirms standard JNI slot labels; not an Android runtime execution claim'}
    (ROOT/'inventory/security-native-linkage.json').write_text(json.dumps(result,indent=2)+'\n');(WORK/'verification.json').write_text(json.dumps({'pass':True,'checks':len(checks),'javaMethods':len(java_proofs),'elfInputs':len(members),'nativeFunctions':sum(len(v['functionProofs'])for v in native.values()),'oemExecuted':False},indent=2)+'\n');print((WORK/'verification.json').read_text())

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--members',action='store_true');p.add_argument('--java',action='store_true');p.add_argument('--elf-analysis',action='store_true');a=p.parse_args()
    if a.members:collect_members()
    if a.java:collect_java()
    if a.elf_analysis:inspect_elf()
    if not(a.members or a.java or a.elf_analysis):summarize()
