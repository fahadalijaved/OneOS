package android.os;
public final class Looper {
 public static Looper main=new Looper(Thread.currentThread()); private final Thread thread;
 public Looper(Thread thread){this.thread=thread;} public static Looper getMainLooper(){return main;}
 public Thread getThread(){return thread;} public static void modelSet(Thread thread){main=new Looper(thread);}
}

