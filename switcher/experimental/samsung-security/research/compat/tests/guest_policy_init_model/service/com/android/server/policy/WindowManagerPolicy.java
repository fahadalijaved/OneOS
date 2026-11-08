package com.android.server.policy;
/** Authored runtime ABI, no OEM implementation. */
public interface WindowManagerPolicy extends android.view.WindowManagerPolicyConstants {
 void init(android.content.Context context, WindowManagerFuncs funcs);
 interface WindowManagerFuncs {}
}
