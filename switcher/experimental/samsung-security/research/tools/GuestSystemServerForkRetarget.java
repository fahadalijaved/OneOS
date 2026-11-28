import java.nio.file.*;
import java.util.*;
import com.android.tools.smali.dexlib2.*;
import com.android.tools.smali.dexlib2.base.reference.BaseTypeReference;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.reference.*;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.dexlib2.immutable.*;
import com.android.tools.smali.dexlib2.immutable.instruction.*;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;

/** Authored PC byte writer only. Neither this class nor OEM classes are executed on Android. */
final class GuestSystemServerForkRetarget {
 static final String OWNER="Lcom/android/internal/os/ZygoteInit;";
 static final String HELPER="Lcom/android/internal/os/PreparedGuestSystemServerFork;";
 static final String FORK="forkSystemServer(Ljava/lang/String;Ljava/lang/String;Lcom/android/internal/os/ZygoteServer;)Ljava/lang/Runnable;";
 static final String HANDOFF="handleSystemServerProcess(Lcom/android/internal/os/ZygoteArguments;)Ljava/lang/Runnable;";
 static final List<String> FORK_ARGS=List.of("I","I","[I","I","[[I","J","J");
 static final List<String> INIT_ARGS=List.of("I","[J","[J","[Ljava/lang/String;","Ljava/lang/ClassLoader;");
 static final MethodReference OLD_FORK=new ImmutableMethodReference("Lcom/android/internal/os/Zygote;","forkSystemServer",FORK_ARGS,"I");
 static final MethodReference NEW_FORK=new ImmutableMethodReference(HELPER,"invokeOriginalForkSystemServer",FORK_ARGS,"I");
 static final MethodReference OLD_INIT=new ImmutableMethodReference(OWNER,"zygoteInit",INIT_ARGS,"Ljava/lang/Runnable;");
 static final MethodReference NEW_INIT=new ImmutableMethodReference(HELPER,"invokeOriginalZygoteInit",INIT_ARGS,"Ljava/lang/Runnable;");
 static void need(boolean b,String m){if(!b)throw new IllegalArgumentException(m);}
 static int selected(Method m){if(!m.getDefiningClass().equals(OWNER))return 0;String s=SecurityDexReader.signature(m);return s.equals(FORK)?1:s.equals(HANDOFF)?2:0;}
 static Method edit(Method m,boolean inverse){
  int kind=selected(m);if(kind==0)return m;
  MethodImplementation body=m.getImplementation();int regs=kind==1?22:11,units=kind==1?408:213,at=kind==1?351:208,insns=kind==1?220:111;
  need(m.getAccessFlags()==10&&body!=null&&body.getRegisterCount()==regs,"Selected original declaration/registers");
  List<Instruction> code=new ArrayList<>();int pc=0,count=0,changed=0;
  for(Instruction i:body.getInstructions()){
   if(pc==at){
    MethodReference expected=inverse?(kind==1?NEW_FORK:NEW_INIT):(kind==1?OLD_FORK:OLD_INIT);
    MethodReference replacement=inverse?(kind==1?OLD_FORK:OLD_INIT):(kind==1?NEW_FORK:NEW_INIT);
    need(i.getCodeUnits()==3&&i instanceof ReferenceInstruction&&SecurityDexReader.ref(((ReferenceInstruction)i).getReference()).equals(SecurityDexReader.ref(expected)),"Exact selected reference/width");
    if(kind==1){
     need(i.getOpcode()==Opcode.INVOKE_STATIC_RANGE&&i instanceof RegisterRangeInstruction,"Exact selected3rc opcode");
     RegisterRangeInstruction x=(RegisterRangeInstruction)i;need(x.getStartRegister()==8&&x.getRegisterCount()==9,"Original nine contiguous words");
     code.add(new ImmutableInstruction3rc(Opcode.INVOKE_STATIC_RANGE,8,9,replacement));
    }else{
     need(i.getOpcode()==Opcode.INVOKE_STATIC&&i instanceof FiveRegisterInstruction,"Exact selected35c opcode");
     FiveRegisterInstruction x=(FiveRegisterInstruction)i;need(x.getRegisterCount()==5&&x.getRegisterC()==1&&x.getRegisterD()==3&&x.getRegisterE()==4&&x.getRegisterF()==5&&x.getRegisterG()==0,"Original five register nibbles");
     code.add(new ImmutableInstruction35c(Opcode.INVOKE_STATIC,5,1,3,4,5,0,replacement));
    }
    changed++;
   }else code.add(i);
   pc+=i.getCodeUnits();count++;
  }
  need(pc==units&&count==insns&&changed==1,"Exact selected method extent/count");
  return new ImmutableMethod(m.getDefiningClass(),m.getName(),m.getParameters(),m.getReturnType(),m.getAccessFlags(),m.getAnnotations(),m.getHiddenApiRestrictions(),new ImmutableMethodImplementation(regs,code,body.getTryBlocks(),body.getDebugItems()));
 }
 static final class Overlay extends BaseTypeReference implements ClassDef {
  final ClassDef base;final boolean inverse;
  Overlay(ClassDef b,boolean i){base=b;inverse=i;}
  public String getType(){return base.getType();}public int getAccessFlags(){return base.getAccessFlags();}public String getSuperclass(){return base.getSuperclass();}public List<String>getInterfaces(){return base.getInterfaces();}public String getSourceFile(){return base.getSourceFile();}public Set<? extends Annotation>getAnnotations(){return base.getAnnotations();}
  public Iterable<? extends Field>getStaticFields(){return base.getStaticFields();}public Iterable<? extends Field>getInstanceFields(){return base.getInstanceFields();}public Iterable<? extends Field>getFields(){return base.getFields();}
  List<Method> methods(Iterable<? extends Method> ms){List<Method>out=new ArrayList<>();for(Method m:ms)out.add(edit(m,inverse));return out;}
  public Iterable<? extends Method>getDirectMethods(){return methods(base.getDirectMethods());}public Iterable<? extends Method>getVirtualMethods(){return methods(base.getVirtualMethods());}public Iterable<? extends Method>getMethods(){List<Method>o=new ArrayList<>();getDirectMethods().forEach(o::add);getVirtualMethods().forEach(o::add);return o;}
 }
 static Collection<? extends ClassDef> overlay(Collection<? extends ClassDef> cs,boolean inverse){
  List<ClassDef>out=new ArrayList<>();int found=0;
  for(ClassDef c:cs){if(c.getType().equals(OWNER)){for(Method m:c.getMethods())if(selected(m)!=0)found++;out.add(new Overlay(c,inverse));}else out.add(c);}
  need(found==2,"Exactly two selected original methods");return out;
 }
 static byte[] read(Path p)throws Exception{
  need(Files.size(p)<=32*1024*1024,"DEX input bound");byte[]b=Files.readAllBytes(p);ProbeSamsungDex041.validate(b);return b;
 }
 static void seed(SourcePreservingDexPool pool,DexBackedDexFile original,byte[] raw){
  // Preserve even unreferenced ORIGINAL IDs. Never seed the added reference on inverse.
  for(int i=0;i<SecurityDexReader.u32(raw,56);i++)pool.stringSection.intern(new DexBackedStringReference(original,i).getString());
  for(int i=0;i<SecurityDexReader.u32(raw,64);i++)pool.typeSection.intern(new DexBackedTypeReference(original,i).getType());
  for(int i=0;i<SecurityDexReader.u32(raw,72);i++)pool.protoSection.intern(new DexBackedMethodProtoReference(original,i));
  for(int i=0;i<SecurityDexReader.u32(raw,80);i++)pool.fieldSection.intern(new DexBackedFieldReference(original,i));
  for(int i=0;i<SecurityDexReader.u32(raw,88);i++)pool.methodSection.intern(new DexBackedMethodReference(original,i));
 }
 public static void main(String[]a)throws Exception{
  need(a.length==5,"noedit|forward|inverse|reemit|decode original input raw-dir output");
  String mode=a[0];Path rawdir=Path.of(a[3]);need(Files.isDirectory(rawdir),"Existing exclusive firmware raw directory");
  byte[]source=read(Path.of(a[1])),input=read(Path.of(a[2]));
  need(source.length==9578132&&SecurityDexReader.sha(source).equals("05bb73f928e9eabbf1ad034df912b970cd46fe60977deae01c0a973282028912"),"Literal original source DEX");
  var original=new DexBackedDexFile(Opcodes.forApi(29),source);var dex=new DexBackedDexFile(Opcodes.forApi(29),input);
  need(original.getClasses().size()==6282&&dex.getClasses().size()==6282,"All original class definitions only");
  var before=ProbeSamsungDex041.normalize(original.getClasses());
  var expected=ProbeSamsungDex041.normalize(overlay(original.getClasses(),false));
  Collection<? extends ClassDef>cs=dex.getClasses();
  if(mode.equals("noedit")){need(Arrays.equals(source,input),"Noedit consumes literal source");ProbeSamsungDex041.same(before,ProbeSamsungDex041.normalize(cs));}
  else if(mode.equals("forward")){ProbeSamsungDex041.same(before,ProbeSamsungDex041.normalize(cs));cs=overlay(cs,false);}
  else if(mode.equals("inverse")){ProbeSamsungDex041.same(expected,ProbeSamsungDex041.normalize(cs));cs=overlay(cs,true);ProbeSamsungDex041.same(before,ProbeSamsungDex041.normalize(cs));}
  else if(mode.equals("reemit"))ProbeSamsungDex041.same(expected,ProbeSamsungDex041.normalize(cs));
  else if(mode.equals("renormal"))ProbeSamsungDex041.same(before,ProbeSamsungDex041.normalize(cs));
  else need(mode.equals("decode"),"Unknown fixed stage");
  var rows=ProbeSamsungDex041.normalize(cs);ProbeSamsungDex041.saveRows(rawdir.resolve(Path.of(a[4]).getFileName()+".normalized.jsonl"),rows);
  if(mode.equals("decode")){System.out.println("{\"decoded\":true,\"records\":"+rows.size()+"}");return;}
  SourcePreservingDexPool pool=new SourcePreservingDexPool();seed(pool,original,source);for(ClassDef c:cs)pool.internClass(c);need(!pool.hasOverflowed(),"16-bit pool capacity");
  MemoryDataStore store=new MemoryDataStore();byte[]output;try{pool.writeTo(store);output=store.getData();}finally{store.close();}
  ProbeSamsungDex041.validate(output);ProbeSamsungDex041.same(rows,ProbeSamsungDex041.normalize(new DexBackedDexFile(Opcodes.forApi(29),output).getClasses()));
  Files.write(Path.of(a[4]),output,StandardOpenOption.CREATE_NEW);
  System.out.println("{\"mode\":"+SecurityDexReader.q(mode)+",\"records\":"+rows.size()+",\"outputSha256\":"+SecurityDexReader.q(SecurityDexReader.sha(output))+"}");
 }
}
