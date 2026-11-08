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
 * 0.4.65 (on by default; F8U InfinityX test): an output-mix effect is put on
 * the output music plays on when it is created, and stays there. Created at
 * boot it sat on the primary output while music (YouTube in a browser) played
 * on the deep-buffer one without it; created while music played it was on
 * that output. So it is created again each time music starts (STREAM_MUSIC
 * active after being idle, AudioSystem.isStreamActive, checked every 2 s), 2 s
 * after the start.
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
   fx = create(c, k, type, i == 0 || i == 29 ? "try " + (i + 1) : null);
   if (fx == null) Thread.sleep(2000);
  }
  if (fx == null) { log("no effect of type " + type + " on the output mix; exiting"); return; }
  boolean was = musicActive();
  int moves = 0;
  while (alive(guest)) {
   Thread.sleep(2000);
   boolean now = musicActive();
   if (now && !was) {
    // Music started: create it again, so it is on the output music plays on. Not at
    // once: created right at the start it went to the primary output again (F8U test);
    // created 2 s in, with the music's output running, it is on that output.
    Thread.sleep(2000);
    if (!alive(guest)) break;
    try { c.getMethod("release").invoke(fx); } catch (Throwable t) { }
    fx = null;
    Object f = create(c, k, type, moves < 5 ? "music started" : null);
    if (f != null) fx = f;
    else { Thread.sleep(1000); fx = create(c, k, type, "music started (again)"); }
    moves++;
   }
   was = now;
  }
  if (fx != null) c.getMethod("release").invoke(fx);
  log("guest system_server " + guest + " gone; released (" + moves + " re-attachments)");
 }

 /** The effect on the output mix, enabled; null when it cannot be created. why: log it (null: quiet). */
 private static Object create(Class<?> c, Constructor<?> k, UUID type, String why) {
  try {
   Object fx = k.newInstance(type, UUID.fromString(TYPE_NULL), 0, 0);
   Object r = c.getMethod("setEnabled", boolean.class).invoke(fx, true);
   if (why != null) {
    Object d = c.getMethod("getDescriptor").invoke(fx);
    log("created " + field(d, "name") + " " + field(d, "uuid") + " (" + field(d, "implementor") + ") on the output mix ("
        + why + "); setEnabled(true) = " + r + ", enabled " + c.getMethod("getEnabled").invoke(fx)
        + ", has control " + c.getMethod("hasControl").invoke(fx));
   }
   return fx;
  } catch (Throwable t) {
   Throwable e = t.getCause() != null ? t.getCause() : t;
   if (why != null) log("create " + type + " failed (" + why + "): " + e);
   return null;
  }
 }

 /** STREAM_MUSIC (3) active now (AudioSystem.isStreamActive, hidden); false when it cannot be asked. */
 private static boolean musicActive() {
  try {
   Class<?> s = Class.forName("android.media.AudioSystem");
   return (Boolean) s.getMethod("isStreamActive", int.class, int.class).invoke(null, 3, 0);
  } catch (Throwable t) {
   return false;
  }
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
