package fixture;
/** Own initialized graph shapes; constructor deliberately leaves policy init links absent. */
public final class PolicyWorld {
 private final android.content.Context context=new android.content.Context();
 private final com.android.server.policy.SubPhoneWindowManager policy=new com.android.server.policy.SubPhoneWindowManager();
 private final com.android.server.wm.OplusWindowManagerService window=new com.android.server.wm.OplusWindowManagerService(context,policy);
 public PolicyWorld(){FrameworkControl.keys(com.android.server.wm.WindowManagerInternal.class,com.android.server.policy.WindowManagerPolicy.class);FrameworkControl.publish(window.fixtureLocal(),policy,window);}
 public Object[] arguments(){return new Object[]{policy,context,window};}
 public void restorePolicy(){window.fixturePolicy(policy);}
 public void fixtureLinkWithoutInvocation(){policy.fixtureBind(context,window);policy.fixtureExtension().fixtureContext(context);}
}
