package model;
import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;

/** Actual module boot issuer and host/client/app bytes, authored F/C graph only. */
public final class RetainedRootViewTest {
    private static int checks;
    private static Throwable finishFailureForDiscriminator;
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
        Class<?> link,wire,peer,offer,os,vector,actions,view;Object module,manager,timing;Method original;
        World(String[] args,int id,String mode)throws Throwable{
            try{
                Path repo=Paths.get(args[6]).toRealPath(),base=Paths.get(args[5]).toRealPath();
                yes(Files.isRegularFile(repo.resolve("tools/test_retained_root_handoff.py"))&&base.startsWith(repo.resolve("out")),"own repository case root");
                data=Files.createDirectory(base.resolve("host-"+id)).toRealPath();yes(data.startsWith(base),"canonical contained case");
                f=new URLClassLoader(new URL[]{Paths.get(args[4]).toUri().toURL(),Paths.get(args[2]).toUri().toURL(),Paths.get(args[1]).toUri().toURL()},ClassLoader.getPlatformClassLoader());
                c=new URLClassLoader(new URL[]{Paths.get(args[3]).toUri().toURL()},f);
                m=new URLClassLoader(new URL[]{Paths.get(args[7]).toUri().toURL(),Paths.get(args[0]).toUri().toURL()},f);
                Thread.currentThread().setContextClassLoader(c);call(Class.forName("com.android.internal.os.ZygoteInit",true,f),"modelSet",c);
                link=Class.forName("model.LinkModel",true,f);wire=Class.forName("model.LinkWireFixture",true,f);peer=Class.forName("model.NativePeerFixture",true,f);offer=Class.forName("model.OfferModel",true,f);os=Class.forName("android.system.Os",true,f);vector=Class.forName("model.VectorWorld",true,f);
                call(wire,"configure",repo.toString(),data.toString(),mode);call(offer,"allowOffer");
                Files.createDirectory(data.resolve("system"));Path apk=data.resolve("installed.apk");Files.write(apk,"authored-installed-app".getBytes(StandardCharsets.US_ASCII));call(wire,"packageInfo",apk.toString(),SIGNER);
                Class<?> world=Class.forName("com.android.server.BootstrapWorld",true,c);call(world,"init");manager=call(world,"manager");
                Class<?> tt=Class.forName("com.android.server.utils.TimingsTraceAndSlog",true,c);timing=tt.getConstructor().newInstance();original=manager.getClass().getMethod("startBootPhase",tt,int.class);
                module=Class.forName("com.appleexploit.oneos.security.authority.RetainedPinHostModule",true,m).getConstructor().newInstance();
                actions=Class.forName("com.appleexploit.oneos.security.authority.ViewActions",true,m);view=Class.forName("model.ViewPeerFixture",true,f);
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
        void ready()throws Throwable{
            yes(!(Boolean)call(actions,"available",module),"genuine pending status is false without poisoning or claiming preparation");
            long until=System.nanoTime()+4_000_000_000L;
            while(System.nanoTime()<until){
                call(link,"drain");
                if((Boolean)call(actions,"available",module)){
                    yes(n(view,"prepares")==0,"genuine availability observation sends no preparation");return;
                }
                Thread.sleep(2);
            }
            // Diagnostic message only: public authored fixture observations,
            // never production private state or a substituted source decision.
            try {
                Map<String,Object> trace=new LinkedHashMap<String,Object>();
                for(String key:new String[]{"installs","unhooks","logs","codes"})trace.put("vector."+key,get(vector,key));
                Class<?> probe=Class.forName("model.BootstrapProbe",true,f);
                for(String key:new String[]{"uid","apiVersion","statUid","fileOperations","originals"})trace.put("probe."+key,get(probe,key));
                for(String key:new String[]{"packageReads","binds","posts","brokerCalls","callbackCalls","callbackCompleted","capturedCalls","failedCalls","registrations","unregistrations"})trace.put("link."+key,get(link,key));
                trace.put("link.queued",call(link,"queued"));trace.put("offer.spawns",get(offer,"spawns"));
                for(String key:new String[]{"connects","commits","socketCloses","rawCloses","dupCloses","procCloses","exited","commitReplyConsumed","writes"})trace.put("peer."+key,get(peer,key));
                trace.put("view.prepares",get(view,"prepares"));
                String message=trace.toString();System.err.println("VIEW_STARTUP_DIAGNOSTIC "+message.substring(0,Math.min(message.length(),4096)));
            } catch(Throwable diagnosticFailure) {System.err.println("VIEW_STARTUP_DIAGNOSTIC_UNAVAILABLE "+diagnosticFailure.getClass().getName());}
            throw new AssertionError("actual source-owned private-view availability did not become true");
        }
        void action(String name)throws Throwable{call(actions,name,module);}
        long[] snapshot()throws Throwable{return(long[])call(actions,"snapshot",module);}
        long[] untilState(int expected)throws Throwable{
            long until=System.nanoTime()+4_000_000_000L;
            while(System.nanoTime()<until){call(link,"drain");long[] s=snapshot();if(s!=null&&s[0]==expected)return s;Thread.sleep(2);}
            throw new AssertionError("view metadata state not reached "+expected);
        }
        void viewCounter(String name,int expected)throws Throwable{
            long until=System.nanoTime()+4_000_000_000L;
            while(System.nanoTime()<until){call(link,"drain");if(n(view,name)>=expected)return;Thread.sleep(2);}
            throw new AssertionError("view peer event not reached "+name);
        }
        void settleNoControl()throws Throwable{call(link,"awaitPackageWorkers");call(link,"drain");call(link,"awaitObservedWorkers");call(link,"drain");}
        Throwable finish(Throwable primary){
            if(view!=null)try{call(view,"releasePrepare");}catch(Throwable e){primary=merge(primary,e);}
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
            if(finishFailureForDiscriminator!=null)primary=merge(primary,finishFailureForDiscriminator);
            return primary;
        }
        public void close()throws Exception{Throwable failure=finish(null);if(failure instanceof Error)throw(Error)failure;if(failure instanceof Exception)throw(Exception)failure;if(failure!=null)throw new AssertionError(failure);}
    }
    private static void description(long[] value){
        yes(value!=null&&value[1]==1,"actual wire marks a descriptive observation");
        yes(value[2]==0xfedcba9876543210L&&value[3]==0x8000000000000001L&&value[4]==-1L,"all unsigned observation bits preserved without positivity/truncation");
    }
    /** Only the explicitly scripted negative actions use this path. Wire/custody
     * assertions below still have to prove the selected failure was exercised. */
    private static void negativeAction(World w,String name)throws Throwable{
        try{w.action(name);}catch(IllegalStateException refused){
            if(refused.getClass()!=IllegalStateException.class)throw refused;
        }
    }
    private static int wireInt(byte[] frame,int offset){return ByteBuffer.wrap(frame).getInt(offset);}
    private static byte[][] consumed(World w)throws Throwable{return(byte[][])call(w.peer,"readViewFrames");}
    /** A post-external failure may poison the Module before either the issuing
     * call or this later observation returns. Refusal is distinct from null. */
    private static void negativeObservation(World w,int expectedState,boolean described)throws Throwable{
        try{
            long[] value=w.snapshot();
            if(expectedState<0)yes(value==null,"fault produced no successful fabricated view observation");
            else{
                yes(value!=null&&value[0]==expectedState,"last legitimate metadata survives without invented terminal state");
                if(described)description(value);
            }
        }catch(IllegalStateException refused){
            if(refused.getClass()!=IllegalStateException.class)throw refused;
            yes(!(Boolean)call(w.actions,"available",w.module),"genuine guarded observation refusal leaves availability false");
        }
    }
    private static void run(int id,String[] args)throws Throwable{
        String[] modes={"view_success","view_success","view_stage","view_refused","view_lost_prepare","view_lost_close","view_lost_terminal","view_block","view_unobserved_values","view_bad_observed","view_reserved","view_changed","view_regression","view_success"};
        World w=new World(args,100+id,modes[id]);Throwable primary=null;
        try{
            w.boot();w.ready();yes(w.n(w.peer,"commits")==1,"genuine original module/captured source commits first");
            if(id==13){yes(w.n(w.view,"prepares")==0&&w.snapshot()==null,"no automatic private preparation after COMMIT");return;}
            if(id==2||id==3||id==4||id>=8&&id<=10)negativeAction(w,"prepare");
            else w.action("prepare");
            if(id==7){
                w.viewCounter("prepares",1);call(w.link,"packageBroadcast");call(w.link,"drain");call(w.view,"releasePrepare");
                w.untilState(5);yes(w.n(w.view,"prepares")==1&&w.n(w.peer,"closes")==1,"source retirement during actual request cannot publish another credit or skip native drain");return;
            }
            if(id==4||id>=8&&id<=10){
                w.pumpUntil("socketCloses",1);byte[][] frames=consumed(w);
                yes(w.n(w.view,"prepares")==1,"negative preparation actually reached the same worker exactly once");
                if(id==4)yes(w.n(w.peer,"lostViewReplies")==1&&frames.length==0,"lost prepare reply actually delivered EOF without a view frame");
                else{
                    yes(w.n(w.peer,"lostViewReplies")==0&&frames.length==1,"selected malformed frame was actually consumed");
                    if(id==8)yes(wireInt(frames[0],20)==0&&ByteBuffer.wrap(frames[0]).getLong(24)!=0,"unobserved nonzero values were exercised");
                    if(id==9)yes(wireInt(frames[0],20)==2,"invalid observed flag was exercised");
                    if(id==10)yes(frames[0][63]!=0,"nonzero reserved tail was exercised");
                }
                negativeObservation(w,-1,false);
                yes(!(Boolean)call(w.actions,"available",w.module),"failed preparation cannot become an available new credit");
                yes(!(Boolean)get(w.peer,"exited")&&(Integer)call(w.peer,"live")>0,"possible GVI effects retain live modeled process/descriptor custody");
                Throwable duplicate=null;try{w.action("prepare");}catch(Throwable failure){duplicate=failure;}
                yes(duplicate!=null&&w.n(w.view,"prepares")==1,"unknown attempt cannot rearm/prepare again");return;
            }
            if(id==2||id==3){
                w.pumpUntil("socketCloses",1);byte[][] frames=consumed(w);
                yes(frames.length==2&&wireInt(frames[0],16)==id&&wireInt(frames[1],16)==6,"actual stage/refusal response was followed by local-terminal6");
                boolean zero=true;for(byte[] frame:frames)for(int n=20;n<64;n++)zero&=frame[n]==0;
                yes(zero,"no-config/refused wire observations carry no fabricated values");
                negativeObservation(w,6,false);
                yes(w.n(w.view,"prepares")==1&&w.n(w.peer,"closes")==0&&w.n(w.view,"queries")>=1,"stage/refusal automatically uses QUERY-only drain, not another CLOSE/prepare");return;
            }
            description(w.untilState(1));
            if(id==0){
                w.action("query");w.viewCounter("queries",1);description(w.untilState(1));
                yes(w.n(w.view,"prepares")==1,"QUERY reads cached descriptive wire values without a second provider preparation");
                Throwable duplicate=null;try{w.action("prepare");}catch(Throwable failure){duplicate=failure;}
                yes(duplicate!=null&&w.n(w.view,"prepares")==1,"one actual source-issued preparation total");return;
            }
            if(id==11){
                negativeAction(w,"query");w.pumpUntil("socketCloses",1);byte[][] frames=consumed(w);
                yes(frames.length==2&&wireInt(frames[0],16)==1&&wireInt(frames[1],16)==1
                        &&ByteBuffer.wrap(frames[1]).getLong(24)==ByteBuffer.wrap(frames[0]).getLong(24)+1,"changed namespace observation actually reached the original reader");
                negativeObservation(w,1,true);
                yes(w.n(w.view,"prepares")==1&&(Integer)call(w.peer,"live")>0,"changed cached observations refuse and preserve prior tombstone/uncertainty");return;
            }
            if(id==5||id==6||id==12)negativeAction(w,"close");else w.action("close");
            if(id==5){
                w.pumpUntil("socketCloses",1);byte[][] frames=consumed(w);
                yes(w.n(w.peer,"closes")==1&&w.n(w.peer,"lostViewReplies")==1&&frames.length==1&&wireInt(frames[0],16)==1,"actual CLOSE lost its reply without any HOLD/terminal frame");
                negativeObservation(w,1,true);
                yes(!(Boolean)get(w.peer,"exited")&&(Integer)call(w.peer,"live")>0,"close/EOF is not process exit or cleanup receipt");return;
            }
            if(id==6||id==12){
                w.pumpUntil("socketCloses",1);byte[][] frames=consumed(w);
                yes(frames.length==(id==6?2:3)&&wireInt(frames[0],16)==1&&wireInt(frames[1],16)==4,"actual close consumed HOLD after the original partial observation");
                if(id==6)yes(w.n(w.peer,"lostViewReplies")==1&&(Boolean)get(w.peer,"exited"),"terminal reply was lost despite modeled process exit");
                else yes(w.n(w.peer,"lostViewReplies")==0&&wireInt(frames[2],16)==1&&(Integer)call(w.peer,"live")>0,"actual regressed reply was consumed while custody remains live");
                negativeObservation(w,4,true);
                yes(w.n(w.peer,"closes")==1&&w.n(w.view,"queries")>=1,"same worker QUERY-drains without a second CLOSE");return;
            }
            long[] finalState=w.untilState(5);description(finalState);
            yes(w.n(w.peer,"closes")==1&&w.n(w.view,"terminalQueries")==1,"partial->HOLD->same-sequence terminal QUERY5 preserves kernel-unconfirmed state");
            yes(finalState[0]!=6,"kernel-unconfirmed is not refused-local-closed or full return");
        }catch(Throwable failure){primary=failure;}
        finally{primary=w.finish(primary);if(primary!=null)throw primary;}
        if(primary!=null)throw primary;
    }
    private static void assertFinishFailurePropagates(String[] args)throws Throwable {
        Throwable expected=new IOException("authored new-view finish discriminator");
        Throwable actual=null;
        finishFailureForDiscriminator=expected;
        try{run(13,args);}catch(Throwable failure){actual=failure;}
        finally{finishFailureForDiscriminator=null;}
        if(actual!=expected)throw new AssertionError("real view case return hid/replaced finish failure",actual);
    }
    public static void main(String[] args)throws Throwable{
        yes(args.length==8,"exact own model loader/control/output arguments");
        assertFinishFailurePropagates(args);System.out.println("VIEW_HARNESS_CLEANUP_DISCRIMINATOR");
        for(int id=0;id<14;id++){run(id,args);System.out.println("VIEW_MODEL_CASE "+id);}
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":14,\"checks\":"+checks+",\"nativeExecuted\":false,\"cleanupCompletePrivateFlagInspected\":false}");
    }
}
