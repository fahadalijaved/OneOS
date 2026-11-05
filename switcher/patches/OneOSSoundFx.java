import android.os.Looper;
import android.os.SystemClock;
import java.io.File;
import java.lang.reflect.Constructor;
import java.util.UUID;

/**
 * Samsung's speaker tuning for the guest (experiment, 0.4.58; started by the
 * UI activator only while /data/local/tmp/oneos/guest_dolby.on exists).
 *
 * One UI's audioserver runs Samsung's processing on what it plays: Dolby DAX3
 * with Samsung's speaker endpoint tuning ("ProfileParamCache(There is specific
 * tuning for endpiont: speaker)", "setEndpointTuning(endpoint=speaker,
 * tuning=speaker)"), SoundBooster Plus and SoundAlive. The guest runs its own
 * audioserver (oneos_switch.sh, run 29), which only has the vendor effect HAL:
 * nothing is attached to its outputs ("0 Effect Chains" on every output thread,
 * report 4933a41d) and ColorOS's own engine (AudioEffectCenter's effect
 * 41f6c0f4-5d8f-11ec-bf63-0242ac130002) is not in Samsung's HAL. The vendor
 * effect HAL does list Dolby ("DAX3_S_3.14.0.0_r1", type 46d279d9): this
 * creates it on the output mix (session 0), enables it and holds it until the
 * guest's system_server (args[0]) is gone. args[1] may name another effect type.
 *
 * Runs inside the guest through app_process, like OneOSCameraWorker. The
 * constructor taking a type and an implementation is hidden, hence reflection.
 */
public final class OneOSSoundFx {
 private static final String DOLBY_TYPE = "46d279d9-9be7-453d-9d7c-ef937f675587";
 private static final String TYPE_NULL = "ec7178ec-e5e1-4432-a3f4-4657e6795210";

 public static void main(String[] args) throws Exception {
  final int guest = Integer.parseInt(args[0]);
  final UUID type = UUID.fromString(args.length > 1 ? args[1] : DOLBY_TYPE);
  Looper.prepareMainLooper();
  Class<?> c = Class.forName("android.media.audiofx.AudioEffect");
  Constructor<?> k = c.getDeclaredConstructor(UUID.class, UUID.class, int.class, int.class);
  k.setAccessible(true);
  Object fx = null;
  // The guest's audioserver registers late (guest_start.sh): try for a minute.
  for (int i = 0; fx == null && i < 30 && alive(guest); i++) {
   try {
    fx = k.newInstance(type, UUID.fromString(TYPE_NULL), 0, 0);
   } catch (Throwable t) {
    Throwable e = t.getCause() != null ? t.getCause() : t;
    if (i == 0 || i == 29) log("create " + type + " failed (try " + (i + 1) + "): " + e);
    Thread.sleep(2000);
   }
  }
  if (fx == null) { log("no effect of type " + type + " on the output mix; exiting"); return; }
  Object d = c.getMethod("getDescriptor").invoke(fx);
  log("created " + field(d, "name") + " " + field(d, "uuid") + " (" + field(d, "implementor") + ") on the output mix");
  Object r = c.getMethod("setEnabled", boolean.class).invoke(fx, true);
  log("setEnabled(true) = " + r + ", enabled " + c.getMethod("getEnabled").invoke(fx)
      + ", has control " + c.getMethod("hasControl").invoke(fx));
  while (alive(guest)) Thread.sleep(5000);
  c.getMethod("release").invoke(fx);
  log("guest system_server " + guest + " gone; released");
 }

 private static boolean alive(int pid) { return new File("/proc/" + pid).exists(); }

 private static Object field(Object o, String n) {
  try { return o.getClass().getField(n).get(o); } catch (Throwable t) { return "?"; }
 }

 private static void log(String s) {
  System.out.println(SystemClock.elapsedRealtime() + " " + s);
  System.out.flush();
 }
}
