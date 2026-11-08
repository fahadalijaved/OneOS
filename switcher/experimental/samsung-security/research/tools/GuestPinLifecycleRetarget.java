import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import com.android.tools.smali.dexlib2.AccessFlags;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Field;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.*;
import com.android.tools.smali.dexlib2.immutable.instruction.*;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;

/** Emits one unselected DEX for static readback. The original APK is read-only. */
final class GuestPinLifecycleRetarget {
    private static final String PACKAGE = "Lcom/oplus/keyguard/security/";
    private static final String CHECKER = PACKAGE + "OplusLockPatternChecker;";
    private static final String CONTROLLER = PACKAGE + "view/OplusKeyguardAbsKeyInputViewController;";
    private static final String SLOT = PACKAGE + "GuestPinCheckRequest$Slot;";
    private static final String VIEW = "Landroid/view/View;";
    private static final String OBJECT = "Ljava/lang/Object;";
    private static final String SLOT_NAME = "oneos$pinSlot";
    private static final String ENTRY = "oneos$retirePinAtLifecycleEntry";
    private static final String FORWARD = "oneos$retirePinForController";
    private static final String PAUSE = CONTROLLER + "->onPause()V";
    private static final String SUBMIT = CONTROLLER + "->verifyPasswordAndUnlock()V";
    private static final String ORIGINAL_SHA = "793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071";
    private static final String HELPER_SHA = "2a22b567f46f7b6d3beee281f0c99f52de4359e1debd23773f5cf89752a81e4f";
    private static final Set<String> HELPER_TYPES = Set.of(
            PACKAGE + "GuestPinCheckRequest;", PACKAGE + "GuestPinCheckRequest$1;", SLOT,
            PACKAGE + "PinCheckCompletion;", PACKAGE + "PinCheckCompletion$FinalKind;",
            PACKAGE + "PinCheckCompletion$Retirement;");

    private static final ImmutableMethodReference ENTRY_REF =
            new ImmutableMethodReference(CONTROLLER, ENTRY, List.of(CONTROLLER), "V");
    private static final ImmutableMethodReference FORWARD_REF =
            new ImmutableMethodReference(CHECKER, FORWARD, List.of(CONTROLLER), "V");
    private static final ImmutableMethodReference GET_CHECKER = new ImmutableMethodReference(
            PACKAGE + "view/OplusKeyguardInputViewController;", "getChecker", List.of(), CHECKER);
    private static final ImmutableFieldReference SLOT_REF = new ImmutableFieldReference(CHECKER, SLOT_NAME, SLOT);
    private static final ImmutableFieldReference VIEW_REF = new ImmutableFieldReference(
            "Lcom/android/systemui/util/ViewController;", "mView", VIEW);
    private static final ImmutableFieldReference MONITOR_REF = new ImmutableFieldReference(
            CHECKER, "keyguardUpdateMonitor", "Lcom/android/keyguard/KeyguardUpdateMonitor;");
    private static final ImmutableMethodReference RETIRE = new ImmutableMethodReference(
            SLOT, "retireAtOriginalLifecycleEntry", List.of(OBJECT, OBJECT, VIEW, OBJECT), "Z");

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }

    private static ImmutableMethod addedMethod(String owner, String name, int flags,
            int registers, List<? extends Instruction> instructions) {
        return new ImmutableMethod(owner, name,
                List.of(new ImmutableMethodParameter(CONTROLLER, Set.of(), null)), "V", flags,
                Set.of(), Set.of(), new ImmutableMethodImplementation(registers, instructions, List.of(), List.of()));
    }

    private static ImmutableMethod controllerEntry() {
        // The controller is already initialized. A missing checker returns without
        // forcing the checker's original Companion initializer to run early.
        return addedMethod(CONTROLLER, ENTRY, AccessFlags.PRIVATE.getValue() | AccessFlags.STATIC.getValue(),
                2, List.of(
                        new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 1, 1, 0, 0, 0, 0, GET_CHECKER),
                        new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 0),
                        new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 5),
                        new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 2, 0, 1, 0, 0, 0, FORWARD_REF),
                        new ImmutableInstruction10x(Opcode.RETURN_VOID)));
    }

    private static ImmutableMethod checkerForward() {
        // v3 is the checker and v4 the original controller. Only a present Slot
        // permits reading the held tuple. Its local retirement has no UI authority.
        return addedMethod(CHECKER, FORWARD, AccessFlags.PUBLIC.getValue() | AccessFlags.FINAL.getValue(),
                5, List.of(
                        new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 3, SLOT_REF),
                        new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 9),
                        new ImmutableInstruction22c(Opcode.IGET_OBJECT, 1, 4, VIEW_REF),
                        new ImmutableInstruction22c(Opcode.IGET_OBJECT, 2, 3, MONITOR_REF),
                        new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 5, 0, 3, 4, 1, 2, RETIRE),
                        new ImmutableInstruction10x(Opcode.RETURN_VOID)));
    }
    private static String key(Method method) {
        return method.getDefiningClass() + "->" + SecurityDexReader.signature(method);
    }

    private static Method changeCall(Method method, boolean undo) {
        String key = key(method);
        if (!PAUSE.equals(key) && !SUBMIT.equals(key)) return method;
        boolean pause = PAUSE.equals(key);
        int cut = pause ? 0 : 5;
        int receiver = pause ? 1 : 4;
        int expectedUnits = (pause ? 21 : 33) + (undo ? 3 : 0);
        var body = method.getImplementation();
        require(body != null && body.getRegisterCount() == receiver + 1
                && body.getTryBlocks().isEmpty() && !body.getDebugItems().iterator().hasNext(),
                "Pinned lifecycle frame differs: " + key);

        // The existing submit edge must reach the inserted invoke at PC 5.
        var hook = new ImmutableInstruction35c(Opcode.INVOKE_STATIC, 1, receiver, 0, 0, 0, 0, ENTRY_REF);
        List<Instruction> code = new ArrayList<>();
        int pc = 0;
        boolean found = false;
        for (Instruction instruction : body.getInstructions()) {
            if (pc == cut) {
                found = true;
                if (undo) {
                    require(SecurityDexReader.instruction(instruction, pc).equals(SecurityDexReader.instruction(hook, pc)),
                            "Inserted call differs: " + key);
                    pc += instruction.getCodeUnits();
                    continue;
                }
                require(instruction.getOpcode() == (pause ? Opcode.INVOKE_SUPER : Opcode.IGET_OBJECT),
                        "Pinned lifecycle cut differs: " + key);
                code.add(hook);
            }
            code.add(instruction);
            pc += instruction.getCodeUnits();
        }
        require(found && pc == expectedUnits, "Pinned lifecycle extent differs: " + key);
        return new ImmutableMethod(method.getDefiningClass(), method.getName(), method.getParameters(),
                method.getReturnType(), method.getAccessFlags(), method.getAnnotations(),
                method.getHiddenApiRestrictions(), new ImmutableMethodImplementation(
                        body.getRegisterCount(), code, body.getTryBlocks(), body.getDebugItems()));
    }
    private static List<ClassDef> overlay(Collection<? extends ClassDef> classes, boolean undo) {
        List<ClassDef> result = new ArrayList<>();
        int controllers = 0;
        int checkers = 0;
        int cuts = 0;
        for (ClassDef definition : classes) {
            String type = definition.getType();
            if (undo && HELPER_TYPES.contains(type)) continue;
            boolean controller = CONTROLLER.equals(type);
            boolean checker = CHECKER.equals(type);
            if (!controller && !checker) {
                result.add(definition);
                continue;
            }
            if (controller) controllers++;
            if (checker) checkers++;
            List<Field> fields = new ArrayList<>();
            for (Field field : definition.getFields()) {
                if (!field.getName().equals(SLOT_NAME)) fields.add(field);
                else require(undo && checker && field.getType().equals(SLOT), "Slot field collision");
            }
            List<Method> methods = new ArrayList<>();
            for (Method method : definition.getMethods()) {
                if (method.getName().equals(ENTRY) || method.getName().equals(FORWARD)) {
                    require(undo && method.equals(controller ? ENTRY_REF : FORWARD_REF), "Lifecycle method collision");
                    continue;
                }
                Method edited = changeCall(method, undo);
                if (edited != method) cuts++;
                methods.add(edited);
            }
            if (!undo) {
                if (checker) fields.add(new ImmutableField(CHECKER, SLOT_NAME, SLOT,
                        AccessFlags.PRIVATE.getValue(), null, Set.of(), Set.of()));
                methods.add(controller ? controllerEntry() : checkerForward());
            }
            result.add(new ImmutableClassDef(type, definition.getAccessFlags(), definition.getSuperclass(),
                    definition.getInterfaces(), definition.getSourceFile(), definition.getAnnotations(), fields, methods));
        }
        require(controllers == 1 && checkers == 1 && cuts == 2, "Exact original owners and two call sites required");
        return result;
    }

    private static byte[] pinned(Path path, int length, String sha) throws Exception {
        require(Files.size(path) == length, "Pinned DEX size differs");
        byte[] bytes = Files.readAllBytes(path);
        require(bytes.length == length && SecurityDexReader.sha(bytes).equals(sha), "Pinned DEX digest differs");
        ProbeSamsungDex041.validate(bytes);
        return bytes;
    }
    public static void main(String[] args) throws Exception {
        require(args.length == 3, "Expected original DEX, staged helper DEX and exclusive output");
        byte[] originalBytes = pinned(Path.of(args[0]), 10_177_500, ORIGINAL_SHA);
        byte[] helperBytes = pinned(Path.of(args[1]), 12_444, HELPER_SHA);
        var original = new DexBackedDexFile(Opcodes.forApi(29), originalBytes);
        var helper = new DexBackedDexFile(Opcodes.forApi(29), helperBytes);
        require(original.getClasses().size() == 6737 && helper.getClasses().stream().map(ClassDef::getType)
                .collect(Collectors.toSet()).equals(HELPER_TYPES), "Pinned class definitions differ");

        var classes = overlay(original.getClasses(), false);
        classes.addAll(helper.getClasses());
        var expected = ProbeSamsungDex041.normalize(classes);
        SourcePreservingDexPool pool = new SourcePreservingDexPool();
        GuestPolicyInitRetarget.seed(pool, original, originalBytes);
        GuestPolicyInitRetarget.seed(pool, helper, helperBytes);
        for (ClassDef definition : classes) pool.internClass(definition);
        require(!pool.hasOverflowed(), "16-bit reference pool overflow");
        byte[] output;
        MemoryDataStore store = new MemoryDataStore();
        try {
            pool.writeTo(store);
            output = store.getData();
        } finally {
            store.close();
        }
        ProbeSamsungDex041.validate(output);
        var decoded = new DexBackedDexFile(Opcodes.forApi(29), output);
        require(decoded.getClasses().size() == 6743, "Decoded class definition count differs");
        ProbeSamsungDex041.same(expected, ProbeSamsungDex041.normalize(decoded.getClasses()));
        expected.clear();
        var originalRows = ProbeSamsungDex041.normalize(original.getClasses());
        ProbeSamsungDex041.same(originalRows, ProbeSamsungDex041.normalize(overlay(decoded.getClasses(), true)));

        Files.write(Path.of(args[2]), output, StandardOpenOption.CREATE_NEW);
        System.out.println("{\"normalizedOriginalRecords\":" + originalRows.size()
                + ",\"originalDefinitions\":6737,\"addedDefinitions\":6,\"changedOriginalMethods\":2"
                + ",\"addedMethods\":2,\"addedFields\":1,\"semanticInverse\":true,\"outputSha256\":"
                + SecurityDexReader.q(SecurityDexReader.sha(output)) + "}");
    }
}
