package com.android.server.am;
public final class UserController {
 public final Object mLock=new Object();public volatile int mCurrentUserId=3,mTargetUserId=-10000;
 public boolean mPendingLogoutTargetUser;public final java.util.ArrayDeque<Integer> mPendingTargetUserIds=new java.util.ArrayDeque<Integer>();
 public final android.util.SparseArray<UserState> mStartedUsers=new android.util.SparseArray<UserState>();
 public final Injector mInjector;
 public UserController(ActivityManagerService a,com.android.server.pm.UserManagerService u){mInjector=new Injector(a,u);}
 static class Injector {
  public ActivityManagerService mService;public com.android.server.pm.UserManagerService mUserManager;
  public com.android.server.pm.UserManagerInternal mUserManagerInternal;
  Injector(ActivityManagerService a,com.android.server.pm.UserManagerService u){mService=a;mUserManager=u;mUserManagerInternal=u.mLocalService;}
  public com.android.server.pm.UserManagerService getUserManager(){throw new AssertionError("lazy getter forbidden");}
  public com.android.server.pm.UserManagerInternal getUserManagerInternal(){throw new AssertionError("lazy getter forbidden");}
 }
}


