package android.content;
import android.os.*;import android.content.pm.PackageManager;
public class Context {
 public static final int BIND_AUTO_CREATE=1,RECEIVER_EXPORTED=2,RECEIVER_NOT_EXPORTED=4;public static final String USER_SERVICE="user";
 private final android.os.UserManager users=new android.os.UserManager();
 private final PackageManager pm=new PackageManager();
 public Object getSystemService(String name){if(!USER_SERVICE.equals(name))throw new AssertionError("known service only");return users;}
 public <T>T getSystemService(Class<T> type){if(type!=android.os.UserManager.class)throw new AssertionError("known type only");return type.cast(users);}
 public Intent registerReceiverAsUser(BroadcastReceiver r,UserHandle user,IntentFilter f,String permission,Handler h){
  if(user==null||user.getIdentifier()!=0||!f.actions.contains(Intent.ACTION_USER_UNLOCKED)||h==null||h.getLooper()!=Looper.getMainLooper())throw new AssertionError("genuine modeled unlock profile");
  model.LinkModel.receivers.put(r,f);model.LinkModel.receiverContext=this;model.LinkModel.registrations++;return null;
 }
 public void unregisterReceiver(BroadcastReceiver r){if(!model.LinkModel.receivers.containsKey(r))throw new AssertionError("same receiver");model.LinkModel.unregistrations++;model.LinkModel.receivers.remove(r);}
 public Looper getMainLooper(){return Looper.getMainLooper();}
 public Intent registerReceiver(BroadcastReceiver r,IntentFilter filter,String permission,Handler handler,int flags){
  if(handler==null||handler.getLooper()!=Looper.getMainLooper()||flags!=RECEIVER_NOT_EXPORTED)throw new AssertionError("actual main/private receiver profile");
  model.LinkModel.receivers.put(r,filter);model.LinkModel.receiverContext=this;model.LinkModel.registrations++;return null;
 }
 public PackageManager getPackageManager(){return pm;}
 public boolean bindServiceAsUser(Intent i,ServiceConnection c,int flags,Handler h,UserHandle user){if(user==null||user.getIdentifier()!=0||h==null||h.getLooper()!=Looper.getMainLooper()||flags!=BIND_AUTO_CREATE)throw new AssertionError("canonical user0/main Handler/bind flags required");return model.LinkModel.bind(i,c);}
 public boolean bindServiceAsUser(Intent i,ServiceConnection c,int flags,UserHandle user){if(Thread.currentThread()!=Looper.getMainLooper().getThread())throw new AssertionError("source-owned main bind");return bindServiceAsUser(i,c,flags,new Handler(Looper.getMainLooper()),user);}
 public void unbindService(ServiceConnection c){model.LinkModel.unbind(c);}
 public Context getApplicationContext(){return this;}
 public String getPackageName(){return "com.fahadali.oneos";}
}
