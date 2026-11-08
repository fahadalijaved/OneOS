package com.android.server;
/** Only authored graph controls; neither private SDK object inspection nor service operations. */
public final class BootstrapWorld {
 public static void init()throws Exception {
  HostPinOperationWorld.init(0,41,1);PinBindingWorld.info.userType="android.os.usertype.full.SYSTEM";
  World.m.mCurrentPhase=999;
 }
 public static Object manager(){return World.m;}
 public static Object otherManager(){World.m.mCurrentPhase=1000;World.n.mCurrentPhase=999;return World.n;}
 public static void phase(int phase){World.m.mCurrentPhase=phase;}
 public static int phase(){return World.m.mCurrentPhase;}
 public static void profile(String profile){
  if(profile.equals("headless")){PinBindingWorld.info.flags=0;PinBindingWorld.info.userType="android.os.usertype.system.HEADLESS";}
  else if(profile.equals("wrong-type"))PinBindingWorld.info.userType="android.os.usertype.full.SECONDARY";
  else if(profile.equals("departing"))PinBindingWorld.info.guestToRemove=true;
  else throw new AssertionError("unknown authored profile");
 }
 public static long[] observations(){return HostPinOperationWorld.observations();}
}
