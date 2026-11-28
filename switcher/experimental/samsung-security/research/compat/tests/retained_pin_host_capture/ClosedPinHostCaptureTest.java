package com.appleexploit.oneos.security.authority;

/** Inert lifecycle fixture. These stand-ins never enter the Android cohort. */
public final class ClosedPinHostCaptureTest {
    private static int checks;

    public static void main(String[] args) throws InterruptedException {
        RetainedClosedPinHostCapture prepared = new RetainedClosedPinHostCapture();
        PreparedRetainedPinOperationOwner base = new PreparedRetainedPinOperationOwner();
        expect(prepare(prepared, base) == base && PreparedRetainedPinCheckOwner.last.base == base &&
                PreparedRetainedPinEndpoint.last.check == PreparedRetainedPinCheckOwner.last,
                "one exact base through both constructors");
        refused(() -> prepare(prepared, new PreparedRetainedPinOperationOwner()));
        offThread(prepared::retire);
        expect(base.closed && PreparedRetainedPinCheckOwner.last.closed && PreparedRetainedPinEndpoint.last.closed,
                "off-main retirement closes all three");
        refused(() -> prepare(prepared, base));

        RetainedClosedPinHostCapture retired = new RetainedClosedPinHostCapture();
        retired.retire();
        PreparedRetainedPinOperationOwner unowned = new PreparedRetainedPinOperationOwner();
        refused(() -> prepare(retired, unowned));
        expect(!unowned.closed, "refused source never becomes owned");

        RetainedClosedPinHostCapture duringBase = new RetainedClosedPinHostCapture();
        PreparedRetainedPinOperationOwner delayed = new PreparedRetainedPinOperationOwner();
        PreparedRetainedPinCheckOwner previousCheck = PreparedRetainedPinCheckOwner.last;
        PreparedRetainedPinOperationOwner.duringPrepare = () -> offThread(duringBase::retire);
        refused(() -> prepare(duringBase, delayed));
        PreparedRetainedPinOperationOwner.duringPrepare = null;
        expect(delayed.closed && PreparedRetainedPinCheckOwner.last == previousCheck,
                "late base retained and closed before check");

        RetainedClosedPinHostCapture early = new RetainedClosedPinHostCapture();
        PreparedRetainedPinOperationOwner earlyBase = new PreparedRetainedPinOperationOwner();
        PreparedRetainedPinEndpoint before = PreparedRetainedPinEndpoint.last;
        PreparedRetainedPinCheckOwner.duringPrepare = () -> offThread(early::retire);
        refused(() -> prepare(early, earlyBase));
        PreparedRetainedPinCheckOwner.duringPrepare = null;
        expect(earlyBase.closed && PreparedRetainedPinCheckOwner.last.closed &&
                PreparedRetainedPinEndpoint.last == before, "late check retained and closed before endpoint");

        RetainedClosedPinHostCapture late = new RetainedClosedPinHostCapture();
        PreparedRetainedPinOperationOwner lateBase = new PreparedRetainedPinOperationOwner();
        PreparedRetainedPinEndpoint.duringPrepare = () -> offThread(late::retire);
        refused(() -> prepare(late, lateBase));
        PreparedRetainedPinEndpoint.duringPrepare = null;
        expect(lateBase.closed && PreparedRetainedPinCheckOwner.last.closed && PreparedRetainedPinEndpoint.last.closed,
                "late endpoint retained and closed");
        refused(() -> prepare(late, lateBase));

        RetainedClosedPinHostCapture failed = new RetainedClosedPinHostCapture();
        PreparedRetainedPinOperationOwner failedBase = new PreparedRetainedPinOperationOwner();
        IllegalArgumentException original = new IllegalArgumentException("fixture failure");
        PreparedRetainedPinEndpoint.duringPrepare = () -> { throw original; };
        try {
            prepare(failed, failedBase);
            throw new AssertionError("constructor exception expected");
        } catch (IllegalArgumentException error) {
            expect(error == original, "original failure propagates");
        }
        PreparedRetainedPinEndpoint.duringPrepare = null;
        expect(failedBase.closed && PreparedRetainedPinCheckOwner.last.closed, "partial preparation is closed");
        refused(() -> prepare(failed, failedBase));
        System.out.println("PASS " + checks + " closed PIN host lifecycle checks");
    }

    private static PreparedRetainedPinOperationOwner prepare(RetainedClosedPinHostCapture capture,
                                                             PreparedRetainedPinOperationOwner base) {
        return capture.prepare(new PreparedRetainedPinBinding(base));
    }

    private static void offThread(Runnable action) {
        Thread worker = new Thread(action);
        worker.setDaemon(true);
        worker.start();
        try { worker.join(2000); }
        catch (InterruptedException error) { throw new AssertionError(error); }
        if (worker.isAlive()) throw new AssertionError("retirement blocked by construction");
    }

    private static void refused(Runnable action) {
        try { action.run(); }
        catch (IllegalStateException expected) { checks++; return; }
        throw new AssertionError("retired or duplicate construction was admitted");
    }

    private static void expect(boolean value, String message) {
        if (!value) throw new AssertionError(message);
        checks++;
    }
}

final class PreparedRetainedPinBinding {
    final PreparedRetainedPinOperationOwner owner;
    PreparedRetainedPinBinding(PreparedRetainedPinOperationOwner owner) { this.owner = owner; }
}

final class PreparedRetainedPinOperationOwner {
    static Runnable duringPrepare;
    boolean closed;
    static PreparedRetainedPinOperationOwner prepare(PreparedRetainedPinBinding binding) {
        if (duringPrepare != null) duringPrepare.run();
        return binding.owner;
    }
    void closeAdapterIngress() { closed = true; }
}

final class PreparedRetainedPinCheckOwner {
    static PreparedRetainedPinCheckOwner last;
    static Runnable duringPrepare;
    final PreparedRetainedPinOperationOwner base;
    boolean closed;
    private PreparedRetainedPinCheckOwner(PreparedRetainedPinOperationOwner base) { this.base = base; }
    static PreparedRetainedPinCheckOwner prepare(PreparedRetainedPinOperationOwner base) {
        last = new PreparedRetainedPinCheckOwner(base);
        if (duringPrepare != null) duringPrepare.run();
        return last;
    }
    void closeAdapterIngress() { closed = true; }
}

final class PreparedRetainedPinEndpoint {
    static PreparedRetainedPinEndpoint last;
    static Runnable duringPrepare;
    final PreparedRetainedPinCheckOwner check;
    boolean closed;
    private PreparedRetainedPinEndpoint(PreparedRetainedPinCheckOwner check) { this.check = check; }
    static PreparedRetainedPinEndpoint prepareWithCheck(PreparedRetainedPinOperationOwner base,
                                                        PreparedRetainedPinCheckOwner check) {
        if (check.base != base) throw new AssertionError("base replaced");
        if (duringPrepare != null) duringPrepare.run();
        last = new PreparedRetainedPinEndpoint(check);
        return last;
    }
    void closeIngress() { closed = true; }
}
