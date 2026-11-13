import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Field;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.immutable.ImmutableExceptionHandler;
import com.android.tools.smali.dexlib2.immutable.ImmutableField;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodParameter;
import com.android.tools.smali.dexlib2.immutable.ImmutableTryBlock;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10t;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction10x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11n;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction11x;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction21t;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction22c;
import com.android.tools.smali.dexlib2.immutable.instruction.ImmutableInstruction35c;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;

/** Adds dormant preference binding hooks to the exact donor Settings classes2 DEX. */
final class GuestFingerprintPreferenceBindRetarget {
    private static final String TARGET =
            "Lcom/oplus/settings/feature/fingerprint/OplusFingerprintSettings$FingerprintSettingsFragment;";
    private static final String DASHBOARD = "Lcom/android/settings/dashboard/DashboardFragment;";
    private static final String SETTINGS = "Lcom/android/settings/SettingsPreferenceFragment;";
    private static final String SETTINGS_BASE = "Lcom/oplus/settings/SettingsBaseFragment;";
    private static final String PREFERENCE_FRAGMENT = "Landroidx/preference/PreferenceFragmentCompat;";
    private static final String SCREEN = "Landroidx/preference/PreferenceScreen;";
    private static final String ADAPTER = "Landroidx/recyclerview/widget/RecyclerView$Adapter;";
    private static final String TRANSPORT = "Lcom/appleexploit/oneos/security/transport/";
    private static final String CAPTURE = TRANSPORT + "FingerprintEnrollmentPreferenceBindCapture;";
    private static final String BIND = TRANSPORT + "FingerprintEnrollmentPreferenceBindCapture$Bind;";
    private static final List<String> CREATE_ARGS = List.of("Landroid/os/Bundle;", "Ljava/lang/String;");
    private static final String CREATE = "onCreatePreferences(Landroid/os/Bundle;Ljava/lang/String;)V";
    private static final String ORIGINAL_SHA = "f063e7b96eef5f74d39e1160cd7c3aaf412a2870c3de2ddcca58aaa14992ee21";
    private static final int ORIGINAL_BYTES = 5_737_616;
    private static final int ORIGINAL_CLASSES = 2328;
    private static final String HELPER_SHA = "0ada17826b7090664972731fa75a6fd61e31a3a440f3f32ddcdb572e17c4b8b3";
    private static final int HELPER_BYTES = 22_708;
    private static final String FRAGMENT_HELPER_SHA = "37facf79e09b94e23c996c4bdca16f52af524be4c70bcd037f890ad7ba1fcaf0";
    private static final int FRAGMENT_HELPER_BYTES = 26_496;
    private static final String SOURCE_ACCESS_HELPER_SHA =
            "c99ab1eb24bb3abf4e93f7029ad726bf28202c5aa206df191001d52984b9bc19";
    private static final int SOURCE_ACCESS_HELPER_BYTES = 39_424;
    private static final Set<String> HELPER_TYPES = Set.of(CAPTURE, BIND,
            TRANSPORT + "FingerprintEnrollmentPreferenceBindCapture$1;",
            TRANSPORT + "FingerprintEnrollmentPreferenceBindCapture$BoundView;",
            TRANSPORT + "FingerprintEnrollmentPreferenceSection;",
            TRANSPORT + "FingerprintEnrollmentPreferenceSection$State;",
            TRANSPORT + "FingerprintEnrollmentPreferenceSession;",
            TRANSPORT + "FingerprintEnrollmentPreferenceSession$1;",
            TRANSPORT + "FingerprintEnrollmentPreferenceSession$Refresh;",
            TRANSPORT + "FingerprintEnrollmentPreferenceViewBinding;",
            TRANSPORT + "FingerprintEnrollmentPresentation;",
            TRANSPORT + "FingerprintEnrollmentPresentation$Status;",
            TRANSPORT + "RetainedFingerprintEnrollmentReport;",
            TRANSPORT + "RetainedFingerprintEnrollmentReport$Row;");
    private static final Set<String> FRAGMENT_HELPER_TYPES = Stream.concat(HELPER_TYPES.stream(), Stream.of(
            TRANSPORT + "FingerprintEnrollmentPreferenceReportOwner;",
            TRANSPORT + "FingerprintEnrollmentPreferenceReportOwner$1;",
            TRANSPORT + "FingerprintEnrollmentPreferenceReportOwner$SubjectSource;"))
            .collect(Collectors.toUnmodifiableSet());
    private static final Set<String> SOURCE_ACCESS_HELPER_TYPES = Stream.concat(
            FRAGMENT_HELPER_TYPES.stream(), Stream.of(
                    TRANSPORT + "FingerprintEnrollmentPreferenceReadySignal;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceReadySignal$1;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceReadySignal$Listener;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceReadySignal$Pulse;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceFeed;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceFeed$1;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceFeed$Listener;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceFeed$Request;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceFeed$ViewSource;",
                    TRANSPORT + "FingerprintEnrollmentPreferenceFeedBinding;"))
            .collect(Collectors.toUnmodifiableSet());

    private static final ImmutableFieldReference CAPTURE_FIELD =
            new ImmutableFieldReference(TARGET, "oneos$preferenceBind", CAPTURE);
    private static final ImmutableMethodReference SUPER_BIND =
            new ImmutableMethodReference(PREFERENCE_FRAGMENT, "bindPreferences", List.of(), "V");
    private static final ImmutableMethodReference SUPER_ADAPTER =
            new ImmutableMethodReference(SETTINGS, "onCreateAdapter", List.of(SCREEN), ADAPTER);
    private static final ImmutableMethodReference SUPER_UNBIND =
            new ImmutableMethodReference(SETTINGS, "onUnbindPreferences", List.of(), "V");
    private static final ImmutableMethodReference SUPER_DESTROY_VIEW =
            new ImmutableMethodReference(SETTINGS_BASE, "onDestroyView", List.of(), "V");
    private static final ImmutableMethodReference SUPER_SCREEN =
            new ImmutableMethodReference(SETTINGS, "setPreferenceScreen", List.of(SCREEN), "V");
    private static final ImmutableMethodReference SUPER_CREATE =
            new ImmutableMethodReference(DASHBOARD, "onCreatePreferences", CREATE_ARGS, "V");
    private static final ImmutableMethodReference FORWARD_CREATE =
            new ImmutableMethodReference(TARGET, "oneos$forwardCreatePreferences", CREATE_ARGS, "V");
    private static final ImmutableMethodReference CAPTURE_CONSTRUCTOR =
            new ImmutableMethodReference(CAPTURE, "<init>", List.of(PREFERENCE_FRAGMENT), "V");
    private static final ImmutableMethodReference BEGIN =
            new ImmutableMethodReference(CAPTURE, "beginBind", List.of(), BIND);
    private static final ImmutableMethodReference CURRENT =
            new ImmutableMethodReference(CAPTURE, "currentBind", List.of(), BIND);
    private static final ImmutableMethodReference FINISH =
            new ImmutableMethodReference(CAPTURE, "finishBind", List.of(BIND), "V");
    private static final ImmutableMethodReference ABORT =
            new ImmutableMethodReference(CAPTURE, "abortBind", List.of(BIND), "V");
    private static final ImmutableMethodReference RECORD =
            new ImmutableMethodReference(CAPTURE, "recordAdapter", List.of(BIND, SCREEN, ADAPTER), "V");
    private static final ImmutableMethodReference RETIRE =
            new ImmutableMethodReference(CAPTURE, "retire", List.of(), "V");
    private static final ImmutableMethodReference RETIRE_SCREEN =
            new ImmutableMethodReference(CAPTURE, "retireIfScreenChanges", List.of(SCREEN), "V");

    private GuestFingerprintPreferenceBindRetarget() {}

    private static ImmutableMethod newMethod(String name, List<String> arguments, String result,
            int flags, int registers, List<Instruction> code) {
        var parameters = arguments.stream().map(type -> new ImmutableMethodParameter(type, Set.of(), null)).toList();
        return new ImmutableMethod(TARGET, name, parameters, result, flags, Set.of(), Set.of(),
                new ImmutableMethodImplementation(registers, code, List.of(), List.of()));
    }

    private static ImmutableMethod bind() {
        List<Instruction> code = List.of(
                new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 3, CAPTURE_FIELD),
                new ImmutableInstruction11n(Opcode.CONST_4, 1, 0),
                new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 6),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 1, 0, 0, 0, 0, 0, BEGIN),
                new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 1),
                new ImmutableInstruction35c(Opcode.INVOKE_SUPER, 1, 3, 0, 0, 0, 0, SUPER_BIND),
                new ImmutableInstruction21t(Opcode.IF_EQZ, 1, 5),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 2, 0, 1, 0, 0, 0, FINISH),
                new ImmutableInstruction10x(Opcode.RETURN_VOID),
                new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION, 2),
                new ImmutableInstruction21t(Opcode.IF_EQZ, 1, 5),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 2, 0, 1, 0, 0, 0, ABORT),
                new ImmutableInstruction11x(Opcode.THROW, 2));
        var stockTry = new ImmutableTryBlock(9, 3, List.of(new ImmutableExceptionHandler(null, 18)));
        return new ImmutableMethod(TARGET, "bindPreferences", List.of(), "V", 0x01, Set.of(), Set.of(),
                new ImmutableMethodImplementation(4, code, List.of(stockTry), List.of()));
    }

    private static ImmutableMethod adapter() {
        return newMethod("onCreateAdapter", List.of(SCREEN), ADAPTER, 0x01, 5, List.of(
                new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 3, CAPTURE_FIELD),
                new ImmutableInstruction11n(Opcode.CONST_4, 1, 0),
                new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 6),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 1, 0, 0, 0, 0, 0, CURRENT),
                new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 1),
                new ImmutableInstruction35c(Opcode.INVOKE_SUPER, 2, 3, 4, 0, 0, 0, SUPER_ADAPTER),
                new ImmutableInstruction11x(Opcode.MOVE_RESULT_OBJECT, 2),
                new ImmutableInstruction21t(Opcode.IF_EQZ, 1, 5),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 4, 0, 1, 4, 2, 0, RECORD),
                new ImmutableInstruction11x(Opcode.RETURN_OBJECT, 2)));
    }

    private static ImmutableMethod retireThenSuper(String name, List<String> arguments, int flags,
            ImmutableMethodReference retirement, ImmutableMethodReference original) {
        int retireInputs = retirement.getParameterTypes().size();
        return newMethod(name, arguments, "V", flags, arguments.size() + 2, List.of(
                new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 1, CAPTURE_FIELD),
                new ImmutableInstruction21t(Opcode.IF_EQZ, 0, 5),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 1 + retireInputs,
                        0, retireInputs == 0 ? 0 : 2, 0, 0, 0, retirement),
                new ImmutableInstruction35c(Opcode.INVOKE_SUPER, 1 + arguments.size(),
                        1, arguments.isEmpty() ? 0 : 2, arguments.size() == 2 ? 3 : 0, 0, 0, original),
                new ImmutableInstruction10x(Opcode.RETURN_VOID)));
    }

    private static ImmutableMethod fragmentOwnedCreate() {
        List<Instruction> code = List.of(
                new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 1, CAPTURE_FIELD),
                new ImmutableInstruction21t(Opcode.IF_NEZ, 0, 10),
                new ImmutableInstruction21c(Opcode.NEW_INSTANCE, 0, new ImmutableTypeReference(CAPTURE)),
                new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 2, 0, 1, 0, 0, 0, CAPTURE_CONSTRUCTOR),
                new ImmutableInstruction22c(Opcode.IPUT_OBJECT, 0, 1, CAPTURE_FIELD),
                new ImmutableInstruction10t(Opcode.GOTO, 4),
                new ImmutableInstruction35c(Opcode.INVOKE_VIRTUAL, 1, 0, 0, 0, 0, 0, RETIRE),
                new ImmutableInstruction35c(Opcode.INVOKE_SUPER, 3, 1, 2, 3, 0, 0, SUPER_CREATE),
                new ImmutableInstruction10x(Opcode.RETURN_VOID),
                new ImmutableInstruction11x(Opcode.MOVE_EXCEPTION, 0),
                new ImmutableInstruction10t(Opcode.GOTO, -5));
        var setupTry = new ImmutableTryBlock(0, 15, List.of(new ImmutableExceptionHandler(null, 19)));
        var parameters = CREATE_ARGS.stream()
                .map(type -> new ImmutableMethodParameter(type, Set.of(), null)).toList();
        return new ImmutableMethod(TARGET, FORWARD_CREATE.getName(), parameters, "V", 0x02, Set.of(), Set.of(),
                new ImmutableMethodImplementation(4, code, List.of(setupTry), List.of()));
    }

    private static List<ImmutableMethod> addedMethods(boolean fragmentOwned, boolean sourceAccess) {
        var methods = List.of(bind(), adapter(),
                retireThenSuper("onUnbindPreferences", List.of(), 0x01, RETIRE, SUPER_UNBIND),
                retireThenSuper("onDestroyView", List.of(), 0x01, RETIRE, SUPER_DESTROY_VIEW),
                retireThenSuper("setPreferenceScreen", List.of(SCREEN), 0x01, RETIRE_SCREEN, SUPER_SCREEN),
                fragmentOwned ? fragmentOwnedCreate()
                        : retireThenSuper(FORWARD_CREATE.getName(), CREATE_ARGS, 0x02, RETIRE, SUPER_CREATE));
        if (!sourceAccess) return methods;
        var withAccessor = new ArrayList<>(methods);
        withAccessor.add(newMethod("oneos$getPreferenceBind", List.of(), CAPTURE, 0x10, 2, List.of(
                new ImmutableInstruction22c(Opcode.IGET_OBJECT, 0, 1, CAPTURE_FIELD),
                new ImmutableInstruction11x(Opcode.RETURN_OBJECT, 0))));
        return withAccessor;
    }

    private static Method editCreate(Method method, boolean inverse) {
        var body = method.getImplementation();
        require(method.getAccessFlags() == 0x01 && body != null && body.getRegisterCount() == 3
                && body.getTryBlocks().isEmpty() && !body.getDebugItems().iterator().hasNext(),
                "Unexpected original onCreatePreferences frame");
        var original = new ImmutableInstruction35c(Opcode.INVOKE_SUPER, 3, 0, 1, 2, 0, 0, SUPER_CREATE);
        var forward = new ImmutableInstruction35c(Opcode.INVOKE_DIRECT, 3, 0, 1, 2, 0, 0, FORWARD_CREATE);
        List<Instruction> instructions = new ArrayList<>();
        int pc = 0;
        for (Instruction instruction : body.getInstructions()) {
            if (pc == 0) {
                require(SecurityDexReader.instruction(instruction, pc).equals(
                        SecurityDexReader.instruction(inverse ? forward : original, pc)),
                        "Unexpected original preference creation call");
                instruction = inverse ? original : forward;
            }
            instructions.add(instruction);
            pc += instruction.getCodeUnits();
        }
        require(pc == 67, "Unexpected original onCreatePreferences extent");
        return new ImmutableMethod(TARGET, method.getName(), method.getParameters(), method.getReturnType(),
                method.getAccessFlags(), method.getAnnotations(), method.getHiddenApiRestrictions(),
                new ImmutableMethodImplementation(body.getRegisterCount(), instructions, body.getTryBlocks(),
                        body.getDebugItems()));
    }

    private static List<ClassDef> overlay(Collection<? extends ClassDef> classes, Set<String> helperTypes,
            boolean inverse, List<ImmutableMethod> added) {
        List<ClassDef> result = new ArrayList<>();
        int targets = 0;
        int cuts = 0;
        for (ClassDef definition : classes) {
            require(!helperTypes.contains(definition.getType()), "External helper definition collides with donor DEX");
            if (!TARGET.equals(definition.getType())) {
                result.add(definition);
                continue;
            }
            require(definition.getAccessFlags() == 0x01 && DASHBOARD.equals(definition.getSuperclass()),
                    "Unexpected fingerprint preference fragment");
            targets++;
            List<Field> fields = new ArrayList<>();
            int removedField = 0;
            for (Field field : definition.getFields()) {
                if (CAPTURE_FIELD.getName().equals(field.getName())) {
                    require(inverse && CAPTURE_FIELD.equals(field) && field.getAccessFlags() == 0x02,
                            "Unexpected preference capture field");
                    removedField++;
                } else {
                    fields.add(field);
                }
            }
            List<Method> methods = new ArrayList<>();
            int removedMethods = 0;
            for (Method method : definition.getMethods()) {
                var replacement = added.stream().filter(candidate -> candidate.getName().equals(method.getName()))
                        .findFirst();
                if (replacement.isPresent()) {
                    var expected = replacement.get();
                    require(inverse && expected.equals(method) && expected.getAccessFlags() == method.getAccessFlags(),
                            "Unexpected preference capture method");
                    removedMethods++;
                } else if (CREATE.equals(SecurityDexReader.signature(method))) {
                    methods.add(editCreate(method, inverse));
                    cuts++;
                } else {
                    methods.add(method);
                }
            }
            require(removedField == (inverse ? 1 : 0) && removedMethods == (inverse ? added.size() : 0),
                    "Unexpected preference capture inverse extent");
            if (!inverse) {
                fields.add(new ImmutableField(TARGET, CAPTURE_FIELD.getName(), CAPTURE, 0x02, null, Set.of(), Set.of()));
                methods.addAll(added);
            }
            result.add(new ImmutableClassDef(TARGET, definition.getAccessFlags(), definition.getSuperclass(),
                    definition.getInterfaces(), definition.getSourceFile(), definition.getAnnotations(), fields, methods));
        }
        require(targets == 1 && cuts == 1, "Expected exactly one fingerprint fragment and creation cut");
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

    private static Set<String> checkHelper(DexBackedDexFile helper, Set<String> expectedTypes,
            boolean fragmentOwned) {
        Set<String> types = helper.getClasses().stream().map(ClassDef::getType).collect(Collectors.toSet());
        require(helper.getClasses().size() == expectedTypes.size() && types.equals(expectedTypes),
                "Unexpected separate preference helper definitions");
        var owner = helper.getClasses().stream().filter(type -> CAPTURE.equals(type.getType())).findFirst().orElseThrow();
        require((owner.getAccessFlags() & 0x01) != 0, "Preference capture class is not public");
        if (fragmentOwned) {
            int constructors = 0;
            for (Method method : owner.getDirectMethods()) {
                if (CAPTURE_CONSTRUCTOR.equals(method) && method.getAccessFlags() == 0x10001
                        && method.getImplementation() != null) constructors++;
            }
            require(constructors == 1, "Expected implemented public fragment capture constructor");
        }
        for (var expected : List.of(BEGIN, CURRENT, FINISH, ABORT, RECORD, RETIRE, RETIRE_SCREEN)) {
            int matches = 0;
            for (Method method : owner.getVirtualMethods()) {
                if (expected.equals(method) && (method.getAccessFlags() & 0x01) != 0
                        && method.getImplementation() != null) matches++;
            }
            require(matches == 1, "Expected implemented public capture method: " + expected.getName());
        }
        return types;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }

    public static void main(String[] args) throws Exception {
        boolean sourceAccess = args.length == 5 && "--source-access".equals(args[4]);
        boolean fragmentOwned = sourceAccess || (args.length == 5 && "--fragment-owned".equals(args[4]));
        require(args.length == 4 || fragmentOwned,
                "Expected donor DEX, helper DEX, helper SHA-256, exclusive output and optional mode");
        String helperSha = sourceAccess ? SOURCE_ACCESS_HELPER_SHA : fragmentOwned ? FRAGMENT_HELPER_SHA : HELPER_SHA;
        int helperBytes = sourceAccess ? SOURCE_ACCESS_HELPER_BYTES
                : fragmentOwned ? FRAGMENT_HELPER_BYTES : HELPER_BYTES;
        Set<String> expectedTypes = sourceAccess ? SOURCE_ACCESS_HELPER_TYPES
                : fragmentOwned ? FRAGMENT_HELPER_TYPES : HELPER_TYPES;
        require(helperSha.equals(args[2]), "Expected the reviewed external preference helper SHA-256");
        byte[] source = pinned(Path.of(args[0]), ORIGINAL_BYTES, ORIGINAL_SHA);
        byte[] helper = pinned(Path.of(args[1]), helperBytes, helperSha);
        var original = new DexBackedDexFile(Opcodes.forApi(29), source);
        require(source.length == ORIGINAL_BYTES && original.getClasses().size() == ORIGINAL_CLASSES
                && helper.length == helperBytes, "Unexpected donor definitions or helper extent");
        Set<String> helperTypes = checkHelper(new DexBackedDexFile(Opcodes.forApi(29), helper), expectedTypes,
                fragmentOwned);
        var added = addedMethods(fragmentOwned, sourceAccess);
        var classes = overlay(original.getClasses(), helperTypes, false, added);
        var expected = ProbeSamsungDex041.normalize(classes);
        SourcePreservingDexPool pool = new SourcePreservingDexPool();
        GuestPolicyInitRetarget.seed(pool, original, source);
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
        var before = ProbeSamsungDex041.normalize(original.getClasses());
        ProbeSamsungDex041.same(before,
                ProbeSamsungDex041.normalize(overlay(decoded.getClasses(), helperTypes, true, added)));
        Files.write(Path.of(args[3]), output, StandardOpenOption.CREATE_NEW);
        System.out.println("{\"normalizedOriginalRecords\":" + before.size()
                + ",\"originalDefinitions\":" + ORIGINAL_CLASSES + ",\"addedDefinitions\":0"
                + ",\"externalHelperDefinitions\":" + helperTypes.size()
                + ",\"changedOriginalMethods\":1,\"addedMethods\":" + added.size()
                + ",\"addedFields\":1,\"semanticInverse\":true"
                + ",\"outputSha256\":" + SecurityDexReader.q(SecurityDexReader.sha(output)) + "}");
    }
}
