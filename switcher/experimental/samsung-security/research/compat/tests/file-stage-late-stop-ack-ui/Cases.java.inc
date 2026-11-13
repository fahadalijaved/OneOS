    static Operation readyWithLostStopReply() {
        Operation op = fresh(true);
        host.commit();
        tick = host::drainMain;
        pump();
        check(sends == 1 && stops == 0 && op.canStop(), "One ready Prepare before Stop");
        loseStop = true;
        op.stop();
        op.stop();
        pump();
        check(stops == 1 && context.unbinds == 0 && !op.terminal()
                && op.message().contains("Stop acknowledgment unconfirmed."), "One Stop with a lost reply");
        return op;
    }

    static void terminalDoesNotReplay(Operation op, int expectedStops) {
        int reads = statusReads;
        op.stop();
        op.refresh();
        pump();
        check(sends == 1 && stops == expectedStops && context.unbinds == 1 && statusReads == reads,
                "A terminal observation releases once and does not send, read or retry");
    }

    static void lateAckAtLocalTerminal() {
        Operation op = readyWithLostStopReply();
        host.sample = RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL;
        lateStopAck = true;
        op.refresh();
        worker();
        check(op.message().contains("Stop acknowledgment unconfirmed.") && context.unbinds == 0,
                "Worker read cannot change the main-thread footer before delivery");
        mainLane();
        check(op.message().startsWith("Local terminal observed. Cleanup still pending.")
                && op.message().contains("Stop request acknowledged.") && !op.terminal()
                && op.canRefresh() && context.unbinds == 0 && stops == 1,
                "Late ack updates footer at status 6 without promoting cleanup or replaying Stop");

        lateStopAck = false;
        host.sample = RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
        op.refresh();
        pump();
        check(op.terminal() && context.unbinds == 1 && op.message().startsWith("Local cleanup observed.")
                && op.message().contains("Stop request acknowledged."), "Later sample cannot erase the observed ack");
        terminalDoesNotReplay(op, 1);
    }

    static void lateAckAtCleanup() {
        Operation op = readyWithLostStopReply();
        host.sample = RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
        lateStopAck = true;
        context.onUnbind = () -> check(op.message().contains("Stop request acknowledged."),
                "Same-sample Stop footer is updated before terminal unbind");
        op.refresh();
        pump();
        check(op.terminal() && context.unbinds == 1 && op.message().startsWith("Local cleanup observed."),
                "Ack and cleanup settle together without a retry");
        terminalDoesNotReplay(op, 1);
    }

    static void cleanupWithoutAck() {
        Operation op = readyWithLostStopReply();
        host.sample = RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
        op.refresh();
        pump();
        check(op.terminal() && context.unbinds == 1 && op.message().startsWith("Local cleanup observed.")
                && op.message().contains("Stop acknowledgment unconfirmed.")
                && !op.message().contains("Stop request acknowledged."),
                "Status 7 alone does not imply Stop acceptance");
        terminalDoesNotReplay(op, 1);
    }

    static void ackWithoutRequestedStop() {
        Operation op = fresh(true);
        host.commit();
        tick = host::drainMain;
        pump();
        lateStopAck = true;
        host.sample = RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED;
        op.refresh();
        pump();
        check(op.terminal() && context.unbinds == 1 && !op.message().contains("Stop request acknowledged."),
                "An ack observation cannot add a Stop footer without an actual local Stop request");
        terminalDoesNotReplay(op, 0);
    }
