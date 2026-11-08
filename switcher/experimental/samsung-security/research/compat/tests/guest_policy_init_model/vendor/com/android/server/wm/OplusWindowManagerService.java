package com.android.server.wm;
/** Authored vendor class/field shadow, no OEM implementation. */
public final class OplusWindowManagerService extends WindowManagerService {
 private android.content.Context mContext=new android.content.Context();
 public OplusWindowManagerService(android.content.Context c,com.android.server.policy.WindowManagerPolicy p){super(c,p);}
 public void fixtureShadow(){mContext=new android.content.Context();}
}
