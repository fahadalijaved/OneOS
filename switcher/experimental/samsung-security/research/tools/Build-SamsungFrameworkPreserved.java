import java.nio.file.*;
import java.util.*;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;

/** Authored offline coordinator. Frozen helpers are called, never their old publisher mains. */
final class BuildSamsungFrameworkPreserved {
    static final String SOURCE="256cc1744c36a88d3ee4c9218d2cf0156816ce89a63cd98787dd1633edbdf1a7";
    static byte[] read(Path p)throws Exception {
        long n=Files.size(p);if(n<112||n>64*1024*1024)throw new IllegalArgumentException("DEX extent");
        byte[] b=Files.readAllBytes(p);ProbeSamsungDex041.validate(b);return b;
    }
    static Collection<? extends ClassDef> classes(byte[] b){return new DexBackedDexFile(Opcodes.forApi(29),b).getClasses();}
    static String q(String s){return SecurityDexReader.q(s);}
    static String hash(byte[] b)throws Exception{return SecurityDexReader.sha(b);}
    static void policy(byte[] original,byte[] other)throws Exception {
        var s=new ProbeSamsungFrameworkDex.RawPolicy(original);var d=new ProbeSamsungFrameworkDex.RawPolicy(other);
        if(!s.classes.equals(d.classes)||!s.members.equals(d.members)||!s.flags.equals(d.flags)||!s.presence.equals(d.presence)||s.members.size()!=99179||
           !Arrays.equals(Arrays.copyOfRange(original,s.section,s.section+s.size),Arrays.copyOfRange(other,d.section,d.section+d.size)))
            throw new IllegalArgumentException("Complete raw policy/order/presence drift");
    }
    static void shape(byte[] b,boolean edited)throws Exception {
        var c=classes(b);if(c.size()!=7881)throw new IllegalArgumentException("Class insertion/loss");
        for(var x:c)if(x.getType().equals("Lcom/appleexploit/oneos/security/boot/PermissionQueryBinding;"))throw new IllegalArgumentException("Helper definition inserted");
        BuildPermissionQueryPayload.shape(BuildPermissionQueryPayload.target(c),edited?BuildPermissionQueryPayload.NEW:BuildPermissionQueryPayload.OLD);
        BuildPermissionQueryPayload.glShape(BuildPermissionQueryPayload.find(c,BuildPermissionQueryPayload.GL_OWNER,BuildPermissionQueryPayload.GL_SIG),edited);
        var raw=new ProbeSamsungFrameworkDex.RawPolicy(b);
        BuildPermissionQueryPayload.codeHeader(raw);BuildPermissionQueryPayload.glHeader(raw,edited);
    }
    static void save(Path raw,String name,Map<String,String> rows)throws Exception {
        if(rows.size()!=107060)throw new IllegalArgumentException("Complete normalized row count");
        ProbeSamsungDex041.saveRows(raw.resolve(name+"-normalized.jsonl"),rows);
    }
    public static void main(String[] a)throws Exception {
        if(a.length<3)throw new IllegalArgumentException("mode original-dex arguments");
        byte[] original=read(Path.of(a[1]));if(original.length!=8830032||!hash(original).equals(SOURCE))throw new IllegalArgumentException("Literal original source");
        if(a[0].equals("emit")) {
            if(a.length!=7)throw new IllegalArgumentException("emit source input-dex output-dir label direction output-name");
            byte[] input=read(Path.of(a[2]));Path dir=Path.of(a[3]);if(!Files.isDirectory(dir))throw new IllegalArgumentException("Exclusive output dir required");
            Collection<? extends ClassDef> c=classes(input);
            if(a[5].equals("forward")){shape(input,false);c=BuildPermissionQueryPayload.overlay(c,BuildPermissionQueryPayload.OLD,BuildPermissionQueryPayload.NEW);}
            else if(a[5].equals("inverse")){shape(input,true);c=BuildPermissionQueryPayload.overlay(c,BuildPermissionQueryPayload.NEW,BuildPermissionQueryPayload.OLD);}
            else if(!a[5].equals("none"))throw new IllegalArgumentException("Unknown direction");
            byte[] emitted=ProbeSamsungFrameworkDex.emitAndRestore(c,new ProbeSamsungFrameworkDex.RawPolicy(original),dir,a[4]);
            Files.write(dir.resolve(a[6]),emitted,StandardOpenOption.CREATE_NEW);
            System.out.println("{\"status\":\"EMITTED_POLICY_RESTORED_HEADERS_PENDING\",\"sha256\":"+q(hash(emitted))+",\"policyRepair\":"+ProbeSamsungFrameworkDex.lastRepair+"}");return;
        }
        if(!a[0].equals("verify")||a.length!=8)throw new IllegalArgumentException("verify source canonical canonical-rt edited edited-rt inverse raw-dir");
        Path raw=Path.of(a[7]);if(!Files.isDirectory(raw))throw new IllegalArgumentException("Exclusive raw dir required");
        byte[] canonical=read(Path.of(a[2])),canonicalRt=read(Path.of(a[3])),edited=read(Path.of(a[4])),editedRt=read(Path.of(a[5])),inverse=read(Path.of(a[6]));
        if(!Arrays.equals(canonical,canonicalRt)||!Arrays.equals(edited,editedRt)||!Arrays.equals(canonical,inverse))throw new IllegalArgumentException("Actual repaired roundtrip/inverse bytes differ");
        Map<String,String> before=ProbeSamsungDex041.normalize(classes(original));String stats=ProbeSamsungFrameworkDex.stats();save(raw,"source",before);
        Map<String,String> expected=new TreeMap<>(before);String pm=before.get(BuildPermissionQueryPayload.KEY);
        if(BuildPermissionQueryPayload.occurrences(pm,BuildPermissionQueryPayload.OLD)!=2)throw new IllegalArgumentException("PM exact one reference/two renderings");
        expected.put(BuildPermissionQueryPayload.KEY,pm.replace(BuildPermissionQueryPayload.OLD,BuildPermissionQueryPayload.NEW));
        var overlay=BuildPermissionQueryPayload.overlay(classes(original),BuildPermissionQueryPayload.OLD,BuildPermissionQueryPayload.NEW);
        ClassDef gl=overlay.stream().filter(c->c.getType().equals(BuildPermissionQueryPayload.GL_OWNER)).findFirst().orElseThrow();
        var glRows=ProbeSamsungDex041.normalize(List.of(gl));
        for(var e:glRows.entrySet())if(!e.getKey().equals(BuildPermissionQueryPayload.GL_KEY)&&!e.getValue().equals(before.get(e.getKey())))throw new IllegalArgumentException("GL sibling metadata drift");
        expected.put(BuildPermissionQueryPayload.GL_KEY,glRows.get(BuildPermissionQueryPayload.GL_KEY));
        List<String> delta=new ArrayList<>();for(var k:before.keySet())if(!before.get(k).equals(expected.get(k)))delta.add(k);
        if(!new HashSet<>(delta).equals(Set.of(BuildPermissionQueryPayload.KEY,BuildPermissionQueryPayload.GL_KEY)))throw new IllegalArgumentException("Only approved two method rows");save(raw,"expected-edited",expected);
        byte[][] all={canonical,canonicalRt,edited,editedRt,inverse};String[] labels={"canonical","canonical-roundtrip","edited","edited-roundtrip","inverse"};
        List<String> summaries=new ArrayList<>();
        for(int n=0;n<all.length;n++){
            boolean edit=n==2||n==3;policy(original,all[n]);shape(all[n],edit);
            Map<String,String> rows=ProbeSamsungDex041.normalize(classes(all[n]));ProbeSamsungDex041.same(edit?expected:before,rows);
            if(!stats.equals(ProbeSamsungFrameworkDex.stats()))throw new IllegalArgumentException("Category counts drift");save(raw,labels[n],rows);
            summaries.add("{\"label\":"+q(labels[n])+",\"sha256\":"+q(hash(all[n]))+",\"normalizedRecords\":"+rows.size()+",\"normalizedDigest\":"+q(ProbeSamsungFrameworkDex.recordDigest(rows))+",\"rawPolicy\":"+new ProbeSamsungFrameworkDex.RawPolicy(all[n]).summary()+"}");
        }
        System.out.println("{\"status\":\"PASS_CORRECTED_FULL_SELECTED_FRAMEWORK\",\"sourceSha256\":"+q(SOURCE)+",\"normalizedRecords\":107060,\"changedMethodRows\":2,\"categoryCounts\":"+stats+",\"actualCanonicalRoundtripByteEqual\":true,\"actualEditedRoundtripByteEqual\":true,\"symbolicBothEditsInverseEqualsNewCanonical\":true,\"allRawPolicyOrderAbsenceExact\":true,\"outputs\":["+String.join(",",summaries)+"],\"oemExecuted\":false}");
    }
}
