package com.fahadali.oneos.core.root;
import android.os.*;
import android.content.Intent;
import java.io.IOException;
import java.util.Arrays;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import model.OfferModel;
import model.HandoffWire;

/** Same-package public Binder entry only; no private production state inspected. */
public final class OfferRelayAssertions {
    private static int checks;
    private static void yes(boolean value) { checks++; if (!value) throw new AssertionError("offer assertion " + checks); }
    private static final class Callback extends Binder {
        final CountDownLatch done = new CountDownLatch(1);
        final AtomicInteger calls = new AtomicInteger();
        volatile int code, pid; volatile String name; volatile boolean loseReply;
        protected boolean onTransact(int code, Parcel data, Parcel reply, int flags) {
            OfferModel.observe(); calls.incrementAndGet(); this.code = code;
            data.enforceInterface(RetainedHostControlProtocol.CALLBACK);
            if (data.readInt()!=2 || flags!=0 || reply==null) throw new AssertionError("exact callback profile");
            if (code == 1) { pid=data.readInt(); name=data.readString(); }
            else if (code == 2) { if(data.readInt()!=1) throw new AssertionError("unavailable only"); }
            else throw new AssertionError("no app control callback");
            data.enforceNoDataAvail();
            done.countDown();
            if (loseReply) throw new IllegalStateException("authored reply lost after delivery");
            reply.writeNoException(); reply.writeInt(1); return true;
        }
    }
    private static void begin(IBinder broker, Callback callback, int version, boolean tail) throws Throwable {
        Parcel data=Parcel.obtain(),reply=Parcel.obtain();
        try {
            data.writeInterfaceToken(RetainedHostControlProtocol.BROKER); data.writeInt(version);
            data.writeStrongBinder(callback); data.writeString(OfferModel.SHA); data.writeLong(128);
            if(tail)data.writeInt(19);
            yes(broker.transact(1,data,reply,0)); reply.readException(); yes(reply.readInt()==1); reply.enforceNoDataAvail();
        } finally { try { reply.recycle(); } finally { data.recycle(); } }
    }
    public static int run(int scenario) throws Throwable {
        Looper.getMainLooper();
        final RetainedRootHostServiceV2 service = new RetainedRootHostServiceV2();
        final IBinder broker=service.onBind(new Intent()); final Callback callback=new Callback();
        boolean rejected=scenario>=12;
        if(scenario==1)OfferModel.offered=HandoffWire.corrupt(OfferModel.offered,0,'X');
        if(scenario==2)OfferModel.offered=Arrays.copyOf(OfferModel.offered,63);
        if(scenario==3)OfferModel.offered=HandoffWire.offer(0,OfferModel.NAME);
        if(scenario==4)OfferModel.offered=HandoffWire.offer(765,"xxxxxxxxxxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
        if(scenario==5)OfferModel.offered=HandoffWire.corrupt(OfferModel.offered,63,1);
        if(scenario==6)OfferModel.error=new byte[]{1};
        if(scenario==7)OfferModel.spawnFailure=new IOException("authored spawn unknown");
        if(scenario==10)callback.loseReply=true;
        if(scenario==12)Binder.fixtureCaller(10234,321);
        if(scenario==13)Binder.fixtureCaller(1000,0);
        Throwable primary=null;
        try {
            Throwable refusal=null;
            try { begin(broker,callback,scenario==14?1:2,scenario==15); } catch(Throwable failure) { refusal=failure; }
            if(rejected) {
                yes(refusal instanceof SecurityException || refusal instanceof IllegalArgumentException);
                yes(OfferModel.spawns.get()==0 && callback.calls.get()==0);
            } else {
                yes(refusal==null);
                yes(OfferModel.spawned.await(4,TimeUnit.SECONDS));
                if(scenario==8)service.onDestroy();
                if(scenario==6)OfferModel.awaitErrorFailure();
                OfferModel.allowOffer.countDown();
                yes(callback.done.await(4,TimeUnit.SECONDS));
                yes(callback.calls.get()==1);
                boolean good=scenario==0||scenario==9||scenario==10||scenario==11;
                yes(callback.code==(good?1:2));
                if(good)yes(callback.pid==765&&OfferModel.NAME.equals(callback.name));
                if(scenario==9)callback.fixtureDie();
                if(scenario==11||scenario==7||scenario==10) {
                    Throwable duplicate=null;
                    try{begin(broker,callback,2,false);}catch(Throwable failure){duplicate=failure;}
                    yes(duplicate instanceof IllegalStateException); yes(OfferModel.spawns.get()==1);
                }
                if(scenario!=7) {
                    byte[] init=OfferModel.awaitInit();
                    RetainedHostControlProtocol.check(init,1,0,0);
                    yes(RetainedHostControlProtocol.readU32(init,16)==321&&RetainedHostControlProtocol.readU32(init,20)==1000);
                    RetainedHostControlProtocol.zeroTail(init,24);
                }
                service.onDestroy(); callback.fixtureDie();
                yes(OfferModel.destroys.get()==0&&OfferModel.closes.get()==0);
            }
        } catch(Throwable failure){primary=failure;}
        finally {
            service.onDestroy();
            try{OfferModel.cleanup();}catch(Throwable failure){if(primary==null)primary=failure;else if(primary!=failure)primary.addSuppressed(failure);}
        }
        if(primary!=null)throw primary;
        yes(OfferModel.destroys.get()==0);
        // Only actual full-offer + both normal EOFs + modeled wrapper reap may
        // retire the three local stream views. Retirement alone closed none.
        boolean fullOffer=!rejected&&(scenario==0||scenario>=8);
        yes(OfferModel.closes.get()==(fullOffer?3:0));
        yes(Parcel.obtained.get()==Parcel.recycled.get());
        return checks;
    }
}
