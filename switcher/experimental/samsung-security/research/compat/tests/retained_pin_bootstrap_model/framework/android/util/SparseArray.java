package android.util;
public class SparseArray<T> {private final java.util.Map<Integer,T> values=new java.util.HashMap<Integer,T>();
 public Object expectedLock,forbiddenLock;
 public T get(int id){if(expectedLock!=null&&!Thread.holdsLock(expectedLock))throw new AssertionError("source monitor absent");if(forbiddenLock!=null&&Thread.holdsLock(forbiddenLock))throw new AssertionError("source monitors nested");return values.get(id);}
 public void put(int id,T value){values.put(id,value);}public void remove(int id){values.remove(id);}}
