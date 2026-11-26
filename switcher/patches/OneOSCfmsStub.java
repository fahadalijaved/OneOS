import android.os.*;
import java.io.File;
import java.lang.reflect.Method;

/**
 * OneOS (0.5.17): stands in for One UI's "CustomFrequencyManagerService" (CFMS) while the guest runs, like
 * OneOSEdmStub for Knox. One UI's libgui in the shared cameraserver asks for CFMS on every camera Surface it
 * creates; only One UI's system_server registers it, so on the Galaxy S26 Exynos each lookup waited libbinder's
 * full 5 s ("Service CustomFrequencyManagerService didn't start. Returning NULL", "Failed to get CFMS service"):
 * 23 waits in one ColorOS session, stream configuration 5102 ms, Samsung Camera timed out waiting for frames
 * (report 7f0b2f5e and every S942B report since 0.5.11). CFMS only asks for CPU/GPU frequency boosts, which are
 * optional; every call is answered "no exception, nothing" (int32 0), so the lookup is immediate and no boost is
 * ever taken. Re-registers if the name goes; exits with the guest. ONEOS_GUEST_CFMS_STUB=0: off.
 * Run in the guest: app_process ... OneOSCfmsStub <guest system_server pid> [<service name> <interface>].
 *
 * 0.5.49: the same stand-in under another name. ColorOS's media codecs and audioserver ask for OPPO's
 * vendor.oplus.hardware.performance.IPerformance/default (a boost service a Samsung vendor lacks) on every
 * codec and track start and waited 2 x 5 s each time: notification sounds and ringtones started 10 s late and
 * ColorOS's notification player gave up after 5 s (Fold5 3e146336, S23 fb94d2c9: no notification, ringtone or
 * alarm sound). Registered under that name it answers at once, every call "no exception, nothing".
 */
public final class OneOSCfmsStub {
 private static String NAME = "CustomFrequencyManagerService";
 private static String DESCRIPTOR = "android.os.ICustomFrequencyManager";

 public static void main(String[] args) throws Exception {
  final int guest = Integer.parseInt(args[0]);
  if (args.length >= 3) { NAME = args[1]; DESCRIPTOR = args[2]; }
  Looper.prepareMainLooper();
  final Binder b = new Binder() {
   @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) throws RemoteException {
    if (code == INTERFACE_TRANSACTION) { if (reply != null) reply.writeString(DESCRIPTOR); return true; }
    if (reply != null) { reply.writeInt(0); reply.writeInt(0); }
    return true;
   }
  };
  final Class<?> sm = Class.forName("android.os.ServiceManager");
  final Method add = sm.getMethod("addService", String.class, IBinder.class, boolean.class, int.class);
  final Method check = sm.getMethod("checkService", String.class);
  if (check.invoke(null, NAME) != null) { System.out.println(NAME + " already registered; nothing to do"); return; }
  add.invoke(null, NAME, b, Boolean.FALSE, Integer.valueOf(1));
  if (check.invoke(null, NAME) == null) throw new IllegalStateException("addService " + NAME + " did not take");
  System.out.println("READY " + NAME + " uid=" + android.os.Process.myUid() + " guest=" + guest);
  System.out.flush();
  final Handler h = new Handler(Looper.myLooper());
  h.postDelayed(new Runnable() { public void run() {
   if (!new File("/proc/" + guest).exists()) { System.out.println("EXIT guest " + guest + " gone"); System.out.flush(); System.exit(0); }
   try {
    if (check.invoke(null, NAME) == null) { add.invoke(null, NAME, b, Boolean.FALSE, Integer.valueOf(1)); System.out.println("REREGISTERED " + NAME); System.out.flush(); }
   } catch (Throwable t) { System.out.println("recheck failed: " + t); System.out.flush(); }
   h.postDelayed(this, 2000);
  } }, 2000);
  Looper.loop();
 }
}
