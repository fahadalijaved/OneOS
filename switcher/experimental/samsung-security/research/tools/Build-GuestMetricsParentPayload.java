import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.*;
import com.android.tools.smali.dexlib2.base.reference.BaseTypeReference;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.debug.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.immutable.*;
import com.android.tools.smali.dexlib2.immutable.debug.*;
import com.android.tools.smali.dexlib2.immutable.instruction.*;
import com.android.tools.smali.dexlib2.immutable.reference.*;

/** Offline symbolic three-hook prototype. No OEM classes are loaded/executed. */
final class BuildGuestMetricsParentPayload {
 static final String DMS="Lcom/android/server/display/DisplayManagerService;",BINDER=DMS.substring(0,DMS.length()-1)+"$BinderService;";
 static final String CELL="Lcom/appleexploit/oneos/security/authority/PreparedGuestMetricsParentCell;",FIELD="mOneOsGuestMetricsLifecycle";
 static final String START="onStart()V",BOOT="onBootPhase(I)V",TRANS="onTransact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z";
 static final String DISPATCH="dispatchOneOsGuestMetricsFromParent(Landroid/os/Binder;Landroid/os/Parcel;Landroid/os/Parcel;I)Z";
 static final List<String> ARGS=List.of("Landroid/os/Binder;","Landroid/os/Parcel;","Landroid/os/Parcel;","I");
 static final ImmutableFieldReference FIELD_REF=new ImmutableFieldReference(DMS,FIELD,CELL);
 static final ImmutableMethodReference CAPTURE=new ImmutableMethodReference(CELL,"captureAfterOnStart",List.of("Ljava/lang/Object;","Landroid/os/Binder;"),CELL);
 static final ImmutableMethodReference PHASE=new ImmutableMethodReference(CELL,"onOriginalBootPhaseCompleted",List.of("Ljava/lang/Object;","I"),CELL.substring(0,CELL.length()-1)+"$PhaseDisposition;");
 static final ImmutableMethodReference PARENT=new ImmutableMethodReference(DMS,"dispatchOneOsGuestMetricsFromParent",ARGS,"Z");
 static final ImmutableMethodReference CELL_DISPATCH=new ImmutableMethodReference(CELL,"dispatchFromParent",List.of("Ljava/lang/Object;","Landroid/os/Binder;","Landroid/os/Parcel;","Landroid/os/Parcel;","I"),"Z");
 static void need(boolean b,String m){if(!b)throw new IllegalArgumentException(m);}
 static String sig(Method m){return SecurityDexReader.signature(m);}
 static boolean selected(Method m){return (m.getDefiningClass().equals(DMS)&&(sig(m).equals(START)||sig(m).equals(BOOT)))||(m.getDefiningClass().equals(BINDER)&&sig(m).equals(TRANS));}
 static int insertion(String s){return s.equals(START)?53:s.equals(BOOT)?276:0;}
 static int width(String s){return s.equals(START)?8:s.equals(BOOT)?9:12;}
 static int map(String s,int p,boolean inverse){int at=insertion(s),n=width(s);if(!inverse)return p<at?p:p+n;need(p<at||p>=at+n,"Inverse debug/try points into authored block");return p<at?p:p-n;}
 static List<Instruction> block(String s){
  if(s.equals(START))return List.of(new ImmutableInstruction35c(Opcode.INVOKE_STATIC,2,3,0,0,0,0,CAPTURE),new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT,1),new ImmutableInstruction22c(Opcode.IPUT_OBJECT,1,3,FIELD_REF),new ImmutableInstruction10t(Opcode.GOTO,2),new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION,1));
  if(s.equals(BOOT))return List.of(new ImmutableInstruction21s(Opcode.CONST_16,0,100),new ImmutableInstruction22t(Opcode.IF_NE,11,0,7),new ImmutableInstruction35c(Opcode.INVOKE_STATIC,2,10,11,0,0,0,PHASE),new ImmutableInstruction10t(Opcode.GOTO,2),new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION,0));
  return List.of(new ImmutableInstruction31i(Opcode.CONST,0,0x00fe0001),new ImmutableInstruction22t(Opcode.IF_NE,3,0,9),new ImmutableInstruction22c(Opcode.IGET_OBJECT,0,2,new ImmutableFieldReference(BINDER,"this$0",DMS)),new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL,5,0,2,4,5,6,PARENT),new ImmutableInstruction11x(Opcode.MOVE_RESULT,0),new ImmutableInstruction11x(Opcode.RETURN,0));
 }
 static DebugItem debug(DebugItem d,String s,boolean inverse){
  int p=map(s,d.getCodeAddress(),inverse);
  if(d instanceof StartLocal l)return new ImmutableStartLocal(p,l.getRegister(),l.getName(),l.getType(),l.getSignature());
  if(d instanceof EndLocal l)return new ImmutableEndLocal(p,l.getRegister(),l.getName(),l.getType(),l.getSignature());
  if(d instanceof RestartLocal l)return new ImmutableRestartLocal(p,l.getRegister(),l.getName(),l.getType(),l.getSignature());
  if(d instanceof LineNumber l)return new ImmutableLineNumber(p,l.getLineNumber());
  if(d instanceof PrologueEnd)return new ImmutablePrologueEnd(p);
  if(d instanceof EpilogueBegin)return new ImmutableEpilogueBegin(p);
  if(d instanceof SetSourceFile l)return new ImmutableSetSourceFile(p,l.getSourceFile());
  throw new IllegalArgumentException("Unknown selected debug item");
 }
 static Method transform(Method m,boolean inverse){
  String s=sig(m);MethodImplementation old=m.getImplementation();need(old!=null&&m.getAccessFlags()==1,"Selected source attributes");
  int originalUnits=s.equals(START)?57:s.equals(BOOT)?277:27,registers=s.equals(START)?4:s.equals(BOOT)?12:7;
  need(old.getRegisterCount()==registers,"Selected register count");
  List<Instruction> code=new ArrayList<>();int pc=0;boolean inserted=false;List<Instruction> added=block(s);int blockIndex=0;
  for(Instruction i:old.getInstructions()){
   if(!inverse&&pc==insertion(s)){code.addAll(added);inserted=true;}
   if(inverse&&pc>=insertion(s)&&pc<insertion(s)+width(s)){
    need(blockIndex<added.size()&&SecurityDexReader.instruction(i,pc-insertion(s)).equals(SecurityDexReader.instruction(added.get(blockIndex),pc-insertion(s))),"Inverse authored instruction mismatch");blockIndex++;
   }else{
    if(i instanceof OffsetInstruction o)need(map(s,pc+o.getCodeOffset(),inverse)-map(s,pc,inverse)==o.getCodeOffset(),"Unapproved original relative branch change");
    code.add(i);
   }
   pc+=i.getCodeUnits();
  }
  need(pc==originalUnits+(inverse?width(s):0),"Selected source code extent");need(inverse?blockIndex==added.size():inserted,"Exact insertion/removal not reached");
  List<TryBlock<? extends ExceptionHandler>> tries=new ArrayList<>();int removed=0;
  for(var t:old.getTryBlocks()){
   int at=s.equals(START)?53:280,len=s.equals(START)?6:3,handler=s.equals(START)?60:284;
   if(inverse&&!s.equals(TRANS)&&t.getStartCodeAddress()==at){need(t.getCodeUnitCount()==len&&t.getExceptionHandlers().size()==1&&"Ljava/lang/Throwable;".equals(t.getExceptionHandlers().get(0).getExceptionType())&&t.getExceptionHandlers().get(0).getHandlerCodeAddress()==handler,"Inverse new catch mismatch");removed++;continue;}
   List<ExceptionHandler> hs=new ArrayList<>();for(var h:t.getExceptionHandlers())hs.add(new ImmutableExceptionHandler(h.getExceptionType(),map(s,h.getHandlerCodeAddress(),inverse)));
   int start=map(s,t.getStartCodeAddress(),inverse),end=map(s,t.getStartCodeAddress()+t.getCodeUnitCount(),inverse);tries.add(new ImmutableTryBlock(start,end-start,hs));
  }
  if(!s.equals(TRANS)){
   if(inverse)need(removed==1,"Exactly one new catch required");
   else tries.add(new ImmutableTryBlock(s.equals(START)?53:280,s.equals(START)?6:3,List.of(new ImmutableExceptionHandler("Ljava/lang/Throwable;",s.equals(START)?60:284))));
  }
  tries.sort(Comparator.comparingInt(TryBlock::getStartCodeAddress));
  List<DebugItem> dbg=new ArrayList<>();for(DebugItem d:old.getDebugItems())dbg.add(debug(d,s,inverse));
  return new ImmutableMethod(m.getDefiningClass(),m.getName(),m.getParameters(),m.getReturnType(),m.getAccessFlags(),m.getAnnotations(),m.getHiddenApiRestrictions(),new ImmutableMethodImplementation(registers,code,tries,dbg));
 }
 static Method dispatch(){
  List<MethodParameter> params=new ArrayList<>();for(String t:ARGS)params.add(new ImmutableMethodParameter(t,Set.of(),null));
  List<Instruction> code=List.of(new ImmutableInstruction22c(Opcode.IGET_OBJECT,0,1,FIELD_REF),new ImmutableInstruction21t(Opcode.IF_EQZ,0,7),new ImmutableInstruction3rc(Opcode.INVOKE_VIRTUAL_RANGE,0,6,CELL_DISPATCH),new ImmutableInstruction11x(Opcode.MOVE_RESULT,0),new ImmutableInstruction11x(Opcode.RETURN,0),new ImmutableInstruction11n(Opcode.CONST_4,0,0),new ImmutableInstruction11x(Opcode.RETURN,0));
  return new ImmutableMethod(DMS,"dispatchOneOsGuestMetricsFromParent",params,"Z",0,Set.of(),Set.of(),new ImmutableMethodImplementation(6,code,List.of(),List.of()));
 }
 static final class Overlay extends BaseTypeReference implements ClassDef {
  final ClassDef base;final boolean inverse;Overlay(ClassDef b,boolean i){base=b;inverse=i;}
  public String getType(){return base.getType();}public int getAccessFlags(){return base.getAccessFlags();}public String getSuperclass(){return base.getSuperclass();}public List<String>getInterfaces(){return base.getInterfaces();}public String getSourceFile(){return base.getSourceFile();}public Set<? extends Annotation>getAnnotations(){return base.getAnnotations();}
  public Iterable<? extends Field>getStaticFields(){return base.getStaticFields();}
  public Iterable<? extends Field>getInstanceFields(){List<Field>out=new ArrayList<>();int found=0;for(Field f:base.getInstanceFields()){if(base.getType().equals(DMS)&&f.getName().equals(FIELD)){need(inverse&&f.getType().equals(CELL)&&f.getAccessFlags()==0x42&&f.getInitialValue()==null&&f.getAnnotations().isEmpty()&&f.getHiddenApiRestrictions().isEmpty(),"New field inverse attributes");found++;}else out.add(f);}if(base.getType().equals(DMS)){need(found==(inverse?1:0),"New field name collision/absence");if(!inverse)out.add(new ImmutableField(DMS,FIELD,CELL,0x42,null,Set.of(),Set.of()));}return out;}
  public Iterable<? extends Field>getFields(){List<Field>out=new ArrayList<>();getStaticFields().forEach(out::add);getInstanceFields().forEach(out::add);return out;}
  List<Method>methods(Iterable<? extends Method> source,boolean direct){List<Method>out=new ArrayList<>();int found=0;for(Method m:source){if(base.getType().equals(DMS)&&sig(m).equals(DISPATCH)){need(inverse&&!direct,"New dispatch collision/partition");found++;}else out.add(selected(m)?transform(m,inverse):m);}if(base.getType().equals(DMS)&&!direct){need(found==(inverse?1:0),"New dispatch absence");if(!inverse)out.add(dispatch());}return out;}
  public Iterable<? extends Method>getDirectMethods(){return methods(base.getDirectMethods(),true);}public Iterable<? extends Method>getVirtualMethods(){return methods(base.getVirtualMethods(),false);}public Iterable<? extends Method>getMethods(){List<Method>out=new ArrayList<>();getDirectMethods().forEach(out::add);getVirtualMethods().forEach(out::add);return out;}
 }
 static List<ClassDef> overlay(Collection<? extends ClassDef> source,boolean inverse){List<ClassDef>out=new ArrayList<>();int changed=0;for(ClassDef c:source){if(c.getType().equals(DMS)||c.getType().equals(BINDER)){out.add(new Overlay(c,inverse));changed++;}else out.add(c);}need(changed==2,"Exact selected class pair");return out;}
 static byte[] original(Path archive)throws Exception{try(ZipFile z=new ZipFile(archive.toFile())){need(z.stream().filter(e->e.getName().equals("classes2.dex")).count()==1,"Unique original DEX");var e=z.getEntry("classes2.dex");need(e.getSize()==10042704,"Original extent");try(var in=z.getInputStream(e)){byte[]b=in.readNBytes(10042705);need(b.length==10042704&&SecurityDexReader.sha(b).equals("c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f"),"Original DEX pin");return b;}}}
 public static void main(String[]a)throws Exception{
  need(a.length==5,"forward|decode|reemit|inverse input archive raw-dir binary-file");String mode=a[0];Path raw=Path.of(a[3]);need(Files.isDirectory(raw),"Exclusive raw directory required");
  byte[]src=original(Path.of(a[2]));ProbeSamsungDex041.validate(src);ProbeColorosServicesDex.absent(src);var source=new DexBackedDexFile(Opcodes.forApi(29),src);
  byte[]input=mode.equals("forward")?src:Files.readAllBytes(Path.of(a[1]));need(input.length<=32*1024*1024,"Generated extent");ProbeSamsungDex041.validate(input);ProbeColorosServicesDex.absent(input);var current=new DexBackedDexFile(Opcodes.forApi(29),input);need(current.getClasses().size()==6554,"Class cohort exact");
  Collection<? extends ClassDef> classes=current.getClasses();
  if(mode.equals("forward")){
   var before=ProbeSamsungDex041.normalize(source.getClasses());ProbeSamsungDex041.saveRows(raw.resolve("original-normalized.jsonl"),before);classes=overlay(classes,false);var expected=ProbeSamsungDex041.normalize(classes);need(expected.size()==76709,"Expected exact +2 records");
   Set<String>allowed=Set.of(DMS+"->"+START,DMS+"->"+BOOT,BINDER+"->"+TRANS);for(var e:before.entrySet())if(!allowed.contains(e.getKey()))need(e.getValue().equals(expected.get(e.getKey())),"Unexpected source record edit "+e.getKey());
   need(expected.keySet().containsAll(before.keySet())&&expected.containsKey(DMS+"->"+FIELD+":"+CELL)&&expected.containsKey(DMS+"->"+DISPATCH),"Exact added members");ProbeSamsungDex041.saveRows(raw.resolve("expected-edited-normalized.jsonl"),expected);
  }else if(mode.equals("inverse")){
   var expected=ProbeSamsungDex041.normalize(overlay(source.getClasses(),false));var actual=ProbeSamsungDex041.normalize(classes);ProbeSamsungDex041.same(expected,actual);classes=overlay(classes,true);var inverse=ProbeSamsungDex041.normalize(classes);ProbeSamsungDex041.same(ProbeSamsungDex041.normalize(source.getClasses()),inverse);ProbeSamsungDex041.saveRows(raw.resolve("symbolic-inverse-normalized.jsonl"),inverse);
  }else if(mode.equals("decode")){ProbeSamsungDex041.saveRows(raw.resolve(Path.of(a[1]).getFileName()+".normalized.jsonl"),ProbeSamsungDex041.normalize(classes));System.out.println("{\"decoded\":true}");return;
  }else need(mode.equals("reemit"),"Unknown mode");
  byte[]emitted=ProbeColorosServicesDex.emit(classes);Files.write(Path.of(a[4]),emitted,StandardOpenOption.CREATE_NEW);System.out.println("{\"mode\":"+SecurityDexReader.q(mode)+",\"inputSha256\":"+SecurityDexReader.q(SecurityDexReader.sha(input))+",\"emittedSha256\":"+SecurityDexReader.q(SecurityDexReader.sha(emitted))+"}");
 }
}
