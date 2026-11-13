package android.util;
/** Authored final collection model, not Android ArrayMap implementation. */
public final class ArrayMap<K,V> extends java.util.HashMap<K,V> {
 @Override public V get(Object key) {
  if(key instanceof Class && ((Class<?>)key).getName().equals("com.android.server.locksettings.LockSettingsInternal")) {
   com.android.server.LocalServices.modelLocalLookups++;
   Throwable failure=com.android.server.LocalServices.modelLocalFault;
   com.android.server.LocalServices.modelLocalFault=null;
   if(failure instanceof RuntimeException)throw(RuntimeException)failure;
   if(failure instanceof Error)throw(Error)failure;
   if(failure!=null)throw new AssertionError("unsupported fixture fault",failure);
  }
  return super.get(key);
 }
}
