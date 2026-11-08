package android.app;

import android.content.Intent;
import android.os.IBinder;

public abstract class Service {
    public abstract IBinder onBind(Intent intent);
    public void onDestroy() {}
}
