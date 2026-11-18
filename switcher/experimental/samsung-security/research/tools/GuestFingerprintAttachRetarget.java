import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.ClassDef;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.immutable.ImmutableClassDef;
import com.android.tools.smali.dexlib2.writer.io.MemoryDataStore;
import com.android.tools.smali.dexlib2.writer.pool.SourcePreservingDexPool;

/** Static staged AMS retarget. The snapshot remains local to its original call. */
final class GuestFingerprintAttachRetarget {
    private static final String AMS = "Lcom/android/server/am/ActivityManagerService;";
    private static final String OUTER = "finishAttachApplication(JJ)V";
    private static final String INNER = "finishAttachApplicationInner(JII)V";
    private static final String CLONE = "finishAttachApplicationForFingerprintObservation(JII)"
            + "Lcom/android/server/am/PreparedGuestFingerprintAttach$Observation;";
    private static final String ORIGINAL_SHA =
            "bcc9cb821ffc6a37b3838ca2391253652a0d40245a4b75b8b35eccd17779ca20";
    private static final int ORIGINAL_BYTES = 12_186_672;
    private static final int ORIGINAL_CLASSES = 6_789;
    private static final int ORIGINAL_METHOD_IDS = 65_533;

    private static void require(boolean condition, String reason) {
        if (!condition) throw new IllegalArgumentException(reason);
    }

    private static ClassDef ams(Collection<? extends ClassDef> definitions) {
        ClassDef result = null;
        for (ClassDef definition : definitions) {
            if (AMS.equals(definition.getType())) {
                require(result == null, "Duplicate ActivityManagerService");
                result = definition;
            }
        }
        require(result != null, "Original ActivityManagerService unavailable");
        return result;
    }

    private static Method method(ClassDef owner, String signature) {
        Method result = null;
        for (Method candidate : owner.getMethods()) {
            if (signature.equals(SecurityDexReader.signature(candidate))) {
                require(result == null, "Duplicate selected AMS method");
                result = candidate;
            }
        }
        require(result != null, "Selected AMS method unavailable");
        return result;
    }

    private static List<ClassDef> overlay(Collection<? extends ClassDef> definitions,
            Method outer, Method added, boolean inverse) {
        var owner = ams(definitions);
        var methods = new ArrayList<Method>();
        int replaced = 0;
        int removed = 0;
        for (Method original : owner.getMethods()) {
            String signature = SecurityDexReader.signature(original);
            if (OUTER.equals(signature)) {
                methods.add(outer);
                replaced++;
            } else if (CLONE.equals(signature)) {
                require(inverse, "Typed attach method already exists");
                removed++;
            } else {
                methods.add(original);
            }
        }
        require(replaced == 1 && removed == (inverse ? 1 : 0), "Unexpected selected method count");
        if (!inverse) {
            require(added != null && CLONE.equals(SecurityDexReader.signature(added)),
                    "Unexpected typed attach method signature");
            methods.add(added);
        }
        var changed = new ImmutableClassDef(AMS, owner.getAccessFlags(), owner.getSuperclass(),
                owner.getInterfaces(), owner.getSourceFile(), owner.getAnnotations(), owner.getFields(), methods);
        var result = new ArrayList<ClassDef>(definitions.size());
        for (ClassDef definition : definitions) {
            result.add(AMS.equals(definition.getType()) ? changed : definition);
        }
        return result;
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 2, "Expected pinned original DEX and exclusive writer output");
        Path originalPath = Path.of(args[0]);
        require(Files.size(originalPath) == ORIGINAL_BYTES, "Unexpected original DEX size");
        byte[] originalBytes = Files.readAllBytes(originalPath);
        require(originalBytes.length == ORIGINAL_BYTES && ORIGINAL_SHA.equals(SecurityDexReader.sha(originalBytes)),
                "Unexpected original DEX digest");
        ProbeSamsungDex041.validate(originalBytes);
        var original = new DexBackedDexFile(Opcodes.forApi(29), originalBytes);
        require(original.getClasses().size() == ORIGINAL_CLASSES
                        && SecurityDexReader.u32(originalBytes, 88) == ORIGINAL_METHOD_IDS,
                "Unexpected original classes or method table");
        var owner = ams(original.getClasses());
        Method originalOuter = method(owner, OUTER);
        Method changedOuter = GuestFingerprintAttachOuter.edit(originalOuter);
        Method added = GuestFingerprintAttachInner.derive(method(owner, INNER));
        var classes = overlay(original.getClasses(), changedOuter, added, false);
        var expected = ProbeSamsungDex041.normalize(classes);

        SourcePreservingDexPool pool = new SourcePreservingDexPool();
        GuestPolicyInitRetarget.seed(pool, original, originalBytes);
        for (ClassDef definition : classes) pool.internClass(definition);
        require(!pool.hasOverflowed(), "Staged attach DEX ID overflow");
        byte[] output;
        MemoryDataStore store = new MemoryDataStore();
        try {
            pool.writeTo(store);
            output = store.getData();
        } finally {
            store.close();
        }
        ProbeSamsungDex041.validate(output);
        require(SecurityDexReader.u32(output, 88) == ORIGINAL_METHOD_IDS + 2
                        && SecurityDexReader.u32(output, 80) == SecurityDexReader.u32(originalBytes, 80),
                "Unexpected method or field ID changes");
        var decoded = new DexBackedDexFile(Opcodes.forApi(29), output);
        require(decoded.getClasses().size() == ORIGINAL_CLASSES, "Unexpected emitted class count");
        ProbeSamsungDex041.same(expected, ProbeSamsungDex041.normalize(decoded.getClasses()));
        expected.clear();
        var before = ProbeSamsungDex041.normalize(original.getClasses());
        var inverse = overlay(decoded.getClasses(), originalOuter, null, true);
        ProbeSamsungDex041.same(before, ProbeSamsungDex041.normalize(inverse));
        Files.write(Path.of(args[1]), output, StandardOpenOption.CREATE_NEW);
        System.out.println("{\"status\":\"PASS_STATIC_GUEST_ATTACH_WRITER_ONLY\",\"originalDefinitions\":"
                + ORIGINAL_CLASSES + ",\"originalRecords\":" + before.size()
                + ",\"addedMethods\":1,\"changedOriginalMethods\":1,\"addedMethodIds\":2"
                + ",\"semanticInverse\":true,\"outputSha256\":"
                + SecurityDexReader.q(SecurityDexReader.sha(output)) + "}");
    }
}
