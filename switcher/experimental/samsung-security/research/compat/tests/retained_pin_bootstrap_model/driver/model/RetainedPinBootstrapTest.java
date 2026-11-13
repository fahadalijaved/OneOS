package model;

import java.io.File;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/** Public first-party module APIs and authored fixtures only. No private SDK inspection. */
public final class RetainedPinBootstrapTest {
    private static final String MODULE="com.appleexploit.oneos.security.authority.RetainedPinHostModule";
    private static final String[] CASES={"default_off","old_capture_permit_not_opt_in","bad_marker_and_data_root",
        "normal_boot_closed","duplicate_fast_return","original_runtime","original_error","original_checked_observer_fault",
        "observer_fault_still_forwards","nested_entry","overlapping_entry","family_capture_fault","binding_capture_fault",
        "owner_prepare_fault","logger_failure","post_report_reentry","permit_revoked","hook_ack_failure","permit_close_failure",
        "headless_profile","wrong_system_type","departing_user","different_ssm_receiver","argument_drift"};
    private static int checks;
    private static void yes(boolean value,String detail){checks++;if(!value)throw new AssertionError(detail);}
    private static Object call(Object receiver,String name,Object...args)throws Throwable{
        Class<?> type=receiver instanceof Class?(Class<?>)receiver:receiver.getClass();Method found=null;
        for(Method method:type.getMethods())if(method.getName().equals(name)&&method.getParameterCount()==args.length){if(found!=null)throw new AssertionError("ambiguous public fixture method "+name);found=method;}
        if(found==null)throw new AssertionError("missing public method "+name);
        try{return found.invoke(receiver instanceof Class?null:receiver,args);}catch(InvocationTargetException failure){throw failure.getCause();}
    }
    private static Object field(Class<?> type,String name)throws Exception{
        if(!type.getName().startsWith("model."))throw new AssertionError("only authored public control fields");return type.getField(name).get(null);
    }
    private static void field(Class<?> type,String name,Object value)throws Exception{
        if(!type.getName().startsWith("model."))throw new AssertionError("only authored public control fields");type.getField(name).set(null,value);
    }
    private static Throwable clean(Throwable primary,AutoCloseable resource){if(resource!=null)try{resource.close();}catch(Throwable failure){if(primary==null)primary=failure;else if(primary!=failure)primary.addSuppressed(failure);}return primary;}

    private static final class World implements AutoCloseable {
        final ClassLoader prior=Thread.currentThread().getContextClassLoader();
        final List<Job> jobs=new ArrayList<Job>();
        URLClassLoader framework,services,moduleLoader;
        Class<?> probe,vector,world,os;
        Object module,manager,timing;
        Method original;
        Path data;
        long baselineConstructions;
        World(String[] paths,int id)throws Throwable{
            try{
                Path repo=Paths.get(paths[5]).toRealPath(),base=Paths.get(paths[4]).toRealPath();
                yes(Files.isRegularFile(repo.resolve("tools/test_retained_pin_bootstrap.py")),"actual repository test entrypoint");
                yes(base.startsWith(repo.resolve("out")),"case data below actual repository out");
                data=Files.createDirectory(base.resolve(String.format("%02d",id))).toRealPath();
                yes(data.startsWith(base),"canonical private case data");
                framework=new URLClassLoader(new URL[]{new File(paths[2]).toURI().toURL()},ClassLoader.getPlatformClassLoader());
                services=new URLClassLoader(new URL[]{new File(paths[3]).toURI().toURL()},framework);
                moduleLoader=new URLClassLoader(new URL[]{new File(paths[0]).toURI().toURL(),new File(paths[1]).toURI().toURL()},framework);
                Thread.currentThread().setContextClassLoader(services);
                call(Class.forName("com.android.internal.os.ZygoteInit",true,framework),"modelSet",services);
                call(Class.forName("android.os.Looper",true,framework),"modelSet",Thread.currentThread());
                probe=Class.forName("model.BootstrapProbe",true,framework);vector=Class.forName("model.VectorWorld",true,framework);
                call(probe,"configureFixtureData",repo.toFile(),data.toFile());
                os=Class.forName("android.system.Os",true,framework);
                world=Class.forName("com.android.server.BootstrapWorld",true,services);call(world,"init");
                manager=call(world,"manager");Class<?> timingType=Class.forName("com.android.server.utils.TimingsTraceAndSlog",true,services);timing=timingType.getConstructor().newInstance();
                original=manager.getClass().getMethod("startBootPhase",timingType,int.class);
                Class<?> type=Class.forName(MODULE,true,moduleLoader);module=type.getConstructor().newInstance();
                yes(type.getClassLoader()==moduleLoader&&manager.getClass().getClassLoader()==services,"actual program M / authored services C");
                Object loaded=Class.forName("model.VectorWorld$Loaded",true,framework).getConstructor().newInstance();call(module,"onModuleLoaded",loaded);
                baselineConstructions=observations()[10];
            }catch(Throwable failure){throw cleanup(failure);}
        }
        void start()throws Throwable{Object event=Class.forName("model.VectorWorld$Starting",true,framework).getConstructor(ClassLoader.class).newInstance(services);call(module,"onSystemServerStarting",event);}
        Path request(){return data.resolve("system/oneos-samsung-pin-host-bootstrap/request-v1");}
        void permit(String kind)throws Exception{
            Path path=kind.equals("old")?data.resolve("system/oneos-samsung-security-capture/request-v2"):request();
            Files.createDirectories(path.getParent());
            String marker=kind.equals("good")?"CAPTURE_PIN_HOST_BOOTSTRAP_V1\n":"CAPTURE_SECURITY_FAMILY_V2\n";
            yes(path.toAbsolutePath().normalize().startsWith(data),"permit remains in own case directory");Files.write(path,marker.getBytes(StandardCharsets.US_ASCII));
        }
        Object chain(Object receiver,int phase)throws Throwable{return Class.forName("model.VectorWorld$Chain",true,framework).getConstructor(Method.class,Object.class,Object.class,int.class).newInstance(original,receiver,timing,phase);}
        Object chain(int phase)throws Throwable{return chain(manager,phase);}
        Object dispatch(Object chain)throws Throwable{return call(vector,"dispatch",chain);}
        void once(Object chain)throws Exception{yes(chain.getClass().getField("proceeded").getInt(chain)==1,"original proceed once per entry");}
        int originals()throws Exception{return((AtomicInteger)field(probe,"originals")).get();}
        int installs()throws Exception{return((Integer)field(vector,"installs")).intValue();}
        int lookups()throws Exception{return Class.forName("com.android.server.LocalServices",false,framework).getField("calls").getInt(null);}
        @SuppressWarnings("unchecked") List<String> codes()throws Exception{return new ArrayList<String>((List<String>)field(vector,"codes"));}
        boolean captured()throws Exception{return codes().contains("HOST_BOOTSTRAP_CAPTURED_CLOSED");}
        void armed()throws Throwable{permit("good");start();yes(installs()==1,"one acknowledged modeled hook");yes(String.valueOf(field(vector,"requestedMode")).equals("PASSTHROUGH"),"requested pass-through mode");}
        long[] observations()throws Throwable{return(long[])call(world,"observations");}
        void closedOnly()throws Throwable{
            long[] values=observations();yes(values[0]==0&&values[1]==0&&values[4]==0,"no verifier/PIN operation reached");
            yes(values[5]==0&&values[6]==0,"no Binder identity clear/restore");
            yes(values[10]==baselineConstructions&&values[11]==0,"no borrowed service construction or lazy getter");
            yes(((Integer)call(os,"activeDescriptors")).intValue()==0,"all authored permit descriptors closed");
            yes(((Integer)field(vector,"unhooks")).intValue()==0,"no unhook or rearm");
        }
        void fault(String stage)throws Exception{field(probe,"faultStage",stage);field(probe,"observerFailure",new AssertionError("authored observer fault"));}
        Job job(Object chain){Job job=new Job(this,chain);jobs.add(job);return job;}
        Throwable cleanup(Throwable failure){
            for(Job job:jobs)try{job.thread.join(1500);if(job.thread.isAlive())throw new AssertionError("model worker remains active");}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}
            if(os!=null)try{int count=((Integer)call(os,"activeDescriptors")).intValue();if(count!=0)throw new AssertionError("leaked modeled descriptor");}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}
            if(os!=null)try{call(os,"fixtureCleanup");}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}
            try{Thread.currentThread().setContextClassLoader(prior);}catch(Throwable error){if(failure==null)failure=error;else if(error!=failure)failure.addSuppressed(error);}
            failure=clean(failure,moduleLoader);failure=clean(failure,services);return clean(failure,framework);
        }
        @Override public void close()throws Exception{Throwable failure=cleanup(null);if(failure instanceof Error)throw(Error)failure;if(failure instanceof Exception)throw(Exception)failure;if(failure!=null)throw new AssertionError(failure);}
    }
    private static final class Job implements Runnable {
        final World world;final Object chain;final Thread thread;volatile Throwable failure;
        Job(World world,Object chain){this.world=world;this.chain=chain;thread=new Thread(this,"authored-noncandidate-entry");thread.setDaemon(true);}
        @Override public void run(){ClassLoader prior=Thread.currentThread().getContextClassLoader();try{Thread.currentThread().setContextClassLoader(world.services);world.dispatch(chain);}catch(Throwable error){failure=error;}finally{Thread.currentThread().setContextClassLoader(prior);}}
        void await()throws InterruptedException{thread.join(1200);yes(!thread.isAlive(),"foreign entry finishes while original active");}
    }
    private static void sourceFault(World w,Runnable action)throws Exception{field(w.probe,"originalWork",action);}
    private static void run(int id,String[] paths)throws Throwable{
        try(World w=new World(paths,id)){
            switch(id){
            case 0:case 1:case 2:{
                if(id==1)w.permit("old");if(id==2)w.permit("bad");w.start();yes(w.installs()==0,"default/old/invalid permit cannot hook");
                if(id==2){field(w.probe,"dataRoot",w.data.resolveSibling("uncreated-foreign-root").toFile());w.start();yes(w.installs()==0,"Environment drift cannot escape private data anchor");}
                Object chain=w.chain(1000);yes(w.dispatch(chain)==null,"void original result");w.once(chain);yes(w.originals()==1&&w.lookups()==0&&!w.captured(),"no capture in disabled path");break;
            }
            case 3:{w.armed();Object chain=w.chain(1000);yes(w.dispatch(chain)==null,"normal void return");w.once(chain);yes(w.originals()==1&&((Integer)call(w.world,"phase")).intValue()==1000,"real modeled phase completion");yes(w.captured()&&w.lookups()>0,"capture-only normal edge observed");break;}
            case 4:{w.armed();call(w.world,"phase",1000);Object chain=w.chain(1000);w.dispatch(chain);w.once(chain);yes(w.originals()==1&&!w.captured()&&w.lookups()==0,"normal fast return is not new completion");break;}
            case 5:case 6:case 7:{
                w.armed();Throwable original=id==5?new IllegalArgumentException("modeled original runtime"):id==6?new AssertionError("modeled original error"):new Exception("modeled original checked");
                field(w.probe,"originalFailure",original);Object chain=w.chain(1000);
                if(id==7){field(w.probe,"observerFailure",new AssertionError("observer before original"));chain.getClass().getField("metadataFault").setBoolean(chain,true);field(w.vector,"throwLogs",true);}
                try{w.dispatch(chain);throw new AssertionError("original failure lost");}catch(Throwable actual){yes(actual==original,"exact original Throwable identity");}
                w.once(chain);yes(w.originals()==1&&!w.captured(),"throw cannot publish completion");break;
            }
            case 8:{w.armed();field(w.probe,"observerFailure",new AssertionError("metadata fault"));Object chain=w.chain(1000);chain.getClass().getField("metadataFault").setBoolean(chain,true);w.dispatch(chain);w.once(chain);yes(w.originals()==1&&!w.captured(),"observer refusal still forwards normally");break;}
            case 9:{
                w.armed();final Object nested=w.chain(1000);sourceFault(w,()->{try{w.dispatch(nested);}catch(Throwable error){throw new AssertionError(error);}});
                Object outer=w.chain(1000);w.dispatch(outer);w.once(outer);w.once(nested);yes(w.originals()==2&&!w.captured(),"nested entry never issues new completion");break;
            }
            case 10:{
                w.armed();final Object competing=w.chain(900);sourceFault(w,()->{Job job=w.job(competing);job.thread.start();try{job.await();}catch(InterruptedException error){throw new AssertionError(error);}if(job.failure!=null)throw new AssertionError(job.failure);});
                Object outer=w.chain(1000);w.dispatch(outer);w.once(outer);w.once(competing);yes(w.originals()==2&&!w.captured(),"overlap invalidates record without blocking original");break;
            }
            case 11:case 12:case 13:{
                w.armed();w.fault(id==11?"PreparedRetainedSecurityFamilyCapture":id==12?"PreparedRetainedPinBinding":"PreparedRetainedPinOperationOwner");
                Object first=w.chain(1000);w.dispatch(first);w.once(first);yes(((Integer)field(w.probe,"faultFired")).intValue()==1&&!w.captured(),"construction-stage fault burns source attempt");
                // Explicit adversarial rollback of the AUTHORED SSM only. This
                // is neither a real reboot nor any reset of private SDK state.
                int lookups=w.lookups();call(w.world,"phase",999);Object duplicate=w.chain(1000);w.dispatch(duplicate);w.once(duplicate);
                yes(w.lookups()==lookups&&w.originals()==2&&!w.captured()&&((Integer)field(w.probe,"faultFired")).intValue()==1,"construction burn survives authored phase rollback");break;
            }
            case 14:{w.armed();field(w.vector,"throwLogs",true);Object chain=w.chain(1000);w.dispatch(chain);w.once(chain);yes(w.originals()==1&&w.lookups()>0,"logger failure cannot escape or skip original");break;}
            case 15:{
                w.armed();final Object late=w.chain(1000);field(w.vector,"logWork",(Runnable)()->{try{w.dispatch(late);}catch(Throwable error){throw new AssertionError(error);}});
                Object chain=w.chain(1000);w.dispatch(chain);w.once(chain);w.once(late);yes(w.originals()==2&&w.codes().contains("HOST_BOOTSTRAP_REFUSED"),"post-report reentry caught by final source check");break;
            }
            case 16:{
                w.armed();Files.delete(w.request());Object first=w.chain(1000);w.dispatch(first);w.once(first);yes(!w.captured()&&w.lookups()==0,"permit must be fresh after normal return");
                w.permit("good");Object duplicate=w.chain(1000);w.dispatch(duplicate);w.once(duplicate);yes(!w.captured()&&w.lookups()==0,"restored permit does not backfill consumed occurrence");break;
            }
            case 17:{w.permit("good");field(w.vector,"badAck",true);w.start();yes(w.installs()==1,"partial hook handle created");Object chain=w.chain(1000);w.dispatch(chain);w.once(chain);yes(!w.captured()&&w.lookups()==0,"unacknowledged hook cannot capture");field(w.vector,"badAck",false);w.start();yes(w.installs()==1,"installation failure cannot rearm");break;}
            case 18:{w.permit("good");field(w.probe,"closeFault",true);w.start();yes(w.installs()==0,"failed permit close acknowledgement refuses");Object chain=w.chain(1000);w.dispatch(chain);w.once(chain);yes(!w.captured(),"close failure never opts in");break;}
            case 19:case 20:case 21:{w.armed();call(w.world,"profile",id==19?"headless":id==20?"wrong-type":"departing");Object chain=w.chain(1000);w.dispatch(chain);w.once(chain);yes(!w.captured()&&w.lookups()>0,"actual captured subject profile refuses without replacement");break;}
            case 22:{w.armed();Object foreign=call(w.world,"otherManager");Object chain=w.chain(foreign,1000);w.dispatch(chain);w.once(chain);yes(!w.captured()&&w.lookups()>0,"exact registry SSM differs from otherwise same-class receiver");break;}
            case 23:{w.armed();final Object chain=w.chain(1000);sourceFault(w,()->{try{((Object[])chain.getClass().getField("args").get(chain))[1]=Integer.valueOf(1001);}catch(Exception error){throw new AssertionError(error);}});w.dispatch(chain);w.once(chain);yes(!w.captured()&&w.lookups()==0,"post-return argument drift refuses before capture");break;}
            default:throw new AssertionError("unknown case");
            }
            w.closedOnly();
        }
        System.out.println("MODEL_CASE "+CASES[id]);
    }
    public static void main(String[] paths)throws Throwable{
        if(paths.length!=6)throw new AssertionError("program/deps/F/C/own-case-data/repository arguments required");
        for(int id=0;id<CASES.length;id++)run(id,paths);
        System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":"+CASES.length+",\"checks\":"+checks+",\"privateSdkStateInspected\":false,\"verificationCalls\":0}");
    }
}
