import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;

/** One entire pinned ordinary039 input DEX, no edits or added definitions. */
final class ProbeSamsungFrameworkDex {
    static String q(String s){return SecurityDexReader.q(s);}
    static String sha(byte[]b)throws Exception{return SecurityDexReader.sha(b);}
    static String stats(){return "{\"fields\":"+ProbeSamsungDex041.fields+",\"methods\":"+ProbeSamsungDex041.methods+",\"instructions\":"+ProbeSamsungDex041.instructions+",\"tryBlocks\":"+ProbeSamsungDex041.tries+",\"debugItems\":"+ProbeSamsungDex041.debugItems+",\"annotationInstances\":"+ProbeSamsungDex041.annotationCount+",\"hiddenApiMembers\":"+ProbeSamsungDex041.hiddenMembers+",\"explicitInitialValues\":"+ProbeSamsungDex041.staticInitialValues+"}";}
    static String recordDigest(Map<String,String> rows)throws Exception{
        var d=java.security.MessageDigest.getInstance("SHA-256");
        for(var e:rows.entrySet()){byte[]k=e.getKey().getBytes(StandardCharsets.UTF_8),v=e.getValue().getBytes(StandardCharsets.UTF_8);d.update(java.nio.ByteBuffer.allocate(8).putInt(k.length).putInt(v.length).array());d.update(k);d.update(v);}
        return java.util.HexFormat.of().formatHex(d.digest());
    }
    /** Independent raw numeric policy/order view: does not call dexlib enum APIs. */
    static final class RawPolicy {
        final byte[] bytes;final int section,size,prefix;final List<String> classes=new ArrayList<>(),members=new ArrayList<>();
        final List<Boolean> presence=new ArrayList<>();final Map<String,Integer> flags=new LinkedHashMap<>();
        final String[] strings;int explicitClasses,absentClasses,numericMembers,absentMembers;
        int u16(int p){range(p,2);return (bytes[p]&255)|((bytes[p+1]&255)<<8);}
        int u32(int p){return Math.toIntExact(SecurityDexReader.u32(bytes,p));}
        void range(int p,int n){if(p<0||n<0||p>bytes.length-n)throw new IllegalArgumentException("Raw policy range");}
        int[] leb(int p){int start=p,value=0;for(int i=0;i<5;i++){range(p,1);int v=bytes[p++]&255;if(i==4&&(v&0xf0)!=0)throw new IllegalArgumentException("ULEB overflow");value|=(v&127)<<(i*7);if((v&128)==0)return new int[]{value,p,p-start};}throw new IllegalArgumentException("ULEB extent");}
        String string(int index){
            if(index<0||index>=strings.length)throw new IllegalArgumentException("Raw string index");if(strings[index]!=null)return strings[index];
            int p=u32(u32(60)+4*index);int[] length=leb(p);p=length[1];StringBuilder text=new StringBuilder();
            while(true){range(p,1);int a=bytes[p++]&255;if(a==0)break;char ch;
                if(a<128)ch=(char)a;
                else if((a&224)==192){range(p,1);int b=bytes[p++]&255;if((b&192)!=128)throw new IllegalArgumentException("MUTF8 continuation");int c=((a&31)<<6)|(b&63);if(c!=0&&c<128)throw new IllegalArgumentException("MUTF8 overlong");ch=(char)c;}
                else if((a&240)==224){range(p,2);int b=bytes[p++]&255,c=bytes[p++]&255;if((b&192)!=128||(c&192)!=128)throw new IllegalArgumentException("MUTF8 continuation");int v=((a&15)<<12)|((b&63)<<6)|(c&63);if(v<2048)throw new IllegalArgumentException("MUTF8 overlong");ch=(char)v;}
                else throw new IllegalArgumentException("Unsupported raw MUTF8 lead");
                text.append(ch);if(text.length()>1_000_000)throw new IllegalArgumentException("String bound");
            }
            if(text.length()!=length[0])throw new IllegalArgumentException("Raw UTF16 length");return strings[index]=text.toString();
        }
        String type(int index){if(index<0||index>=u32(64))throw new IllegalArgumentException("Raw type index");return string(u32(u32(68)+4*index));}
        String field(int index){if(index<0||index>=u32(80))throw new IllegalArgumentException("Raw field index");int p=u32(84)+8*index;return type(u16(p))+"->"+string(u32(p+4))+":"+type(u16(p+2));}
        String method(int index){
            if(index<0||index>=u32(88))throw new IllegalArgumentException("Raw method index");int p=u32(92)+8*index,proto=u16(p+2);if(proto>=u32(72))throw new IllegalArgumentException("Raw proto index");int pp=u32(76)+12*proto,list=u32(pp+8);StringBuilder sig=new StringBuilder(type(u16(p))).append("->").append(string(u32(p+4))).append('(');
            if(list!=0){int count=u32(list);if(count>65535)throw new IllegalArgumentException("Raw parameter count");range(list+4,count*2);for(int i=0;i<count;i++)sig.append(type(u16(list+4+2*i)));}return sig.append(')').append(type(u32(pp+4))).toString();
        }
        RawPolicy(byte[] bytes){
            this.bytes=bytes;if(!SecurityDexReader.headers(bytes).equals(List.of(0)))throw new IllegalArgumentException("Only intact ordinary selected DEX supported");
            strings=new String[u32(56)];int map=u32(52),count=u32(map),found=-1;
            if(count<1||count>64)throw new IllegalArgumentException("Raw map count");range(map+4,count*12);
            for(int i=0;i<count;i++){int p=map+4+12*i;if(u16(p)==0xf000){if(found!=-1||u32(p+4)!=1)throw new IllegalArgumentException("Hidden section identity");found=u32(p+8);}}
            if(found<0)throw new IllegalArgumentException("Hidden section absent");section=found;size=u32(section);int classCount=u32(96);prefix=4+classCount*4;range(section,size);if(size<prefix)throw new IllegalArgumentException("Hidden prefix size");
            int previousOffset=prefix;
            for(int ci=0;ci<classCount;ci++){
                int cp=u32(100)+32*ci;String owner=type(u32(cp));classes.add(owner);int relative=u32(section+4+ci*4);boolean present=relative!=0;presence.add(present);
                if(present){if(relative<previousOffset||relative>=size)throw new IllegalArgumentException("Hidden class offset/order");previousOffset=relative;explicitClasses++;}else absentClasses++;
                int data=u32(cp+24);if(data==0)continue;int pos=data;int[] counts=new int[4];for(int k=0;k<4;k++){int[]v=leb(pos);counts[k]=v[0];pos=v[1];if(counts[k]>100000)throw new IllegalArgumentException("Raw member count");}
                int flagPos=present?section+relative:-1;
                for(int k=0;k<4;k++){int index=0;for(int mi=0;mi<counts[k];mi++){
                    int[]delta=leb(pos);index=Math.addExact(index,delta[0]);pos=delta[1];int[] access=leb(pos);pos=access[1];if(k>=2){int[]code=leb(pos);pos=code[1];}
                    String member=k+":"+(k<2?field(index):method(index));if(!member.substring(2).startsWith(owner+"->"))throw new IllegalArgumentException("Member owner differs");members.add(member);int flag=-1;
                    if(present){int[]v=leb(flagPos);if(v[2]!=1||v[1]>section+size)throw new IllegalArgumentException("Exact target single-byte flags/extent required");flag=v[0];flagPos=v[1];numericMembers++;}else absentMembers++;
                    if(flags.put(member,flag)!=null)throw new IllegalArgumentException("Duplicate raw member");
                }}
                if(present){int end=size;for(int next=ci+1;next<classCount;next++){int off=u32(section+4+next*4);if(off!=0){end=off;break;}}if(flagPos!=section+end)throw new IllegalArgumentException("Hidden class payload does not close");}
            }
        }
        String summary()throws Exception{return "{\"sectionOffset\":"+section+",\"sectionBytes\":"+size+",\"prefixBytes\":"+prefix+",\"sectionSha256\":"+q(sha(Arrays.copyOfRange(bytes,section,section+size)))+",\"classes\":"+classes.size()+",\"members\":"+members.size()+",\"explicitClasses\":"+explicitClasses+",\"absentClasses\":"+absentClasses+",\"numericMembers\":"+numericMembers+",\"absentMembers\":"+absentMembers+",\"classOrderSha256\":"+q(ProbeSamsungDex041.hash(String.join("\n",classes)))+",\"memberOrderSha256\":"+q(ProbeSamsungDex041.hash(String.join("\n",members)))+",\"classPresenceSha256\":"+q(ProbeSamsungDex041.hash(presence.toString()))+",\"numericFlagsSha256\":"+q(ProbeSamsungDex041.hash(flags.toString()))+"}";}
    }
    static String lastRepair;
    static byte[] emitAndRestore(Collection<? extends ClassDef> classes,RawPolicy source,Path binary,String label)throws Exception{
        SourcePreservingDexPool pool=new SourcePreservingDexPool();for(ClassDef c:classes)pool.internClass(c);if(pool.hasOverflowed())throw new IllegalArgumentException("Pool overflow");
        MemoryDataStore store=new MemoryDataStore();byte[] emitted;try{pool.writeTo(store);emitted=store.getData();}finally{store.close();}
        ProbeSamsungDex041.validate(emitted);Files.write(binary.resolve(label+"-writer-unrepaired.dex"),emitted,StandardOpenOption.CREATE_NEW);
        RawPolicy destination=new RawPolicy(emitted);
        if(source.size!=130706||source.numericMembers!=99178||source.absentMembers!=1||source.explicitClasses!=6882||source.absentClasses!=999)throw new IllegalArgumentException("Pinned raw source profile differs");
        if(!source.classes.equals(destination.classes)||!source.members.equals(destination.members)||!source.presence.equals(destination.presence)||!source.flags.keySet().equals(destination.flags.keySet()))throw new IllegalArgumentException("Raw class/member/order/presence guard differs");
        if(source.size!=destination.size||source.prefix!=destination.prefix||!Arrays.equals(Arrays.copyOfRange(source.bytes,source.section,source.section+source.prefix),Arrays.copyOfRange(emitted,destination.section,destination.section+destination.prefix)))throw new IllegalArgumentException("Exact hidden section extent/header/relative offsets differ");
        int changedFlags=0;for(String member:source.members)if(!source.flags.get(member).equals(destination.flags.get(member)))changedFlags++;
        if(changedFlags!=28559)throw new IllegalArgumentException("Unexpected unrepaired raw mismatch count "+changedFlags);
        byte[] repaired=emitted.clone();System.arraycopy(source.bytes,source.section,repaired,destination.section,source.size);
        byte[] signature=java.security.MessageDigest.getInstance("SHA-1").digest(Arrays.copyOfRange(repaired,32,repaired.length));System.arraycopy(signature,0,repaired,12,20);Adler32 checksum=new Adler32();checksum.update(repaired,12,repaired.length-12);long value=checksum.getValue();for(int i=0;i<4;i++)repaired[8+i]=(byte)(value>>>(8*i));
        ProbeSamsungDex041.validate(repaired);RawPolicy exact=new RawPolicy(repaired);
        if(!source.flags.equals(exact.flags)||!source.classes.equals(exact.classes)||!source.members.equals(exact.members)||!source.presence.equals(exact.presence)||!Arrays.equals(Arrays.copyOfRange(source.bytes,source.section,source.section+source.size),Arrays.copyOfRange(repaired,exact.section,exact.section+exact.size)))throw new IllegalArgumentException("Raw numeric policy restoration failed");
        int changedBytes=0;for(int i=0;i<emitted.length;i++)if(emitted[i]!=repaired[i]){changedBytes++;if(!(i>=8&&i<32)&&!(i>=destination.section&&i<destination.section+destination.size))throw new IllegalArgumentException("Repair escaped section/integrity whitelist");}
        lastRepair="{\"label\":"+q(label)+",\"sourceRawPolicy\":"+source.summary()+",\"unrepairedRawPolicy\":"+destination.summary()+",\"repairedRawPolicy\":"+exact.summary()+",\"unrepairedChangedNumericMembers\":"+changedFlags+",\"repairedChangedNumericMembers\":0,\"repairChangedBytes\":"+changedBytes+",\"wholeSectionByteEqual\":true,\"classMemberOrderPresenceAndOffsetsGuarded\":true}";
        return repaired;
    }
    public static void main(String[]a)throws Exception{
        if(a.length!=3)throw new IllegalArgumentException("framework.jar exclusive-firmware-raw-dir exclusive-out-dex-dir");
        Path raw=Path.of(a[1]),binary=Path.of(a[2]);if(!Files.isDirectory(raw)||!Files.isDirectory(binary))throw new IllegalArgumentException("Exclusive directories required");
        byte[]input;
        try(ZipFile z=new ZipFile(a[0])){
            if(z.stream().filter(e->e.getName().equals("classes3.dex")).count()!=1)throw new IllegalArgumentException("Unique classes3.dex required");
            var e=z.getEntry("classes3.dex");if(e.getSize()!=8830032)throw new IllegalArgumentException("Pinned selected DEX length");
            try(var in=z.getInputStream(e)){input=in.readNBytes(8830033);}
        }
        if(input.length!=8830032||!sha(input).equals("256cc1744c36a88d3ee4c9218d2cf0156816ce89a63cd98787dd1633edbdf1a7"))throw new IllegalArgumentException("Selected DEX SHA/extent differs");
        ProbeSamsungDex041.validate(input);
        if(SecurityDexReader.u32(input,88)!=65412||SecurityDexReader.u32(input,96)!=7881)throw new IllegalArgumentException("Original pool/declaration counts differ");
        var originalDex=new DexBackedDexFile(Opcodes.forApi(29),input);
        RawPolicy sourcePolicy=new RawPolicy(input);
        if(originalDex.getMapItemForSection(0xf000)==null)throw new IllegalArgumentException("Expected actual source hidden-API section");
        Collection<? extends ClassDef> originals=originalDex.getClasses();
        if(originals.size()!=7881)throw new IllegalArgumentException("No subset/filtering permitted");
        System.err.println("stage=normalize-original");
        Map<String,String> before=ProbeSamsungDex041.normalize(originals);String originalStats=stats();
        if(ProbeSamsungDex041.hiddenMembers==0)throw new IllegalArgumentException("Hidden-API source section was not decoded as nonempty restrictions");
        ProbeSamsungDex041.saveRows(raw.resolve("original-normalized.jsonl"),before);
        String beforeDigest=recordDigest(before);
        System.err.println("stage=emit-first");
        byte[]first=emitAndRestore(originals,sourcePolicy,binary,"first");String firstRepair=lastRepair;ProbeSamsungDex041.validate(first);
        Files.write(binary.resolve("classes3-noedit-039.dex"),first,StandardOpenOption.CREATE_NEW);
        System.err.println("stage=normalize-decoded");
        var firstDex=new DexBackedDexFile(Opcodes.forApi(29),first);
        if(firstDex.getClasses().size()!=7881||firstDex.getMapItemForSection(0xf000)==null)throw new IllegalArgumentException("Class or hidden-API section loss");
        Map<String,String> after=ProbeSamsungDex041.normalize(firstDex.getClasses());String decodedStats=stats();
        ProbeSamsungDex041.saveRows(raw.resolve("decoded-normalized.jsonl"),after);
        ProbeSamsungDex041.same(before,after);
        if(!originalStats.equals(decodedStats))throw new IllegalArgumentException("Category counts differ");
        after=null;System.err.println("stage=emit-second");
        byte[]second=emitAndRestore(firstDex.getClasses(),sourcePolicy,binary,"second");String secondRepair=lastRepair;ProbeSamsungDex041.validate(second);
        Files.write(binary.resolve("classes3-roundtrip-039.dex"),second,StandardOpenOption.CREATE_NEW);
        if(!Arrays.equals(first,second))throw new IllegalArgumentException("Second emission not byte identical");
        System.err.println("stage=normalize-roundtrip");
        Map<String,String> last=ProbeSamsungDex041.normalize(new DexBackedDexFile(Opcodes.forApi(29),second).getClasses());
        ProbeSamsungDex041.same(before,last);ProbeSamsungDex041.saveRows(raw.resolve("roundtrip-normalized.jsonl"),last);
        if(!originalStats.equals(stats()))throw new IllegalArgumentException("Roundtrip category counts differ");
        System.out.println("{\"status\":\"PASS_NO_EDIT_FULL_SELECTED_DEX_ONLY\",\"profile\":\"v2-exact-initializers-and-raw-hiddenapi\",\"physicalDex\":\"classes3.dex\",\"sourceVersion\":39,\"sourceHeaderOffset\":0,\"sourceClasses\":7881,\"sourceMethodIds\":65412,\"sourceDexSha256\":"+q(sha(input))+",\"sourceBytes\":"+input.length+",\"normalizedRecords\":"+before.size()+",\"normalizedRecordsSha256\":"+q(beforeDigest)+",\"categoryCounts\":"+originalStats+",\"outputMethodIds\":"+SecurityDexReader.u32(first,88)+",\"outputFieldIds\":"+SecurityDexReader.u32(first,80)+",\"outputStrings\":"+SecurityDexReader.u32(first,56)+",\"outputBytes\":"+first.length+",\"outputDexSha256\":"+q(sha(first))+",\"roundtripDexSha256\":"+q(sha(second))+",\"allNormalizedMetadataEqual\":true,\"secondEmitByteIdentical\":true,\"actualNonemptyHiddenApiCompared\":true,\"independentAllRawFlagsEqual\":true,\"repairs\":["+firstRepair+","+secondRepair+"],\"androidExecuted\":false,\"oemExecuted\":false}");
    }
}
