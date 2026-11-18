package android.net;
/** Name holder only; no socket or namespace is created. */
public final class LocalSocketAddress {
    public enum Namespace {ABSTRACT,RESERVED,FILESYSTEM}
    private final String name;private final Namespace namespace;
    public LocalSocketAddress(String name,Namespace namespace){this.name=name;this.namespace=namespace;}
    public String getName(){return name;}
    public Namespace getNamespace(){return namespace;}
}
