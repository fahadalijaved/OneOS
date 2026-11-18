package android.view;
/** Authored direct-cache shape only. */
public final class WindowManagerGlobal {
 private static IWindowManager sWindowManagerService;
 public static void modelSet(Object value){sWindowManagerService=(IWindowManager)value;}
 public static IWindowManager getWindowManagerService(){fixture.FrameworkControl.forbidden++;throw new AssertionError("model lazy WMG getter invoked");}
}
