package android.os;
/** Authored thread identity controls; NO message queue or Android scheduling. */
public final class Looper {
 private static Looper main;
 private static final ThreadLocal<Looper> current=new ThreadLocal<Looper>();
 private final Thread thread;
 public Looper(Thread t){thread=t;}
 public Thread getThread(){return thread;}
 public static void modelSet(Thread t){main=new Looper(t);if(Thread.currentThread()==t)current.set(main);}
 public static void attachCurrentThread(){current.set(new Looper(Thread.currentThread()));}
 public static Looper myLooper(){return current.get();}
 public static Looper getMainLooper(){fixture.FrameworkControl.onPlacement();return main;}
}
