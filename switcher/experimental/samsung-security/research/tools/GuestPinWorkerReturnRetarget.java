import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10t;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21t;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction22c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction3rc;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;

/** Static successor of the split, disabled PIN final-callback DEX. */
final class GuestPinWorkerReturnRetarget {
    private static final String PACKAGE = "Lcom/oplus/keyguard/security/";
    private static final String TASK = PACKAGE + "OplusLockPatternChecker$oplusCheckCredential$task$1;";
    private static final String CALLBACK = PACKAGE + "OplusLockPatternChecker$OplusOnCheckCallback;";
    private static final String REQUEST = PACKAGE + "GuestPinCheckRequest;";
    private static final String FINAL_HELPER = PACKAGE + "GuestPinFinalCallbackBridge;";
    private static final String WORKER_HELPER = PACKAGE + "GuestPinWorkerReturnBridge;";
    private static final String ASYNC_TASK = "Landroid/os/AsyncTask;";
    private static final String RESPONSE = "Lcom/android/internal/widget/VerifyCredentialResponse;";
    private static final String REMOTE = "Landroid/os/RemoteException;";
    private static final String WORKER = "doInBackground([Ljava/lang/Object;)Ljava/lang/Object;";
    private static final String BASE_SHA = "8235ff3c6dce66faf81a1761cbfda9843c40d2ab0ebdbfd9b8d7a9fc365b96e4";
    private static final int BASE_BYTES = 10_183_800;
    private static final int BASE_CLASSES = 6737;
    private static final int WORKER_UNITS = 77;
    private static final Set<String> HELPER_TYPES = Set.of(
            REQUEST, PACKAGE + "GuestPinCheckRequest$1;", PACKAGE + "GuestPinCheckRequest$EntryState;",
            PACKAGE + "GuestPinCheckRequest$PostState;", PACKAGE + "GuestPinCheckRequest$ProgressEntry;",
            PACKAGE + "GuestPinCheckRequest$ProgressPost;", PACKAGE + "GuestPinCheckRequest$Slot;",
            PACKAGE + "GuestPinCheckRequest$TerminalDelivery;", PACKAGE + "GuestPinCheckRequest$TerminalState;",
            PACKAGE + "GuestPinCheckRequest$WorkerExit;", PACKAGE + "GuestPinCheckRequest$WorkerExitKind;",
            PACKAGE + "GuestPinSourceOccurrence;", PACKAGE + "GuestPinSourceOccurrence$1;",
            PACKAGE + "GuestPinSourceOccurrence$Owner;", PACKAGE + "GuestPinSourceOccurrence$Readback;",
            PACKAGE + "GuestPinSourceOccurrence$Transition;", PACKAGE + "PinCheckCompletion;",
            PACKAGE + "PinCheckCompletion$FinalKind;", PACKAGE + "PinCheckCompletion$Retirement;",
            FINAL_HELPER, WORKER_HELPER);
    private static final ImmutableFieldReference REQUEST_FIELD =
            new ImmutableFieldReference(TASK, "oneos$pinRequest", REQUEST);
    private static final ImmutableMethodReference NORMAL = new ImmutableMethodReference(
            TASK, "oneos$observeNormalWorkerReturn", List.of(RESPONSE), "V");
    private static final ImmutableMethodReference CAUGHT = new ImmutableMethodReference(
            TASK, "oneos$observeCaughtWorkerReturn", List.of(RESPONSE, REMOTE), "V");
    private static final ImmutableMethodReference HELPER_NORMAL = new ImmutableMethodReference(
            WORKER_HELPER, "observeNormalWorkerReturn", List.of(REQUEST, ASYNC_TASK, RESPONSE), "V");
    private static final ImmutableMethodReference HELPER_CAUGHT = new ImmutableMethodReference(
            WORKER_HELPER, "observeCaughtWorkerReturn", List.of(REQUEST, ASYNC_TASK, RESPONSE, REMOTE), "V");
    private static final ImmutableMethodReference HELPER_FINAL = new ImmutableMethodReference(
            FINAL_HELPER, "forwardOriginal", List.of(REQUEST, ASYNC_TASK, CALLBACK, RESPONSE, "I", "Z"), "V");
    private static final ImmutableMethodReference LOG_ERROR = new ImmutableMethodReference(
            "Lcom/oplusos/keyguard/utils/KgdLogUtil;", "e",
            List.of("Ljava/lang/String;", "Ljava/lang/String;", "Ljava/lang/Throwable;"), "V");

    private record Edit(Instruction stock, Instruction changed) {}

    private static final Instruction RETURN_RESPONSE = new ImmutableInstruction11x(Opcode.RETURN_OBJECT, 1);
    private static final Map<Integer, Edit> EDITS = Map.of(
            67, new Edit(RETURN_RESPONSE, new ImmutableInstruction10t(Opcode.GOTO, 10)),
            68, new Edit(new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION, 6),
                         new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION, 5)),
            70, new Edit(RETURN_RESPONSE, new ImmutableInstruction10t(Opcode.GOTO, 7)),
            73, new Edit(new ImmutableInstruction35c(Opcode.INVOKE_STATIC, 3, 0, 7, 6, 0, 0, LOG_ERROR),
                         new ImmutableInstruction35c(Opcode.INVOKE_STATIC, 3, 0, 7, 5, 0, 0, LOG_ERROR)),
            76, new Edit(RETURN_RESPONSE, new ImmutableInstruction10t(Opcode.GOTO, 5)));
    private static final List<Instruction> APPENDED = List.of(
            new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 2, 6, 1, 0, 0, 0, NORMAL),
            RETURN_RESPONSE,
            new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 3, 6, 1, 5, 0, 0, CAUGHT),
            RETURN_RESPONSE);

    private GuestPinWorkerReturnRetarget() {}

    private static ImmutableMethod observer(ImmutableMethodReference method, ImmutableMethodReference target) {
        var parameters = method.getParameterTypes().stream()
                .map(type -> new ImmutableMethodParameter(type, Set.of(), null)).toList();
        int words = parameters.size() + 2;
        // v0 is the existing field value, v1 the original task, and v2 onward the original inputs.
        return new ImmutableMethod(TASK, method.getName(), parameters, "V", 0x02, Set.of(), Set.of(),
                new ImmutableMethodImplementation(words, List.of(
                        new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 1, REQUEST_FIELD),
                        new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 5),
                        new ImmutableInstruction3rc(Opcode.INVOKE_STATIC_RANGE, 0, words, target),
                        new ImmutableInstruction10x(Opcode.RETURN_VOID)), List.of(), List.of()));
    }

    private static void requireWorkerFrame(Method method, MethodImplementation body) {
        require(method.getAccessFlags() == 0x11 && body != null && body.getRegisterCount() == 8
                && body.getTryBlocks().size() == 1 && !body.getDebugItems().iterator().hasNext(),
                "Unexpected worker method frame");
        var region = body.getTryBlocks().get(0);
        require(region.getStartCodeAddress() == 27 && region.getCodeUnitCount() == 40
                && region.getExceptionHandlers().size() == 1, "Unexpected worker try range");
        var handler = region.getExceptionHandlers().get(0);
        require(REMOTE.equals(handler.getExceptionType()) && handler.getHandlerCodeAddress() == 68,
                "Unexpected worker exception handler");
    }

    private static Method editWorker(Method method, boolean inverse) {
        MethodImplementation body = method.getImplementation();
        requireWorkerFrame(method, body);
        List<Instruction> code = new ArrayList<>();
        int pc = 0;
        int edits = 0;
        int appended = 0;
        for (Instruction instruction : body.getInstructions()) {
            if (pc >= WORKER_UNITS) {
                require(inverse && appended < APPENDED.size()
                        && sameInstruction(instruction, APPENDED.get(appended), pc),
                        "Unexpected appended worker instruction at PC " + pc);
                appended++;
            } else {
                Edit edit = EDITS.get(pc);
                if (edit != null) {
                    require(sameInstruction(instruction, inverse ? edit.changed() : edit.stock(), pc),
                            "Unexpected worker source instruction at PC " + pc);
                    instruction = inverse ? edit.stock() : edit.changed();
                    edits++;
                }
                code.add(instruction);
            }
            pc += instruction.getCodeUnits();
        }
        require(edits == EDITS.size() && pc == (inverse ? 85 : WORKER_UNITS)
                && appended == (inverse ? APPENDED.size() : 0), "Unexpected worker instruction extent");
        if (!inverse) code.addAll(APPENDED);
        return new ImmutableMethod(TASK, method.getName(), method.getParameters(), method.getReturnType(),
                method.getAccessFlags(), method.getAnnotations(), method.getHiddenApiRestrictions(),
                new ImmutableMethodImplementation(body.getRegisterCount(), code, body.getTryBlocks(), body.getDebugItems()));
    }

    private static boolean sameInstruction(Instruction first, Instruction second, int pc) {
        return SecurityDexReader.instruction(first, pc).equals(SecurityDexReader.instruction(second, pc));
    }

    private static List<ClassDef> overlay(Collection<? extends ClassDef> classes, boolean inverse) {
        List<ClassDef> result = new ArrayList<>();
        int tasks = 0;
        int workers = 0;
        for (ClassDef definition : classes) {
            require(!HELPER_TYPES.contains(definition.getType()), "Helper definition collides with donor DEX");
            if (!TASK.equals(definition.getType())) {
                result.add(definition);
                continue;
            }
            require(definition.getAccessFlags() == 0x11 && ASYNC_TASK.equals(definition.getSuperclass()),
                    "Unexpected worker task class");
            tasks++;
            int requestFields = 0;
            for (var field : definition.getInstanceFields()) {
                if (REQUEST_FIELD.getName().equals(field.getName())) {
                    require(REQUEST_FIELD.equals(field) && field.getAccessFlags() == 0x1042,
                            "Existing request field changed");
                    requestFields++;
                }
            }
            require(requestFields == 1, "Expected the existing private request field");
            List<Method> methods = new ArrayList<>();
            int removedNormal = 0;
            int removedCaught = 0;
            for (Method method : definition.getMethods()) {
                if (NORMAL.getName().equals(method.getName())) {
                    require(inverse && NORMAL.equals(method) && method.getAccessFlags() == 0x02,
                            "Unexpected normal observer definition");
                    removedNormal++;
                } else if (CAUGHT.getName().equals(method.getName())) {
                    require(inverse && CAUGHT.equals(method) && method.getAccessFlags() == 0x02,
                            "Unexpected caught observer definition");
                    removedCaught++;
                } else if (WORKER.equals(SecurityDexReader.signature(method))) {
                    methods.add(editWorker(method, inverse));
                    workers++;
                } else {
                    methods.add(method);
                }
            }
            require(removedNormal == (inverse ? 1 : 0) && removedCaught == (inverse ? 1 : 0),
                    "Unexpected observer definition counts");
            if (!inverse) {
                methods.add(observer(NORMAL, HELPER_NORMAL));
                methods.add(observer(CAUGHT, HELPER_CAUGHT));
            }
            result.add(new ImmutableClassDef(TASK, definition.getAccessFlags(), definition.getSuperclass(),
                    definition.getInterfaces(), definition.getSourceFile(), definition.getAnnotations(),
                    definition.getFields(), methods));
        }
        require(tasks == 1 && workers == 1, "Expected exactly one worker task and method");
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

    private static void checkHelper(DexBackedDexFile helper) {
        require(helper.getClasses().size() == HELPER_TYPES.size() && helper.getClasses().stream()
                .map(ClassDef::getType).collect(Collectors.toSet()).equals(HELPER_TYPES),
                "Unexpected external helper definition closure");
        for (var expected : List.of(HELPER_FINAL, HELPER_NORMAL, HELPER_CAUGHT)) {
            var owner = helper.getClasses().stream().filter(type -> expected.getDefiningClass().equals(type.getType()))
                    .findFirst().orElseThrow();
            int matches = 0;
            for (Method method : owner.getDirectMethods()) {
                if (expected.equals(method) && method.getAccessFlags() == 0x08 && method.getImplementation() != null) {
                    matches++;
                }
            }
            require(matches == 1, "Expected an implemented package-static helper: " + expected.getName());
        }
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 4, "Expected base DEX, helper DEX, helper SHA-256, and exclusive output");
        byte[] baseBytes = pinned(Path.of(args[0]), BASE_BYTES, BASE_SHA);
        byte[] helperBytes = pinned(Path.of(args[1]), 2 * 1024 * 1024, args[2]);
        var base = new DexBackedDexFile(Opcodes.forApi(29), baseBytes);
        require(baseBytes.length == BASE_BYTES && base.getClasses().size() == BASE_CLASSES,
                "Unexpected base DEX definition count");
        checkHelper(new DexBackedDexFile(Opcodes.forApi(29), helperBytes));
        var classes = overlay(base.getClasses(), false);
        var expected = ProbeSamsungDex041.normalize(classes);
        SourcePreservingDexPool pool = new SourcePreservingDexPool();
        GuestPolicyInitRetarget.seed(pool, base, baseBytes);
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
        require(decoded.getClasses().size() == BASE_CLASSES, "Unexpected decoded donor class count");
        ProbeSamsungDex041.same(expected, ProbeSamsungDex041.normalize(decoded.getClasses()));
        expected.clear();
        var before = ProbeSamsungDex041.normalize(base.getClasses());
        ProbeSamsungDex041.same(before, ProbeSamsungDex041.normalize(overlay(decoded.getClasses(), true)));
        Files.write(Path.of(args[3]), output, StandardOpenOption.CREATE_NEW);
        System.out.println("{\"normalizedOriginalRecords\":" + before.size()
                + ",\"originalDefinitions\":" + BASE_CLASSES + ",\"addedDefinitions\":0"
                + ",\"externalHelperDefinitions\":" + HELPER_TYPES.size()
                + ",\"changedOriginalMethods\":1,\"addedMethods\":2,\"addedFields\":0,\"semanticInverse\":true"
                + ",\"outputSha256\":" + SecurityDexReader.q(SecurityDexReader.sha(output)) + "}");
    }
}
