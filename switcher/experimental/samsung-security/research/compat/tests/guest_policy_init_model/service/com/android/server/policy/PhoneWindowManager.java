package com.android.server.policy;
/** Authored field schema; no policy implementation. */
public class PhoneWindowManager implements WindowManagerPolicy {
 android.content.Context mContext;
 WindowManagerPolicy.WindowManagerFuncs mWindowManagerFuncs;
 com.android.server.wm.WindowManagerInternal mWindowManagerInternal;
 protected IPhoneWindowManagerExt mPhoneWindowManagerExt;
 com.android.server.policy.keyguard.KeyguardServiceDelegate mKeyguardDelegate;
 public void init(android.content.Context c,WindowManagerPolicy.WindowManagerFuncs w){fixture.FrameworkControl.forbidden++;throw new AssertionError("base init bypassed vendor override");}
 public PhoneWindowManager(){fixture.FrameworkControl.constructions++;}
 public void fixtureBind(android.content.Context c,com.android.server.wm.WindowManagerService w){mContext=c;mWindowManagerFuncs=w;mWindowManagerInternal=(com.android.server.wm.WindowManagerInternal)w.fixtureLocal();mKeyguardDelegate=new com.android.server.policy.keyguard.KeyguardServiceDelegate(new KeyguardStateCallback());}
 final class KeyguardStateCallback implements com.android.server.policy.keyguard.KeyguardServiceDelegate.StateCallback {public Object fixtureParent(){return PhoneWindowManager.this;}}
 public void fixtureContext(android.content.Context c){mContext=c;}
 public void fixtureDelegateReplace(){mKeyguardDelegate=new com.android.server.policy.keyguard.KeyguardServiceDelegate(new KeyguardStateCallback());}
 public com.android.server.policy.keyguard.KeyguardServiceDelegate fixtureDelegate(){return mKeyguardDelegate;}
 public boolean isKeyguardShowingAndNotOccluded(){fixture.FrameworkControl.forbidden++;throw new AssertionError("model policy operation invoked");}
}
