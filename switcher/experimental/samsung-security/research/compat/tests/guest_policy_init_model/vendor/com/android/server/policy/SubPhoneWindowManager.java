package com.android.server.policy;
/** First-party modeled init behavior, not original OEM implementation. */
public class SubPhoneWindowManager extends PhoneWindowManager {
 public SubPhoneWindowManager(){mPhoneWindowManagerExt=new PhoneWindowManagerExtImpl(this);}
 public PhoneWindowManagerExtImpl fixtureExtension(){return(PhoneWindowManagerExtImpl)mPhoneWindowManagerExt;}
 @Override public void init(android.content.Context c,WindowManagerPolicy.WindowManagerFuncs f){try{boolean links=fixture.PolicyControl.enter(this,c,f);com.android.server.wm.WindowManagerService w=(com.android.server.wm.WindowManagerService)f;if(links){fixtureBind(c,w);fixtureExtension().fixtureContext(c);}fixture.PolicyControl.afterLinks(w);}finally{fixture.PolicyControl.exit();}}
}
