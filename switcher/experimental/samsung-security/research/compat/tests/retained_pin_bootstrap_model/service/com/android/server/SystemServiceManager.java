package com.android.server;
/** Authored normal/fast-return/throw seam, not the original SSM implementation. */
public final class SystemServiceManager {
 public java.util.List<SystemService> mServices=new java.util.ArrayList<SystemService>();
 public int mCurrentPhase=1000;
 public final boolean isBootCompleted(){return mCurrentPhase>=1000;}
 public final void startBootPhase(com.android.server.utils.TimingsTraceAndSlog timing,int phase){
  model.BootstrapProbe.original();if(phase<=mCurrentPhase)return;
  mCurrentPhase=phase;model.BootstrapProbe.afterPhase();
 }
}
