package android.content.pm; public final class Signature {private final byte[] value;public Signature(byte[] v){value=v.clone();}public byte[] toByteArray(){return value.clone();}}
