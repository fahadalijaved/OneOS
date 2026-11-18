package android.content.pm;
public class PackageInfo {public String packageName;public ApplicationInfo applicationInfo;public SigningInfo signingInfo;public Signature[] signatures;public int versionCode;public long longVersionCode;public long getLongVersionCode(){return longVersionCode;}}
