package android.content.pm;
public class PackageManager {
 public static final int GET_SIGNING_CERTIFICATES=0x08000000,GET_SIGNATURES=64;
 public static final class PackageInfoFlags {private PackageInfoFlags(){}public static PackageInfoFlags of(long flags){return new PackageInfoFlags();}}
 public static class NameNotFoundException extends Exception {public NameNotFoundException(String name){super(name);}}
 public PackageInfo getPackageInfo(String name,int flags)throws NameNotFoundException{return model.LinkModel.packageInfo(name);}
 public PackageInfo getPackageInfo(String name,PackageInfoFlags flags)throws NameNotFoundException{return model.LinkModel.packageInfo(name);}
 public ServiceInfo getServiceInfo(android.content.ComponentName name,int flags)throws NameNotFoundException {
  PackageInfo info=model.LinkModel.packageInfo(name.getPackageName());ServiceInfo service=new ServiceInfo();service.applicationInfo=info.applicationInfo;service.packageName=info.packageName;service.name="com.fahadali.oneos.core.root.RetainedRootHostServiceV2";return service;
 }
 public ApplicationInfo getApplicationInfo(String name,int flags)throws NameNotFoundException{return getPackageInfo(name,flags).applicationInfo;}
 public int getPackageUidAsUser(String name,int user)throws NameNotFoundException{return getPackageInfo(name,0).applicationInfo.uid;}
}
