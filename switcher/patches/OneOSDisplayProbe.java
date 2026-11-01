import java.lang.reflect.Method;
import java.util.List;

/**
 * Diagnostics: what the guest's window manager reports as the default
 * display's possible sizes (the launcher sizes its grid from these; run 17:
 * only the cover, so the inner panel got a phone grid), and every logical
 * display, disabled ones included. Run in the guest by the UI activator when
 * $STAGE/OneOSDisplayProbe.dex is staged; output to diag_displays.txt.
 */
public final class OneOSDisplayProbe {
  public static void main(String[] a) {
    try {
      Class<?> wmg = Class.forName("android.view.WindowManagerGlobal");
      Object wms = wmg.getMethod("getWindowManagerService").invoke(null);
      Method m = wms.getClass().getMethod("getPossibleDisplayInfo", int.class);
      List<?> l = (List<?>) m.invoke(wms, 0);
      System.out.println("window possible infos for display 0: " + l.size());
      for (Object o : l) System.out.println("  " + o);
    } catch (Throwable t) {
      System.out.println("possible infos: " + t + (t.getCause() != null ? " caused by " + t.getCause() : ""));
    }
    try {
      Class<?> dmg = Class.forName("android.hardware.display.DisplayManagerGlobal");
      Object dm = dmg.getMethod("getInstance").invoke(null);
      int[] ids;
      try {
        ids = (int[]) dmg.getMethod("getDisplayIds", boolean.class).invoke(dm, true);
      } catch (NoSuchMethodException e) {
        ids = (int[]) dmg.getMethod("getDisplayIds").invoke(dm);
      }
      for (int id : ids) {
        Object di = dmg.getMethod("getDisplayInfo", int.class).invoke(dm, id);
        System.out.println("display " + id + ": " + di);
      }
    } catch (Throwable t) {
      System.out.println("displays: " + t);
    }
  }
}
