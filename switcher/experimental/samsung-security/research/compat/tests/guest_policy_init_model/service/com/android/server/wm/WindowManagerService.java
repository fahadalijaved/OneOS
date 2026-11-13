package com.android.server.wm;
/** Authored field/parent schema. No WMS implementation or hardware behavior. */
public class WindowManagerService extends android.view.IWindowManager.Stub implements com.android.server.policy.WindowManagerPolicy.WindowManagerFuncs {
 final android.content.Context mContext;
 final WindowManagerInternal mInternal;
 com.android.server.policy.WindowManagerPolicy mPolicy;
 public WindowManagerService(android.content.Context c,com.android.server.policy.WindowManagerPolicy p){fixture.FrameworkControl.constructions++;mContext=c;mPolicy=p;mInternal=new LocalService();}
 final class LocalService extends WindowManagerInternal { public Object fixtureParent(){return WindowManagerService.this;} }
 public Object fixtureLocal(){return mInternal;}
 public void fixturePolicy(com.android.server.policy.WindowManagerPolicy value){mPolicy=value;}
 public boolean isKeyguardLocked(){fixture.FrameworkControl.forbidden++;throw new AssertionError("model policy getter invoked");}
}
