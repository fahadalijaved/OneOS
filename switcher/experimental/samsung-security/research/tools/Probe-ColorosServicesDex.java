import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;

/** Authored offline writer only. Exact original complete classes2; no edits/repair. */
final class ProbeColorosServicesDex {
 static String q(String s){return SecurityDexReader.q(s);}
 static String sha(byte[] b)throws Exception{return SecurityDexReader.sha(b);}
 static String stats(){return "{\"fields\":"+ProbeSamsungDex041.fields+",\"methods\":"+ProbeSamsungDex041.methods+",\"instructions\":"+ProbeSamsungDex041.instructions+",\"tryBlocks\":"+ProbeSamsungDex041.tries+",\"debugItems\":"+ProbeSamsungDex041.debugItems+",\"annotations\":"+ProbeSamsungDex041.annotationCount+",\"hiddenApiMembers\":"+ProbeSamsungDex041.hiddenMembers+",\"explicitInitialValues\":"+ProbeSamsungDex041.staticInitialValues+"}";}
 static void absent(byte[] b){
  if(!SecurityDexReader.headers(b).equals(List.of(0))||SecurityDexReader.u32(b,36)!=112||b[4]!='0'||b[5]!='3'||b[6]!='9')throw new IllegalArgumentException("Complete ordinary039 only");
  int map=Math.toIntExact(SecurityDexReader.u32(b,52)),n=Math.toIntExact(SecurityDexReader.u32(b,map));
  if(n<1||n>64||map<112||map+4L+12L*n>b.length)throw new IllegalArgumentException("Map extent");
  Set<Integer> types=new HashSet<>();long previous=-1;
  for(int i=0;i<n;i++){int p=map+4+12*i,type=(b[p]&255)|((b[p+1]&255)<<8);long size=SecurityDexReader.u32(b,p+4),off=SecurityDexReader.u32(b,p+8);
   if(type==0xf000||!types.add(type)||size<1||off>=b.length||off<previous)throw new IllegalArgumentException("Map duplicate/order/extent or HAPI synthesized");previous=off;
  }
 }
 static byte[] emit(Collection<? extends ClassDef> classes)throws Exception{
  SourcePreservingDexPool pool=new SourcePreservingDexPool();for(ClassDef c:classes)pool.internClass(c);
  if(pool.hasOverflowed())throw new IllegalArgumentException("Pool overflow");
  MemoryDataStore store=new MemoryDataStore();try{pool.writeTo(store);byte[] b=store.getData();ProbeSamsungDex041.validate(b);absent(b);return b;}finally{store.close();}
 }
 static void compare(Map<String,String> original,Map<String,String> decoded,Path binary)throws Exception{
  if(original.equals(decoded))return;
  List<String> changed=new ArrayList<>();Set<String> keys=new TreeSet<>(original.keySet());keys.addAll(decoded.keySet());
  for(String k:keys)if(!Objects.equals(original.get(k),decoded.get(k)))changed.add(k);
  StringBuilder report=new StringBuilder("{\"changedRecords\":").append(changed.size()).append(",\"firstKeys\":[");
  for(int i=0;i<Math.min(20,changed.size());i++){if(i>0)report.append(',');report.append(q(changed.get(i)));}
  Files.writeString(binary.resolve("strict-differences.json"),report.append("]}").toString(),StandardOpenOption.CREATE_NEW);
  throw new IllegalArgumentException("Strict normalized equality failed: "+changed.size()+" records; first="+changed.get(0));
 }
 public static void main(String[] args)throws Exception{
  if(args.length!=3)throw new IllegalArgumentException("services.jar exclusive-raw-dir exclusive-binary-dir");
  Path raw=Path.of(args[1]),binary=Path.of(args[2]);if(!Files.isDirectory(raw)||!Files.isDirectory(binary))throw new IllegalArgumentException("Exclusive output directories required");
  byte[] input;
  try(ZipFile z=new ZipFile(args[0])){
   if(z.stream().filter(e->e.getName().equals("classes2.dex")).count()!=1)throw new IllegalArgumentException("Unique selected entry required");
   var e=z.getEntry("classes2.dex");if(e.getSize()!=10042704)throw new IllegalArgumentException("Pinned DEX size");
   try(var in=z.getInputStream(e)){input=in.readNBytes(10042705);}
  }
  if(input.length!=10042704||!sha(input).equals("c9a84cebd3bc22a48c0737a7de34d96ba0b97a6294d4bdd97c935543e605659f"))throw new IllegalArgumentException("Pinned complete DEX differs");
  ProbeSamsungDex041.validate(input);absent(input);
  var source=new DexBackedDexFile(Opcodes.forApi(29),input);if(source.getClasses().size()!=6554)throw new IllegalArgumentException("No subset permitted");
  System.err.println("stage=normalize-original");var original=ProbeSamsungDex041.normalize(source.getClasses());String counts=stats();
  if(ProbeSamsungDex041.hiddenMembers!=0)throw new IllegalArgumentException("Unexpected decoded restriction metadata");
  ProbeSamsungDex041.saveRows(raw.resolve("original-normalized.jsonl"),original);
  System.err.println("stage=emit-first");byte[] first=emit(source.getClasses());Files.write(binary.resolve("classes2-noedit-039.dex"),first,StandardOpenOption.CREATE_NEW);
  System.err.println("stage=normalize-decoded");var decoded=new DexBackedDexFile(Opcodes.forApi(29),first);var after=ProbeSamsungDex041.normalize(decoded.getClasses());ProbeSamsungDex041.saveRows(raw.resolve("decoded-normalized.jsonl"),after);compare(original,after,binary);
  if(!counts.equals(stats()))throw new IllegalArgumentException("Category counts differ");after=null;
  System.err.println("stage=emit-second");byte[] second=emit(decoded.getClasses());Files.write(binary.resolve("classes2-roundtrip-039.dex"),second,StandardOpenOption.CREATE_NEW);
  if(!Arrays.equals(first,second))throw new IllegalArgumentException("Second emit bytes differ");
  System.err.println("stage=normalize-roundtrip");var last=ProbeSamsungDex041.normalize(new DexBackedDexFile(Opcodes.forApi(29),second).getClasses());ProbeSamsungDex041.saveRows(raw.resolve("roundtrip-normalized.jsonl"),last);compare(original,last,binary);
  if(!counts.equals(stats()))throw new IllegalArgumentException("Roundtrip counts differ");
  System.out.println("{\"status\":\"PASS_STRICT_NO_EDIT_CLASSES2_ONLY\",\"classes\":6554,\"normalizedRecords\":"+original.size()+",\"categoryCounts\":"+counts+",\"sourceDexSha256\":"+q(sha(input))+",\"outputDexSha256\":"+q(sha(first))+",\"outputBytes\":"+first.length+",\"secondEmitByteIdentical\":true,\"allNormalizedRecordsEqual\":true,\"hiddenApiAbsentAllThree\":true,\"repairsApplied\":false}");
 }
}
