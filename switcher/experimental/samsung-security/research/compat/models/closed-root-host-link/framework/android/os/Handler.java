package android.os;
public class Handler {
 private final Looper looper;public Handler(){this(Looper.myLooper());}public Handler(Looper l){looper=l;}
 public Looper getLooper(){return looper;}public boolean post(Runnable r){return model.LinkModel.post(r);}
 public void removeCallbacks(Runnable r){synchronized(model.LinkModel.queue){model.LinkModel.queue.remove(r);}}
}
