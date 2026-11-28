package model;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.concurrent.*;

/** Scripted wire input only. No actual GVI, mount, authority or process custody. */
public final class ViewPeerFixture {
    public static final long NAMESPACE=0xfedcba9876543210L, DATA=0x8000000000000001L, MIRROR=0xffffffffffffffffL;
    public static volatile boolean keepAliveOnSocketClose;
    public static volatile int prepares,queries,terminalQueries,closeQueries;
    public static final CountDownLatch prepareEntered=new CountDownLatch(1),prepareRelease=new CountDownLatch(1);
    private static String mode;
    private static boolean attempted,draining,observed;
    private static long lastSequence=1;
    public static void configure(String selected){
        mode=selected;
        keepAliveOnSocketClose=selected.equals("view_lost_prepare")||selected.equals("view_lost_close")
                ||selected.equals("view_changed")||selected.equals("view_regression")
                ||selected.equals("view_bad_observed")||selected.equals("view_unobserved_values")||selected.equals("view_reserved");
    }
    public static void releasePrepare(){prepareRelease.countDown();}
    private static long sequence(byte[] frame){return ByteBuffer.wrap(frame).order(ByteOrder.BIG_ENDIAN).getInt(8)&0xffffffffL;}
    private static byte[] state(long seq,int value,boolean obs){
        byte[] bytes=HandoffWire.reply(11,(int)seq,1);ByteBuffer b=ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN);
        b.putInt(16,value).putInt(20,obs?1:0);
        if(obs)b.putLong(24,NAMESPACE).putLong(32,DATA).putLong(40,MIRROR);
        return bytes;
    }
    public static boolean handle(byte[] frame)throws IOException{
        if(frame.length!=64)throw new IOException("whole frame required");int kind=frame[7]&255;
        if(kind!=10&&kind!=12&&!(kind==6&&attempted))return false;
        long seq=sequence(frame);
        synchronized(ViewPeerFixture.class){if(seq<=lastSequence)throw new IOException("single increasing view sequence");lastSequence=seq;}
        NativePeerFixture.viewFrame(frame,kind);
        if(kind==10){
            synchronized(ViewPeerFixture.class){if(attempted)throw new IOException("peer refuses second prepare");attempted=true;prepares++;}
            prepareEntered.countDown();
            if(mode.equals("view_block"))try{if(!prepareRelease.await(4,TimeUnit.SECONDS))throw new IOException("authored GVI barrier timeout");}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IOException(e);}
            if(mode.equals("view_lost_prepare")){keepAliveOnSocketClose=true;NativePeerFixture.lostViewReply(false);return true;}
            int result=mode.equals("view_stage")?2:mode.equals("view_refused")?3:1;
            observed=result==1;
            byte[] response=state(seq,result,observed);
            if(mode.equals("view_unobserved_values"))response=state(seq,2,true);
            if(mode.equals("view_bad_observed"))ByteBuffer.wrap(response).putInt(20,2);
            if(mode.equals("view_reserved"))response[63]=1;
            if(mode.equals("view_unobserved_values")){ByteBuffer.wrap(response).putInt(20,0);keepAliveOnSocketClose=true;}
            if(mode.equals("view_bad_observed")||mode.equals("view_reserved"))keepAliveOnSocketClose=true;
            if(result>=2)draining=true;
            NativePeerFixture.enqueueView(response);return true;
        }
        if(kind==6){
            draining=true;
            if(mode.equals("view_lost_close")){keepAliveOnSocketClose=true;NativePeerFixture.lostViewReply(false);return true;}
            NativePeerFixture.enqueueView(state(seq,4,observed));return true;
        }
        queries++;
        if(!draining){
            byte[] response=state(seq,attempted?1:0,observed);
            if(mode.equals("view_changed")&&observed)ByteBuffer.wrap(response).putLong(24,NAMESPACE+1);
            NativePeerFixture.enqueueView(response);return true;
        }
        closeQueries++;
        if(mode.equals("view_lost_terminal")){terminalQueries++;NativePeerFixture.lostViewReply(true);return true;}
        if(mode.equals("view_regression")){NativePeerFixture.enqueueView(state(seq,1,observed));keepAliveOnSocketClose=true;return true;}
        terminalQueries++;
        int terminal=observed?5:6;
        NativePeerFixture.enqueueView(state(seq,terminal,observed));
        // Exit is supplied after the terminal frame is actually read, not before
        // the host's pre-send pidfd liveness check.
        return true;
    }
    public static void terminalRead(){if(terminalQueries>0&&!mode.equals("view_lost_terminal"))NativePeerFixture.exited=true;}
}
