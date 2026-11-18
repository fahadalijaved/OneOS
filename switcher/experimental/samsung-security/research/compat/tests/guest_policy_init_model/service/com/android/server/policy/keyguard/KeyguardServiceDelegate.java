package com.android.server.policy.keyguard;
/** Authored field and anonymous-parent schema, not a keyguard protocol. */
public class KeyguardServiceDelegate {
 public interface StateCallback {}
 private final StateCallback mCallback;
 private final com.android.internal.policy.IKeyguardStateCallback mKeyguardStateCallback;
 private final android.content.ServiceConnection mKeyguardConnection;
 private final com.android.internal.policy.KeyguardState mKeyguardState=new com.android.internal.policy.KeyguardState();
 private final KeyguardReportedState mKeyguardReportedState=new KeyguardReportedState();
 private com.android.internal.policy.IKeyguardService mKeyguardService;
 static final class KeyguardReportedState {}
 public KeyguardServiceDelegate(StateCallback cb){
  fixture.FrameworkControl.constructions++;mCallback=cb;
  // Lexical anonymous1/3 preserve actual expected2/4 names. Explicit outer reads
  // force this$0 retention even with modern javac's unused-outer optimization.
  Object one=new Object(){public Object fixtureParent(){return KeyguardServiceDelegate.this;}};
  mKeyguardStateCallback=new com.android.internal.policy.IKeyguardStateCallback.Stub(){public Object fixtureParent(){return KeyguardServiceDelegate.this;}};
  Object three=new Object(){public Object fixtureParent(){return KeyguardServiceDelegate.this;}};
  mKeyguardConnection=new android.content.ServiceConnection(){public Object fixtureParent(){return KeyguardServiceDelegate.this;}};
  if(one==three)throw new AssertionError("authored anonymous ordering");
 }
 public void fixtureService(Object value){mKeyguardService=(com.android.internal.policy.IKeyguardService)value;}
 public void fixtureConnectionFrom(KeyguardServiceDelegate other)throws Exception{
  java.lang.reflect.Field f=KeyguardServiceDelegate.class.getDeclaredField("mKeyguardConnection");
  if(f.getModifiers()!=18||f.getDeclaringClass()!=KeyguardServiceDelegate.class)throw new AssertionError("model-only connection field shape");
  f.setAccessible(true);f.set(this,other.mKeyguardConnection);
 }
}
