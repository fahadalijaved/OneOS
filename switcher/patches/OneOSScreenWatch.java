import android.os.IBinder;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Method;

/**
 * OneOS (0.5.15): tells the double-tap keeper (guest_start.sh) when the guest sleeps with its AOD on.
 *
 * The keeper takes a lit panel for an awake guest unless /data/oneos_dt2w_aod says 1; its reader of the
 * guest's power_screen_state events sets that. Nothing OS writes no events after its boot (its event log
 * stops about 30 s in) and logs no sleep or wake, and the A36's panel reads the same on the AOD as awake
 * (dpms On, alpm 2), so a double tap on the AOD did nothing (owner, 2026-11-15). This asks the guest's power
 * service every 0.3 s whether it is interactive (one binder call) and, on each change, writes 1 (asleep
 * with doze_always_on=1: the lit panel is the AOD, low-power mode for it) or 0 (awake, or asleep with AOD
 * off: a lit panel then is a notification pulse and keeps its touch), as the reader does.
 *
 * Run in the guest's mount namespace: app_process ... OneOSScreenWatch <guest system_server pid>.
 * Ends with that system_server.
 */
public final class OneOSScreenWatch {
 private static final String FLAG = "/data/oneos_dt2w_aod";

 public static void main(String[] args) throws Exception {
  final int guest = Integer.parseInt(args[0]);
  Class<?> sm = Class.forName("android.os.ServiceManager");
  Method get = sm.getMethod("getService", String.class);
  Object pm = null;
  for (int i = 0; pm == null && i < 60 && alive(guest); i++) {
   IBinder b = (IBinder) get.invoke(null, "power");
   if (b != null) pm = Class.forName("android.os.IPowerManager$Stub").getMethod("asInterface", IBinder.class).invoke(null, b);
   if (pm == null) Thread.sleep(2000);
  }
  if (pm == null) { log("no power service; exiting"); return; }
  Method interactive = pm.getClass().getMethod("isInteractive");
  Method reason = null;
  try { reason = pm.getClass().getMethod("getLastSleepReason"); } catch (Throwable t) { }
  boolean wasAwake = true;
  int last = -1;
  int changes = 0;
  log("watching guest " + guest + " (power service, every 0.3 s)");
  while (alive(guest)) {
   boolean awake;
   try { awake = (Boolean) interactive.invoke(pm); } catch (Throwable t) { Thread.sleep(5000); continue; }
   // A click for a double tap to sleep (owner: "there should be haptic feedback for dt2w and dt2s"): the
   // lock screen's double tap goes to sleep as GO_TO_SLEEP_REASON_APPLICATION (0); the power key (4) and
   // the timeout (2) do not, and get none.
   if (wasAwake && !awake && reason != null) {
    try { if (((Integer) reason.invoke(pm)) == 0) click(); } catch (Throwable t) { }
   }
   wasAwake = awake;
   int v = awake ? 0 : (aodOn() ? 1 : 0);
   // Asleep: report it only when it lasts 1.5 s. A double tap to sleep puts the guest to sleep on the
   // second tap's touch down; low-power mode right then turned the finger's release into a tap on the
   // AOD, which woke it again a second later (A36 Nothing OS, owner: "cant dt2s now in lockscreen").
   if (v == 1 && last != 1) {
    Thread.sleep(1500);
    if (!alive(guest)) break;
    try { if ((Boolean) interactive.invoke(pm)) continue; } catch (Throwable t) { continue; }
   }
   if (v != last) {
    write(v);
    if (changes++ < 20) log((awake ? "awake" : "asleep") + ": " + FLAG + " = " + v);
    last = v;
   }
   Thread.sleep(300);
  }
  write(0);
  log("guest system_server " + guest + " gone after " + changes + " changes");
 }

 /** doze_always_on, read once per sleep through the settings command. */
 private static boolean aodOn() {
  try {
   Process p = Runtime.getRuntime().exec(new String[] {"/system/bin/settings", "get", "secure", "doze_always_on"});
   BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()));
   String s = r.readLine();
   p.waitFor();
   return "1".equals(s == null ? null : s.trim());
  } catch (Throwable t) {
   return false;
  }
 }

 private static void write(int v) {
  try {
   File n = new File(FLAG + ".n");
   try (FileOutputStream o = new FileOutputStream(n)) { o.write((v + "\n").getBytes()); }
   n.renameTo(new File(FLAG));
  } catch (Throwable t) { }
 }

 private static void click() {
  try { Runtime.getRuntime().exec(new String[] {"/system/bin/cmd", "vibrator_manager", "synced", "-f", "-d", "oneos_dt2s", "prebaked", "0"}); } catch (Throwable t) { }
 }

 private static boolean alive(int pid) { return new File("/proc/" + pid).exists(); }

 private static void log(String s) { System.out.println(s); }
}
