package model;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

/** Actual module boot issuer and host/client/app bytes, authored F/C graph only. */
public final class HostHandoffAssertions {
    private static int checks;
    private static final byte[] SIGNER="authored-current-signer".getBytes(StandardCharsets.US_ASCII);
    private static void yes(boolean value,String why){checks++;if(!value)throw new AssertionError(why);}
    private static Object call(Object target,String name,Object...args)throws Throwable {
        Class<?> type=target instanceof Class?(Class<?>)target:target.getClass();Method found=null;
        for(Method m:type.getMethods())if(m.getName().equals(name)&&m.getParameterCount()==args.length){if(found!=null)throw new AssertionError("ambiguous public method");found=m;}
        if(found==null)throw new AssertionError("missing public method "+name);
        try{return found.invoke(target instanceof Class?null:target,args);}catch(InvocationTargetException problem){throw problem.getCause();}
    }
    private static Object get(Class<?> type,String field)throws Exception{
        if(!type.getName().startsWith("model."))throw new AssertionError("authored controls only");return type.getField(field).get(null);
    }
    private static void set(Class<?> type,String field,Object value)throws Exception{
        if(!type.getName().startsWith("model."))throw new AssertionError("authored controls only");type.getField(field).set(null,value);
    }
    private static String hash(byte[] data)throws Exception{StringBuilder b=new StringBuilder();for(byte v:MessageDigest.getInstance("SHA-256").digest(data))b.append(String.format("%02x",v&255));return b.toString();}
    private static Throwable merge(Throwable first,Throwable next){if(first==null)return next;if(first!=next)first.addSuppressed(next);return first;}
    private static final class World implements AutoCloseable {
        final ClassLoader prior=Thread.currentThread().getContextClassLoader();URLClassLoader f,c,m;Path data;
        Class<?> link,wire,peer,offer,os,vector;Object module,manager,timing;Method original;
        World(String[] args,int id,String mode)throws Throwable{
            try{
                Path repo=Paths.get(args[6]).toRealPath(),base=Paths.get(args[5]).toRealPath();
                yes(Files.isRegularFile(repo.resolve("tools/test_retained_root_handoff.py"))&&base.startsWith(repo.resolve("out")),"own repository case root");
                data=Files.createDirectory(base.resolve("host-"+id)).toRealPath();yes(data.startsWith(base),"canonical contained case");
                f=new URLClassLoader(new URL[]{Paths.get(args[2]).toUri().toURL(),Paths.get(args[1]).toUri().toURL()},ClassLoader.getPlatformClassLoader());
                c=new URLClassLoader(new URL[]{Paths.get(args[3]).toUri().toURL()},f);
                m=new URLClassLoader(new URL[]{Paths.get(args[0]).toUri().toURL()},f);
                Thread.currentThread().setContextClassLoader(c);call(Class.forName("com.android.internal.os.ZygoteInit",true,f),"modelSet",c);
                link=Class.forName("model.LinkModel",true,f);wire=Class.forName("model.LinkWireFixture",true,f);peer=Class.forName("model.NativePeerFixture",true,f);offer=Class.forName("model.OfferModel",true,f);os=Class.forName("android.system.Os",true,f);vector=Class.forName("model.VectorWorld",true,f);
                call(wire,"configure",repo.toString(),data.toString(),mode);call(offer,"allowOffer");
                Files.createDirectory(data.resolve("system"));Path apk=data.resolve("installed.apk");Files.write(apk,"authored-installed-app".getBytes(StandardCharsets.US_ASCII));call(wire,"packageInfo",apk.toString(),SIGNER);
                Class<?> world=Class.forName("com.android.server.BootstrapWorld",true,c);call(world,"init");manager=call(world,"manager");
                Class<?> tt=Class.forName("com.android.server.utils.TimingsTraceAndSlog",true,c);timing=tt.getConstructor().newInstance();original=manager.getClass().getMethod("startBootPhase",tt,int.class);
                module=Class.forName("com.appleexploit.oneos.security.authority.RetainedPinHostModule",true,m).getConstructor().newInstance();
                call(module,"onModuleLoaded",Class.forName("model.VectorWorld$Loaded",true,f).getConstructor().newInstance());
                if(id!=0){Path permit=data.resolve("system/oneos-samsung-pin-host-bootstrap/request-v1");Files.createDirectories(permit.getParent());Files.write(permit,"CAPTURE_PIN_HOST_BOOTSTRAP_V1\n".getBytes(StandardCharsets.US_ASCII));}
                if(id!=1&&id!=0){
                    String profile="version=2\npackage=com.fahadali.oneos\nsigner="+hash(SIGNER)+"\napk="+hash(Files.readAllBytes(apk))+"\ncode=7\nnative="+String.join("",Collections.nCopies(64,"a"))+"\nbytes=128\n";
                    Files.write(data.resolve("system/oneos_retained_root_link_v2"),profile.getBytes(StandardCharsets.US_ASCII));
                }
            }catch(Throwable failure){throw finish(failure);}
        }
        void boot()throws Throwable{
            Object starting=Class.forName("model.VectorWorld$Starting",true,f).getConstructor(ClassLoader.class).newInstance(c);call(module,"onSystemServerStarting",starting);
            Object chain=Class.forName("model.VectorWorld$Chain",true,f).getConstructor(Method.class,Object.class,Object.class,int.class).newInstance(original,manager,timing,1000);
            call(vector,"dispatch",chain);yes(chain.getClass().getField("proceeded").getInt(chain)==1,"actual original boot once");
        }
        int n(Class<?> type,String field)throws Exception{return((Number)get(type,field)).intValue();}
        void pumpUntil(String field,int expected)throws Throwable{
            long until=System.nanoTime()+4_000_000_000L;
            while(System.nanoTime()<until){call(link,"drain");if(n(peer,field)>=expected){call(link,"drain");return;}Thread.sleep(2);}
            throw new AssertionError("authored source path did not reach "+field);
        }
        void settleNoControl()throws Throwable{call(link,"awaitPackageWorkers");call(link,"drain");call(link,"awaitObservedWorkers");call(link,"drain");}
        Throwable finish(Throwable primary){
            if(wire!=null)try{call(wire,"destroyed");}catch(Throwable e){primary=merge(primary,e);}
            if(link!=null)try{call(link,"packageBroadcast");call(link,"drain");}catch(Throwable e){primary=merge(primary,e);}
            if(peer!=null)try{call(peer,"cleanup");}catch(Throwable e){primary=merge(primary,e);}
            if(offer!=null)try{call(offer,"cleanup");}catch(Throwable e){primary=merge(primary,e);}
            if(link!=null)try{call(link,"cleanup");}catch(Throwable e){primary=merge(primary,e);}
            if(os!=null){try{yes((Integer)call(os,"activeDescriptors")==0,"profile/APK FDs consumed before forced cleanup");}catch(Throwable e){primary=merge(primary,e);}try{call(os,"fixtureCleanup");}catch(Throwable e){primary=merge(primary,e);}}
            if(link!=null)try{yes(n(link,"parcelObtains")==n(link,"parcelRecycles")&&n(link,"borrowedRecycles")==0,"owned Parcel cleanup");}catch(Throwable e){primary=merge(primary,e);}
            try{Thread.currentThread().setContextClassLoader(prior);}catch(Throwable e){primary=merge(primary,e);}
            for(URLClassLoader loader:new URLClassLoader[]{m,c,f})if(loader!=null)try{loader.close();}catch(Throwable e){primary=merge(primary,e);}
            if(data!=null)try{List<Path> paths=new ArrayList<Path>();try(java.util.stream.Stream<Path> walk=Files.walk(data)){walk.forEach(paths::add);}paths.sort(Collections.reverseOrder());for(Path p:paths){if(!p.toAbsolutePath().normalize().startsWith(data))throw new IOException("cleanup escape");Files.delete(p);}}catch(Throwable e){primary=merge(primary,e);}
            return primary;
        }
        public void close()throws Exception{Throwable failure=finish(null);if(failure instanceof Error)throw(Error)failure;if(failure instanceof Exception)throw(Exception)failure;if(failure!=null)throw new AssertionError(failure);}
    }
    public static int run(String[] args)throws Throwable{
        String[] modes={"normal","normal","normal","wrong_peer_pid","wrong_peer_uid","no_rights","extra_rights","wrong_fd_kind","wrong_fd_target","dup_uncertain","lost_commit","normal","close_uncertain","partial_identity","unexpected_poll","ack_without_exit"};
        for(int id=0;id<modes.length;id++){
            World w=new World(args,id,modes[id]);Throwable primary=null;
            try{
                w.boot();
                if(id<2){w.settleNoControl();yes(w.n(w.link,"binds")==0&&w.n(w.peer,"connects")==0,"default permit/profile absence never opens native control");}
                else if(id==2||id==11||id==12||id==15){
                    w.pumpUntil("commits",1);yes(w.n(w.peer,"connects")==1&&w.n(w.peer,"commits")==1,"genuine module/callback/source continuation commits once");
                    if(id==11){call(w.wire,"destroyed");call(get(w.link,"broker"),"modelDie");call(w.wire,"reconnect");call(w.link,"drain");yes(w.n(w.link,"brokerCalls")==1&&w.n(w.peer,"closes")==0,"app death/reconnect cannot issue another BEGIN or revoke direct host");}
                    call(w.link,"packageBroadcast");w.pumpUntil("closes",1);yes(w.n(w.peer,"commits")==1&&w.n(w.peer,"closes")==1,"real package retirement cuts sole direct host socket once");
                    if(id==15){
                        w.pumpUntil("socketCloses",1);
                        yes(!(Boolean)get(w.peer,"exited")&&w.n(w.peer,"dupCloses")==0&&(Integer)call(w.peer,"live")>0,"CLOSED ACK and socket cleanup cannot release live pidfd custody");
                        // Only harness teardown now supplies synthetic exit. This
                        // assertion is earned beforehand, not a source drain PASS.
                    }else{
                        w.pumpUntil("dupCloses",1);
                        yes((Integer)call(w.peer,"live")== (id==12?1:0),"consumed close uncertainty retains exact modeled descriptor");
                    }
                }else{
                    w.pumpUntil("socketCloses",1);if(id!=14)yes(w.n(w.peer,"commits")== (id==10?1:0),"invalid peer/rights never commit; lost commit never retries");
                    yes(w.n(w.peer,"closes")==0,"no precommit or ambiguous-commit CLOSE protocol fallback");
                    if(id==6){w.pumpUntil("rawCloses",2);yes(w.n(w.peer,"rawCloses")==2,"all extra rights adopted and independently consumed");}
                    if(id==13){w.pumpUntil("rawCloses",1);yes(w.n(w.peer,"rawCloses")==1,"right accompanying incomplete identity is adopted before EOF refusal");}
                    if(id==14)yes(w.n(w.peer,"dupCloses")==0&&(Integer)call(w.peer,"live")>0,"unusable exit event retains unproved process/descriptor owner");
                }
                yes((Integer)call(w.peer,"writerCount")<=1,"all actual host frames have one retained writer; app has none");
            }catch(Throwable failure){primary=failure;}
            finally{primary=w.finish(primary);}
            if(primary!=null)throw primary;
            System.out.println("HOST_MODEL_CASE "+id);
        }
        return checks;
    }
}
