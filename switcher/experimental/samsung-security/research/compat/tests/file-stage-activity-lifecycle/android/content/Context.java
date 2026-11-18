package android.content;

import android.content.res.Resources;

public class Context {
    public static final int BIND_AUTO_CREATE = 1;
    private static Context application;
    private final Resources resources = new Resources();

    public static void setApplicationForTest(Context value) { application = value; }
    public Context getApplicationContext() {
        if (application == null) throw new IllegalStateException("No model application context");
        return application;
    }
    public Resources getResources() { return resources; }
    public String getPackageName() { return "com.fahadali.oneos.viewprep.filetree"; }

    public boolean bindService(Intent intent, ServiceConnection connection, int flags) {
        throw new UnsupportedOperationException("Test must supply a service binding");
    }

    public void unbindService(ServiceConnection connection) {
        throw new UnsupportedOperationException("Test must supply a service binding");
    }
}
