import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.*;
import com.android.tools.smali.dexlib2.base.reference.*;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.debug.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction21c;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction31c;
import com.android.tools.smali.dexlib2.iface.instruction.formats.ArrayPayload;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction31c;
import com.android.tools.smali.dexlib2.immutable.debug.ImmutableLineNumber;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

/** Unselected exact PM-reference plus GL format-widening edit. Static parsing only. */
final class BuildPermissionQueryPayload {
    static final String OWNER="Landroid/permission/PermissionManager;";
    static final String SIG="checkPermissionUncached(Ljava/lang/String;III)I";
    static final String KEY=OWNER+"->"+SIG;
    static final String GL_OWNER="Landroid/opengl/GLLogWrapper;",GL_SIG="glStencilMask(I)V",GL_KEY=GL_OWNER+"->"+GL_SIG;
    static final String RETURN="Landroid/app/IActivityManager;";
    static final String OLD="Landroid/app/ActivityManager;->getService()"+RETURN;
    static final String NEW="Lcom/appleexploit/oneos/security/boot/PermissionQueryBinding;->get()"+RETURN;
    static final String ORIGINAL_BODY="9337df69165b01e95e5f834e89cd4cc4ed9abc86008f20493d0aa5aab63877fe";
    static final String CANONICAL_INVERSE="2254a4d6b98f2b382ef739378ebbc4923fa91e05c0281e75a40b5a8e4244487d";
    static String q(String s){return SecurityDexReader.q(s);}
    static String sha(byte[] b)throws Exception{return SecurityDexReader.sha(b);}
    static Method find(Collection<? extends ClassDef> classes,String owner,String signature){Method out=null;for(ClassDef c:classes)if(c.getType().equals(owner))for(Method m:c.getMethods())if(SecurityDexReader.signature(m).equals(signature)){if(out!=null)throw new IllegalArgumentException("Ambiguous target");out=m;}if(out==null)throw new IllegalArgumentException("Missing exact target");return out;}
    static Method target(Collection<? extends ClassDef> classes){return find(classes,OWNER,SIG);}
    static String bodyHash(Method m)throws Exception{
        MethodImplementation b=m.getImplementation();List<String> code=new ArrayList<>(),catches=new ArrayList<>();int pc=0;
        for(Instruction i:b.getInstructions()){code.add(SecurityDexReader.instruction(i,pc));pc+=i.getCodeUnits();}
        for(var t:b.getTryBlocks())for(var h:t.getExceptionHandlers())catches.add("{\"startPc\":"+t.getStartCodeAddress()+",\"codeUnits\":"+t.getCodeUnitCount()+",\"exceptionType\":"+q(h.getExceptionType())+",\"handlerPc\":"+h.getHandlerCodeAddress()+"}");
        String value="{\"owner\":"+q(m.getDefiningClass())+",\"signature\":"+q(SecurityDexReader.signature(m))+",\"accessFlags\":"+m.getAccessFlags()+",\"registerCount\":"+b.getRegisterCount()+",\"hasCode\":true,\"instructions\":["+String.join(",",code)+"],\"catches\":["+String.join(",",catches)+"]}";
        return ProbeSamsungDex041.hash(value);
    }
    static Instruction35c shape(Method m,String reference){
        if(m.getAccessFlags()!=10||m.getImplementation()==null||m.getImplementation().getRegisterCount()!=6)throw new IllegalArgumentException("Target attributes/registers differ");
        var b=m.getImplementation();int pc=0;Instruction first=null;for(Instruction i:b.getInstructions()){if(pc==0)first=i;pc+=i.getCodeUnits();}
        if(pc!=49||!(first instanceof Instruction35c i)||i.getOpcode()!=Opcode.INVOKE_STATIC||i.getRegisterCount()!=0||i.getCodeUnits()!=3||!(i.getReference()instanceof MethodReference r)||!SecurityDexReader.ref(r).equals(reference)||!r.getReturnType().equals(RETURN)||!r.getParameterTypes().isEmpty())throw new IllegalArgumentException("Exact PC0/35c/zero-argument/same-return/49unit contract differs");
        if(b.getTryBlocks().size()!=1)throw new IllegalArgumentException("Target try count");var t=b.getTryBlocks().get(0);
        if(t.getStartCodeAddress()!=36||t.getCodeUnitCount()!=6||t.getExceptionHandlers().size()!=1||t.getExceptionHandlers().get(0).getHandlerCodeAddress()!=43||!"Landroid/os/RemoteException;".equals(t.getExceptionHandlers().get(0).getExceptionType()))throw new IllegalArgumentException("Target try/handler contract differs");
        return i;
    }
    static abstract class ForwardMethod extends BaseMethodReference implements Method {
        final Method original;ForwardMethod(Method original){this.original=original;}
        public String getDefiningClass(){return original.getDefiningClass();}public String getName(){return original.getName();}public List<? extends CharSequence>getParameterTypes(){return original.getParameterTypes();}public List<? extends MethodParameter>getParameters(){return original.getParameters();}public String getReturnType(){return original.getReturnType();}public int getAccessFlags(){return original.getAccessFlags();}public Set<? extends Annotation>getAnnotations(){return original.getAnnotations();}public Set<HiddenApiRestriction>getHiddenApiRestrictions(){return original.getHiddenApiRestrictions();}
    }
    static final class EditedMethod extends ForwardMethod {
        final MethodImplementation body;
        EditedMethod(Method original,String from,String to){
            super(original);Instruction35c first=shape(original,from);List<Instruction> code=new ArrayList<>();boolean replaced=false;
            String owner=to.substring(0,to.indexOf("->")),name=to.substring(to.indexOf("->")+2,to.indexOf('('));
            MethodReference replacement=new ImmutableMethodReference(owner,name,List.of(),RETURN);
            for(Instruction i:original.getImplementation().getInstructions()){
                if(!replaced){code.add(new ImmutableInstruction35c(first.getOpcode(),first.getRegisterCount(),first.getRegisterC(),first.getRegisterD(),first.getRegisterE(),first.getRegisterF(),first.getRegisterG(),replacement));replaced=true;}else code.add(i);
            }
            MethodImplementation base=original.getImplementation();List<Instruction> immutable=List.copyOf(code);
            body=new MethodImplementation(){public int getRegisterCount(){return base.getRegisterCount();}public Iterable<? extends Instruction>getInstructions(){return immutable;}public List<? extends TryBlock<? extends ExceptionHandler>>getTryBlocks(){return base.getTryBlocks();}public Iterable<? extends DebugItem>getDebugItems(){return base.getDebugItems();}};
            shape(this,to);
        }
        public MethodImplementation getImplementation(){return body;}
    }
    static void glShape(Method m,boolean jumbo){
        if(m.getAccessFlags()!=1||!SecurityDexReader.signature(m).equals(GL_SIG)||m.getParameters().size()!=1||m.getParameters().get(0).getName()!=null||m.getImplementation()==null||m.getImplementation().getRegisterCount()!=3||!m.getImplementation().getTryBlocks().isEmpty())throw new IllegalArgumentException("GL attributes/parameter/register/try shape differs");
        int pc=0,count=0;for(Instruction i:m.getImplementation().getInstructions()){
            if(count==0){if(jumbo?!(i instanceof Instruction31c):!(i instanceof Instruction21c))throw new IllegalArgumentException("GL exact format differs");if(i.getOpcode()!=(jumbo?Opcode.CONST_STRING_JUMBO:Opcode.CONST_STRING)||((OneRegisterInstruction)i).getRegisterA()!=0||!(((ReferenceInstruction)i).getReference()instanceof StringReference s)||!s.getString().equals("glStencilMask"))throw new IllegalArgumentException("GL PC0 opcode/register/literal differs");}
            if(i instanceof OffsetInstruction||i instanceof SwitchPayload||i instanceof ArrayPayload)throw new IllegalArgumentException("GL branch/payload not admitted");pc+=i.getCodeUnits();count++;
        }
        if(count!=9||pc!=(jumbo?24:23))throw new IllegalArgumentException("GL instruction count/width differs");
        int[] oldPcs={0,5,11,14,19},lines={2366,2367,2368,2370,2371};int n=0;for(DebugItem d:m.getImplementation().getDebugItems()){
            if(n>=5||!(d instanceof LineNumber l)||l.getLineNumber()!=lines[n]||l.getCodeAddress()!=(jumbo&&oldPcs[n]>=2?oldPcs[n]+1:oldPcs[n]))throw new IllegalArgumentException("GL exact five line events differ");n++;
        }if(n!=5)throw new IllegalArgumentException("GL debug count differs");
    }
    static final class GlMethod extends ForwardMethod {
        final MethodImplementation body;
        GlMethod(Method original,boolean widen){
            super(original);glShape(original,!widen);MethodImplementation base=original.getImplementation();List<Instruction> code=new ArrayList<>();int count=0;
            for(Instruction i:base.getInstructions()){if(count++==0){Reference ref=((ReferenceInstruction)i).getReference();code.add(widen?new ImmutableInstruction31c(Opcode.CONST_STRING_JUMBO,0,ref):new ImmutableInstruction21c(Opcode.CONST_STRING,0,ref));}else code.add(i);}
            List<DebugItem> debug=new ArrayList<>();for(DebugItem d:base.getDebugItems()){LineNumber l=(LineNumber)d;int p=l.getCodeAddress();int mapped=p==0?0:widen?p+1:p-1;debug.add(new ImmutableLineNumber(mapped,l.getLineNumber()));}
            body=new MethodImplementation(){public int getRegisterCount(){return base.getRegisterCount();}public Iterable<? extends Instruction>getInstructions(){return code;}public List<? extends TryBlock<? extends ExceptionHandler>>getTryBlocks(){return base.getTryBlocks();}public Iterable<? extends DebugItem>getDebugItems(){return debug;}};
            glShape(this,widen);
        }
        public MethodImplementation getImplementation(){return body;}
    }
    static final class EditedClass extends BaseTypeReference implements ClassDef {
        final ClassDef original;final Method replacement;
        EditedClass(ClassDef original,Method replacement){this.original=original;this.replacement=replacement;}
        List<Method> methods(Iterable<? extends Method>source){List<Method> out=new ArrayList<>();String signature=SecurityDexReader.signature(replacement);for(Method m:source)out.add(SecurityDexReader.signature(m).equals(signature)?replacement:m);return out;}
        public String getType(){return original.getType();}public int getAccessFlags(){return original.getAccessFlags();}public String getSuperclass(){return original.getSuperclass();}public List<String>getInterfaces(){return original.getInterfaces();}public String getSourceFile(){return original.getSourceFile();}public Set<? extends Annotation>getAnnotations(){return original.getAnnotations();}public Iterable<? extends Field>getStaticFields(){return original.getStaticFields();}public Iterable<? extends Field>getInstanceFields(){return original.getInstanceFields();}public Iterable<? extends Field>getFields(){return original.getFields();}public Iterable<? extends Method>getDirectMethods(){return methods(original.getDirectMethods());}public Iterable<? extends Method>getVirtualMethods(){return methods(original.getVirtualMethods());}public Iterable<? extends Method>getMethods(){return methods(original.getMethods());}
    }
    static List<ClassDef> overlay(Collection<? extends ClassDef> source,String from,String to){
        Method m=target(source);Method replacement=new EditedMethod(m,from,to);Method gl=new GlMethod(find(source,GL_OWNER,GL_SIG),from.equals(OLD));List<ClassDef> out=new ArrayList<>();int changed=0;
        for(ClassDef c:source){if(c.getType().equals(OWNER)){out.add(new EditedClass(c,replacement));changed++;}else if(c.getType().equals(GL_OWNER)){out.add(new EditedClass(c,gl));changed++;}else out.add(c);}
        if(changed!=2||out.size()!=7881)throw new IllegalArgumentException("No class insertion/filtering permitted");return out;
    }
    static int codeOffset(ProbeSamsungFrameworkDex.RawPolicy p,String owner,String key){
        int ci=p.classes.indexOf(owner);if(ci<0)throw new IllegalArgumentException("Raw target class absent");int pos=p.u32(p.u32(100)+32*ci+24);int[]counts=new int[4];
        for(int k=0;k<4;k++){int[]v=p.leb(pos);counts[k]=v[0];pos=v[1];}
        for(int k=0;k<4;k++){int index=0;for(int n=0;n<counts[k];n++){int[]v=p.leb(pos);index+=v[0];pos=v[1];v=p.leb(pos);pos=v[1];if(k>=2){v=p.leb(pos);pos=v[1];if(p.method(index).equals(key))return v[0];}}}
        throw new IllegalArgumentException("Raw target code absent");
    }
    static String codeHeader(ProbeSamsungFrameworkDex.RawPolicy p){int o=codeOffset(p,OWNER,KEY);if(p.u16(o)!=6||p.u16(o+2)!=4||p.u16(o+4)!=5||p.u16(o+6)!=1||p.u32(o+12)!=49)throw new IllegalArgumentException("Raw target code header differs");return "{\"codeOffset\":"+o+",\"registers\":6,\"incomingWords\":4,\"outgoingWords\":5,\"tryCount\":1,\"codeUnits\":49,\"pc0Opcode\":"+p.u16(o+16)+",\"pc0MethodId\":"+p.u16(o+18)+"}";}
    static String glHeader(ProbeSamsungFrameworkDex.RawPolicy p,boolean jumbo){int o=codeOffset(p,GL_OWNER,GL_KEY);int debug=p.u32(o+8),v[]=p.leb(debug);if(v[0]!=2366)throw new IllegalArgumentException("GL raw initial line");v=p.leb(v[1]);if(v[0]!=1)throw new IllegalArgumentException("GL parameter count");v=p.leb(v[1]);if(v[0]!=0)throw new IllegalArgumentException("GL unnamed parameter");int id=jumbo?p.u32(o+18):p.u16(o+18);if(p.u16(o)!=3||p.u16(o+2)!=2||p.u16(o+4)!=3||p.u16(o+6)!=0||p.u32(o+12)!=(jumbo?24:23)||p.u16(o+16)!=(jumbo?0x1b:0x1a)||id!=(jumbo?65536:65535))throw new IllegalArgumentException("GL raw header/format/string ID differs");return "{\"codeOffset\":"+o+",\"registers\":3,\"incomingWords\":2,\"outgoingWords\":3,\"tryCount\":0,\"codeUnits\":"+(jumbo?24:23)+",\"pc0StringId\":"+id+",\"initialLine\":2366,\"unnamedParameterCount\":1}";}
    static int occurrences(String text,String needle){int count=0,pos=0;while((pos=text.indexOf(needle,pos))>=0){count++;pos+=needle.length();}return count;}
    public static void main(String[]a)throws Exception{
        if(a.length!=3)throw new IllegalArgumentException("pinned-framework.jar exclusive-firmware-raw-dir exclusive-out-dex-dir");Path raw=Path.of(a[1]),binary=Path.of(a[2]);if(!Files.isDirectory(raw)||!Files.isDirectory(binary))throw new IllegalArgumentException("Exclusive output dirs required");
        byte[] input;try(ZipFile z=new ZipFile(a[0])){if(z.stream().filter(e->e.getName().equals("classes3.dex")).count()!=1)throw new IllegalArgumentException("Duplicate source DEX");var entry=z.getEntry("classes3.dex");if(entry.getSize()!=8830032)throw new IllegalArgumentException("Pinned source extent");try(var in=z.getInputStream(entry)){input=in.readNBytes(8830033);}}
        if(input.length!=8830032||!sha(input).equals("256cc1744c36a88d3ee4c9218d2cf0156816ce89a63cd98787dd1633edbdf1a7"))throw new IllegalArgumentException("Source DEX differs");ProbeSamsungDex041.validate(input);
        var source=new DexBackedDexFile(Opcodes.forApi(29),input);Collection<? extends ClassDef> originals=source.getClasses();var policy=new ProbeSamsungFrameworkDex.RawPolicy(input);String originalCode=codeHeader(policy),originalGlCode=glHeader(policy,false);
        Method original=target(originals);Method originalGl=find(originals,GL_OWNER,GL_SIG);glShape(originalGl,false);String originalGlBody=bodyHash(originalGl);shape(original,OLD);if(!bodyHash(original).equals(ORIGINAL_BODY))throw new IllegalArgumentException("Pinned original method body differs");
        if(originals.size()!=7881||SecurityDexReader.u32(input,88)!=65412)throw new IllegalArgumentException("Source class/pool count");
        for(ClassDef c:originals)if(c.getType().equals("Lcom/appleexploit/oneos/security/boot/PermissionQueryBinding;"))throw new IllegalArgumentException("Unexpected existing helper definition");
        System.err.println("stage=normalize-original");Map<String,String> before=ProbeSamsungDex041.normalize(originals);if(before.size()!=107060)throw new IllegalArgumentException("Record count");ProbeSamsungDex041.saveRows(raw.resolve("original-normalized.jsonl"),before);
        if(occurrences(before.get(KEY),OLD)!=2)throw new IllegalArgumentException("Exact one reference/two normalizer renderings expected");Map<String,String> expected=new TreeMap<>(before);expected.put(KEY,before.get(KEY).replace(OLD,NEW));
        List<ClassDef> edited=overlay(originals,OLD,NEW);
        ClassDef glClass=edited.stream().filter(c->c.getType().equals(GL_OWNER)).findFirst().orElseThrow();Map<String,String> glExpected=ProbeSamsungDex041.normalize(List.of(glClass));
        for(var e:glExpected.entrySet()){if(!e.getKey().equals(GL_KEY)&&!e.getValue().equals(before.get(e.getKey())))throw new IllegalArgumentException("GL class non-target metadata changed");}
        expected.put(GL_KEY,glExpected.get(GL_KEY));int changed=0;for(String key:before.keySet())if(!before.get(key).equals(expected.get(key)))changed++;if(changed!=2)throw new IllegalArgumentException("Exact two-record contract differs");
        ProbeSamsungDex041.saveRows(raw.resolve("expected-edited-normalized.jsonl"),expected);
        System.err.println("stage=emit-edited");byte[]first=ProbeSamsungFrameworkDex.emitAndRestore(edited,policy,binary,"edited");String firstRepair=ProbeSamsungFrameworkDex.lastRepair;Files.write(binary.resolve("permission-query-edited-039.dex"),first,StandardOpenOption.CREATE_NEW);
        var decoded=new DexBackedDexFile(Opcodes.forApi(29),first);var decodedPolicy=new ProbeSamsungFrameworkDex.RawPolicy(first);String editedCode=codeHeader(decodedPolicy),editedGlCode=glHeader(decodedPolicy,true);shape(target(decoded.getClasses()),NEW);glShape(find(decoded.getClasses(),GL_OWNER,GL_SIG),true);String editedGlBody=bodyHash(find(decoded.getClasses(),GL_OWNER,GL_SIG));
        System.err.println("stage=compare-exact-edited-delta");Map<String,String> after=ProbeSamsungDex041.normalize(decoded.getClasses());ProbeSamsungDex041.saveRows(raw.resolve("edited-normalized.jsonl"),after);ProbeSamsungDex041.same(expected,after);String editedTargetHash=ProbeSamsungDex041.hash(after.get(KEY));String editedBodyHash=bodyHash(target(decoded.getClasses()));after=null;
        if(SecurityDexReader.u32(first,88)!=65413||SecurityDexReader.u32(first,64)!=9964||SecurityDexReader.u32(first,56)!=86257||SecurityDexReader.u32(first,96)!=7881)throw new IllegalArgumentException("Exact one external method reference/no defined class insertion expected");
        System.err.println("stage=emit-edited-roundtrip");byte[]second=ProbeSamsungFrameworkDex.emitAndRestore(decoded.getClasses(),policy,binary,"edited-roundtrip");String secondRepair=ProbeSamsungFrameworkDex.lastRepair;Files.write(binary.resolve("permission-query-roundtrip-039.dex"),second,StandardOpenOption.CREATE_NEW);if(!Arrays.equals(first,second))throw new IllegalArgumentException("Edited second emit bytes differ");
        var roundDex=new DexBackedDexFile(Opcodes.forApi(29),second);Map<String,String> round=ProbeSamsungDex041.normalize(roundDex.getClasses());ProbeSamsungDex041.same(expected,round);ProbeSamsungDex041.saveRows(raw.resolve("roundtrip-normalized.jsonl"),round);round=null;
        System.err.println("stage=symbolic-inverse");List<ClassDef> inverse=overlay(decoded.getClasses(),NEW,OLD);byte[]restored=ProbeSamsungFrameworkDex.emitAndRestore(inverse,policy,binary,"inverse");String inverseRepair=ProbeSamsungFrameworkDex.lastRepair;Files.write(binary.resolve("permission-query-inverse-039.dex"),restored,StandardOpenOption.CREATE_NEW);
        if(!sha(restored).equals(CANONICAL_INVERSE))throw new IllegalArgumentException("Inverse differs from canonical no-edit2254 profile");var inverseDex=new DexBackedDexFile(Opcodes.forApi(29),restored);Map<String,String> inv=ProbeSamsungDex041.normalize(inverseDex.getClasses());ProbeSamsungDex041.same(before,inv);ProbeSamsungDex041.saveRows(raw.resolve("inverse-normalized.jsonl"),inv);if(!bodyHash(target(inverseDex.getClasses())).equals(ORIGINAL_BODY))throw new IllegalArgumentException("Inverse source body mismatch");glShape(find(inverseDex.getClasses(),GL_OWNER,GL_SIG),false);glHeader(new ProbeSamsungFrameworkDex.RawPolicy(restored),false);if(!bodyHash(find(inverseDex.getClasses(),GL_OWNER,GL_SIG)).equals(originalGlBody))throw new IllegalArgumentException("Inverse GL source body mismatch");
        String glProof="{\"method\":"+q(GL_KEY)+",\"sourceBodySha256\":"+q(originalGlBody)+",\"editedBodySha256\":"+q(editedGlBody)+",\"sourceCodeHeader\":"+originalGlCode+",\"editedCodeHeader\":"+editedGlCode+",\"instructionCount\":9,\"pcMap\":\"old0->0;old>=2->old+1;end23->24\",\"originalDebugPcs\":[0,5,11,14,19],\"editedDebugPcs\":[0,6,12,15,20],\"lineValues\":[2366,2367,2368,2370,2371]}";
        System.out.println("{\"status\":\"PASS_UNSELECTED_TWO_RECORD_LEAF\",\"sourceMethod\":"+q(KEY)+",\"oldReference\":"+q(OLD)+",\"newReference\":"+q(NEW)+",\"sourceBodySha256\":"+q(ORIGINAL_BODY)+",\"editedBodySha256\":"+q(editedBodyHash)+",\"originalTargetRecordSha256\":"+q(ProbeSamsungDex041.hash(before.get(KEY)))+",\"editedTargetRecordSha256\":"+q(editedTargetHash)+",\"sourceCodeHeader\":"+originalCode+",\"editedCodeHeader\":"+editedCode+",\"glFormatProof\":"+glProof+",\"normalizedRecords\":107060,\"changedMethodRecords\":2,\"editedDexSha256\":"+q(sha(first))+",\"secondEmitDexSha256\":"+q(sha(second))+",\"inverseDexSha256\":"+q(sha(restored))+",\"canonicalNoEditSha256\":"+q(CANONICAL_INVERSE)+",\"sourceMethodIds\":65412,\"editedMethodIds\":"+SecurityDexReader.u32(first,88)+",\"editedTypeIds\":"+SecurityDexReader.u32(first,64)+",\"editedStrings\":"+SecurityDexReader.u32(first,56)+",\"definedClasses\":7881,\"allOtherRecordsExact\":true,\"secondEmitByteIdentical\":true,\"inverseMetadataAndCanonicalBytesEqual\":true,\"allRawPolicyAndOrderingExact\":true,\"repairs\":["+firstRepair+","+secondRepair+","+inverseRepair+"],\"helperDefinitionInserted\":false,\"androidExecuted\":false,\"oemExecuted\":false}");
    }
}
