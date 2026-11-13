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
final class GuestPolicyInitRetarget {
 static final String OWNER="Lcom/android/server/wm/WindowManagerService$6;";
 static final String POLICY="Lcom/android/server/policy/WindowManagerPolicy;";
 static final String CONTEXT="Landroid/content/Context;";
 static final String FUNCS="Lcom/android/server/policy/WindowManagerPolicy$WindowManagerFuncs;";
 static final String HELPER="Lcom/appleexploit/oneos/security/authority/PreparedGuestPolicyInitCompletion;";
 static final MethodReference OLD=new ImmutableMethodReference(POLICY,"init",List.of(CONTEXT,FUNCS),"V");
 static final MethodReference NEW=new ImmutableMethodReference(HELPER,"invokeOriginal",List.of(POLICY,CONTEXT,FUNCS),"V");
 static void need(boolean b,String m){if(!b)throw new IllegalArgumentException(m);}
 static boolean target(Method m){return m.getDefiningClass().equals(OWNER)&&SecurityDexReader.signature(m).equals("run()V");}
 static Method edit(Method m,boolean inverse){
  if(!target(m))return m;
  MethodImplementation body=m.getImplementation();
  need(m.getAccessFlags()==1&&body!=null&&body.getRegisterCount()==4&&body.getTryBlocks().isEmpty(),"Selected declaration/registers/tries");
  List<Instruction> code=new ArrayList<>();int pc=0,count=0,changed=0;
  for(Instruction i:body.getInstructions()){
   need(!(i instanceof OffsetInstruction),"No selected branch/payload");
   if(pc==21){
    need(i.getCodeUnits()==3&&i.getOpcode()==(inverse?Opcode.INVOKE_STATIC:Opcode.INVOKE_INTERFACE),"Selected opcode/width");
    need(i instanceof FiveRegisterInstruction&&i instanceof ReferenceInstruction,"Selected format35c");
    FiveRegisterInstruction r=(FiveRegisterInstruction)i;
    need(r.getRegisterCount()==3&&r.getRegisterC()==0&&r.getRegisterD()==1&&r.getRegisterE()==2&&r.getRegisterF()==0&&r.getRegisterG()==0,"All selected register nibbles");
    need(SecurityDexReader.ref(((ReferenceInstruction)i).getReference()).equals(SecurityDexReader.ref(inverse?NEW:OLD)),"Selected exact method reference");
    code.add(new ImmutableInstruction35c(inverse?Opcode.INVOKE_INTERFACE:Opcode.INVOKE_STATIC,3,0,1,2,0,0,inverse?OLD:NEW));changed++;
   }else code.add(i);
   if(pc==24)need(i.getOpcode()==Opcode.RETURN_VOID&&i.getCodeUnits()==1,"Original sole terminal return");
   pc+=i.getCodeUnits();count++;
  }
  need(pc==25&&count==12&&changed==1,"Selected exact extent/count");
  return new ImmutableMethod(m.getDefiningClass(),m.getName(),m.getParameters(),m.getReturnType(),m.getAccessFlags(),m.getAnnotations(),m.getHiddenApiRestrictions(),new ImmutableMethodImplementation(4,code,body.getTryBlocks(),body.getDebugItems()));
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
  for(ClassDef c:cs){if(c.getType().equals(OWNER)){for(Method m:c.getMethods())if(target(m))found++;out.add(new Overlay(c,inverse));}else out.add(c);}
  need(found==1,"Exactly one selected original method");return out;
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
  need(source.length==10520292&&SecurityDexReader.sha(source).equals("69a7371f7ef48300562a2c1fe442298b369f64672a6bdf61d8099eeef9ad6264"),"Literal original source DEX");
  var original=new DexBackedDexFile(Opcodes.forApi(29),source);var dex=new DexBackedDexFile(Opcodes.forApi(29),input);
  need(original.getClasses().size()==6914&&dex.getClasses().size()==6914,"All original class definitions only");
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
