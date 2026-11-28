package android.util;
public class SparseBooleanArray {private final java.util.Map<Integer,Boolean> values=new java.util.HashMap<Integer,Boolean>();
 public Object expectedLock,forbiddenLock;
 public boolean get(int id){if(expectedLock!=null&&!Thread.holdsLock(expectedLock))throw new AssertionError("source monitor absent");if(forbiddenLock!=null&&Thread.holdsLock(forbiddenLock))throw new AssertionError("source monitors nested");return Boolean.TRUE.equals(values.get(id));}
 public void put(int id,boolean value){values.put(id,value);}}
