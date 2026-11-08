package model;
import com.fahadali.oneos.core.root.RetainedRootHostServiceV2;
/** Sets up authored framework/package facts, never a supplied host owner. */
public final class LinkWireFixture {
    public static void configure(String repo,String path,String mode)throws Exception {
        LinkModel.configure(repo,path);NativePeerFixture.configure(repo,path,mode);
        BootstrapProbe.configureFixtureData(new java.io.File(repo),new java.io.File(path));
        android.os.Looper.modelSet(Thread.currentThread());LinkModel.appUid=10234;
        int prior=LinkModel.uid.get();try{LinkModel.uid.set(LinkModel.appUid);LinkModel.app=new RetainedRootHostServiceV2();}finally{LinkModel.uid.set(prior);}
    }
    public static void packageInfo(String apk,byte[] signer){
        android.content.pm.PackageInfo p=new android.content.pm.PackageInfo();p.packageName="com.fahadali.oneos";p.longVersionCode=7;
        p.applicationInfo=new android.content.pm.ApplicationInfo();p.applicationInfo.packageName=p.packageName;p.applicationInfo.uid=LinkModel.appUid;p.applicationInfo.sourceDir=apk;p.applicationInfo.publicSourceDir=apk;
        p.signingInfo=new android.content.pm.SigningInfo();p.signingInfo.current=new android.content.pm.Signature[]{new android.content.pm.Signature(signer)};p.signatures=p.signingInfo.current;LinkModel.info=p;
    }
    public static void destroyed(){LinkModel.app.onDestroy();}
    public static void reconnect(){
        RetainedRootHostServiceV2 replacement=new RetainedRootHostServiceV2();
        LinkModel.connection.onServiceConnected(LinkModel.component,replacement.onBind(new android.content.Intent()));
    }
}
