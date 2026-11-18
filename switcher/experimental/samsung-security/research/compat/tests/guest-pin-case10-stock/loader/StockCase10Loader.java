import java.io.File;
import java.lang.reflect.InvocationTargetException;
import java.net.URL;
import java.net.URLClassLoader;

/** Keeps the authored framework types in the parent of the services model. */
public final class StockCase10Loader {
    public static void main(String[] args) throws Throwable {
        if (args.length != 2) throw new IllegalArgumentException("Model and caller-frame directories required");
        ClassLoader parent = StockCase10Loader.class.getClassLoader();
        URL[] sources = {new File(args[0]).toURI().toURL(), new File(args[1]).toURI().toURL()};
        try (URLClassLoader child = new URLClassLoader(sources, parent)) {
            String services = "com.android.server.locksettings.";
            String framework = "com.android.internal.widget.";
            Class<?> stub = Class.forName(framework + "ILockSettings$Stub", false, child);
            Class<?> service = Class.forName(services + "LockSettingsService", false, child);
            Class<?> frame = Class.forName(services + "GuestPinCallerFrame", false, child);
            Class<?> driver = Class.forName(services + "StockCase10Fixture", false, child);
            if (stub.getClassLoader() != parent || service.getSuperclass() != stub
                    || service.getClassLoader() != child || frame.getClassLoader() != child
                    || driver.getClassLoader() != child) {
                throw new AssertionError("Framework and services loader placement differs");
            }
            try {
                driver.getMethod("main", String[].class).invoke(null, (Object) new String[0]);
            } catch (InvocationTargetException failure) {
                throw failure.getCause();
            }
        }
    }
}
