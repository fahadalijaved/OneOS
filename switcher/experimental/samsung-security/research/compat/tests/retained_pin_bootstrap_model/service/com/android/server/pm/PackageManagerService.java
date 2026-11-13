package com.android.server.pm;
public class PackageManagerService {
 public final UserManagerService mUserManager;public final Installer mInstaller=new Installer();
 public final PackageManagerTracedLock mInstallLock=new PackageManagerTracedLock(),mLock=new PackageManagerTracedLock();
 public static PersonaManagerService sPersonaManager;public final android.content.pm.PackageManagerInternal modelPmi;
 public PackageManagerService(){modelPmi=new PackageManagerInternalImpl(this);sPersonaManager=new PersonaManagerService();
  mUserManager=new UserManagerService(this,new android.content.Context());}
 static class PackageManagerInternalImpl extends android.content.pm.PackageManagerInternal {
  public final PackageManagerService this$0;PackageManagerInternalImpl(PackageManagerService p){this$0=p;}}
}

