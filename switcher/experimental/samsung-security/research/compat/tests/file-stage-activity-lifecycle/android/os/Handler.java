package android.os;

import java.util.Comparator;
import java.util.Objects;
import java.util.PriorityQueue;

/** Shared main queue. Posting from a worker never runs callbacks on that worker. */
public final class Handler {
    private static final PriorityQueue<Post> queue = new PriorityQueue<>(
            Comparator.comparingLong((Post item) -> item.due)
                    .thenComparingLong(item -> item.sequence));
    private static long nextSequence;

    private static final class Post {
        final Handler handler;
        final Runnable task;
        final long due;
        final long sequence;

        Post(Handler handler, Runnable task, long due, long sequence) {
            this.handler = handler;
            this.task = task;
            this.due = due;
            this.sequence = sequence;
        }
    }

    public Handler(Looper looper) {
        if (looper != Looper.getMainLooper()) throw new IllegalArgumentException("Expected main looper");
    }

    public boolean post(Runnable task) { return postDelayed(task, 0); }

    public boolean postDelayed(Runnable task, long delayMillis) {
        Objects.requireNonNull(task);
        synchronized (queue) {
            long due = SystemClock.elapsedRealtime() + Math.max(0, delayMillis);
            queue.add(new Post(this, task, due, nextSequence++));
        }
        return true;
    }

    public void removeCallbacks(Runnable task) {
        synchronized (queue) {
            queue.removeIf(item -> item.handler == this && item.task == task);
        }
    }

    public static boolean runNextForTest() {
        if (Looper.myLooper() != Looper.getMainLooper()) {
            throw new IllegalStateException("Main queue must be pumped by the fixture main thread");
        }
        Post item;
        synchronized (queue) {
            item = queue.peek();
            if (item == null || item.due > SystemClock.elapsedRealtime()) return false;
            queue.remove();
        }
        item.task.run();
        return true;
    }

    public static void runReadyForTest() {
        while (runNextForTest()) {
            // Continue until no callback is currently due.
        }
    }
}
