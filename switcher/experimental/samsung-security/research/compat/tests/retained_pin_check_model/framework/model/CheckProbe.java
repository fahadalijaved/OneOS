package model;

import android.os.*;
import com.android.internal.widget.ICheckCredentialProgressCallback;
import java.util.concurrent.atomic.AtomicInteger;

/** Explicit first-party event/caller observations, never source or native evidence. */
public final class CheckProbe {
    public static final AtomicInteger checkCalls=new AtomicInteger(),callbacks=new AtomicInteger(),callbackTransacts=new AtomicInteger();
    public static volatile int callbackFlags,callbackCode,lastUser;
    public static volatile long entryIdentity,callbackIdentity;
    public static volatile Thread checkThread,callbackThread;
    public static volatile ICheckCredentialProgressCallback lastOriginalCallback;
    public static volatile Object lastOriginalPin;
    public static volatile Runnable callbackAction;
    public static volatile Throwable callbackFailure;
    public static volatile Throwable asBinderFailure,factoryFailure;
    public static volatile boolean finalReached;
    public static void original(Object pin,int user,ICheckCredentialProgressCallback callback) {
        checkCalls.incrementAndGet();lastOriginalPin=pin;lastUser=user;
        entryIdentity=Binder.modelIdentity();checkThread=Thread.currentThread();lastOriginalCallback=callback;
    }
    public static IInterface newCallback(boolean proxy) {
        ICheckCredentialProgressCallback local=new ICheckCredentialProgressCallback.Stub(){
            public void onCredentialVerified()throws RemoteException {
                callbacks.incrementAndGet();callbackIdentity=Binder.modelIdentity();callbackThread=Thread.currentThread();
                Runnable hook=callbackAction;if(hook!=null)hook.run();Binder.modelThrow(callbackFailure);
            }
        };
        return proxy?ICheckCredentialProgressCallback.Stub.asInterface(new Remote(local.asBinder())):local;
    }
    public static IBinder binderOf(IInterface callback){return callback==null?null:callback.asBinder();}
    public static IInterface wrongCallback(){return new IInterface(){public IBinder asBinder(){return new Binder();}};}
    public static IInterface nullBinderCallback(){return new ICheckCredentialProgressCallback.Stub(){
        public IBinder asBinder(){return null;}
        public void onCredentialVerified(){throw new AssertionError("invalid callback executed");}
    };}
    public static IInterface throwingBinderCallback(){return new ICheckCredentialProgressCallback.Stub(){
        public IBinder asBinder(){Binder.modelThrow(asBinderFailure);return null;}
        public void onCredentialVerified(){throw new AssertionError("failed Binder callback executed");}
    };}
    public static IInterface factoryFailureCallback(){return new ICheckCredentialProgressCallback.Stub(){
        public IInterface queryLocalInterface(String descriptor){Binder.modelThrow(factoryFailure);return super.queryLocalInterface(descriptor);}
        public void onCredentialVerified(){throw new AssertionError("failed callback factory executed");}
    };}
    public static Object canonicalFromBinder(IBinder binder){return ICheckCredentialProgressCallback.Stub.asInterface(binder);}
    public static void fireLate()throws RemoteException {if(lastOriginalCallback!=null)lastOriginalCallback.onCredentialVerified();}
    private static final class Remote implements IBinder {
        private final IBinder target;
        Remote(IBinder target){this.target=target;}
        public IInterface queryLocalInterface(String descriptor){return null;}
        public boolean transact(int code,Parcel data,Parcel reply,int flags)throws RemoteException {return target.transact(code,data,reply,flags);}
    }
}
