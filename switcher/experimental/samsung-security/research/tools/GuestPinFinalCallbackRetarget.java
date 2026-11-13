import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Field;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableField;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21t;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction22c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction3rc;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;

/** Writes the disabled final-callback edge, with its checked helper kept in a separate DEX. */
final class GuestPinFinalCallbackRetarget {
    private static final String PACKAGE = "Lcom/oplus/keyguard/security/";
    private static final String TASK = PACKAGE + "OplusLockPatternChecker$oplusCheckCredential$task$1;";
    private static final String CALLBACK = PACKAGE + "OplusLockPatternChecker$OplusOnCheckCallback;";
    private static final String REQUEST = PACKAGE + "GuestPinCheckRequest;";
    private static final String HELPER = PACKAGE + "GuestPinFinalCallbackBridge;";
    private static final String ASYNC_TASK = "Landroid/os/AsyncTask;";
    private static final String RESPONSE = "Lcom/android/internal/widget/VerifyCredentialResponse;";
    private static final String FINAL = "onPostExecute(Ljava/lang/Object;)V";
    private static final String FIELD = "oneos$pinRequest";
    private static final String BRIDGE = "oneos$forwardOriginalFinal";
    private static final int FIELD_FLAGS = 0x1042; // private, volatile, synthetic
    private static final int CALL_PC = 61;
    private static final String ORIGINAL_SHA = "793b3239aaaff2272bc912c67396ced50bd3077e30f8ab511e830389754e5071";
    private static final int ORIGINAL_BYTES = 10_177_500;
    private static final int ORIGINAL_CLASSES = 6737;
    private static final Set<String> HELPER_TYPES = Set.of(
            REQUEST, PACKAGE + "GuestPinCheckRequest$1;", PACKAGE + "GuestPinCheckRequest$EntryState;",
            PACKAGE + "GuestPinCheckRequest$PostState;", PACKAGE + "GuestPinCheckRequest$ProgressEntry;",
            PACKAGE + "GuestPinCheckRequest$ProgressPost;", PACKAGE + "GuestPinCheckRequest$Slot;",
            PACKAGE + "GuestPinCheckRequest$TerminalDelivery;", PACKAGE + "GuestPinCheckRequest$TerminalState;",
            PACKAGE + "GuestPinCheckRequest$WorkerExit;", PACKAGE + "GuestPinCheckRequest$WorkerExitKind;",
            PACKAGE + "GuestPinSourceOccurrence;", PACKAGE + "GuestPinSourceOccurrence$1;",
            PACKAGE + "GuestPinSourceOccurrence$Owner;", PACKAGE + "GuestPinSourceOccurrence$Readback;",
            PACKAGE + "GuestPinSourceOccurrence$Transition;", PACKAGE + "PinCheckCompletion;",
            PACKAGE + "PinCheckCompletion$FinalKind;", PACKAGE + "PinCheckCompletion$Retirement;", HELPER);
    private static final List<String> FORWARD_ARGS = List.of(CALLBACK, RESPONSE, "I", "Z");
    private static final ImmutableFieldReference REQUEST_FIELD = new ImmutableFieldReference(TASK, FIELD, REQUEST);
    private static final ImmutableMethodReference BRIDGE_METHOD =
            new ImmutableMethodReference(TASK, BRIDGE, FORWARD_ARGS, "V");
    private static final ImmutableMethodReference ORIGINAL_CALLBACK =
            new ImmutableMethodReference(CALLBACK, "onChecked", List.of(RESPONSE, "I", "Z"), "V");
    private static final ImmutableMethodReference HELPER_FORWARD = new ImmutableMethodReference(
            HELPER, "forwardOriginal", List.of(REQUEST, ASYNC_TASK, CALLBACK, RESPONSE, "I", "Z"), "V");

    private GuestPinFinalCallbackRetarget() {}

    private static ImmutableMethod newBridge() {
        var parameters = FORWARD_ARGS.stream().map(type -> new ImmutableMethodParameter(type, Set.of(), null)).toList();
        // v0 is a single field read, v1 is the exact task, and v2..v5 are the original call arguments.
        return new ImmutableMethod(TASK, BRIDGE, parameters, "V", 0x02, Set.of(), Set.of(),
                new ImmutableMethodImplementation(6, List.of(
                        new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 1, REQUEST_FIELD),
                        new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 6),
                        new ImmutableInstruction3rc(Opcode.INVOKE_STATIC_RANGE, 0, 6, HELPER_FORWARD),
                        new ImmutableInstruction10x(Opcode.RETURN_VOID),
                        new ImmutableInstruction35c(Opcode.INVOKE_INTERFACE, 4, 2, 3, 4, 5, 0, ORIGINAL_CALLBACK),
                        new ImmutableInstruction10x(Opcode.RETURN_VOID)), List.of(), List.of()));
    }

    private static Method editCall(Method method, boolean inverse) {
        var body = method.getImplementation();
        require(method.getAccessFlags() == 0x11 && body != null && body.getRegisterCount() == 8
                && body.getTryBlocks().isEmpty() && !body.getDebugItems().iterator().hasNext(),
                "Unexpected final callback method frame");
        var stock = new ImmutableInstruction35c(Opcode.INVOKE_INTERFACE, 4, 1, 7, 3, 2, 0, ORIGINAL_CALLBACK);
        var forward = new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 5, 6, 1, 7, 3, 2, BRIDGE_METHOD);
        List<Instruction> code = new ArrayList<>();
        int pc = 0;
        boolean found = false;
        for (Instruction instruction : body.getInstructions()) {
            if (pc == CALL_PC) {
                require(SecurityDexReader.instruction(instruction, pc).equals(
                        SecurityDexReader.instruction(inverse ? forward : stock, pc)),
                        "Unexpected final callback instruction or arguments");
                instruction = inverse ? stock : forward;
                found = true;
            }
            code.add(instruction);
            pc += instruction.getCodeUnits();
        }
        require(found && pc == 73, "Unexpected final callback method extent");
        return new ImmutableMethod(TASK, method.getName(), method.getParameters(), method.getReturnType(),
                method.getAccessFlags(), method.getAnnotations(), method.getHiddenApiRestrictions(),
                new ImmutableMethodImplementation(body.getRegisterCount(), code, body.getTryBlocks(), body.getDebugItems()));
    }

    private static List<ClassDef> overlay(Collection<? extends ClassDef> classes, boolean inverse) {
        List<ClassDef> result = new ArrayList<>();
        int tasks = 0;
        int cuts = 0;
        for (ClassDef definition : classes) {
            require(!HELPER_TYPES.contains(definition.getType()), "Helper definition collides with donor DEX");
            if (!TASK.equals(definition.getType())) {
                result.add(definition);
                continue;
            }
            require(definition.getAccessFlags() == 0x11 && ASYNC_TASK.equals(definition.getSuperclass()),
                    "Unexpected exact task class");
            tasks++;
            List<Field> fields = new ArrayList<>();
            int removedField = 0;
            for (Field field : definition.getFields()) {
                if (FIELD.equals(field.getName())) {
                    require(inverse && REQUEST_FIELD.equals(field) && field.getAccessFlags() == FIELD_FLAGS,
                            "Added request field collides or differs");
                    removedField++;
                } else {
                    fields.add(field);
                }
            }
            List<Method> methods = new ArrayList<>();
            int removedBridge = 0;
            for (Method method : definition.getMethods()) {
                if (BRIDGE.equals(method.getName())) {
                    require(inverse && BRIDGE_METHOD.equals(method) && method.getAccessFlags() == 0x02,
                            "Added final bridge collides or differs");
                    removedBridge++;
                } else if (FINAL.equals(SecurityDexReader.signature(method))) {
                    methods.add(editCall(method, inverse));
                    cuts++;
                } else {
                    methods.add(method);
                }
            }
            require(removedField == (inverse ? 1 : 0) && removedBridge == (inverse ? 1 : 0),
                    "Unexpected added field or bridge count");
            if (!inverse) {
                fields.add(new ImmutableField(TASK, FIELD, REQUEST, FIELD_FLAGS, null, Set.of(), Set.of()));
                methods.add(newBridge());
            }
            result.add(new ImmutableClassDef(TASK, definition.getAccessFlags(), definition.getSuperclass(),
                    definition.getInterfaces(), definition.getSourceFile(), definition.getAnnotations(), fields, methods));
        }
        require(tasks == 1 && cuts == 1, "Expected one task and one changed call");
        return result;
    }

    private static byte[] pinned(Path path, int maximum, String sha) throws Exception {
        require(sha.matches("[a-f0-9]{64}"), "Exact lower-case SHA-256 required");
        byte[] bytes;
        try (InputStream stream = Files.newInputStream(path)) {
            bytes = stream.readNBytes(maximum + 1);
        }
        require(bytes.length <= maximum && SecurityDexReader.sha(bytes).equals(sha), "Pinned DEX digest differs");
        ProbeSamsungDex041.validate(bytes);
        return bytes;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 4, "Expected original DEX, helper DEX, helper SHA-256, and exclusive output");
        byte[] originalBytes = pinned(Path.of(args[0]), ORIGINAL_BYTES, ORIGINAL_SHA);
        byte[] helperBytes = pinned(Path.of(args[1]), 2 * 1024 * 1024, args[2]);
        var original = new DexBackedDexFile(Opcodes.forApi(29), originalBytes);
        var helper = new DexBackedDexFile(Opcodes.forApi(29), helperBytes);
        require(originalBytes.length == ORIGINAL_BYTES && original.getClasses().size() == ORIGINAL_CLASSES
                && helper.getClasses().size() == HELPER_TYPES.size() && helper.getClasses().stream()
                .map(ClassDef::getType).collect(Collectors.toSet()).equals(HELPER_TYPES),
                "Unexpected original or helper definition closure");
        var helperClass = helper.getClasses().stream().filter(type -> HELPER.equals(type.getType())).findFirst().orElseThrow();
        int helperEntries = 0;
        for (Method method : helperClass.getDirectMethods()) {
            if (HELPER_FORWARD.equals(method) && method.getAccessFlags() == 0x08 && method.getImplementation() != null) {
                helperEntries++;
            }
        }
        require(helperEntries == 1, "Expected exact implemented package-static final callback helper");

        var classes = overlay(original.getClasses(), false);
        var expected = ProbeSamsungDex041.normalize(classes);
        SourcePreservingDexPool pool = new SourcePreservingDexPool();
        GuestPolicyInitRetarget.seed(pool, original, originalBytes);
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
        require(decoded.getClasses().size() == ORIGINAL_CLASSES, "Unexpected decoded donor class count");
        ProbeSamsungDex041.same(expected, ProbeSamsungDex041.normalize(decoded.getClasses()));
        expected.clear();
        var originalRows = ProbeSamsungDex041.normalize(original.getClasses());
        ProbeSamsungDex041.same(originalRows, ProbeSamsungDex041.normalize(overlay(decoded.getClasses(), true)));

        Files.write(Path.of(args[3]), output, StandardOpenOption.CREATE_NEW);
        System.out.println("{\"normalizedOriginalRecords\":" + originalRows.size()
                + ",\"originalDefinitions\":" + ORIGINAL_CLASSES + ",\"addedDefinitions\":0"
                + ",\"externalHelperDefinitions\":" + HELPER_TYPES.size()
                + ",\"changedOriginalMethods\":1,\"addedMethods\":1,\"addedFields\":1,\"semanticInverse\":true"
                + ",\"outputSha256\":" + SecurityDexReader.q(SecurityDexReader.sha(output)) + "}");
    }
}
