import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.ArrayPayload;
import com.android.tools.smali.dexlib2.iface.reference.*;

/** Static metadata/instruction reader. Raw stdout MUST be kept under ignored firmware/. */
public final class SecurityDexReader {
    static final class LogicalDex extends DexBackedDexFile {
        LogicalDex(byte[] container,int header){super(null,container,0,false,header);}
    }
    static String q(String s){if(s==null)return "null";StringBuilder b=new StringBuilder("\"");for(int i=0;i<s.length();i++){char c=s.charAt(i);switch(c){case '"':b.append("\\\"");break;case '\\':b.append("\\\\");break;case '\n':b.append("\\n");break;case '\r':b.append("\\r");break;case '\t':b.append("\\t");break;default:if(c<32||Character.isSurrogate(c))b.append(String.format("\\u%04x",(int)c));else b.append(c);}}return b.append('"').toString();}
    static String sha(byte[] b)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b));}
    static long u32(byte[] b,int p){if(p<0||p>b.length-4)throw new IllegalArgumentException("Header range");return ((long)b[p]&255)|(((long)b[p+1]&255)<<8)|(((long)b[p+2]&255)<<16)|(((long)b[p+3]&255)<<24);}
    static List<Integer> headers(byte[] b){List<Integer> out=new ArrayList<>();int pos=0;do{
        if(pos>b.length-112||b[pos]!='d'||b[pos+1]!='e'||b[pos+2]!='x'||b[pos+3]!='\n'||b[pos+7]!=0)throw new IllegalArgumentException("DEX magic/header range");
        String v=new String(b,pos+4,3,StandardCharsets.US_ASCII);if(!Set.of("035","037","038","039","040","041").contains(v))throw new IllegalArgumentException("Unsupported DEX "+v);
        long size=u32(b,pos+32),hs=u32(b,pos+36);if(u32(b,pos+40)!=0x12345678L)throw new IllegalArgumentException("DEX endian");
        if(v.equals("041")){if(pos>b.length-120||hs!=120||u32(b,pos+112)!=b.length||u32(b,pos+116)!=pos||size<120||size>b.length-pos)throw new IllegalArgumentException("Invalid full-container041 extent/headerOffset");}
        else if(pos!=0||hs!=112||size!=b.length)throw new IllegalArgumentException("Unexpected ordinary DEX extent");
        for(int off:new int[]{56,64,72,80,88,96}){long count=u32(b,pos+off),table=u32(b,pos+off+4);int width=off==56||off==64?4:off==72?12:off==96?32:8;if(count>2_000_000||count>0&&table+count*width>b.length)throw new IllegalArgumentException("DEX table extent");}
        out.add(pos);if(out.size()>128)throw new IllegalArgumentException("Logical DEX count bound");pos+=Math.toIntExact(size);
    }while(pos<b.length);if(pos!=b.length)throw new IllegalArgumentException("Container does not close");return out;}
    static String signature(MethodReference m){StringBuilder b=new StringBuilder(m.getName()).append('(');for(CharSequence p:m.getParameterTypes())b.append(p);return b.append(')').append(m.getReturnType()).toString();}
    static String ref(Reference r){if(r instanceof MethodReference m)return m.getDefiningClass()+"->"+signature(m);if(r instanceof FieldReference f)return f.getDefiningClass()+"->"+f.getName()+":"+f.getType();if(r instanceof TypeReference t)return t.getType();if(r instanceof StringReference s)return "string="+s.getString();return r.toString();}
    static String refKind(Reference r){return r instanceof MethodReference?"method":r instanceof FieldReference?"field":r instanceof TypeReference?"type":r instanceof StringReference?"string":"other";}
    static boolean matches(Reference r,String wanted){if(ref(r).equals(wanted))return true;if(wanted.startsWith("L")&&wanted.endsWith(";"))return r instanceof MethodReference m&&m.getDefiningClass().equals(wanted)||r instanceof FieldReference f&&f.getDefiningClass().equals(wanted);return false;}
    static String instruction(Instruction i,int pc){StringBuilder b=new StringBuilder("{\"pc\":").append(pc).append(",\"opcode\":").append(q(i.getOpcode().name())).append(",\"codeUnits\":").append(i.getCodeUnits());
        if(i instanceof FiveRegisterInstruction r){int[] regs={r.getRegisterC(),r.getRegisterD(),r.getRegisterE(),r.getRegisterF(),r.getRegisterG()};List<String> v=new ArrayList<>();for(int n=0;n<r.getRegisterCount();n++)v.add(""+regs[n]);b.append(",\"registers\":[").append(String.join(",",v)).append(']');}
        else if(i instanceof RegisterRangeInstruction r)b.append(",\"registerStart\":").append(r.getStartRegister()).append(",\"registerCount\":").append(r.getRegisterCount());
        else {List<String> regs=new ArrayList<>();if(i instanceof OneRegisterInstruction r)regs.add(""+r.getRegisterA());if(i instanceof TwoRegisterInstruction r)regs.add(""+r.getRegisterB());if(i instanceof ThreeRegisterInstruction r)regs.add(""+r.getRegisterC());if(!regs.isEmpty())b.append(",\"registers\":[").append(String.join(",",regs)).append(']');}
        if(i instanceof OffsetInstruction r)b.append(",\"targetPc\":").append(pc+r.getCodeOffset());
        if(i instanceof WideLiteralInstruction r)b.append(",\"literal\":").append(r.getWideLiteral());
        if(i instanceof ReferenceInstruction r)b.append(",\"referenceKind\":").append(q(refKind(r.getReference()))).append(",\"reference\":").append(q(ref(r.getReference())));
        if(i instanceof DualReferenceInstruction r)b.append(",\"reference2\":").append(q(ref(r.getReference2())));
        if(i instanceof SwitchPayload r){List<String> e=new ArrayList<>();for(SwitchElement s:r.getSwitchElements())e.add("{\"key\":"+s.getKey()+",\"offsetFromReferringSwitchPc\":"+s.getOffset()+"}");b.append(",\"switchElements\":[").append(String.join(",",e)).append(']');}
        if(i instanceof ArrayPayload r){List<String> values=new ArrayList<>();for(Number n:r.getArrayElements())values.add(n.toString());b.append(",\"elementWidth\":").append(r.getElementWidth()).append(",\"arrayElements\":[").append(String.join(",",values)).append(']');}
        if(i instanceof FieldOffsetInstruction r)b.append(",\"fieldOffset\":").append(r.getFieldOffset());
        if(i instanceof InlineIndexInstruction r)b.append(",\"inlineIndex\":").append(r.getInlineIndex());
        if(i instanceof VtableIndexInstruction r)b.append(",\"vtableIndex\":").append(r.getVtableIndex());
        return b.append('}').toString();}
    static String declaration(ClassDef c,boolean full){List<String> methods=new ArrayList<>(),fields=new ArrayList<>(),interfaces=new ArrayList<>();for(Method m:c.getMethods())methods.add("{\"signature\":"+q(signature(m))+",\"accessFlags\":"+m.getAccessFlags()+"}");for(Field f:c.getFields())fields.add("{\"name\":"+q(f.getName())+",\"descriptor\":"+q(f.getType())+",\"accessFlags\":"+f.getAccessFlags()+"}");for(String i:c.getInterfaces())interfaces.add(q(i));Collections.sort(methods);Collections.sort(fields);Collections.sort(interfaces);return "{\"record\":\"class\",\"descriptor\":"+q(c.getType())+",\"accessFlags\":"+c.getAccessFlags()+",\"superclass\":"+q(c.getSuperclass())+",\"interfaces\":["+String.join(",",interfaces)+"],\"declaredMethodCount\":"+methods.size()+",\"declaredFieldCount\":"+fields.size()+(full?",\"methods\":["+String.join(",",methods)+"],\"fields\":["+String.join(",",fields)+"]":"")+"}";}
    public static void main(String[] a)throws Exception{
        if(a.length<3)throw new IllegalArgumentException("archive class-descriptor-or-* reference-or-- [exact-signature...]");
        String wanted=a[1],reference=a[2];Set<String> selectors=new HashSet<>(Arrays.asList(a).subList(3,a.length)),seenMethods=new HashSet<>();if(selectors.size()>128)throw new IllegalArgumentException("Method selection bound");
        boolean allMethods=selectors.equals(Set.of("--ALL-DECLARED-METHODS--"));boolean allClasses=wanted.equals("--ALL-CLASSES--");int selectedClasses=0,classes=0,selectedMethods=0;long scannedInstructions=0;Set<String> physicalNames=new HashSet<>();
        try(var archive=new ZipFile(a[0]);var out=new PrintWriter(new OutputStreamWriter(System.out,StandardCharsets.UTF_8))){
            var entries=archive.stream().filter(e->e.getName().matches("classes(?:[2-9]|[1-9][0-9]+)?\\.dex")).sorted(Comparator.comparingInt(e->e.getName().equals("classes.dex")?1:Integer.parseInt(e.getName().substring(7,e.getName().length()-4)))).toList();
            if(entries.isEmpty()||entries.size()>64)throw new IllegalArgumentException("Physical DEX count bound");long expanded=0;
            for(var entry:entries){if(!physicalNames.add(entry.getName())||entry.getSize()<112||entry.getSize()>256L*1024*1024||(expanded+=entry.getSize())>512L*1024*1024)throw new IllegalArgumentException("DEX expansion/duplicate bound");
                byte[] bytes;try(var in=archive.getInputStream(entry)){bytes=in.readNBytes(256*1024*1024+1);}if(bytes.length!=entry.getSize())throw new IllegalArgumentException("DEX length");
                for(int header:headers(bytes)){var dex=new LogicalDex(bytes,header);var types=dex.getClasses();if(types.size()!=u32(bytes,header+96))throw new IllegalArgumentException("Logical class count mismatch");
                    out.println("{\"record\":\"dex\",\"physicalDex\":"+q(entry.getName())+",\"logicalHeaderOffset\":"+header+",\"containerBytes\":"+bytes.length+",\"logicalBytes\":"+u32(bytes,header+32)+",\"version\":"+q(new String(bytes,header+4,3,StandardCharsets.US_ASCII))+",\"physicalDexSha256\":"+q(sha(bytes))+",\"classCount\":"+types.size()+"}");
                    for(ClassDef c:types){if(++classes>200000)throw new IllegalArgumentException("Class bound");boolean selected=c.getType().equals(wanted);if(selected)selectedClasses++;
                        if((selected||allClasses)&&reference.equals("-")){String row=declaration(c,!allClasses);out.println(row.substring(0,row.length()-1)+",\"physicalDex\":"+q(entry.getName())+",\"logicalHeaderOffset\":"+header+"}");}
                        for(Method m:c.getMethods()){
                            boolean take=selected&&(allMethods||selectors.contains(signature(m)));var body=(take||!reference.equals("-"))?m.getImplementation():null;
                            if(take){seenMethods.add(signature(m));selectedMethods++;if(selectedMethods>2048)throw new IllegalArgumentException("Method bound");List<String> instructions=new ArrayList<>(),catches=new ArrayList<>();int pc=0,count=0;
                                if(body!=null){for(Instruction i:body.getInstructions()){if(++count>100000)throw new IllegalArgumentException("Selected method instruction bound");instructions.add(instruction(i,pc));pc+=i.getCodeUnits();}for(var t:body.getTryBlocks())for(var h:t.getExceptionHandlers())catches.add("{\"startPc\":"+t.getStartCodeAddress()+",\"codeUnits\":"+t.getCodeUnitCount()+",\"exceptionType\":"+q(h.getExceptionType())+",\"handlerPc\":"+h.getHandlerCodeAddress()+"}");}
                                String normalized="{\"owner\":"+q(c.getType())+",\"signature\":"+q(signature(m))+",\"accessFlags\":"+m.getAccessFlags()+",\"registerCount\":"+(body==null?0:body.getRegisterCount())+",\"hasCode\":"+(body!=null)+",\"instructions\":["+String.join(",",instructions)+"],\"catches\":["+String.join(",",catches)+"]}";
                                out.println("{\"record\":\"method\",\"physicalDex\":"+q(entry.getName())+",\"logicalHeaderOffset\":"+header+",\"normalizedBodySha256\":"+q(sha(normalized.getBytes(StandardCharsets.UTF_8)))+",\"body\":"+normalized+"}");
                            }
                            if(!reference.equals("-")&&body!=null){int pc=0;for(Instruction i:body.getInstructions()){if(++scannedInstructions>20_000_000)throw new IllegalArgumentException("Reference scan instruction bound");if(i instanceof ReferenceInstruction r&&matches(r.getReference(),reference))out.println("{\"record\":\"reference\",\"physicalDex\":"+q(entry.getName())+",\"logicalHeaderOffset\":"+header+",\"caller\":"+q(c.getType()+"->"+signature(m))+",\"instruction\":"+instruction(i,pc)+"}");pc+=i.getCodeUnits();}}
                        }
                    }
                }
            }
            if(!allClasses&&selectedClasses!=1)throw new IllegalArgumentException("Selected class absent/ambiguous: "+selectedClasses);
            if(!allMethods&&!seenMethods.equals(selectors))throw new IllegalArgumentException("Exact selected signatures absent: "+selectors+" observed="+seenMethods);
            out.println("{\"record\":\"summary\",\"classDefinitions\":"+classes+",\"selectedClassDefinitions\":"+selectedClasses+",\"selectedMethods\":"+selectedMethods+",\"scannedReferenceInstructions\":"+scannedInstructions+"}");
            if(out.checkError())throw new IOException("Output failed");
        }
    }
}
