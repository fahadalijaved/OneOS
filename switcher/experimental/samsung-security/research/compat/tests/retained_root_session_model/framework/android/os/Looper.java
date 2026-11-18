package android.os;
/** Authored thread association only; no Android queue is implemented. */
public final class Looper {
    public static Looper main;
    private final Thread thread;
    public Looper(Thread thread){this.thread=thread;}
    public static Looper getMainLooper(){return main;}
    public static Looper myLooper(){return main!=null && Thread.currentThread()==main.thread?main:null;}
    public Thread getThread(){return thread;}
}
