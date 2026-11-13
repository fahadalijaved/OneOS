package model;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Scripted peer input and repository-owned ordinary FDs, never a native process/custody issuer. */
public final class NativePeerFixture {
    public static final String NAME=OfferModel.NAME;
    public static final int PID=765;
    public static String mode="normal";
    public static volatile boolean exited;
    public static volatile int connects,commits,pings,closes,socketCloses,rawCloses,dupCloses,procCloses;
    public static final List<Integer> writes=new ArrayList<Integer>();
    public static final Set<Thread> writers=Collections.newSetFromMap(new IdentityHashMap<Thread,Boolean>());
    private static Path data;
    private static final IdentityHashMap<FileDescriptor,Held> fds=new IdentityHashMap<FileDescriptor,Held>();
    private static final Map<Integer,Held> numbers=new HashMap<Integer,Held>();
    private static final List<Thread> threads=new ArrayList<Thread>();
    private static int next=400;
    private static final ArrayDeque<byte[]> frames=new ArrayDeque<byte[]>();
    private static byte[] active;
    private static int position;
    private static boolean ancillaryTaken;
    private static boolean identityRead;
    private static boolean peerEof;
    public static volatile boolean commitReplyConsumed;
    public static volatile Thread commitWriter;
    public static volatile int lostViewReplies;
    private static final List<byte[]> consumedViewFrames=new ArrayList<byte[]>();
    /** Owned copies of full scripted frames actually read; never a production input. */
    public static synchronized byte[][] readViewFrames(){
        byte[][] copy=new byte[consumedViewFrames.size()][];
        for(int n=0;n<copy.length;n++)copy[n]=consumedViewFrames.get(n).clone();
        return copy;
    }
    public static final class Held {
        public final int number;public final FileDescriptor fd;public final String role;
        final FileInputStream input;public byte[] metadata;public int offset;boolean closed;public int attempts;
        Held(int n,FileInputStream input,String role)throws IOException{number=n;this.input=input;fd=input.getFD();this.role=role;}
    }
    public static synchronized void configure(String repo,String directory,String selected)throws Exception {
        if(data!=null)throw new IOException("fresh fixture loader required");
        Path r=Paths.get(repo).toAbsolutePath().normalize(),d=Paths.get(directory).toAbsolutePath().normalize();
        if(!d.startsWith(r.resolve("out"))||!Files.isRegularFile(r.resolve("tools/test_retained_root_handoff.py")))throw new IOException("owned repository output required");
        r=r.toRealPath();data=d.toRealPath();
        if(!data.equals(d)||!data.startsWith(r.resolve("out")))throw new IOException("alias refused");
        mode=selected;
        frames.add(HandoffWire.identity(PID));
        ViewPeerFixture.configure(selected);
    }
    public static synchronized void observe(){if(!threads.contains(Thread.currentThread()))threads.add(Thread.currentThread());}
    public static synchronized Held create(String role)throws IOException {
        if(data==null)throw new IOException("fixture not configured");
        Path path=data.resolve("peer-fd-"+next);
        Files.write(path,new byte[]{1});if(!path.toRealPath().startsWith(data))throw new IOException("fixture escape");
        FileInputStream input=new FileInputStream(path.toFile());Held h=new Held(next++,input,role);fds.put(h.fd,h);numbers.put(h.number,h);return h;
    }
    public static synchronized Held held(FileDescriptor fd)throws IOException {Held h=fds.get(fd);if(h==null||h.closed)throw new IOException("unknown/closed model FD");return h;}
    public static synchronized Held number(int n)throws IOException {Held h=numbers.get(n);if(h==null||h.closed)throw new IOException("unknown model FD number");return h;}
    public static synchronized void close(FileDescriptor fd)throws IOException {
        Held h=held(fd);h.attempts++;
        if(h.role.equals("raw"))rawCloses++;else if(h.role.equals("dup"))dupCloses++;else procCloses++;
        if(mode.equals("close_uncertain")&&h.role.equals("dup"))throw new IOException("authored consumed close uncertainty");
        h.input.close();h.closed=true;
    }
    public static synchronized int live(){int n=0;for(Held h:fds.values())if(!h.closed)n++;return n;}
    public static synchronized FileDescriptor duplicate(FileDescriptor raw)throws IOException {
        held(raw);if(mode.equals("dup_uncertain"))throw new IOException("authored duplicate uncertainty");return create("dup").fd;
    }
    public static synchronized FileDescriptor[] ancillary()throws IOException {
        if(!identityRead||ancillaryTaken)return null;ancillaryTaken=true;
        if(mode.equals("no_rights"))return null;
        if(mode.equals("extra_rights"))return new FileDescriptor[]{create("raw").fd,create("raw").fd};
        return new FileDescriptor[]{create("raw").fd};
    }
    public static synchronized int read(byte[] buffer,int offset,int count)throws IOException {
        observe();long until=System.nanoTime()+TimeUnit.SECONDS.toNanos(4);
        if(mode.equals("partial_identity")&&identityRead)return -1;
        while(active==null&&frames.isEmpty()&&!exited&&!peerEof){
            long left=until-System.nanoTime();if(left<=0)throw new IOException("authored peer response lost");
            try{TimeUnit.NANOSECONDS.timedWait(NativePeerFixture.class,left);}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IOException(e);}
        }
        if(active==null){if(frames.isEmpty())return -1;active=frames.remove();position=0;}
        identityRead=true;
        int length=Math.min(count,active.length-position);if(mode.equals("partial_identity"))length=Math.min(length,7);System.arraycopy(active,position,buffer,offset,length);position+=length;
        if(position==active.length){if((active[7]&255)==9)commitReplyConsumed=true;if((active[7]&255)==11){consumedViewFrames.add(active.clone());if((active[19]&255)==5||(active[19]&255)==6)ViewPeerFixture.terminalRead();}active=null;position=0;}return length;
    }
    public static void write(byte[] frame)throws IOException {
        if(ViewPeerFixture.handle(frame))return;
        writeLegacy(frame);
    }
    private static synchronized void writeLegacy(byte[] frame)throws IOException {
        observe();if(frame.length!=64||frame[0]!='O'||frame[1]!='R'||frame[2]!='S'||frame[3]!='H')throw new IOException("exact host frame expected");
        int kind=frame[7]&255;long seq=((long)(frame[8]&255)<<24)|((long)(frame[9]&255)<<16)|((long)(frame[10]&255)<<8)|(frame[11]&255);
        for(int n=16;n<64;n++)if(frame[n]!=0)throw new IOException("host payload must be zero");
        writes.add(kind);
        writers.add(Thread.currentThread());
        if(kind==8){
            commitWriter=Thread.currentThread();commits++;if(seq!=1)throw new IOException("first commit sequence");
            if(mode.equals("lost_commit")){exited=true;NativePeerFixture.class.notifyAll();return;}
            frames.add(HandoffWire.reply(9,(int)seq,1));
        }else if(kind==4){pings++;frames.add(HandoffWire.reply(5,(int)seq,1));}
        else if(kind==6){closes++;frames.add(HandoffWire.reply(7,(int)seq,2));if(!mode.equals("ack_without_exit"))exited=true;}
        else throw new IOException("only sole host COMMIT/PING/CLOSE allowed");
        NativePeerFixture.class.notifyAll();
    }
    public static synchronized void socketClosed(){socketCloses++;if(!mode.equals("ack_without_exit")&&!ViewPeerFixture.keepAliveOnSocketClose)exited=true;NativePeerFixture.class.notifyAll();}
    public static synchronized void exitForHarnessCleanup(){exited=true;NativePeerFixture.class.notifyAll();}
    public static synchronized void viewFrame(byte[] frame,int kind) throws IOException {
        observe();if(frame.length!=64||frame[0]!='O'||frame[1]!='R'||frame[2]!='S'||frame[3]!='H'||frame[4]!=0||frame[5]!=2||frame[6]!=0||(frame[7]&255)!=kind||frame[12]!=0||frame[13]!=0||frame[14]!=0||frame[15]!=0)throw new IOException("whole v2 request required");
        for(int n=16;n<64;n++)if(frame[n]!=0)throw new IOException("view request payload must be zero");
        writes.add(kind);writers.add(Thread.currentThread());if(kind==6)closes++;
    }
    public static synchronized void enqueueView(byte[] frame){frames.add(frame);NativePeerFixture.class.notifyAll();}
    public static synchronized void lostViewReply(boolean processExited){lostViewReplies++;peerEof=true;exited=processExited;NativePeerFixture.class.notifyAll();}
    public static synchronized int writerCount(){return writers.size();}
    public static void cleanup()throws Throwable {
        synchronized(NativePeerFixture.class){exited=true;NativePeerFixture.class.notifyAll();}
        Throwable primary=null;List<Thread> copy;synchronized(NativePeerFixture.class){copy=new ArrayList<Thread>(threads);}
        for(Thread t:copy)if(t!=Thread.currentThread())try{t.join(4500);if(t.isAlive())throw new AssertionError("observed native-control Java worker remains");}
        catch(Throwable failure){if(primary==null)primary=failure;else if(primary!=failure)primary.addSuppressed(failure);}
        List<Held> handles;synchronized(NativePeerFixture.class){handles=new ArrayList<Held>(fds.values());}
        for(Held h:handles)if(!h.closed)try{h.input.close();h.closed=true;}catch(Throwable failure){if(primary==null)primary=failure;else if(primary!=failure)primary.addSuppressed(failure);}
        if(primary!=null)throw primary;
    }
}
