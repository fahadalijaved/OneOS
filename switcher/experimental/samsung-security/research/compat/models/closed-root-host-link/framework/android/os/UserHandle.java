package android.os;
/** Retains the existing authored mHandle field shape consumed by actual Binding. */
public final class UserHandle {
 final int mHandle;
 public static final UserHandle SYSTEM=new UserHandle(0);
 public UserHandle(int id){model.Forbidden.constructions++;mHandle=id;}
 public int getIdentifier(){return mHandle;}
 public boolean equals(Object v){return v instanceof UserHandle&&((UserHandle)v).mHandle==mHandle;}
 public int hashCode(){return mHandle;}
 public static UserHandle getUserHandleForUid(int uid){return new UserHandle(uid/100000);}
}
