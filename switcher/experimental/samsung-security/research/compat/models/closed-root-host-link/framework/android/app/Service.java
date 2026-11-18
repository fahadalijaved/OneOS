package android.app;
import android.content.*;import android.os.IBinder;
public abstract class Service extends Context {
 public void onCreate(){}public abstract IBinder onBind(Intent intent);public boolean onUnbind(Intent intent){return false;}public void onDestroy(){}
}
