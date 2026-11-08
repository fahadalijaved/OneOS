package model;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Public fixture observations only. No process, kernel pidfd or host /proc exists. */
public final class SessionModel {
    private static Path repository,data;
    public static int callerPid,callerUid,nativePid;
    public static int scenario,spawns,polls,reaps,rawCloses,dupCloses,procCloses,socketCloses;
    public static int stdinCloses,stdoutCloses,stderrCloses,controlInCloses,controlOutCloses;
    public static int wrapperFdCloses;
    public static volatile Thread workerObserved;
    public static boolean initCorrect,commandCorrect,retainedBeforeSpawn;
    public static volatile boolean nativeExited,wrapperExited,forceEof,allowStderr=true;
    public static volatile boolean closeSent,holdPoll;
    public static volatile boolean lateError;
    public static Runnable spawnHook,peerHook;
    public static final IOException exact=new IOException("authored root fixture failure");
    public static final CountDownLatch pollEntered=new CountDownLatch(1),reapEntered=new CountDownLatch(1);
    public static final List<Thread> observedThreads=new ArrayList<Thread>();
    private static final IdentityHashMap<FileDescriptor,Handle> handles=new IdentityHashMap<FileDescriptor,Handle>();
    private static final Map<Integer,Handle> numbers=new HashMap<Integer,Handle>();
    private static int next=100;
    public static ModelProcess process;
    public static ModelSocket socket;
    public static final class Handle {
        public final FileInputStream input;public final FileDescriptor fd;public final int number;public final String role;
        public byte[] bytes;public int offset,attempts;public boolean closed,delivered;
        Handle(FileInputStream input,FileDescriptor fd,int number,String role){this.input=input;this.fd=fd;this.number=number;this.role=role;}
    }
    public static void configure(String repo,String directory,int selected)throws IOException {
        if(repository!=null)throw new IOException("fresh fixture loader required");
        Path r=Paths.get(repo).toAbsolutePath().normalize(),d=Paths.get(directory).toAbsolutePath().normalize();
        if(!d.startsWith(r.resolve("out")) || !Files.isRegularFile(r.resolve("tools/test_retained_root_session.py")))
            throw new IOException("repository-only model directory required");
        repository=r.toRealPath();data=d.toRealPath();
        if(!data.equals(d) || !data.startsWith(repository.resolve("out")))throw new IOException("fixture alias refused");
        scenario=selected;callerPid=1234+selected*7;callerUid=10234+selected;nativePid=2345+selected*11;
    }
    public static synchronized Handle create(String role)throws IOException {
        if(data==null)throw new IOException("unconfigured fixture");
        int number=next++;Path path=data.resolve("fd-"+number);Files.write(path,new byte[]{1});
        if(!path.toRealPath().startsWith(data))throw new IOException("fixture escaped");
        FileInputStream input=new FileInputStream(path.toFile());FileDescriptor fd=input.getFD();
        Handle h=new Handle(input,fd,number,role);handles.put(fd,h);numbers.put(number,h);return h;
    }
    public static synchronized Handle handle(FileDescriptor fd)throws IOException {
        Handle h=handles.get(fd);if(h==null || h.closed)throw new IOException("unknown/closed modeled descriptor");return h;
    }
    public static synchronized Handle number(int value)throws IOException {
        Handle h=numbers.get(value);if(h==null || h.closed)throw new IOException("unowned modeled descriptor number");return h;
    }
    public static synchronized void closeFd(FileDescriptor fd)throws IOException {
        Handle h=handles.get(fd);if(h==null)throw new IOException("foreign modeled descriptor");h.attempts++;
        if(h.closed)throw new IOException("modeled descriptor closed twice");
        if(h.role.equals("raw"))rawCloses++;else if(h.role.equals("dup"))dupCloses++;else procCloses++;
        if(scenario==17 && h.role.equals("raw") && h.number==100)throw exact;
        if(scenario==16 && h.role.equals("dup"))throw exact;
        h.input.close();h.closed=true;
    }
    public static synchronized int live(){int n=0;for(Handle h:handles.values())if(!h.closed)n++;return n;}
    public static synchronized int rawCount(){int n=0;for(Handle h:handles.values())if(h.role.equals("raw"))n++;return n;}
    public static synchronized boolean rawAllAttempted(){for(Handle h:handles.values())if(h.role.equals("raw") && h.attempts!=1)return false;return true;}
    public static synchronized int deliveredRaw(){int n=0;for(Handle h:handles.values())if(h.role.equals("raw") && h.delivered)n++;return n;}
    public static synchronized boolean deliveredRawAttempted(){for(Handle h:handles.values())if(h.role.equals("raw") && h.delivered && h.attempts!=1)return false;return true;}
    public static synchronized void delivered(FileDescriptor[] values)throws IOException {if(values!=null)for(FileDescriptor fd:values)handle(fd).delivered=true;}
    public static synchronized void recordThread(){Thread t=Thread.currentThread();if(!observedThreads.contains(t))observedThreads.add(t);}
    public static void fakeExit(boolean nativeExit,boolean wrapperExit) {
        nativeExited=nativeExit;wrapperExited=wrapperExit;
        if(process!=null)process.wake();
    }
    public static void cleanup()throws Throwable {
        forceEof=true;allowStderr=true;nativeExited=true;wrapperExited=true;holdPoll=false;
        if(process!=null)process.wake();if(socket!=null)socket.input.end();
        Throwable primary=null;
        List<Thread> threads;
        synchronized(SessionModel.class){threads=new ArrayList<Thread>(observedThreads);}
        for(Thread thread:threads)if(thread!=Thread.currentThread())try {
            thread.join(4000);if(thread.isAlive())throw new AssertionError("modeled API caller thread remained live");
        }catch(Throwable failure){if(primary==null)primary=failure;else primary.addSuppressed(failure);}
        synchronized(SessionModel.class){for(Handle h:handles.values())try{h.input.close();h.closed=true;}
        catch(Throwable failure){if(primary==null)primary=failure;else primary.addSuppressed(failure);}}
        if(primary!=null)throw primary;
    }

    public static final class ModelProcess extends java.lang.Process {
        public final Gate stdout=new Gate(true),stderr=new Gate(false);
        public final ByteArrayOutputStream init=new ByteArrayOutputStream();
        private final OutputStream stdin=new OutputStream(){
            public void write(int value)throws IOException {init.write(value);}
            public void write(byte[] bytes,int offset,int count)throws IOException {init.write(bytes,offset,count);}
            public void flush()throws IOException {initCorrect=SessionWire.sourceInit(init.toByteArray());if(!initCorrect)throw exact;}
            public void close(){stdinCloses++;}
        };
        public OutputStream getOutputStream(){return stdin;}
        public InputStream getInputStream(){if(scenario==18)throw new IllegalStateException("authored partial setup");return stdout;}
        public InputStream getErrorStream(){return stderr;}
        public int waitFor()throws InterruptedException {return waitFor(1,TimeUnit.SECONDS)?0:1;}
        public boolean waitFor(long timeout,TimeUnit unit) {
            reaps++;reapEntered.countDown();
            if(!closeSent){forceEof=true;wrapperExited=true;wake();}
            return wrapperExited;
        }
        public int exitValue(){if(!wrapperExited)throw new IllegalThreadStateException();return 0;}
        public void destroy(){throw new AssertionError("no real process termination model");}
        public boolean isAlive(){return !wrapperExited;}
        public void wake(){stdout.wake();stderr.wake();}
    }
    public static final class Gate extends InputStream {
        private final boolean offer;private int position;private boolean closed;
        Gate(boolean offer){this.offer=offer;}
        public synchronized void wake(){notifyAll();}
        public int read()throws IOException {byte[] one=new byte[1];int n=read(one,0,1);return n<0?-1:one[0]&255;}
        public synchronized int read(byte[] bytes,int offset,int count)throws IOException {
            recordThread();
            if(closed)return -1;
            if(offer && position<64) {
                byte[] value=SessionWire.offer();if(scenario==3)value[0]='X';
                int n=Math.min(count,Math.min(13,64-position));System.arraycopy(value,position,bytes,offset,n);position+=n;return n;
            }
            while(!closed && !forceEof && (!nativeExited || (!offer && !allowStderr)) && !(!offer && lateError)) {
                try {wait(100);}catch(InterruptedException failure){Thread.currentThread().interrupt();throw new IOException(failure);}
            }
            if(!offer && lateError)throw exact;
            return -1;
        }
        public synchronized void close()throws IOException {if(offer)stdoutCloses++;else stderrCloses++;closed=true;notifyAll();}
    }
    public static final class Entry {
        final byte[] bytes;final FileDescriptor[] rights;int offset;
        Entry(byte[] bytes,FileDescriptor[] rights){this.bytes=bytes;this.rights=rights;}
    }
    public static final class QueueInput extends InputStream {
        private final BlockingQueue<Entry> entries=new LinkedBlockingQueue<Entry>();
        private Entry current;private boolean ended;
        public FileDescriptor[] ancillary;
        void add(byte[] bytes,FileDescriptor[] rights){entries.add(new Entry(bytes,rights));}
        public void end(){ended=true;entries.add(new Entry(new byte[0],null));}
        public int read()throws IOException {byte[] one=new byte[1];int n=read(one,0,1);return n<0?-1:one[0]&255;}
        public int read(byte[] bytes,int offset,int count)throws IOException {
            if(current==null || current.offset==current.bytes.length) {
                try{current=entries.poll(2,TimeUnit.SECONDS);}catch(InterruptedException failure){throw new IOException(failure);}
                if(current==null)throw new IOException("authored missing reply");
                ancillary=current.rights;
                if(scenario==17 && current.rights!=null)throw exact;
            }
            if(current.bytes.length==0 || ended)return -1;
            int n=Math.min(count,Math.min(11,current.bytes.length-current.offset));
            System.arraycopy(current.bytes,current.offset,bytes,offset,n);current.offset+=n;return n;
        }
        public void close(){controlInCloses++;end();}
    }
    public static final class ModelSocket {
        public final QueueInput input=new QueueInput();private final ByteArrayOutputStream partial=new ByteArrayOutputStream();
        public final OutputStream output=new OutputStream(){
            public void write(int value)throws IOException {partial.write(value);dispatch();}
            public void write(byte[] bytes,int offset,int count)throws IOException {partial.write(bytes,offset,count);dispatch();}
            public void close(){controlOutCloses++;}
            private void dispatch()throws IOException {
                if(partial.size()<64)return;if(partial.size()!=64)throw new IOException("authored request length");
                byte[] request=partial.toByteArray();partial.reset();int kind=SessionWire.kind(request),seq=SessionWire.sequence(request);
                if(kind==4) {
                    byte[] pong=SessionWire.frame(5,seq,1);
                    FileDescriptor[] rights=scenario==15?new FileDescriptor[]{create("raw").fd}:null;
                    input.add(pong,rights);
                } else if(kind==6) {
                    closeSent=true;input.add(SessionWire.frame(7,scenario==21?seq+1:seq,2),null);
                    nativeExited=scenario!=12;wrapperExited=scenario!=13;
                    if(scenario==12 || scenario==13 || scenario==22)forceEof=true;
                    if(process!=null)process.wake();
                } else throw new IOException("unexpected authored control kind");
            }
        };
        public ModelSocket()throws IOException {
            int count=scenario==23?0:scenario==7 || scenario==17?3:1;FileDescriptor[] rights=count==0?null:new FileDescriptor[count];
            for(int n=0;n<count;n++)rights[n]=create("raw").fd;
            byte[] identity=SessionWire.identity();if(scenario==6)identity[19]++;
            if(scenario==7 || scenario==17)identity[63]=1;
            input.add(identity,rights);
        }
        public void close(){socketCloses++;input.end();}
    }
}
