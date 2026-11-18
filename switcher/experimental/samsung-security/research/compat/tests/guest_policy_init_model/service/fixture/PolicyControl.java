package fixture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
/** Authored policy behavior only; never reads or edits SDK helper private state. */
public final class PolicyControl {
 public static volatile String mode="NORMAL";
 public static volatile int calls;
 public static volatile Throwable sentinel;
 public static volatile Thread lastThread;
 public static volatile Object[] lastArgs;
 public static final CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
 private static final ThreadLocal<Integer> depth=new ThreadLocal<Integer>();
 public static boolean enter(Object policy,android.content.Context context,com.android.server.policy.WindowManagerPolicy.WindowManagerFuncs window){
  int d=depth.get()==null?0:depth.get();depth.set(d+1);
  int call; synchronized(PolicyControl.class){call=++calls;lastThread=Thread.currentThread();lastArgs=new Object[]{policy,context,window};}
  if(mode.equals("BLOCK_FIRST")&&call==1){entered.countDown();try{if(!release.await(3,TimeUnit.SECONDS))throw new AssertionError("model original release timeout");}catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}}
  if(mode.equals("THROW_BEFORE"))raise(sentinel);
  if(mode.equals("REENTER_ONCE")&&d==0){
   try{Class<?> h=Class.forName("com.appleexploit.oneos.security.authority.PreparedGuestPolicyInitCompletion",false,PolicyControl.class.getClassLoader());h.getMethod("invokeOriginal",com.android.server.policy.WindowManagerPolicy.class,android.content.Context.class,com.android.server.policy.WindowManagerPolicy.WindowManagerFuncs.class).invoke(null,policy,context,window);}
   catch(java.lang.reflect.InvocationTargetException e){raise(e.getCause());}catch(ReflectiveOperationException e){throw new AssertionError(e);}
  }
  return !mode.equals("KEEP_LINKS");
 }
 public static void afterLinks(com.android.server.wm.WindowManagerService w){if(mode.equals("THROW_AFTER"))raise(sentinel);if(mode.equals("DRIFT_AFTER"))w.fixturePolicy(null);}
 public static void exit(){Integer d=depth.get();if(d!=null)depth.set(d-1);}
 private static <T extends Throwable> void sneaky(Throwable t)throws T{throw(T)t;}
 private static void raise(Throwable t){if(t==null)throw new AssertionError("missing model sentinel");PolicyControl.<RuntimeException>sneaky(t);}
}
