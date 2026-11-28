package com.appleexploit.oneos.security.transport;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Synthetic opaque packets and recording dependencies only; no OEM/Android code. */
public final class CredentialDispatchTest {
    private static final String PROTOCOL_SHA256 =
            "aa2baaa0b449d5f93a4b796704176659ad54315a082547cb06c39f3acff13d18";
    private static int checks;
    private static int scenarios;

    private interface Action {
        void run() throws Throwable;
    }

    private interface CheckAction {
        void run(int ordinal) throws Throwable;
    }

    private static final class Opaque {
        @Override public String toString() {
            throw new AssertionError("Opaque packet inspected through toString");
        }
        @Override public boolean equals(Object other) {
            throw new AssertionError("Opaque packet compared through equals");
        }
        @Override public int hashCode() {
            throw new AssertionError("Opaque packet hashed");
        }
    }

    /** Records transport behavior; it models no credential or permission policy. */
    private static final class RecordingAuthority implements DispatchAuthority<Opaque> {
        final List<String> events = new ArrayList<String>();
        final IllegalStateException retired = new IllegalStateException("retired marker");
        boolean live = true;
        boolean handled = true;
        boolean nullCall;
        long generation;
        int opens;
        int checks;
        int invokes;
        int closes;
        int guest;
        int source;
        int uid;
        int pid;
        int flags;
        Opaque data;
        Opaque reply;
        Thread openThread;
        Thread invokeThread;
        Thread closeThread;
        Throwable openFailure;
        Throwable checkFailure;
        int failingCheck;
        Throwable invokeFailure;
        Throwable closeFailure;
        Action onOpen;
        CheckAction onCheck;
        Action onInvoke;

        @Override public DispatchCall<Opaque> open(int guestCode, int sourceCode,
                int callerUid, int callerPid, int callFlags) throws Throwable {
            opens++;
            events.add("open");
            guest = guestCode;
            source = sourceCode;
            uid = callerUid;
            pid = callerPid;
            flags = callFlags;
            openThread = Thread.currentThread();
            final long admittedGeneration = generation;
            if (onOpen != null) onOpen.run();
            if (openFailure != null) throw openFailure;
            if (nullCall) return null;
            return new DispatchCall<Opaque>() {
                private int ordinal;
                private boolean closed;

                @Override public void checkLive() throws Throwable {
                    checks++;
                    ordinal++;
                    events.add("check" + ordinal);
                    require(!closed, "check before close");
                    require(Thread.currentThread() == openThread, "check same thread");
                    if (onCheck != null) onCheck.run(ordinal);
                    if (!live || admittedGeneration != generation) throw retired;
                    if (ordinal == failingCheck && checkFailure != null) throw checkFailure;
                }

                @Override public boolean invoke(int sourceCode, Opaque input,
                        Opaque output, int callFlags) throws Throwable {
                    invokes++;
                    events.add("invoke");
                    require(!closed, "invoke before close");
                    require(sourceCode == source, "invoke mapped code");
                    require(callFlags == flags, "invoke exact flags");
                    data = input;
                    reply = output;
                    invokeThread = Thread.currentThread();
                    if (onInvoke != null) onInvoke.run();
                    if (invokeFailure != null) throw invokeFailure;
                    return handled;
                }

                @Override public void close() throws Exception {
                    closes++;
                    events.add("close");
                    require(!closed, "close exactly once per opened call");
                    closed = true;
                    closeThread = Thread.currentThread();
                    if (closeFailure instanceof Exception) throw (Exception) closeFailure;
                    if (closeFailure instanceof Error) throw (Error) closeFailure;
                    if (closeFailure != null) throw new AssertionError("Invalid close fixture", closeFailure);
                }
            };
        }
    }

    private static void require(boolean condition, String name) {
        checks++;
        if (!condition) throw new AssertionError(name);
    }

    private static Throwable failure(Action action) {
        try {
            action.run();
        } catch (Throwable thrown) {
            return thrown;
        }
        throw new AssertionError("Expected failure");
    }

    private static String sha256(byte[] bytes) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
        StringBuilder result = new StringBuilder();
        for (byte value : digest) result.append(String.format("%02x", value & 255));
        return result.toString();
    }

    private static Set<Integer> routeProvenance(Path root) throws Throwable {
        byte[] bytes = Files.readAllBytes(root.resolve("inventory/construction-protocol.json"));
        require(PROTOCOL_SHA256.equals(sha256(bytes)), "frozen reviewed protocol evidence");
        String json = new String(bytes, StandardCharsets.UTF_8);
        int start = json.indexOf("\"operations\":");
        int end = json.indexOf("\"operationCount\":", start);
        require(start >= 0 && end > start, "bounded protocol operations section");
        String operations = json.substring(start, end);
        Pattern operation = Pattern.compile("\"name\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"exactSignature\"");
        Matcher matcher = operation.matcher(operations);
        List<Integer> offsets = new ArrayList<Integer>();
        while (matcher.find()) offsets.add(matcher.start());
        offsets.add(operations.length());
        Pattern guest = Pattern.compile("\"coloros\"\\s*:\\s*\\{\\s*\"transaction\"\\s*:\\s*(\\d+)");
        Pattern source = Pattern.compile("\"samsung\"\\s*:\\s*\\{\\s*\"transaction\"\\s*:\\s*(\\d+)");
        Set<Integer> selected = new HashSet<Integer>();
        Set<Integer> targets = new HashSet<Integer>();
        for (int index = 0; index + 1 < offsets.size(); index++) {
            String row = operations.substring(offsets.get(index), offsets.get(index + 1));
            Matcher from = guest.matcher(row);
            Matcher to = source.matcher(row);
            require(from.find() && to.find(), "both reviewed transaction numbers");
            int guestCode = Integer.parseInt(from.group(1));
            int sourceCode = Integer.parseInt(to.group(1));
            require(selected.add(guestCode), "unique guest route");
            require(targets.add(sourceCode), "unique source route");
            require(CredentialRoutes.sourceCode(guestCode) == sourceCode,
                    "actual reviewed route table provenance");
            RecordingAuthority owner = new RecordingAuthority();
            DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
            Opaque data = new Opaque();
            Opaque reply = new Opaque();
            require(core.handles(guestCode), "selected handles");
            require(core.dispatch(guestCode, data, reply, 32, 1000, 4242), "handled result forwarded");
            require(owner.guest == guestCode && owner.source == sourceCode,
                    "original owner receives both exact codes");
            require(owner.uid == 1000 && owner.pid == 4242 && owner.flags == 32,
                    "original caller metadata forwarded");
            require(owner.data == data && owner.reply == reply, "opaque identity preserved");
            require(owner.opens == 1 && owner.invokes == 1 && owner.checks == 2 && owner.closes == 1,
                    "one direct invocation and bounded lease");
            require(owner.events.toString().equals("[open, check1, invoke, check2, close]"),
                    "exact successful lifetime order");
            require(owner.openThread == Thread.currentThread()
                    && owner.invokeThread == Thread.currentThread()
                    && owner.closeThread == Thread.currentThread(), "same original thread");
            scenarios++;
        }
        require(selected.size() == 33 && CredentialRoutes.ROUTE_COUNT == 33, "exact route count");
        require(json.contains(CredentialRoutes.COLOROS_FRAMEWORK_SHA256)
                && json.contains(CredentialRoutes.SAMSUNG_FRAMEWORK_SHA256)
                && json.contains(CredentialRoutes.COLOROS_SERVICES_SHA256)
                && json.contains(CredentialRoutes.SAMSUNG_SERVICES_SHA256), "fixed original source pins");
        return selected;
    }

    private static void unknownAndValidation(Set<Integer> selected) throws Throwable {
        final RecordingAuthority owner = new RecordingAuthority();
        final DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
        for (int code = -4; code < 130; code++) {
            if (selected.contains(code)) continue;
            require(!core.handles(code), "unknown handles false");
            require(CredentialRoutes.sourceCode(code) == -1, "unknown has no source route");
            require(!core.dispatch(code, null, null, 1, -1, -1), "unknown no packet/owner access");
        }
        for (int code : new int[] {Integer.MIN_VALUE, Integer.MAX_VALUE, 1598968902}) {
            require(!core.dispatch(code, null, null, 1, 0, 0), "unknown boundary/code fallback");
        }
        require(owner.opens == 0, "unknown never opens authority");
        require(failure(() -> new DirectCredentialDispatch<Opaque>(null)) instanceof NullPointerException,
                "no default authority");
        require(failure(() -> core.dispatch(10, null, new Opaque(), 0, 1, 2)) instanceof NullPointerException,
                "selected data required");
        require(failure(() -> core.dispatch(10, new Opaque(), null, 0, 1, 2)) instanceof NullPointerException,
                "selected reply required");
        for (final int flags : new int[] {1, 33, Integer.MIN_VALUE | 1}) {
            require(failure(() -> core.dispatch(10, new Opaque(), new Opaque(), flags, 1, 2))
                    instanceof IllegalArgumentException, "oneway refused");
        }
        require(owner.opens == 0, "packet/flag validation precedes owner");
        scenarios++;
    }

    private static void ordinaryResultsAndFlags() throws Throwable {
        for (int flags : new int[] {0, 32, 0x40000000, Integer.MIN_VALUE | 32}) {
            RecordingAuthority owner = new RecordingAuthority();
            owner.handled = false;
            DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
            require(!core.dispatch(7, new Opaque(), new Opaque(), flags, -7, Integer.MAX_VALUE),
                    "original unhandled result stays false");
            require(owner.flags == flags && owner.uid == -7 && owner.pid == Integer.MAX_VALUE,
                    "all other flags and caller bits unchanged");
            require(owner.checks == 2 && owner.closes == 1, "false still postchecks and closes");
            scenarios++;
        }
    }

    private static void failuresAndClose() throws Throwable {
        final Opaque input = new Opaque();
        final Opaque output = new Opaque();
        final RecordingAuthority denied = new RecordingAuthority();
        final Error opening = new AssertionError("open marker");
        denied.openFailure = opening;
        final DirectCredentialDispatch<Opaque> refused = new DirectCredentialDispatch<Opaque>(denied);
        require(failure(() -> refused.dispatch(10, input, output, 0, 1, 2)) == opening,
                "open failure identity");
        require(denied.closes == 0 && denied.invokes == 0, "failed acquisition has no invented call");
        final RecordingAuthority missing = new RecordingAuthority();
        missing.nullCall = true;
        final DirectCredentialDispatch<Opaque> noCall = new DirectCredentialDispatch<Opaque>(missing);
        require(failure(() -> noCall.dispatch(10, input, output, 0, 1, 2)) instanceof NullPointerException,
                "null call rejected");
        require(missing.invokes == 0 && missing.closes == 0, "null call has no work");
        for (int stage = 1; stage <= 3; stage++) {
            final RecordingAuthority owner = new RecordingAuthority();
            final Error primary = new AssertionError("primary marker");
            final Exception closing = new Exception("close marker");
            owner.closeFailure = closing;
            if (stage == 2) owner.invokeFailure = primary;
            else {
                owner.checkFailure = primary;
                owner.failingCheck = stage == 1 ? 1 : 2;
            }
            final DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
            Throwable thrown = failure(() -> core.dispatch(10, input, output, 0, 1, 2));
            require(thrown == primary, "primary check/invoke Throwable identity");
            require(thrown.getSuppressed().length == 1 && thrown.getSuppressed()[0] == closing,
                    "distinct close failure suppressed under primary");
            require(owner.opens == 1 && owner.closes == 1, "failure closes exactly once, no retry");
            require(owner.invokes == (stage == 1 ? 0 : 1), "failure invocation bound");
            require(owner.checks == (stage == 3 ? 2 : 1), "no successful postcheck after invoke failure");
            scenarios++;
        }
        final RecordingAuthority closingOnly = new RecordingAuthority();
        final Exception closeFailure = new Exception("close-only marker");
        closingOnly.closeFailure = closeFailure;
        final DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(closingOnly);
        require(failure(() -> core.dispatch(10, input, output, 0, 1, 2)) == closeFailure,
                "close failure prevents normal handled publication");
        require(closingOnly.checks == 2 && closingOnly.invokes == 1 && closingOnly.closes == 1,
                "close-only order and bound");
        scenarios++;
        for (int stage = 1; stage <= 3; stage++) {
            final RecordingAuthority owner = new RecordingAuthority();
            final RuntimeException same = new IllegalStateException("same primary/close marker");
            owner.closeFailure = same;
            if (stage == 2) owner.invokeFailure = same;
            else {
                owner.checkFailure = same;
                owner.failingCheck = stage == 1 ? 1 : 2;
            }
            final DirectCredentialDispatch<Opaque> sameCore = new DirectCredentialDispatch<Opaque>(owner);
            require(failure(() -> sameCore.dispatch(10, input, output, 0, 1, 2)) == same,
                    "same-instance close cannot replace primary with self-suppression failure");
            require(same.getSuppressed().length == 0 && owner.closes == 1,
                    "same instance not suppressed onto itself, close once");
            scenarios++;
        }
        final RecordingAuthority closingError = new RecordingAuthority();
        final Error error = new AssertionError("close error marker");
        closingError.closeFailure = error;
        final DirectCredentialDispatch<Opaque> errorCore = new DirectCredentialDispatch<Opaque>(closingError);
        require(failure(() -> errorCore.dispatch(10, input, output, 0, 1, 2)) == error,
                "close Error without primary is preserved");
        scenarios++;
    }

    private static void retirementAndReentry() throws Throwable {
        for (int phase = 0; phase <= 3; phase++) {
            final RecordingAuthority owner = new RecordingAuthority();
            if (phase == 0) owner.live = false;
            if (phase == 1) owner.onOpen = () -> owner.generation++;
            if (phase == 2) owner.onInvoke = () -> owner.generation++;
            if (phase == 3) owner.onCheck = ordinal -> {
                if (ordinal == 2) owner.generation++;
            };
            final DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
            require(failure(() -> core.dispatch(10, new Opaque(), new Opaque(), 0, 1, 2)) == owner.retired,
                    "retired generation cannot publish normal result");
            require(owner.invokes == (phase < 2 ? 0 : 1) && owner.closes == 1,
                    "retirement closes without retry");
            scenarios++;
        }
        final RecordingAuthority owner = new RecordingAuthority();
        final DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
        final boolean[] entered = {false};
        owner.onInvoke = () -> {
            if (!entered[0]) {
                entered[0] = true;
                owner.generation++;
                require(core.dispatch(10, new Opaque(), new Opaque(), 32, 1, 2),
                        "independent nested current-generation handled status");
            }
        };
        require(failure(() -> core.dispatch(10, new Opaque(), new Opaque(), 32, 1, 2)) == owner.retired,
                "outer retired call rejected after nested reentry");
        require(owner.opens == 2 && owner.invokes == 2 && owner.closes == 2,
                "nested leases each close once, no retry");
        scenarios++;
    }

    private static void workerThreadAndNoPacketFields() throws Throwable {
        final RecordingAuthority owner = new RecordingAuthority();
        final DirectCredentialDispatch<Opaque> core = new DirectCredentialDispatch<Opaque>(owner);
        final Throwable[] failure = {null};
        Thread worker = new Thread(() -> {
            try {
                require(core.dispatch(15, new Opaque(), new Opaque(), 32, 1, 2), "worker handled");
            } catch (Throwable thrown) {
                failure[0] = thrown;
            }
        }, "authored-transport-test");
        worker.start();
        worker.join();
        if (failure[0] != null) throw failure[0];
        require(owner.openThread == worker && owner.invokeThread == worker && owner.closeThread == worker,
                "no main-thread hop or executor");
        int instanceFields = 0;
        for (Field field : DirectCredentialDispatch.class.getDeclaredFields()) {
            if (Modifier.isStatic(field.getModifiers())) continue;
            instanceFields++;
            require(field.getType() == DispatchAuthority.class && Modifier.isFinal(field.getModifiers()),
                    "only supplied authority retained by core");
        }
        require(instanceFields == 1, "no opaque packet fields");
        scenarios++;
    }

    public static void main(String[] args) throws Throwable {
        Path root = args.length == 0 ? Paths.get(".") : Paths.get(args[0]);
        Set<Integer> selected = routeProvenance(root);
        unknownAndValidation(selected);
        ordinaryResultsAndFlags();
        failuresAndClose();
        retirementAndReentry();
        workerThreadAndNoPacketFields();
        System.out.println("{\"pass\":true,\"status\":\"PASS\",\"checks\":" + checks
                + ",\"scenarios\":" + scenarios + ",\"routeCount\":" + selected.size()
                + ",\"protocolSha256\":\"" + PROTOCOL_SHA256
                + "\",\"oemExecuted\":false,\"androidExecuted\":false}");
    }
}
