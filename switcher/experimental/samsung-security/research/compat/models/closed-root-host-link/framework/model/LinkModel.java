package model;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import android.os.*;
import android.app.Service;
import android.content.*;
import android.content.pm.*;
/** Authored direct calls/queues and synthetic package facts, never Android transport. */
public final class LinkModel {
 private static Path repo,data;
 public static final InheritableThreadLocal<Integer> uid=new InheritableThreadLocal<Integer>() {
  protected Integer initialValue(){return 1000;}
 };
 public static volatile int appUid=10234,packageReads,binds,unbinds,posts;public static final java.util.concurrent.atomic.AtomicInteger parcelObtains=new java.util.concurrent.atomic.AtomicInteger(),parcelRecycles=new java.util.concurrent.atomic.AtomicInteger(),borrowedRecycles=new java.util.concurrent.atomic.AtomicInteger();
 public static volatile int brokerCalls,callbackCalls,callbackCompleted,capturedCalls,failedCalls,controlCalls,pingCalls,closeCalls;public static volatile Runnable callbackHook;
 public static boolean unlocked=true;public static int unlockReads,registrations,unregistrations;public static final Map<BroadcastReceiver,IntentFilter> receivers=new LinkedHashMap<BroadcastReceiver,IntentFilter>();public static Context receiverContext;
 public static final List<Thread> packageWorkers=new ArrayList<Thread>();
 public static volatile boolean postRefused,bindRefused,unbindThrows,packageMissing;
 public static volatile Throwable packageFailure;
 public static volatile Runnable packageHook,afterTransact;
 public static Service app;
 public static android.os.IBinder broker,lastControl,lastCallback;
 public static volatile boolean waitCallbackBeforeBeginReturn,callbackBeforeBeginReturn;
 public static ServiceConnection connection;
 public static ComponentName component;
 public static PackageInfo info;
 public static final List<Runnable> queue=new ArrayList<Runnable>();
 public static final List<Thread> workers=new ArrayList<Thread>();
 public static synchronized void configure(String repository,String directory)throws Exception {
  if(repo!=null)throw new IOException("fresh loader required");
  Path r=Paths.get(repository).toAbsolutePath().normalize(),d=Paths.get(directory).toAbsolutePath().normalize();
  if(!d.startsWith(r.resolve("out"))||!Files.isRegularFile(r.resolve("tools/test_closed_root_host_link.py")))throw new IOException("repository data required");
  repo=r.toRealPath();data=d.toRealPath();if(!data.equals(d)||!data.startsWith(repo.resolve("out")))throw new IOException("aliases refused");
 }
 public static Path path(String value)throws IOException {
  if(data==null)throw new IOException("not configured");Path p=Paths.get(value).toAbsolutePath().normalize();
  if(!p.startsWith(data)||Files.isSymbolicLink(p)||!p.toRealPath().startsWith(data))throw new IOException("outside private fixture root");return p;
 }
 public static boolean post(Runnable task){synchronized(queue){posts++;if(postRefused)return false;queue.add(task);return true;}}
 public static int queued(){synchronized(queue){return queue.size();}}
 public static void drain(){if(Thread.currentThread()!=Looper.getMainLooper().getThread())throw new AssertionError("fixture main only");
  for(int i=0;i<128;i++){Runnable r;synchronized(queue){if(queue.isEmpty())return;r=queue.remove(0);}r.run();}throw new AssertionError("queue bound");}
 public static PackageInfo packageInfo(String name)throws PackageManager.NameNotFoundException {
  observe();synchronized(packageWorkers){if(!packageWorkers.contains(Thread.currentThread()))packageWorkers.add(Thread.currentThread());}packageReads++;Runnable h=packageHook;packageHook=null;if(h!=null)h.run();
  if(packageFailure!=null)raise(packageFailure);if(packageMissing||info==null||!name.equals(info.packageName))throw new PackageManager.NameNotFoundException(name);return info;
 }
 public static boolean bind(Intent intent,ServiceConnection callback){
  if(intent==null||intent.getComponent()==null||info==null||!info.packageName.equals(intent.getComponent().getPackageName())||!"com.fahadali.oneos.core.root.RetainedRootHostService".equals(intent.getComponent().getClassName()))throw new AssertionError("exact explicit app component required");
  binds++;if(bindRefused)return false;component=intent.getComponent();connection=callback;
  if(app==null)throw new AssertionError("actual app Service required");
  int old=uid.get();try{uid.set(appUid);broker=app.onBind(intent);}finally{uid.set(old);}
  post(()->callback.onServiceConnected(component,broker));return true;
 }
 public static void disconnect(){if(connection==null)throw new AssertionError("no actual connection");connection.onServiceDisconnected(component);}
 public static void unbind(ServiceConnection expected){unbinds++;if(expected!=connection)throw new AssertionError("same connection required");if(unbindThrows)throw new IllegalStateException("authored uncertain unbind");}
 public static void observe(){synchronized(workers){Thread t=Thread.currentThread();if(!workers.contains(t))workers.add(t);}}
 public static void awaitObservedWorkers()throws InterruptedException {List<Thread> copy;synchronized(workers){copy=new ArrayList<Thread>(workers);}for(Thread t:copy)if(t!=Thread.currentThread()){t.join(4000);if(t.isAlive())throw new AssertionError("observed worker remains active");}}
 public static void awaitPackageWorkers()throws InterruptedException {
  List<Thread> copy;synchronized(packageWorkers){copy=new ArrayList<Thread>(packageWorkers);}
  for(Thread t:copy)if(t!=Thread.currentThread()){t.join(4000);if(t.isAlive())throw new AssertionError("host package worker still active");}
 }
 public static void unlockBroadcast(int user){for(Map.Entry<BroadcastReceiver,IntentFilter> e:new ArrayList<Map.Entry<BroadcastReceiver,IntentFilter>>(receivers.entrySet()))if(e.getValue().actions.contains(Intent.ACTION_USER_UNLOCKED)){BroadcastReceiver current=e.getKey();post(()->current.onReceive(receiverContext,new Intent(Intent.ACTION_USER_UNLOCKED).putExtra(Intent.EXTRA_USER_HANDLE,user)));}}
 public static void packageBroadcast(){for(Map.Entry<BroadcastReceiver,IntentFilter> e:new ArrayList<Map.Entry<BroadcastReceiver,IntentFilter>>(receivers.entrySet()))if(e.getValue().actions.contains(Intent.ACTION_PACKAGE_REPLACED)){BroadcastReceiver current=e.getKey();post(()->current.onReceive(receiverContext,new Intent(Intent.ACTION_PACKAGE_REPLACED).setData(android.net.Uri.parse("package:com.fahadali.oneos"))));}}
 public static void cleanup()throws Throwable {
  List<Thread> copy;synchronized(workers){copy=new ArrayList<Thread>(workers);}Throwable primary=null;
  for(Thread t:copy)if(t!=Thread.currentThread())try{t.join(4000);if(t.isAlive())throw new AssertionError("link worker retained after fixture shutdown");}
  catch(Throwable failure){if(primary==null)primary=failure;else if(primary!=failure)primary.addSuppressed(failure);}
  synchronized(queue){queue.clear();}if(primary!=null)throw primary;
 }
 @SuppressWarnings("unchecked") private static <T extends Throwable>void rethrow(Throwable t)throws T{throw(T)t;}
 public static void raise(Throwable t){LinkModel.<RuntimeException>rethrow(t);}
}
