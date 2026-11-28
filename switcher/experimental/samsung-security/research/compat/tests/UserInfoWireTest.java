package com.appleexploit.oneos.security.userinfo;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

/** Independent synthetic operation-tape oracle; not an Android Parcel emulator. */
public final class UserInfoWireTest {
    private static int checks;
    private static final String[] NAMES = {"id", "name", "iconPath", "flags", "userType",
        "serialNumber", "creationTime", "lastLoggedInTime", "lastLoggedInFingerprint",
        "partial", "preCreated", "profileGroupId", "guestToRemove",
        "restrictedProfileParentId", "profileBadge", "attributes"};
    private static final String[] KINDS = {"I", "S8", "S8", "I", "S8", "I", "J", "J",
        "S8", "B", "B", "I", "B", "I", "I", "I"};

    private interface Action { void run(); }
    private static void require(boolean ok) {
        checks++;
        if (!ok) { throw new AssertionError("Synthetic wire check failed"); }
    }
    private static void rejected(Class<? extends Throwable> type, Action action) {
        try { action.run(); } catch (Throwable failure) {
            require(type.isInstance(failure));
            return;
        }
        throw new AssertionError("Expected synthetic rejection");
    }

    private static final class Cell {
        final String kind;
        final Object value;
        Cell(String kind, Object value) { this.kind = kind; this.value = value; }
    }
    private static final class Tape implements UserInfoWire.Packet {
        final List<Cell> cells = new ArrayList<Cell>();
        int cursor;
        int operations;
        int failAt = -1;
        RuntimeException failure;
        private void step() {
            if (operations++ == failAt) { throw failure; }
        }
        Object take(String kind) {
            step();
            if (cursor == cells.size() || !cells.get(cursor).kind.equals(kind)) {
                throw new IllegalStateException("Synthetic operation underflow or mismatch");
            }
            return cells.get(cursor++).value;
        }
        void add(String kind, Object value) { step(); cells.add(new Cell(kind, value)); }
        public int readInt() { return (Integer) take("I"); }
        public long readLong() { return (Long) take("J"); }
        public String readString8() { return (String) take("S8"); }
        public boolean readBoolean() { return (Boolean) take("B"); }
        public void writeInt(int v) { add("I", v); }
        public void writeLong(long v) { add("J", v); }
        public void writeString8(String v) { add("S8", v); }
        public void writeBoolean(boolean v) { add("B", v); }
    }

    private static Object[] values(int seed, int attributes) {
        return new Object[] {seed, "name-" + seed, "icon-" + seed, 0x86000400 ^ seed,
            "type-" + seed, seed + 113, Long.MIN_VALUE + seed, Long.MAX_VALUE - seed,
            "fp-\u0000-\u6f22-\ud83e\udd8a-" + seed, seed % 2 == 0, seed % 3 == 0,
            seed + 227, seed % 5 == 0, seed + 331, seed + 449, attributes};
    }

    // The literal schema above comes from the frozen source inventory, not production code.
    private static void sourceObject(Tape tape, Object[] values) {
        tape.add("I", values == null ? 0 : 1);
        if (values != null) {
            for (int i = 0; i < 16; i++) { tape.add(KINDS[i], values[i]); }
        }
    }
    private static Tape sourceList(Object[]... values) {
        Tape tape = new Tape();
        tape.add("I", values.length);
        for (Object[] value : values) { sourceObject(tape, value); }
        return tape;
    }
    private static Object[] guestOracle(Tape tape) {
        int presence = (Integer) tape.take("I");
        if (presence == 0) { return null; }
        if (presence != 1) { throw new IllegalArgumentException("Oracle presence"); }
        Object[] value = new Object[15];
        for (int i = 0; i < 15; i++) { value[i] = tape.take(KINDS[i]); }
        return value;
    }
    private static List<Object[]> guestListOracle(Tape tape) {
        int count = (Integer) tape.take("I");
        if (count == -1) { return null; }
        if (count < 0 || count > 1024) { throw new IllegalArgumentException("Oracle count"); }
        List<Object[]> result = new ArrayList<Object[]>();
        for (int i = 0; i < count; i++) { result.add(guestOracle(tape)); }
        return result;
    }
    private static void recordEquals(UserInfoWire.SourceRecord record, Object[] expected)
            throws Exception {
        if (expected == null) { require(record == null); return; }
        require(record != null);
        for (int i = 0; i < 16; i++) {
            require(java.util.Objects.equals(UserInfoWire.SourceRecord.class.getField(NAMES[i]).get(record), expected[i]));
        }
    }
    private static void guestEquals(Object[] actual, Object[] source) {
        if (source == null) { require(actual == null); return; }
        require(actual != null && actual.length == 15);
        for (int i = 0; i < 15; i++) { require(java.util.Objects.equals(actual[i], source[i])); }
    }

    private static void exactRecords() throws Exception {
        Random random = new Random(0x16a015L);
        for (int i = 0; i < 64; i++) {
            Object[] value = values(i + 11, random.nextInt());
            value[3] = random.nextInt();
            value[6] = random.nextLong();
            value[7] = random.nextLong();
            if (i % 2 == 0) { value[1] = null; }
            if (i % 3 == 0) { value[2] = null; }
            if (i % 5 == 0) { value[4] = null; }
            if (i % 7 == 0) { value[8] = null; }
            Tape input = new Tape(); sourceObject(input, value); input.add("I", 0x12345678);
            Tape guest = new Tape();
            UserInfoWire.SourceRecord record = UserInfoWire.convertObject(input, guest);
            recordEquals(record, value);
            require(input.take("I").equals(0x12345678)); // exact source cursor, no overread
            guestEquals(guestOracle(guest), value);
            require(guest.cursor == guest.cells.size());
            require(record.attributes == (Integer) value[15]);
        }
        Tape input = new Tape(); sourceObject(input, null); Tape guest = new Tape();
        require(UserInfoWire.convertObject(input, guest) == null);
        require(guestOracle(guest) == null && guest.cells.size() == 1);
    }

    private static void listsAndMisalignment() throws Exception {
        Object[] a = values(41, 28), b = values(73, 0x80000004);
        Tape source = sourceList(a, b), guest = new Tape();
        UserInfoWire.SourceList records = UserInfoWire.convertList(source, guest, 2);
        require(records.size() == 2);
        recordEquals(records.get(0), a); recordEquals(records.get(1), b);
        List<Object[]> output = guestListOracle(guest);
        guestEquals(output.get(0), a); guestEquals(output.get(1), b);
        require(guest.cursor == guest.cells.size() && source.cursor == source.cells.size());
        final Tape naive = sourceList(a, b);
        rejected(IllegalArgumentException.class, new Action() { public void run() { guestListOracle(naive); } });
        Tape mixed = sourceList(a, null, b); Tape mixedGuest = new Tape();
        UserInfoWire.SourceList mixedRecords = UserInfoWire.convertList(mixed, mixedGuest, 3);
        require(mixedRecords.get(1) == null);
        List<Object[]> mixedOutput = guestListOracle(mixedGuest);
        guestEquals(mixedOutput.get(0), a); guestEquals(mixedOutput.get(1), null); guestEquals(mixedOutput.get(2), b);
        Tape empty = sourceList(); Tape emptyGuest = new Tape();
        require(UserInfoWire.convertList(empty, emptyGuest, 0).size() == 0);
        require(guestListOracle(emptyGuest).isEmpty());
        Tape absent = new Tape(); absent.add("I", -1); Tape absentGuest = new Tape();
        require(UserInfoWire.convertList(absent, absentGuest, 0) == null);
        require(guestListOracle(absentGuest) == null);
        final Tape tooSmallGuest = new Tape();
        final UserInfoWire.SourceList retained = records;
        rejected(IllegalArgumentException.class, new Action() { public void run() { UserInfoWire.writeGuestList(tooSmallGuest, retained, 1); } });
        require(tooSmallGuest.cells.isEmpty());
        Tape large = new Tape(); large.add("I", 1024);
        for (int i = 0; i < 1024; i++) { sourceObject(large, null); }
        require(UserInfoWire.readSourceList(large, 1024).size() == 1024);
    }

    private static void malformedAndFailure() {
        final Tape sameObject = new Tape(); sourceObject(sameObject, values(12, 31));
        final int beforeObject = sameObject.operations;
        rejected(IllegalArgumentException.class, new Action() { public void run() { UserInfoWire.convertObject(sameObject, sameObject); } });
        require(sameObject.operations == beforeObject && sameObject.cursor == 0);
        final Tape sameList = sourceList(values(13, 32));
        final int beforeList = sameList.operations;
        rejected(IllegalArgumentException.class, new Action() { public void run() { UserInfoWire.convertList(sameList, sameList, 1); } });
        require(sameList.operations == beforeList && sameList.cursor == 0);
        for (int n : new int[] {-2, Integer.MIN_VALUE, 3, 1025}) {
            final Tape source = new Tape(); source.add("I", n); final Tape guest = new Tape();
            rejected(IllegalArgumentException.class, new Action() { public void run() { UserInfoWire.convertList(source, guest, 2); } });
            require(source.cursor == 1 && guest.cells.isEmpty());
        }
        for (int n : new int[] {-1, 2, Integer.MAX_VALUE}) {
            final Tape source = new Tape(); source.add("I", n);
            rejected(IllegalArgumentException.class, new Action() { public void run() { UserInfoWire.readSourceObject(source); } });
            require(source.cursor == 1);
        }
        for (final int bound : new int[] {-1, 1025, Integer.MAX_VALUE}) {
            final Tape source = new Tape();
            rejected(IllegalArgumentException.class, new Action() { public void run() { UserInfoWire.readSourceList(source, bound); } });
            require(source.operations == 0);
        }
        final Tape truncated = new Tape(); sourceObject(truncated, values(7, 19));
        truncated.cells.remove(truncated.cells.size()-1); final Tape untouched = new Tape();
        rejected(IllegalStateException.class, new Action() { public void run() { UserInfoWire.convertObject(truncated, untouched); } });
        require(untouched.cells.isEmpty()); // no attributes=0/default success
        final Tape badType = new Tape(); sourceObject(badType, values(8, 1));
        badType.cells.set(7, new Cell("I", 123));
        rejected(IllegalStateException.class, new Action() { public void run() { UserInfoWire.readSourceObject(badType); } });
        rejected(NullPointerException.class, new Action() { public void run() { UserInfoWire.readSourceObject(null); } });
        final RuntimeException original = new RuntimeException("synthetic failure");
        Tape failureInput = new Tape(); sourceObject(failureInput, values(9, 3));
        failureInput.operations = 0; failureInput.failAt = 6; failureInput.failure = original;
        try { UserInfoWire.readSourceObject(failureInput); throw new AssertionError(); }
        catch (RuntimeException actual) { require(actual == original); }
        Tape full = new Tape(); sourceObject(full, values(10, 7));
        Tape failingGuest = new Tape(); failingGuest.failAt = 5; failingGuest.failure = original;
        try { UserInfoWire.convertObject(full, failingGuest); throw new AssertionError(); }
        catch (RuntimeException actual) { require(actual == original); }
        require(failingGuest.cells.size() == 5); // partial unpublished output must be discarded
    }

    private static void immutableAndLossy() throws Exception {
        require(UserInfoWire.SourceRecord.class.getDeclaredFields().length == 16);
        for (Field field : UserInfoWire.SourceRecord.class.getDeclaredFields()) {
            require(Modifier.isFinal(field.getModifiers()) && !Modifier.isStatic(field.getModifiers()));
            require(field.getType().isPrimitive() || field.getType() == String.class);
        }
        Field listStorage = UserInfoWire.SourceList.class.getDeclaredField("records");
        require(Modifier.isPrivate(listStorage.getModifiers()) && Modifier.isFinal(listStorage.getModifiers()));
        Tape a = new Tape(), b = new Tape(); sourceObject(a, values(19, 0)); sourceObject(b, values(19, 28));
        Tape guestA = new Tape(), guestB = new Tape();
        UserInfoWire.SourceRecord first = UserInfoWire.convertObject(a, guestA);
        UserInfoWire.SourceRecord second = UserInfoWire.convertObject(b, guestB);
        require(first.attributes == 0 && second.attributes == 28);
        require(Arrays.equals(guestOracle(guestA), guestOracle(guestB)));
        guestA.cursor = 0;
        final Tape lossy = guestA;
        rejected(IllegalStateException.class, new Action() { public void run() { UserInfoWire.readSourceObject(lossy); } });
    }

    public static void main(String[] args) throws Exception {
        exactRecords(); listsAndMisalignment(); malformedAndFailure(); immutableAndLossy();
        System.out.println("{\"pass\":true,\"checks\":" + checks
                + ",\"syntheticOnly\":true,\"androidExecuted\":false,\"oemExecuted\":false}");
    }
}
