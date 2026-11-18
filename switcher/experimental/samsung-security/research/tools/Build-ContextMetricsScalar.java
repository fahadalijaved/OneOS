import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.*;
import com.android.tools.smali.dexlib2.base.reference.*;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.debug.DebugItem;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.*;

/** Static source-derived diagnostic only. Never loads or invokes OEM classes. */
final class BuildContextMetricsScalar {
    static final String OWNER="Landroid/view/DisplayInfo;";
    static final String DIAG="Lcom/appleexploit/oneos/security/diagnostic/ContextMetricsScalar;";
    static final String NAME="getMetricsWithSize";
    static final String SIG=NAME+"(Landroid/util/DisplayMetrics;Landroid/content/res/CompatibilityInfo;Landroid/content/res/Configuration;II)V";
    static final String BODY_SHA="4c9f073201d90b89486fd11b2f8330e717f3172c4da788f34214709a87b4e703";
    static final String RAW_SHA="f09114b4b9ef2b6515cdf8ecfcb4d78c3fb69a1eef5c5e42deeedf32e2564bdf";
    static final List<Integer> PCS=List.of(0,6,38,44), DEST=List.of(0,0,0,2), ARGS=List.of(8,8,9,10);
    static final List<String> FIELDS=List.of("logicalDensityDpi:I","logicalDensityDpi:I","physicalXDpi:F","physicalYDpi:F");
    static String q(String s){return SecurityDexReader.q(s);}
    static void need(boolean value,String message){if(!value)throw new IllegalArgumentException(message);}
    static List<Instruction> instructions(Method m){List<Instruction> out=new ArrayList<>();m.getImplementation().getInstructions().forEach(out::add);return out;}
    static String key(Method m){return m.getDefiningClass()+"->"+SecurityDexReader.signature(m);}
    static Method target(Collection<? extends ClassDef> cs,String owner){
        Method result=null;for(ClassDef c:cs)if(c.getType().equals(owner))for(Method m:c.getMethods())if(m.getName().equals(NAME)){need(result==null,"Ambiguous selected name");result=m;}
        need(result!=null,"Missing selected member");return result;
    }
    static String bodyHash(Method m)throws Exception{
        var b=m.getImplementation();List<String> code=new ArrayList<>(),catches=new ArrayList<>();int pc=0;
        for(Instruction i:b.getInstructions()){code.add(SecurityDexReader.instruction(i,pc));pc+=i.getCodeUnits();}
        for(var t:b.getTryBlocks())for(var h:t.getExceptionHandlers())catches.add("{\"startPc\":"+t.getStartCodeAddress()+",\"codeUnits\":"+t.getCodeUnitCount()+",\"exceptionType\":"+q(h.getExceptionType())+",\"handlerPc\":"+h.getHandlerCodeAddress()+"}");
        return ProbeSamsungDex041.hash("{\"owner\":"+q(m.getDefiningClass())+",\"signature\":"+q(SecurityDexReader.signature(m))+",\"accessFlags\":"+m.getAccessFlags()+",\"registerCount\":"+b.getRegisterCount()+",\"hasCode\":true,\"instructions\":["+String.join(",",code)+"],\"catches\":["+String.join(",",catches)+"]}");
    }
    static List<String> debug(Method m){List<String>d=new ArrayList<>();m.getImplementation().getDebugItems().forEach(i->d.add(ProbeSamsungDex041.debug(i)));return d;}
    static void sourceShape(Method m)throws Exception{
        need(m.getDefiningClass().equals(OWNER)&&SecurityDexReader.signature(m).equals(SIG)&&m.getAccessFlags()==2,"Original identity/flags");
        need(m.getImplementation().getRegisterCount()==8&&m.getImplementation().getTryBlocks().isEmpty(),"Original registers/tries");
        need(m.getAnnotations().isEmpty()&&m.getParameters().size()==5,"Original annotation/parameter count");
        for(var p:m.getParameters())need(p.getName()==null&&p.getSignature()==null&&p.getAnnotations().isEmpty(),"Original parameter metadata");
        List<String> lines=new ArrayList<>();int[]p={0,6,19,26,31,38,44,52,62,68,72,76,87},l={945,946,948,949,950,952,953,956,957,958,960,961,965};
        for(int i=0;i<p.length;i++)lines.add(q("10:"+p[i]+":line="+l[i]));need(debug(m).equals(lines),"Exact line-only debug");
        int pc=0,count=0,sites=0;for(Instruction i:m.getImplementation().getInstructions()){
            int s=PCS.indexOf(pc);if(s>=0){need(i instanceof Instruction22c,"Exact source IGET format");var a=(Instruction22c)i;need(i.getOpcode()==Opcode.IGET&&i.getCodeUnits()==2&&a.getRegisterA()==DEST.get(s)&&a.getRegisterB()==2&&SecurityDexReader.ref(a.getReference()).equals(OWNER+"->"+FIELDS.get(s)),"Exact IGET site");sites++;}
            else if(i instanceof ReferenceInstruction r)need(!SecurityDexReader.ref(r.getReference()).startsWith(OWNER+"->"),"Unexpected receiver member");
            pc+=i.getCodeUnits();count++;
        }
        need(count==50&&pc==91&&sites==4&&bodyHash(m).equals(BODY_SHA),"Pinned entire selected body");
    }
    static final class Derived extends BaseMethodReference implements Method {
        final Method source;final boolean inverse;final List<MethodParameter>params;final MethodImplementation impl;
        Derived(Method source,Method original,boolean inverse){
            this.source=source;this.inverse=inverse;params=new ArrayList<>();params.addAll(original.getParameters());
            if(!inverse)for(String t:List.of("I","F","F"))params.add(new ImmutableMethodParameter(t,Set.of(),null));
            List<Instruction> code=new ArrayList<>();List<Instruction>old=instructions(original);Map<Integer,Instruction> sites=new HashMap<>();int pc=0;
            for(Instruction i:old){if(PCS.contains(pc))sites.put(pc,i);pc+=i.getCodeUnits();}
            pc=0;List<Instruction> src=instructions(source);
            for(int n=0;n<src.size();n++){
                Instruction i=src.get(n);int s=PCS.indexOf(pc);
                if(s>=0){
                    if(!inverse){code.add(new ImmutableInstruction12x(Opcode.MOVE,DEST.get(s),ARGS.get(s)));code.add(new ImmutableInstruction10x(Opcode.NOP));}
                    else {need(i instanceof Instruction12x,"Inverse MOVE format");var a=(Instruction12x)i;need(a.getOpcode()==Opcode.MOVE&&a.getRegisterA()==DEST.get(s)&&a.getRegisterB()==ARGS.get(s)&&n+1<src.size()&&src.get(n+1).getOpcode()==Opcode.NOP,"Inverse exact MOVE+NOP");code.add(sites.get(pc));n++;}
                    pc+=2;
                }else{code.add(i);pc+=i.getCodeUnits();}
            }
            need(pc==91,"Preserved total PCs");List<Instruction>fixed=List.copyOf(code);var base=original.getImplementation();
            impl=new MethodImplementation(){public int getRegisterCount(){return inverse?8:11;}public Iterable<? extends Instruction>getInstructions(){return fixed;}public List<? extends TryBlock<? extends ExceptionHandler>>getTryBlocks(){return base.getTryBlocks();}public Iterable<? extends DebugItem>getDebugItems(){return base.getDebugItems();}};
        }
        public String getDefiningClass(){return inverse?OWNER:DIAG;}public String getName(){return NAME;}public List<? extends CharSequence>getParameterTypes(){List<String>t=new ArrayList<>();for(var p:params)t.add(p.getType());return t;}public List<? extends MethodParameter>getParameters(){return params;}public String getReturnType(){return "V";}public int getAccessFlags(){return inverse?2:10;}public Set<? extends Annotation>getAnnotations(){return source.getAnnotations();}public Set<HiddenApiRestriction>getHiddenApiRestrictions(){return source.getHiddenApiRestrictions();}public MethodImplementation getImplementation(){return impl;}
    }
    /** One-method projection, never a claim of a complete original runtime class. */
    static final class Projection extends BaseTypeReference implements ClassDef {
        final Method method;Projection(Method m){method=m;}
        public String getType(){return method.getDefiningClass();}public int getAccessFlags(){return 17;}public String getSuperclass(){return "Ljava/lang/Object;";}public List<String>getInterfaces(){return List.of();}public String getSourceFile(){return "DisplayInfo.java";}public Set<? extends Annotation>getAnnotations(){return Set.of();}public Iterable<? extends Field>getStaticFields(){return List.of();}public Iterable<? extends Field>getInstanceFields(){return List.of();}public Iterable<? extends Field>getFields(){return List.of();}public Iterable<? extends Method>getDirectMethods(){return List.of(method);}public Iterable<? extends Method>getVirtualMethods(){return List.of();}public Iterable<? extends Method>getMethods(){return List.of(method);}
    }
    static Map<String,String> normalized(Method m){return ProbeSamsungDex041.normalize(List.of(new Projection(m)));}
    static Method decode(byte[] b,String owner)throws Exception{ProbeSamsungDex041.validate(b);var d=new DexBackedDexFile(Opcodes.forApi(29),b);need(d.getClasses().size()==1,"One emitted class");return target(d.getClasses(),owner);}
    static byte[] emit(Method m)throws Exception{return ProbeSamsungDex041.emit(List.of(new Projection(m)));}
    static void scalarShape(Method m,Method original){
        need(m.getDefiningClass().equals(DIAG)&&m.getAccessFlags()==10&&m.getImplementation().getRegisterCount()==11&&m.getParameters().size()==8&&instructions(m).size()==54,"Scalar member shape");
        need(m.getAnnotations().isEmpty()&&m.getImplementation().getTryBlocks().isEmpty()&&debug(m).equals(debug(original)),"Scalar metadata");
        for(var p:m.getParameters())need(p.getName()==null&&p.getSignature()==null&&p.getAnnotations().isEmpty(),"Scalar null parameter metadata");
        for(Instruction i:m.getImplementation().getInstructions())if(i instanceof ReferenceInstruction r)need(!SecurityDexReader.ref(r.getReference()).contains(OWNER),"No DisplayInfo member/type reference");
    }
    public static void main(String[]args)throws Exception{
        need(args.length==3,"Pinned framework archive, exclusive raw and output dirs required");Path raw=Path.of(args[1]),out=Path.of(args[2]);need(Files.isDirectory(raw)&&Files.isDirectory(out),"Own existing dirs required");
        byte[]input;try(ZipFile z=new ZipFile(args[0])){var entries=z.stream().filter(e->e.getName().equals("classes4.dex")).toList();need(entries.size()==1&&entries.get(0).getSize()==8458024,"Pinned DEX entry/size");try(var in=z.getInputStream(entries.get(0))){input=in.readNBytes(8458025);}}
        need(input.length==8458024&&SecurityDexReader.sha(input).equals("b3088ece8acfc76067eed2aefd2b93a0604da9b8645bd2f2f84012859fefb5c4"),"Exact source DEX");ProbeSamsungDex041.validate(input);
        var sourceDex=new DexBackedDexFile(Opcodes.forApi(29),input);Method original=target(sourceDex.getClasses(),OWNER);sourceShape(original);
        for(ClassDef c:sourceDex.getClasses()){need(!c.getType().equals(DIAG),"Diagnostic definition already exists");if(c.getType().equals(OWNER))need("DisplayInfo.java".equals(c.getSourceFile()),"Original source filename");}
        need(SecurityDexReader.sha(Arrays.copyOfRange(input,3412524,3412706)).equals(RAW_SHA),"Original literal instruction slice");Files.write(raw.resolve("source-instructions.bin"),Arrays.copyOfRange(input,3412524,3412706),StandardOpenOption.CREATE_NEW);
        var before=normalized(original);ProbeSamsungDex041.saveRows(raw.resolve("source-selected-normalized.jsonl"),before);
        byte[]projection=emit(original);Files.write(out.resolve("source-method-projection.dex"),projection,StandardOpenOption.CREATE_NEW);Method projected=decode(projection,OWNER);sourceShape(projected);ProbeSamsungDex041.same(before,normalized(projected));
        Method derived=new Derived(original,original,false);scalarShape(derived,original);var expected=normalized(derived);ProbeSamsungDex041.saveRows(raw.resolve("expected-scalar-normalized.jsonl"),expected);
        byte[]first=emit(derived);Files.write(out.resolve("context-metrics-scalar.dex"),first,StandardOpenOption.CREATE_NEW);Method decoded=decode(first,DIAG);scalarShape(decoded,original);ProbeSamsungDex041.same(expected,normalized(decoded));ProbeSamsungDex041.saveRows(raw.resolve("decoded-scalar-normalized.jsonl"),normalized(decoded));
        byte[]second=emit(decoded);Files.write(out.resolve("context-metrics-scalar-roundtrip.dex"),second,StandardOpenOption.CREATE_NEW);need(Arrays.equals(first,second),"Actual second emit byte equality");ProbeSamsungDex041.same(expected,normalized(decode(second,DIAG)));
        Method inverse=new Derived(decoded,original,true);sourceShape(inverse);ProbeSamsungDex041.same(before,normalized(inverse));byte[]restored=emit(inverse);Files.write(out.resolve("inverse-source-method-projection.dex"),restored,StandardOpenOption.CREATE_NEW);Method back=decode(restored,OWNER);sourceShape(back);ProbeSamsungDex041.same(before,normalized(back));need(Arrays.equals(projection,restored),"Selected projection inverse byte equality");ProbeSamsungDex041.saveRows(raw.resolve("inverse-selected-normalized.jsonl"),normalized(back));
        System.out.println("{\"status\":\"PASS_UNSELECTED_DIAGNOSTIC_SCALAR\",\"selected\":false,\"sourceBodySha256\":"+q(bodyHash(original))+",\"derivedBodySha256\":"+q(bodyHash(decoded))+",\"sourceSelectedRecordSha256\":"+q(ProbeSamsungDex041.hash(before.get(key(original))))+",\"derivedSelectedRecordSha256\":"+q(ProbeSamsungDex041.hash(expected.get(key(derived))))+",\"artifactSha256\":"+q(SecurityDexReader.sha(first))+",\"roundtripSha256\":"+q(SecurityDexReader.sha(second))+",\"sourceProjectionSha256\":"+q(SecurityDexReader.sha(projection))+",\"inverseProjectionSha256\":"+q(SecurityDexReader.sha(restored))+",\"secondEmitByteEqual\":true,\"selectedMethodInverseNormalizedAndProjectionByteEqual\":true,\"sourceInstructionBytesSha256\":"+q(RAW_SHA)+",\"fullFrameworkInverse\":false,\"sourceFrameworkModified\":false,\"oemExecuted\":false}");
    }
}
