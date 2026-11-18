import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.*;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.debug.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.dexlib2.iface.value.*;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;

/** Static subset re-emission. Raw normalizations in firmware/, generated DEX in out/. */
final class ProbeSamsungDex041 {
    static String q(String s) { return SecurityDexReader.q(s); }
    static String hash(String s)throws Exception{return SecurityDexReader.sha(s.getBytes(StandardCharsets.UTF_8));}
    static String join(Collection<String> a){return "["+String.join(",",a)+"]";}
    static String list(Iterable<? extends CharSequence>a){List<String>b=new ArrayList<>();for(CharSequence s:a)b.add(q(s.toString()));return join(b);}
    static String reference(Reference r){
        if(r instanceof MethodProtoReference p)return "proto:"+list(p.getParameterTypes())+":"+p.getReturnType();
        if(r instanceof MethodHandleReference h)return "handle:"+h.getMethodHandleType()+":"+reference(h.getMemberReference());
        if(r instanceof CallSiteReference c)return "callsite:"+q(c.getName())+":"+reference(c.getMethodHandle())+":"+q(c.getMethodName())+":"+reference(c.getMethodProto())+":"+encodedList(c.getExtraArguments());
        if(r instanceof MethodReference||r instanceof FieldReference||r instanceof TypeReference||r instanceof StringReference)return SecurityDexReader.ref(r);
        throw new IllegalArgumentException("Unnormalized reference type "+r.getClass().getName());
    }
    static String encodedList(Iterable<? extends EncodedValue>a){List<String>b=new ArrayList<>();for(EncodedValue v:a)b.add(encoded(v));return join(b);}
    static String elements(BasicAnnotation a){List<String>b=new ArrayList<>();for(AnnotationElement e:a.getElements())b.add(q(e.getName())+":"+encoded(e.getValue()));Collections.sort(b);return q(a.getType())+"{"+String.join(",",b)+"}";}
    static String annotations(Set<? extends Annotation>a){List<String>b=new ArrayList<>();for(Annotation n:a)b.add(n.getVisibility()+":"+elements(n));Collections.sort(b);return join(b);}
    static String encoded(EncodedValue v){
        if(v==null)return "absent";
        String x;
        switch(v.getValueType()){
        case ValueType.BYTE:x=""+((ByteEncodedValue)v).getValue();break;
        case ValueType.SHORT:x=""+((ShortEncodedValue)v).getValue();break;
        case ValueType.CHAR:x=""+(int)((CharEncodedValue)v).getValue();break;
        case ValueType.INT:x=""+((IntEncodedValue)v).getValue();break;
        case ValueType.LONG:x=""+((LongEncodedValue)v).getValue();break;
        case ValueType.FLOAT:x="bits:"+Integer.toUnsignedString(Float.floatToRawIntBits(((FloatEncodedValue)v).getValue()));break;
        case ValueType.DOUBLE:x="bits:"+Long.toUnsignedString(Double.doubleToRawLongBits(((DoubleEncodedValue)v).getValue()));break;
        case ValueType.STRING:x=q(((StringEncodedValue)v).getValue());break;
        case ValueType.TYPE:x=q(((TypeEncodedValue)v).getValue());break;
        case ValueType.FIELD:x=q(reference(((FieldEncodedValue)v).getValue()));break;
        case ValueType.ENUM:x=q(reference(((EnumEncodedValue)v).getValue()));break;
        case ValueType.METHOD:x=q(reference(((MethodEncodedValue)v).getValue()));break;
        case ValueType.METHOD_TYPE:x=q(reference(((MethodTypeEncodedValue)v).getValue()));break;
        case ValueType.METHOD_HANDLE:x=q(reference(((MethodHandleEncodedValue)v).getValue()));break;
        case ValueType.ARRAY:x=encodedList(((ArrayEncodedValue)v).getValue());break;
        case ValueType.ANNOTATION:x=elements((AnnotationEncodedValue)v);break;
        case ValueType.NULL:x="null";break;
        case ValueType.BOOLEAN:x=""+((BooleanEncodedValue)v).getValue();break;
        default:throw new IllegalArgumentException("Unnormalized encoded value "+v.getValueType());
        }
        return v.getValueType()+":"+x;
    }
    static String hidden(Set<HiddenApiRestriction> restrictions){List<String>b=new ArrayList<>();for(var r:restrictions)b.add(r.name());Collections.sort(b);return join(b);}
    static String debug(DebugItem d){
        String b=d.getDebugItemType()+":"+d.getCodeAddress();
        if(d instanceof LocalInfo l)b+=":"+q(l.getName())+":"+q(l.getType())+":"+q(l.getSignature());
        if(d instanceof StartLocal l)b+=":reg="+l.getRegister();
        else if(d instanceof EndLocal l)b+=":reg="+l.getRegister();
        else if(d instanceof RestartLocal l)b+=":reg="+l.getRegister();
        else if(d instanceof LineNumber l)b+=":line="+l.getLineNumber();
        else if(d instanceof SetSourceFile l)b+=":source="+q(l.getSourceFile());
        else if(!(d instanceof PrologueEnd)&&!(d instanceof EpilogueBegin))throw new IllegalArgumentException("Unnormalized debug item "+d.getDebugItemType());
        return q(b);
    }
    static long fields,methods,instructions,tries,debugItems,annotationCount,hiddenMembers,staticInitialValues;
    static Map<String,String> normalize(Collection<? extends ClassDef> classes){
        Map<String,String> rows=new TreeMap<>();fields=methods=instructions=tries=debugItems=annotationCount=hiddenMembers=staticInitialValues=0;
        for(ClassDef c:classes){
            annotationCount+=c.getAnnotations().size();
            rows.put(c.getType(),"class:"+c.getAccessFlags()+":"+q(c.getSuperclass())+":"+list(c.getInterfaces())+":"+q(c.getSourceFile())+":"+annotations(c.getAnnotations()));
            for(String partition:List.of("static","instance"))for(Field f:partition.equals("static")?c.getStaticFields():c.getInstanceFields()){
                fields++;annotationCount+=f.getAnnotations().size();if(!f.getHiddenApiRestrictions().isEmpty())hiddenMembers++;if(f.getInitialValue()!=null)staticInitialValues++;
                String k=c.getType()+"->"+f.getName()+":"+f.getType();
                if(rows.put(k,partition+":"+f.getAccessFlags()+":"+encoded(f.getInitialValue())+":"+annotations(f.getAnnotations())+":"+hidden(f.getHiddenApiRestrictions()))!=null)throw new IllegalArgumentException("Duplicate field");
            }
            for(String partition:List.of("direct","virtual"))for(Method m:partition.equals("direct")?c.getDirectMethods():c.getVirtualMethods()){
                methods++;annotationCount+=m.getAnnotations().size();if(!m.getHiddenApiRestrictions().isEmpty())hiddenMembers++;
                List<String> params=new ArrayList<>();for(MethodParameter p:m.getParameters()){annotationCount+=p.getAnnotations().size();params.add(q(p.getType())+":"+q(p.getName())+":"+q(p.getSignature())+":"+annotations(p.getAnnotations()));}
                String value=partition+":"+m.getAccessFlags()+":"+join(params)+":"+annotations(m.getAnnotations())+":"+hidden(m.getHiddenApiRestrictions());
                MethodImplementation impl=m.getImplementation();
                if(impl==null)value+=":noCode";
                else{
                    List<String> code=new ArrayList<>(),handlers=new ArrayList<>(),dbg=new ArrayList<>();int pc=0;
                    for(Instruction i:impl.getInstructions()){
                        if(++instructions>2_000_000)throw new IllegalArgumentException("Instruction bound");
                        String item=SecurityDexReader.instruction(i,pc);
                        // Include exact proto/handle/callsite values, never opaque toString identity.
                        if(i instanceof ReferenceInstruction r)item+="|ref="+reference(r.getReference());
                        if(i instanceof DualReferenceInstruction r)item+="|ref2="+reference(r.getReference2());
                        code.add(item);pc+=i.getCodeUnits();
                    }
                    for(var t:impl.getTryBlocks()){tries++;List<String> hs=new ArrayList<>();for(var h:t.getExceptionHandlers())hs.add(q(h.getExceptionType())+":"+h.getHandlerCodeAddress());handlers.add(t.getStartCodeAddress()+":"+t.getCodeUnitCount()+":"+join(hs));}
                    for(DebugItem d:impl.getDebugItems()){debugItems++;dbg.add(debug(d));}
                    value+=":code:"+impl.getRegisterCount()+":"+join(code)+":"+join(handlers)+":"+join(dbg);
                }
                if(rows.put(c.getType()+"->"+SecurityDexReader.signature(m),value)!=null)throw new IllegalArgumentException("Duplicate method");
            }
        }
        return rows;
    }
    static byte[] emit(Collection<? extends ClassDef> classes)throws Exception{
        if(VersionMap.mapApiToDexVersion(29)!=39)throw new IllegalArgumentException("Writer API29 no longer selects ordinary039");
        DexPool pool=new DexPool(Opcodes.forApi(29));for(ClassDef c:classes)pool.internClass(c);
        if(pool.hasOverflowed())throw new IllegalArgumentException("Subset pool overflow");
        MemoryDataStore store=new MemoryDataStore();try{pool.writeTo(store);return store.getData();}finally{store.close();}
    }
    static void validate(byte[]b)throws Exception{
        if(!SecurityDexReader.headers(b).equals(List.of(0))||!new String(b,4,3,StandardCharsets.US_ASCII).equals("039"))throw new IllegalArgumentException("Not standalone ordinary039");
        if(!Arrays.equals(Arrays.copyOfRange(b,12,32),java.security.MessageDigest.getInstance("SHA-1").digest(Arrays.copyOfRange(b,32,b.length))))throw new IllegalArgumentException("Output SHA1");
        Adler32 a=new Adler32();a.update(b,12,b.length-12);if(a.getValue()!=SecurityDexReader.u32(b,8))throw new IllegalArgumentException("Output Adler32");
    }
    static void saveRows(Path p,Map<String,String> rows)throws Exception{
        try(BufferedWriter out=Files.newBufferedWriter(p,StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW)){for(var e:rows.entrySet())out.write("{\"member\":"+q(e.getKey())+",\"sha256\":"+q(hash(e.getValue()))+",\"normalized\":"+q(e.getValue())+"}\n");}
    }
    static void same(Map<String,String>a,Map<String,String>b){
        if(!a.keySet().equals(b.keySet()))throw new IllegalArgumentException("Declarations differ");
        for(var e:a.entrySet())if(!e.getValue().equals(b.get(e.getKey())))throw new IllegalArgumentException("Preservation mismatch "+e.getKey());
    }
    public static void main(String[]args)throws Exception{
        if(args.length!=3)throw new IllegalArgumentException("pinned-services.jar exclusive-firmware-raw-dir exclusive-out-dex-dir");
        Path input=Path.of(args[0]),output=Path.of(args[1]),binary=Path.of(args[2]);
        if(!Files.isDirectory(output)||!Files.isDirectory(binary))throw new IllegalArgumentException("Explicit exclusive output directories required");
        Set<String> wanted=Set.of("Lcom/android/server/pm/UserManagerService;","Lcom/android/server/locksettings/LockSettingsService;");
        List<ClassDef> selected=new ArrayList<>();Map<String,Integer> locations=new TreeMap<>();List<String> headers=new ArrayList<>();
        try(ZipFile zip=new ZipFile(input.toFile())){
            var entries=zip.stream().filter(e->e.getName().matches("classes(?:[2-9]|[1-9][0-9]+)?\\.dex")).toList();if(entries.size()!=1)throw new IllegalArgumentException("Pinned single physical DEX expected");
            ZipEntry entry=entries.get(0);if(!entry.getName().equals("classes.dex")||entry.getSize()!=28157552)throw new IllegalArgumentException("Pinned physical DEX extent");
            byte[]container;try(var in=zip.getInputStream(entry)){container=in.readNBytes(28157553);}if(container.length!=28157552)throw new IllegalArgumentException("DEX bound");
            List<Integer> offsets=SecurityDexReader.headers(container);if(!offsets.equals(List.of(0,10057984)))throw new IllegalArgumentException("Pinned logical-header identities");
            for(int header:offsets){var dex=new SecurityDexReader.LogicalDex(container,header);var classes=dex.getClasses();if(classes.size()!=SecurityDexReader.u32(container,header+96))throw new IllegalArgumentException("Source declaration count");headers.add("{\"headerOffset\":"+header+",\"classCount\":"+classes.size()+"}");for(ClassDef c:classes)if(wanted.contains(c.getType())){if(locations.put(c.getType(),header)!=null)throw new IllegalArgumentException("Ambiguous selected class");selected.add(c);}}
        }
        if(!locations.keySet().equals(wanted))throw new IllegalArgumentException("Missing selected definition");
        Map<String,String> original=normalize(selected);long f=fields,m=methods,ins=instructions,tr=tries,dbg=debugItems,ann=annotationCount,hid=hiddenMembers,initial=staticInitialValues;
        saveRows(output.resolve("original-normalized.jsonl"),original);
        byte[]first=emit(selected);validate(first);Files.write(binary.resolve("subset-039.dex"),first,StandardOpenOption.CREATE_NEW);
        var decoded=new DexBackedDexFile(Opcodes.forApi(29),first);Map<String,String> after=normalize(decoded.getClasses());saveRows(output.resolve("decoded-normalized.jsonl"),after);same(original,after);
        byte[]second=emit(decoded.getClasses());validate(second);Files.write(binary.resolve("roundtrip-039.dex"),second,StandardOpenOption.CREATE_NEW);
        Map<String,String> roundtrip=normalize(new DexBackedDexFile(Opcodes.forApi(29),second).getClasses());same(original,roundtrip);saveRows(output.resolve("roundtrip-normalized.jsonl"),roundtrip);
        if(!Arrays.equals(first,second))throw new IllegalArgumentException("Ordinary039 roundtrip bytes differ");
        List<String> pins=new ArrayList<>();for(var e:original.entrySet())pins.add(q(e.getKey())+":"+q(hash(e.getValue())));
        List<String> loc=new ArrayList<>();for(var e:locations.entrySet())loc.add(q(e.getKey())+":"+e.getValue());
        System.out.println("{\"status\":\"PASS_STATIC_SUBSET_ONLY\",\"originalHeaders\":"+join(headers)+",\"selectedClassHeaders\":{"+String.join(",",loc)+"},\"selectedClasses\":2,\"fields\":"+f+",\"methods\":"+m+",\"instructions\":"+ins+",\"tryBlocks\":"+tr+",\"debugItems\":"+dbg+",\"annotationInstances\":"+ann+",\"hiddenApiMembers\":"+hid+",\"explicitInitialValues\":"+initial+",\"normalizedRecords\":"+original.size()+",\"subsetDexSha256\":"+q(SecurityDexReader.sha(first))+",\"roundtripDexSha256\":"+q(SecurityDexReader.sha(second))+",\"roundtripByteEqual\":true,\"allNormalizedMetadataEqual\":true,\"memberHashes\":{"+String.join(",",pins)+"},\"androidExecuted\":false,\"oemExecuted\":false}");
    }
}
