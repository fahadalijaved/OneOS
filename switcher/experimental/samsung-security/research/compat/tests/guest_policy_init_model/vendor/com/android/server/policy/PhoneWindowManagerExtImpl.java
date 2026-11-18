package com.android.server.policy;
/** Authored vendor reciprocal fields only. */
public class PhoneWindowManagerExtImpl implements IPhoneWindowManagerExt {
 PhoneWindowManager mBase;
 SubPhoneWindowManager mSub;
 android.content.Context mContext;
 public PhoneWindowManagerExtImpl(SubPhoneWindowManager p){fixture.FrameworkControl.constructions++;mBase=p;mSub=p;}
 public void fixtureContext(android.content.Context c){mContext=c;}
 public void fixtureParent(SubPhoneWindowManager p){mBase=p;mSub=p;}
}
