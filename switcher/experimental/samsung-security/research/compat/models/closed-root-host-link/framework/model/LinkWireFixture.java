package model;
import android.os.*;
import com.fahadali.oneos.core.root.*;
/** Exercises actual public Binder transport endpoints; never accesses production fields. */
public final class LinkWireFixture {
 public static void configure(String repo,String path,int scenario)throws Exception {
  LinkModel.configure(repo,path);SessionModel.configure(repo,path,scenario);
  BootstrapProbe.configureFixtureData(new java.io.File(repo),new java.io.File(path));
  android.os.Looper.modelSet(Thread.currentThread());
  LinkModel.appUid=SessionModel.callerUid;
  int prior=LinkModel.uid.get();try{LinkModel.uid.set(LinkModel.appUid);LinkModel.app=new RetainedRootHostService();}finally{LinkModel.uid.set(prior);}
 }
 public static void packageInfo(String apk,byte[] signer){
  android.content.pm.PackageInfo p=new android.content.pm.PackageInfo();p.packageName="com.fahadali.oneos";p.longVersionCode=7;
  p.applicationInfo=new android.content.pm.ApplicationInfo();p.applicationInfo.packageName=p.packageName;p.applicationInfo.uid=LinkModel.appUid;p.applicationInfo.sourceDir=apk;p.applicationInfo.publicSourceDir=apk;
  p.signingInfo=new android.content.pm.SigningInfo();p.signingInfo.current=new android.content.pm.Signature[]{new android.content.pm.Signature(signer)};p.signatures=p.signingInfo.current;
  LinkModel.info=p;
 }
 public static void version(long version){LinkModel.info.longVersionCode=version;}
 public static void signer(byte[] value){LinkModel.info.signingInfo.current=new android.content.pm.Signature[]{new android.content.pm.Signature(value)};}
 public static void destroyed(){LinkModel.app.onDestroy();}
 public static boolean sessionExists(){return RetainedRootSession.currentAttempt()!=null;}
 public static String sessionState(){RetainedRootSession.Attempt a=RetainedRootSession.currentAttempt();return a==null?"ABSENT":a.state().name();}
 public static int control(int code)throws Exception {
  IBinder target=LinkModel.lastControl;if(target==null)throw new AssertionError("no actual captured Control");
  Parcel data=Parcel.obtain(),reply=Parcel.obtain();
  try{data.writeInterfaceToken(ClosedRootLinkProtocol.CONTROL);data.writeInt(ClosedRootLinkProtocol.VERSION);
   if(!target.transact(code,data,reply,0))throw new AssertionError("unhandled control");reply.readException();int state=reply.readInt();reply.enforceNoDataAvail();return state;
  }finally{try{reply.recycle();}finally{data.recycle();}}
 }
 public static boolean badBegin(int bad)throws Exception {
  IBinder target=LinkModel.app.onBind(new android.content.Intent());
  Parcel data=Parcel.obtain(),reply=Parcel.obtain();int prior=LinkModel.uid.get();
  try{LinkModel.uid.set(bad==0?12345:1000);data.writeInterfaceToken(ClosedRootLinkProtocol.BROKER);data.writeInt(bad==1?2:1);
   data.writeStrongBinder(new Binder());data.writeString("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");data.writeLong(128);
   if(bad==2)data.writeInt(99);
   try{target.transact(1,data,reply,bad==3?1:0);return false;}catch(SecurityException|IllegalArgumentException expected){return true;}
  }finally{LinkModel.uid.set(prior);try{reply.recycle();}finally{data.recycle();}}
 }
 public static boolean retryBegin()throws Exception {try{return badBegin(4);}catch(IllegalStateException expected){return true;}}
 public static void awaitSession()throws Exception{Thread t=SessionModel.workerObserved;if(t!=null){t.join(4000);if(t.isAlive())throw new AssertionError("session worker remains active");}}
 public static void closeSession()throws Throwable {
  RetainedRootSession.Attempt a=RetainedRootSession.currentAttempt();if(a==null)return;
  a.requestClose();a.close();
 }
}
