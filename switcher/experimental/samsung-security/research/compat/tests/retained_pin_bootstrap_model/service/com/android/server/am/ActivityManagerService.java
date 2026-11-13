package com.android.server.am;
public class ActivityManagerService {
 public final android.app.ActivityManagerInternal mInternal;public com.android.server.SystemServiceManager mSystemServiceManager;
 public final UserController mUserController;
 public ActivityManagerService(com.android.server.pm.UserManagerService u,com.android.server.SystemServiceManager m){
  mSystemServiceManager=m;mInternal=new LocalService(this);mUserController=new UserController(this,u);}
 public static final class LocalService extends android.app.ActivityManagerInternal {
  public final ActivityManagerService this$0;LocalService(ActivityManagerService s){this$0=s;}}
}

