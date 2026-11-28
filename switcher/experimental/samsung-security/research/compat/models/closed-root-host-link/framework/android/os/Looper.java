package android.os;
public final class Looper {
 public static Looper main=new Looper(Thread.currentThread());private final Thread thread;
 public Looper(Thread t){thread=t;}public static Looper getMainLooper(){return main;}
 public static Looper myLooper(){return main!=null&&Thread.currentThread()==main.thread?main:null;}
 public Thread getThread(){return thread;}public static void modelSet(Thread t){main=new Looper(t);}
}
