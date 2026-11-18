import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;

/** Hash-only whole-archive static proof; raw output belongs under ignored firmware/. */
public final class SettingsRpmbLeafProof {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("One archive required");
        int classes=0, methods=0, codeBodies=0; long instructions=0, expanded=0;
        Set<String> seenClasses=new HashSet<>(), seenMethods=new HashSet<>();
        try (ZipFile archive=new ZipFile(args[0]); PrintWriter out=new PrintWriter(new OutputStreamWriter(System.out,StandardCharsets.UTF_8))) {
            var entries=archive.stream().filter(e->e.getName().matches("classes(?:[2-9]|[1-9][0-9]+)?\\.dex"))
                .sorted(Comparator.comparingInt(e->e.getName().equals("classes.dex")?1:Integer.parseInt(e.getName().substring(7,e.getName().length()-4)))).toList();
            if(entries.size()!=14)throw new IllegalArgumentException("Exact fourteen DEX input required");
            for(var entry:entries){
                if(entry.getSize()<112||entry.getSize()>64L*1024*1024||(expanded+=entry.getSize())>256L*1024*1024)throw new IllegalArgumentException("DEX expanded bound");
                byte[] bytes;try(var input=archive.getInputStream(entry)){bytes=input.readNBytes(64*1024*1024+1);}
                if(bytes.length!=entry.getSize())throw new IllegalArgumentException("DEX length");
                for(int header:SecurityDexReader.headers(bytes)){
                    var dex=new SecurityDexReader.LogicalDex(bytes,header);
                    for(ClassDef c:dex.getClasses()){
                        if(++classes>100000||!seenClasses.add(c.getType()))throw new IllegalArgumentException("Class count/alias");
                        String declaration=SecurityDexReader.declaration(c,true);
                        out.println("{\"record\":\"class\",\"owner\":"+SecurityDexReader.q(c.getType())+",\"sha256\":"+SecurityDexReader.q(SecurityDexReader.sha(declaration.getBytes(StandardCharsets.UTF_8)))+"}");
                        for(Method m:c.getMethods()){
                            String sig=SecurityDexReader.signature(m),key=c.getType()+"->"+sig;
                            if(++methods>1000000||!seenMethods.add(key))throw new IllegalArgumentException("Method count/alias");
                            var implementation=m.getImplementation();List<String> ins=new ArrayList<>(),catches=new ArrayList<>();int pc=0;
                            if(implementation!=null){
                                codeBodies++;
                                for(Instruction i:implementation.getInstructions()){
                                    if(++instructions>30000000)throw new IllegalArgumentException("Instruction bound");
                                    ins.add(SecurityDexReader.instruction(i,pc));pc+=i.getCodeUnits();
                                }
                                for(var t:implementation.getTryBlocks())for(var h:t.getExceptionHandlers())
                                    catches.add("{\"startPc\":"+t.getStartCodeAddress()+",\"codeUnits\":"+t.getCodeUnitCount()+",\"exceptionType\":"+SecurityDexReader.q(h.getExceptionType())+",\"handlerPc\":"+h.getHandlerCodeAddress()+"}");
                            }
                            String body="{\"owner\":"+SecurityDexReader.q(c.getType())+",\"signature\":"+SecurityDexReader.q(sig)+",\"accessFlags\":"+m.getAccessFlags()+",\"registerCount\":"+(implementation==null?0:implementation.getRegisterCount())+",\"hasCode\":"+(implementation!=null)+",\"instructions\":["+String.join(",",ins)+"],\"catches\":["+String.join(",",catches)+"]}";
                            out.println("{\"record\":\"method\",\"owner\":"+SecurityDexReader.q(c.getType())+",\"signature\":"+SecurityDexReader.q(sig)+",\"sha256\":"+SecurityDexReader.q(SecurityDexReader.sha(body.getBytes(StandardCharsets.UTF_8)))+"}");
                        }
                    }
                }
                out.flush();
            }
            out.println("{\"record\":\"summary\",\"classes\":"+classes+",\"methods\":"+methods+",\"codeBodies\":"+codeBodies+",\"instructions\":"+instructions+"}");
            if(out.checkError())throw new IOException("Proof output failed");
        }
    }
}
