package com.android.server;
import com.android.server.pm.*;import com.android.server.am.*;import java.lang.reflect.*;
public final class World {
 public static int preparations;public static PackageManagerService p,q;public static StorageManagerService s,t;
 public static ActivityManagerService a,b;public static SystemServiceManager m,n;
 public static Object injector,otherInjector;
 public static void init()throws Exception{preparations++;p=new PackageManagerService();q=new PackageManagerService();
  s=new StorageManagerService();t=new StorageManagerService();m=new SystemServiceManager();n=new SystemServiceManager();
  a=new ActivityManagerService(p.mUserManager,m);b=new ActivityManagerService(q.mUserManager,n);
  injector=get(a.mUserController,"mInjector");otherInjector=get(b.mUserController,"mInjector");install(false);}
 static Object get(Object o,String name)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);return f.get(o);}
 static void put(Object o,String name,Object v)throws Exception{Field f=o.getClass().getDeclaredField(name);f.setAccessible(true);f.set(o,v);}
 static void root(Class<?> c,Object v){LocalServices.entries.put(c,v);}
 public static void install(boolean foreign){PackageManagerService v=foreign?q:p;StorageManagerService z=foreign?t:s;
  ActivityManagerService x=foreign?b:a;SystemServiceManager y=foreign?n:m;
  UserManagerService.sInstance=v.mUserManager;PackageManagerService.sPersonaManager=v.mUserManager.sPersonaManager;
  LocalServices.modelClear();root(UserManagerInternal.class,v.mUserManager.mLocalService);root(PackageManagerService.class,v);
  root(android.content.pm.PackageManagerInternal.class,v.modelPmi);root(StorageManagerService.StorageManagerInternalImpl.class,z.mStorageManagerInternal);
  root(android.app.ActivityManagerInternal.class,x.mInternal);root(SystemServiceManager.class,y);}
 public static Object[] expected(){return new Object[]{p.mUserManager.mLocalService,p.mUserManager,p,p.modelPmi,
  p.mUserManager.mUserDataPreparer,p.mUserManager.sPersonaManager,p.mInstaller,p.mInstallLock,p.mLock,p.mUserManager.mContext,
  s.mStorageManagerInternal,s,s.mVold,a.mInternal,a,a.mUserController,injector,m};}
 public static void change(String k)throws Exception{
  UserManagerService u=p.mUserManager,v=q.mUserManager;
  if(k.equals("umi-root"))root(UserManagerInternal.class,null);
  else if(k.equals("pms-root"))root(PackageManagerService.class,null);
  else if(k.equals("pmi-root"))root(android.content.pm.PackageManagerInternal.class,null);
  else if(k.equals("smi-root"))root(StorageManagerService.StorageManagerInternalImpl.class,null);
  else if(k.equals("wrong-smi-key")){root(StorageManagerService.StorageManagerInternalImpl.class,null);
   root(android.os.storage.StorageManagerInternal.class,s.mStorageManagerInternal);}
  else if(k.equals("ami-root"))root(android.app.ActivityManagerInternal.class,null);
  else if(k.equals("manager-root"))root(SystemServiceManager.class,null);
  else if(k.equals("wrong-root-class"))root(android.content.pm.PackageManagerInternal.class,new Object());
  else if(k.equals("singleton"))UserManagerService.sInstance=v;
  else if(k.equals("umi-parent"))put(u.mLocalService,"this$0",v);
  else if(k.equals("ums-local"))put(u,"mLocalService",v.mLocalService);
  else if(k.equals("ums-pms"))put(u,"mPm",q);
  else if(k.equals("pms-ums"))put(p,"mUserManager",v);
  else if(k.equals("pmi-parent"))put(p.modelPmi,"this$0",q);
  else if(k.equals("cached-pmi"))put(u,"mPmInternal",q.modelPmi);
  else if(k.equals("persona"))PackageManagerService.sPersonaManager=v.sPersonaManager;
  else if(k.equals("preparer"))put(u,"mUserDataPreparer",v.mUserDataPreparer);
  else if(k.equals("installer"))put(u.mUserDataPreparer,"mInstaller",q.mInstaller);
  else if(k.equals("install-lock"))put(u.mUserDataPreparer,"mInstallLock",q.mInstallLock);
  else if(k.equals("packages-lock"))put(u,"mPackagesLock",q.mLock);
  else if(k.equals("context"))put(u.mUserDataPreparer,"mContext",v.mContext);
  else if(k.equals("smi-parent"))put(s.mStorageManagerInternal,"this$0",t);
  else if(k.equals("sms-local"))put(s,"mStorageManagerInternal",t.mStorageManagerInternal);
  else if(k.equals("vold-null"))s.mVold=null;
  else if(k.equals("vold-replaced"))s.mVold=t.mVold;
  else if(k.equals("ami-parent"))put(a.mInternal,"this$0",b);
  else if(k.equals("ams-local"))put(a,"mInternal",b.mInternal);
  else if(k.equals("boot-manager"))a.mSystemServiceManager=n;
  else if(k.equals("controller"))put(a,"mUserController",b.mUserController);
  else if(k.equals("injector"))put(a.mUserController,"mInjector",otherInjector);
  else if(k.equals("injector-ams"))put(injector,"mService",b);
  else if(k.equals("injector-ums-null"))put(injector,"mUserManager",null);
  else if(k.equals("injector-ums"))put(injector,"mUserManager",v);
  else if(k.equals("injector-umi-null"))put(injector,"mUserManagerInternal",null);
  else if(k.equals("injector-umi"))put(injector,"mUserManagerInternal",v.mLocalService);
  else if(k.equals("phase"))m.mCurrentPhase=999;
  else throw new AssertionError("unknown mutation "+k);
 }
}

