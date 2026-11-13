package android.system;
public final class ErrnoException extends Exception {
    public final int errno;
    public ErrnoException(String name,int errno){super("modeled "+name+" errno "+errno);this.errno=errno;}
}
