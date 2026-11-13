package android.os;
import java.io.File;
import model.ForkControl;
public final class Environment {
    public static File getDataDirectory() {
        try { return ForkControl.owned(ForkControl.data()).toFile(); }
        catch(java.io.IOException failure) { throw new IllegalStateException(failure); }
    }
}
