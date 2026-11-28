package model;

import java.io.*;
import java.lang.reflect.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** Real first-party module/app/session APIs; authored framework fields only. Never private production inspection. */
public final class ClosedRootHostLinkTest {
 private static int checks;
 private static final byte[] SIGNER="authored-current-signer".getBytes(StandardCharsets.US_ASCII);
 private static void yes(boolean v,String why){checks++;if(!v)throw new AssertionError(why);}
 private static Object call(Object target,String name,Object...args)throws Throwable {
  Class<?> c=target instanceof Class?(Class<?>)target:target.getClass();Method found=null;
  for(Method m:c.getMethods())if(m.getName().equals(name)&&m.getParameterCount()==args.length){if(found!=null)throw new AssertionError("ambiguous public method "+name);found=m;}
  if(found==null)throw new AssertionError("missing public method "+name);
  try{return found.invoke(target instanceof Class?null:target,args);}catch(InvocationTargetException e){throw e.getCause();}
 }
 private static Object get(Class<?> type,String field)throws Exception {if(!type.getName().startsWith("model."))throw new AssertionError("authored model controls only");return type.getField(field).get(null);}
 private static void set(Class<?> type,String field,Object value)throws Exception {if(!type.getName().startsWith("model."))throw new AssertionError("authored model controls only");type.getField(field).set(null,value);}
 private static String hash(byte[] bytes)throws Exception {StringBuilder out=new StringBuilder();for(byte v:MessageDigest.getInstance("SHA-256").digest(bytes))out.append(String.format("%02x",v&255));return out.toString();}
 private interface Work {Object run()throws Throwable;}
 private static Object offMain(Work work)throws Throwable {
  AtomicReference<Object> result=new AtomicReference<Object>();AtomicReference<Throwable> error=new AtomicReference<Throwable>();
  Thread t=new Thread(()->{try{result.set(work.run());}catch(Throwable e){error.set(e);}},"authored-link-caller");t.setDaemon(true);t.start();t.join(5000);yes(!t.isAlive(),"authored caller joined");if(error.get()!=null)throw error.get();return result.get();
 }
 private static Throwable cleanup(Throwable primary,AutoCloseable resource){if(resource!=null)try{resource.close();}catch(Throwable e){if(primary==null)primary=e;else if(primary!=e)primary.addSuppressed(e);}return primary;}
 private static final class World implements AutoCloseable {
  Throwable expectedCloseFailure;
  final int selected;boolean hasProfile,closeExpected,closeAttempted;final java.util.concurrent.CountDownLatch startupRelease=new java.util.concurrent.CountDownLatch(1);
  final ClassLoader prior=Thread.currentThread().getContextClassLoader();URLClassLoader f,c,m;
  Class<?> link,wire,session,probe,vector,world,os;Object module,manager,timing;Method original;Path data,apk;
  World(String[] args,int id,int sessionCase)throws Throwable {
   selected=id;try {
    Path repo=Paths.get(args[5]).toRealPath(),base=Paths.get(args[4]).toRealPath();
    yes(Files.isRegularFile(repo.resolve("tools/test_closed_root_host_link.py"))&&base.startsWith(repo.resolve("out")),"actual runner/repo-only output");
    data=Files.createDirectory(base.resolve(String.format("%02d",id))).toRealPath();yes(data.startsWith(base),"private canonical case root");
    f=new URLClassLoader(new URL[]{new File(args[2]).toURI().toURL(),new File(args[1]).toURI().toURL()},ClassLoader.getPlatformClassLoader());
    c=new URLClassLoader(new URL[]{new File(args[3]).toURI().toURL()},f);
    m=new URLClassLoader(new URL[]{new File(args[0]).toURI().toURL()},f);
    Thread.currentThread().setContextClassLoader(c);
    call(Class.forName("com.android.internal.os.ZygoteInit",true,f),"modelSet",c);
    link=Class.forName("model.LinkModel",true,f);wire=Class.forName("model.LinkWireFixture",true,f);session=Class.forName("model.SessionModel",true,f);
    call(wire,"configure",repo.toString(),data.toString(),sessionCase);
    probe=Class.forName("model.BootstrapProbe",true,f);vector=Class.forName("model.VectorWorld",true,f);os=Class.forName("android.system.Os",true,f);
    Files.createDirectory(data.resolve("system"));apk=data.resolve("installed.apk");Files.write(apk,"authored-installed-app".getBytes(StandardCharsets.US_ASCII));
    call(wire,"packageInfo",apk.toString(),SIGNER);
    world=Class.forName("com.android.server.BootstrapWorld",true,c);call(world,"init");manager=call(world,"manager");
    Class<?> tt=Class.forName("com.android.server.utils.TimingsTraceAndSlog",true,c);timing=tt.getConstructor().newInstance();original=manager.getClass().getMethod("startBootPhase",tt,int.class);
    module=Class.forName("com.appleexploit.oneos.security.authority.RetainedPinHostModule",true,m).getConstructor().newInstance();
    call(module,"onModuleLoaded",Class.forName("model.VectorWorld$Loaded",true,f).getConstructor().newInstance());
   }catch(Throwable e){throw finish(e);}
  }
  void permit()throws Exception {Path p=data.resolve("system/oneos-samsung-pin-host-bootstrap/request-v1");Files.createDirectories(p.getParent());Files.write(p,"CAPTURE_PIN_HOST_BOOTSTRAP_V1\n".getBytes(StandardCharsets.US_ASCII));}
  void profile(String kind)throws Exception {
   hasProfile=!kind.equals("malformed");
   String value="version=1\npackage=com.fahadali.oneos\nsigner="+hash(SIGNER)+"\napk="+hash(Files.readAllBytes(apk))+"\ncode=7\nnative="+String.join("",Collections.nCopies(64,"a"))+"\nbytes=128\n";
   if(kind.equals("malformed"))value+="unknown=1\n";
   if(kind.equals("hash"))value=value.replace("apk="+hash(Files.readAllBytes(apk)),"apk="+String.join("",Collections.nCopies(64,"b")));
   Files.write(data.resolve("system/oneos_retained_root_link"),value.getBytes(StandardCharsets.US_ASCII));
  }
  void boot()throws Throwable {
   Object event=Class.forName("model.VectorWorld$Starting",true,f).getConstructor(ClassLoader.class).newInstance(c);call(module,"onSystemServerStarting",event);
   Object chain=Class.forName("model.VectorWorld$Chain",true,f).getConstructor(Method.class,Object.class,Object.class,int.class).newInstance(original,manager,timing,1000);
   call(vector,"dispatch",chain);yes(chain.getClass().getField("proceeded").getInt(chain)==1,"original boot phase exactly once");
  }
  int n(String key)throws Exception{return((Number)get(link,key)).intValue();}
  int spawns()throws Exception{return((Number)get(session,"spawns")).intValue();}
  void drain()throws Throwable{call(link,"drain");}
  void settle()throws Throwable {
   long end=System.nanoTime()+4000000000L;
   while(System.nanoTime()<end){
    call(link,"awaitPackageWorkers");drain();call(link,"awaitObservedWorkers");drain();
    if(n("brokerCalls")==0 && ((Integer)call(link,"queued")).intValue()==0 && (!hasProfile || selected==23 || !(Boolean)get(link,"unlocked") || n("packageReads")>0))return;
    if(n("callbackCalls")>0){call(link,"awaitObservedWorkers");drain();boolean mustPing=selected!=16&&selected!=17&&selected!=20;boolean mustClose=selected==16||selected==17||closeExpected;if(((Integer)call(link,"queued")).intValue()==0&&(!mustPing||n("pingCalls")>0)&&(!mustClose||n("closeCalls")>0))return;}
    Thread.sleep(2);
   }
   throw new AssertionError("bounded synthetic callback path not quiescent");
  }
  void linked()throws Throwable {
   settle();yes(n("binds")==1&&n("brokerCalls")==1&&n("capturedCalls")==1,"actual module-to-service-to-host callback path");
   yes(spawns()==1&&(Boolean)call(wire,"sessionExists"),"one actual Session factory, exact Spawn replacement");
   yes(n("pingCalls")==1&&String.valueOf(call(wire,"sessionState")).equals("ADMISSION_CLOSED"),"actual host validation PING reaches same closed-live Session");
  }
  Throwable finish(Throwable failure) {
   startupRelease.countDown();
   if(wire!=null)try{call(wire,"destroyed");if(!closeAttempted)offMain(()->{call(wire,"closeSession");return null;});}catch(Throwable e){if(e!=expectedCloseFailure){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}}
   for(Class<?> type:new Class<?>[]{session,link})if(type!=null)try{call(type,"cleanup");}catch(Throwable e){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}
   if(os!=null){
    try{yes(((Integer)call(os,"activeDescriptors")).intValue()==0,"profile/APK descriptors closed before fixture cleanup");}catch(Throwable e){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}
    try{call(os,"fixtureCleanup");}catch(Throwable e){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}
   }
   if(link!=null)try{yes(n("parcelObtains")==n("parcelRecycles")&&n("borrowedRecycles")==0,"all acquired Parcels independently recycled, borrowed never recycled");}catch(Throwable e){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}
   try{Thread.currentThread().setContextClassLoader(prior);}catch(Throwable e){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}
   failure=cleanup(failure,m);failure=cleanup(failure,c);failure=cleanup(failure,f);
   if(data!=null)try{List<Path> list=new ArrayList<Path>();try(java.util.stream.Stream<Path> walk=Files.walk(data)){walk.forEach(list::add);}Collections.sort(list,Collections.reverseOrder());for(Path p:list){if(!p.toAbsolutePath().normalize().startsWith(data))throw new AssertionError("cleanup escape");Files.delete(p);}}catch(Throwable e){if(failure==null)failure=e;else if(e!=failure)failure.addSuppressed(e);}
   return failure;
  }
  public void close()throws Exception {Throwable e=finish(null);if(e instanceof Error)throw(Error)e;if(e instanceof Exception)throw(Exception)e;if(e!=null)throw new AssertionError(e);}
 }
 private static void run(int id,String[] args)throws Throwable {
  int sessionCase=id==20?2:id==21?12:id==22?16:0;
  World w=new World(args,id,sessionCase);Throwable primary=null;
  try {
   if(id==0){w.boot();yes(w.n("binds")==0&&w.spawns()==0,"default absent capture permit does not bind/spawn");return;}
   if(id==1){w.permit();w.boot();w.settle();yes(w.n("binds")==0&&w.spawns()==0,"capture permit alone cannot enable app link");return;}
   if(id>=11&&id<=14){yes((Boolean)call(w.wire,"badBegin",id-11),"actual broker rejects unauthorized/version/trailing/oneway");yes(w.spawns()==0,"rejected frame never begins");return;}
   w.permit();w.profile(id==2?"malformed":id==4?"hash":"good");
   if(id==5)call(w.wire,"signer","different".getBytes(StandardCharsets.US_ASCII));
   if(id==6)call(w.wire,"version",8L);
   if(id==7)set(w.link,"packageMissing",true);
   if(id==8)set(w.link,"packageFailure",new IllegalStateException("authored PM failure"));
   if(id==9)set(w.link,"bindRefused",true);
   if(id==10)set(w.link,"postRefused",true);
   if(id==15)set(w.link,"waitCallbackBeforeBeginReturn",true);
   if(id==16){
    set(w.session,"spawnHook",(Runnable)()->{try{if(!w.startupRelease.await(4,java.util.concurrent.TimeUnit.SECONDS))throw new AssertionError("authored release missing");}catch(InterruptedException e){throw new AssertionError(e);}});
    set(w.link,"callbackHook",(Runnable)()->{try{set(w.link,"postRefused",true);}catch(Exception e){throw new AssertionError(e);}});
   }
   if(id==17)set(w.link,"callbackHook",(Runnable)()->{try{call(w.wire,"version",9L);}catch(Throwable e){throw new AssertionError(e);}});
   if(id>=24)set(w.link,"unlocked",false);
   if(id==23)set(w.probe,"closeFault",true);
   w.boot();
   if(id==2||id>=4&&id<=10||id==23){w.settle();yes(w.spawns()==0,"profile/package/worker/dispatch refusal cannot spawn");if(id!=9)yes(w.n("binds")==0,"failure before source bind");return;}
   if(id>=24){
    w.settle();yes(w.n("binds")==0&&w.spawns()==0,"CE-locked app cannot bind/spawn");
    if(id>=25){call(w.link,"unlockBroadcast",0);w.drain();w.settle();yes(w.n("binds")==0&&w.spawns()==0,"unlock event alone cannot fabricate actual CE state");}
    if(id==26){set(w.link,"unlocked",true);call(w.link,"unlockBroadcast",0);w.drain();w.linked();call(w.link,"unlockBroadcast",0);w.drain();yes(w.n("binds")==1&&w.spawns()==1,"real modeled unlock admits exactly one bind/factory");}
    return;
   }
   if(id==16){
    long end=System.nanoTime()+3000000000L;while(w.spawns()==0&&System.nanoTime()<end){w.drain();Thread.sleep(2);}
    yes(w.spawns()==1&&w.n("callbackCalls")==0,"actual Session begins before late callback");
    call(w.link,"disconnect");w.drain();yes(w.n("unbinds")==1,"host retirement precedes callback arrival");w.startupRelease.countDown();
   }
   if(id==16||id==17){w.settle();yes(w.spawns()==1&&w.n("capturedCalls")==1,"actual late callback owner retained");yes(w.n("pingCalls")==0,"refused post/package drift cannot validate captured control");yes(w.n("closeCalls")==1,"same actual control receives one cutoff");return;}
   if(id==20){w.expectedCloseFailure=(Throwable)get(w.session,"exact");w.settle();yes(w.spawns()==1&&w.n("failedCalls")==1&&w.n("pingCalls")==0,"actual failed begin publishes only unavailable, never Control");yes(String.valueOf(call(w.wire,"sessionState")).equals("UNRESOLVED"),"spawn uncertainty retained in actual session");yes((Boolean)call(w.wire,"retryBegin")&&w.spawns()==1,"service tombstone cannot retry uncertain begin");return;}
   w.linked();
   if(id==15)yes((Boolean)get(w.link,"callbackBeforeBeginReturn"),"actual callback delivered before BEGIN response completed");
   if(id==18){w.closeExpected=true;set(w.link,"unbindThrows",true);call(get(w.link,"broker"),"modelDie");w.settle();yes(w.n("unbinds")==1&&w.n("closeCalls")==1,"uncertain unbind retains cutoff/no retry");yes(w.spawns()==1,"retirement uncertainty never restarts native owner");}
   else if(id==19){w.closeExpected=true;Object control=get(w.link,"lastControl");call(control,"modelDie");w.settle();yes(w.n("closeCalls")==1&&w.n("unbinds")==1&&w.spawns()==1,"binder death cuts off same actual control and unbinds once without retry");}
   else if(id==21||id==22){
    offMain(()->call(w.wire,"control",2));Throwable actual=null;
    w.closeAttempted=true; // Before the fallible explicit close call; never retry uncertain progress in cleanup.
    try{offMain(()->{call(w.wire,"closeSession");return null;});}catch(Throwable failure){actual=failure;}
    yes(actual!=null,"uncertain cleanup must throw, never report successful close");
    if(id==22)yes(actual==w.os.getField("closeFailure").get(null),"mode16 propagates exact modeled pidfd-close ErrnoException");
    else yes(actual instanceof IOException,"mode12 native-exit observation failure is IOException");
    w.expectedCloseFailure=actual;call(w.wire,"awaitSession");yes(String.valueOf(call(w.wire,"sessionState")).equals("UNRESOLVED"),"ACK is not native exit/known descriptor cleanup");yes(w.spawns()==1&&(Integer)call(w.session,"live")>0,"actual unresolved observation ownership retained without retry");}
   else {Object state=offMain(()->call(w.wire,"control",3));yes(((Integer)state).intValue()>=1,"Control reports explicit actual state, not ready grant");}
  } catch(Throwable failure){primary=failure;throw failure;}
  finally {
   Throwable cleanupFailure=w.finish(null);
   if(cleanupFailure!=null){if(primary==null)throw cleanupFailure;else if(cleanupFailure!=primary)primary.addSuppressed(cleanupFailure);}
  }
 }
 public static void main(String[] args)throws Throwable {
  yes(args.length==6,"exact loader/output arguments");for(int n=0;n<27;n++){run(n,args);System.out.println("MODEL_CASE "+n);}
  System.out.println("{\"pass\":true,\"modeledOnly\":true,\"cases\":27,\"checks\":"+checks+",\"androidNativeOrAuthorityAccepted\":false}");
 }
}
