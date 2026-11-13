package com.android.server.pm;
public final class UserManagerService implements android.os.IUserManager {
 public final Object mUsersLock=new Object();
 public final android.util.SparseArray<UserData> mUsers=new android.util.SparseArray<UserData>();
 public final android.util.SparseBooleanArray mRemovingUserIds=new android.util.SparseBooleanArray();
 static class UserData {public android.content.pm.UserInfo info;UserData(android.content.pm.UserInfo i){info=i;}}
 public Object modelInstall(int id,int serial){UserData data=new UserData(new android.content.pm.UserInfo(id,serial));mUsers.put(id,data);return data;}
 public android.content.pm.UserInfo modelInfo(int id){return mUsers.get(id).info;}
 public static UserManagerService sInstance;public final LocalService mLocalService;
 public final PackageManagerService mPm;public android.content.pm.PackageManagerInternal mPmInternal;
 public final UserDataPreparer mUserDataPreparer;public final PersonaManagerService sPersonaManager;
 public final Object mPackagesLock;public final android.content.Context mContext;
 public UserManagerService(PackageManagerService p,android.content.Context c){mPm=p;mContext=c;mPackagesLock=p.mLock;
  mUserDataPreparer=new UserDataPreparer(c,p.mInstaller,p.mInstallLock);sPersonaManager=PackageManagerService.sPersonaManager;
  mLocalService=new LocalService(this);sInstance=this;}
 public static UserManagerService getInstance(){return sInstance;}
 public static final class LocalService extends UserManagerInternal {public UserManagerService this$0;
  LocalService(UserManagerService p){this$0=p;}}
}


