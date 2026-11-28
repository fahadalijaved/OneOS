package model;
import java.io.*;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Pure Java child/pipe boundary. No command, process, native socket or pidfd runs. */
public final class OfferModel {
    public static final String NAME = "oneos.orh.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    public static final String SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    public static volatile byte[] offered = HandoffWire.offer(765, NAME);
    public static volatile byte[] error = new byte[0];
    public static volatile IOException spawnFailure;
    public static volatile Thread errorReader;
    public static final AtomicInteger spawns = new AtomicInteger(), destroys = new AtomicInteger(), closes = new AtomicInteger();
    public static final CountDownLatch spawned = new CountDownLatch(1), allowOffer = new CountDownLatch(1), finish = new CountDownLatch(1);
    private static final List<Thread> observed = new ArrayList<Thread>();
    public static final ByteArrayOutputStream init = new ByteArrayOutputStream();
    public static void observe() { synchronized (observed) { if (!observed.contains(Thread.currentThread())) observed.add(Thread.currentThread()); } }
    public static void allowOffer(){allowOffer.countDown();}
    public static Process spawn(String sha, long bytes) throws IOException {
        observe();
        if (!SHA.equals(sha) || bytes != 128) throw new AssertionError("unchanged fixed spawn arguments required");
        spawns.incrementAndGet(); spawned.countDown();
        if (spawnFailure != null) throw spawnFailure;
        return new Child();
    }
    private static final class Child extends Process {
        private final InputStream out = new InputStream() {
            private int position;
            @Override public int read() throws IOException {
                observe(); await(allowOffer);
                byte[] bytes = offered;
                return position < bytes.length ? bytes[position++] & 255 : -1;
            }
            @Override public int read(byte[] bytes, int offset, int count) throws IOException {
                observe(); await(allowOffer);
                if (position == offered.length) return -1;
                int length = Math.min(count, offered.length - position);
                System.arraycopy(offered, position, bytes, offset, length); position += length; return length;
            }
            @Override public void close() { closes.incrementAndGet(); }
        };
        private final InputStream err = new ByteArrayInputStream(error) {
            @Override public synchronized int read(byte[] b, int o, int n) { observe(); errorReader=Thread.currentThread(); return super.read(b,o,n); }
            @Override public void close() { closes.incrementAndGet(); }
        };
        private final OutputStream in = new OutputStream() {
            @Override public void write(int value) { synchronized (init) { init.write(value); } }
            @Override public void write(byte[] bytes, int off, int len) { synchronized (init) { init.write(bytes,off,len); } }
            @Override public void close() { closes.incrementAndGet(); }
        };
        public OutputStream getOutputStream() { return in; }
        public InputStream getInputStream() { return out; }
        public InputStream getErrorStream() { return err; }
        public int waitFor() throws InterruptedException { observe(); finish.await(); return 0; }
        public int exitValue() { if (finish.getCount() != 0) throw new IllegalThreadStateException(); return 0; }
        public void destroy() { destroys.incrementAndGet(); }
        public Process destroyForcibly() { destroys.incrementAndGet(); return this; }
    }
    private static void await(CountDownLatch latch) throws IOException {
        try { if (!latch.await(4, TimeUnit.SECONDS)) throw new IOException("authored pipe barrier timed out"); }
        catch (InterruptedException failure) { Thread.currentThread().interrupt(); throw new IOException(failure); }
    }
    public static void awaitErrorFailure() throws Exception {
        long until=System.nanoTime()+TimeUnit.SECONDS.toNanos(4);
        while(errorReader==null&&System.nanoTime()<until)Thread.sleep(1);
        if(errorReader==null)throw new AssertionError("error reader did not run");
        errorReader.join(4000);
        if(errorReader.isAlive())throw new AssertionError("error failure did not finish before offer release");
    }
    public static byte[] awaitInit() throws Exception {
        long until=System.nanoTime()+TimeUnit.SECONDS.toNanos(4);
        while(System.nanoTime()<until){synchronized(init){if(init.size()==64)return init.toByteArray();}Thread.sleep(1);}
        throw new AssertionError("actual launch did not write complete captured-caller INIT");
    }
    public static void cleanup() throws Throwable {
        allowOffer.countDown(); finish.countDown();
        Throwable primary = null;
        // A retained actual launcher can acquire pumps after the first snapshot.
        for (int pass=0; pass<3; pass++) {
            List<Thread> copy; synchronized (observed) { copy = new ArrayList<Thread>(observed); }
            for (Thread thread : copy) if (thread != Thread.currentThread()) try {
                thread.join(4500); if (thread.isAlive()) throw new AssertionError("observed app launch worker remains");
            } catch (Throwable failure) { if (primary == null) primary = failure; else if (primary != failure) primary.addSuppressed(failure); }
        }
        if (primary != null) throw primary;
    }
}
