import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction12x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction22x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction3rc;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.debug.DebugItem;
import com.android.tools.smali.dexlib2.iface.debug.EndLocal;
import com.android.tools.smali.dexlib2.iface.debug.EpilogueBegin;
import com.android.tools.smali.dexlib2.iface.debug.LineNumber;
import com.android.tools.smali.dexlib2.iface.debug.LocalInfo;
import com.android.tools.smali.dexlib2.iface.debug.PrologueEnd;
import com.android.tools.smali.dexlib2.iface.debug.RestartLocal;
import com.android.tools.smali.dexlib2.iface.debug.SetSourceFile;
import com.android.tools.smali.dexlib2.iface.debug.StartLocal;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OffsetInstruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableExceptionHandler;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.ImmutableTryBlock;
import com.android.tools.smali.dexlib2.immutable.debug.ImmutableEndLocal;
import com.android.tools.smali.dexlib2.immutable.debug.ImmutableRestartLocal;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableFieldReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

/** Static derivative of the exact staged guest AMS inner method. */
final class GuestFingerprintAttachInner {
    private static final String AMS = "Lcom/android/server/am/ActivityManagerService;";
    private static final String RECORD = "Lcom/android/server/am/ProcessRecord;";
    private static final String THREAD = "Landroid/app/IApplicationThread;";
    private static final String HELPER = "Lcom/android/server/am/PreparedGuestFingerprintAttach;";
    private static final String OBSERVATION = "Lcom/android/server/am/PreparedGuestFingerprintAttach$Observation;";
    private static final String SOURCE_BODY = "64c0d7458ca6f822beb86cd48bc3a908fe1641b3722d5b14049130848cc1e228";
    private static final int MONITOR_EXIT = 793;
    private static final int SUCCESS = 800;
    private static final int SCRATCH = 6;
    private static final ImmutableFieldReference APP_THREAD = new ImmutableFieldReference(
            RECORD, "mThread", "Lcom/android/server/am/ApplicationThreadDeferred;");
    private static final ImmutableMethodReference SNAPSHOT = new ImmutableMethodReference(
            HELPER, "snapshot", List.of(RECORD, THREAD, "J", "I", "I"), OBSERVATION);

    private GuestFingerprintAttachInner() {}

    static ImmutableMethod derive(Method original) throws Exception {
        MethodImplementation body = original.getImplementation();
        require(AMS.equals(original.getDefiningClass()) && original.getAccessFlags() == 2
                && "finishAttachApplicationInner(JII)V".equals(SecurityDexReader.signature(original))
                && body != null && body.getRegisterCount() == 43 && body.getTryBlocks().size() == 30,
                "Unexpected finish-attach source declaration or frame");
        List<Integer> pcs = new ArrayList<>();
        List<Instruction> instructions = new ArrayList<>();
        List<String> normalized = new ArrayList<>();
        int units = 0;
        for (Instruction instruction : body.getInstructions()) {
            pcs.add(units);
            instructions.add(instruction);
            normalized.add(SecurityDexReader.instruction(instruction, units));
            units += instruction.getCodeUnits();
        }
        List<String> catches = catches(body, false);
        String source = "{\"owner\":\"" + AMS + "\",\"signature\":\"finishAttachApplicationInner(JII)V\""
                + ",\"accessFlags\":2,\"registerCount\":43,\"hasCode\":true,\"instructions\":["
                + String.join(",", normalized) + "],\"catches\":[" + String.join(",", catches) + "]}";
        require(units == 977 && pcs.size() == 505
                && SOURCE_BODY.equals(SecurityDexReader.sha(source.getBytes(StandardCharsets.UTF_8))),
                "Unexpected finish-attach source instructions or handlers");
        require(!debugLive(body, MONITOR_EXIT, SCRATCH) && !debugLive(body, SUCCESS, SCRATCH),
                "Finish-attach thread scratch overlaps a live debug local");
        for (int register = 8; register <= 13; register++) {
            require(!debugLive(body, SUCCESS, register), "Finish-attach argument pack overlaps a live debug local");
        }

        MutableMethodImplementation derived = new MutableMethodImplementation(body);
        derived.replaceInstruction(pcs.indexOf(959), new BuilderInstruction11x(Opcode.RETURN_OBJECT, 4));
        int success = pcs.indexOf(SUCCESS);
        // v2 still holds the source record. v39/v40, v41 and v42 are the unchanged input tuple.
        List<BuilderInstruction> successCode = List.of(
                new BuilderInstruction12x(Opcode.MOVE_OBJECT, 8, 2),
                new BuilderInstruction12x(Opcode.MOVE_OBJECT, 9, SCRATCH),
                new BuilderInstruction22x(Opcode.MOVE_WIDE_FROM16, 10, 39),
                new BuilderInstruction22x(Opcode.MOVE_FROM16, 12, 41),
                new BuilderInstruction22x(Opcode.MOVE_FROM16, 13, 42),
                new BuilderInstruction3rc(Opcode.INVOKE_STATIC_RANGE, 8, 6, SNAPSHOT),
                new BuilderInstruction11x(Opcode.MOVE_RESULT_OBJECT, SCRATCH),
                new BuilderInstruction11x(Opcode.RETURN_OBJECT, SCRATCH));
        derived.replaceInstruction(success, successCode.get(0));
        for (int i = 1; i < successCode.size(); i++) derived.addInstruction(success + i, successCode.get(i));
        // Before the existing monitor exit and inside its original catch-all.
        derived.addInstruction(pcs.indexOf(MONITOR_EXIT),
                new BuilderInstruction22c(Opcode.IGET_OBJECT, SCRATCH, 2, APP_THREAD));
        // Both rejected paths already hold a literal zero in v4.
        derived.replaceInstruction(pcs.indexOf(461), new BuilderInstruction11x(Opcode.RETURN_OBJECT, 4));

        verifyInstructions(pcs, instructions, derived);
        List<String> mappedCatches = catches(body, true);
        require(mappedCatches.equals(catches(derived, false)), "Finish-attach handler remap changed");
        var implementation = new ImmutableMethodImplementation(body.getRegisterCount(), derived.getInstructions(),
                relocatedTries(body), relocatedDebug(body, derived));
        require(implementation.getTryBlocks().size() == 30
                && mappedCatches.equals(catches(implementation, false)), "Finish-attach try grouping changed");
        return new ImmutableMethod(AMS, "finishAttachApplicationForFingerprintObservation",
                original.getParameters(), OBSERVATION, original.getAccessFlags(),
                original.getAnnotations(), original.getHiddenApiRestrictions(), implementation);
    }

    private static int mapped(int pc) {
        return pc + (pc >= MONITOR_EXIT ? 2 : 0) + (pc > SUCCESS ? 12 : 0);
    }

    private static void verifyInstructions(List<Integer> pcs, List<Instruction> source,
            MutableMethodImplementation derived) {
        List<Instruction> result = new ArrayList<>(derived.getInstructions());
        require(result.size() == source.size() + 8, "Unexpected finish-attach instruction count");
        int newPc = 0;
        int index = 0;
        for (int i = 0; i < source.size(); i++) {
            int oldPc = pcs.get(i);
            if (oldPc == MONITOR_EXIT) newPc += result.get(index++).getCodeUnits();
            require(newPc == mapped(oldPc), "Unexpected finish-attach PC mapping at " + oldPc);
            if (oldPc == SUCCESS) {
                for (int n = 0; n < 8; n++) newPc += result.get(index++).getCodeUnits();
                continue;
            }
            Instruction previous = source.get(i);
            Instruction current = result.get(index++);
            String expected;
            if (oldPc == 461 || oldPc == 959) {
                expected = SecurityDexReader.instruction(new BuilderInstruction11x(Opcode.RETURN_OBJECT, 4), newPc);
            } else {
                expected = SecurityDexReader.instruction(previous, newPc);
                if (previous instanceof OffsetInstruction offset) {
                    int displacement = offset.getCodeOffset();
                    expected = expected.replace("\"targetPc\":" + (newPc + displacement),
                            "\"targetPc\":" + mapped(oldPc + displacement));
                }
            }
            require(expected.equals(SecurityDexReader.instruction(current, newPc)),
                    "Unexpected finish-attach instruction drift at " + oldPc);
            newPc += current.getCodeUnits();
        }
        require(index == result.size() && newPc == 991, "Unexpected finish-attach method extent");
    }

    private static List<String> catches(MethodImplementation body, boolean map) {
        List<String> result = new ArrayList<>();
        for (var block : body.getTryBlocks()) {
            int start = block.getStartCodeAddress();
            int end = start + block.getCodeUnitCount();
            for (var handler : block.getExceptionHandlers()) {
                int target = handler.getHandlerCodeAddress();
                int address = map ? mapped(start) : start;
                int length = (map ? mapped(end) : end) - address;
                result.add("{\"startPc\":" + address + ",\"codeUnits\":" + length
                        + ",\"exceptionType\":" + SecurityDexReader.q(handler.getExceptionType())
                        + ",\"handlerPc\":" + (map ? mapped(target) : target) + "}");
            }
        }
        return result;
    }

    private static List<ImmutableTryBlock> relocatedTries(MethodImplementation source) {
        // The mutable builder represents each handler as a separate row for its labels.
        // Restore the source's ordered handler group for each range before serialization.
        List<ImmutableTryBlock> result = new ArrayList<>();
        for (var block : source.getTryBlocks()) {
            int oldStart = block.getStartCodeAddress();
            int start = mapped(oldStart);
            int end = mapped(oldStart + block.getCodeUnitCount());
            List<ImmutableExceptionHandler> handlers = new ArrayList<>();
            for (var handler : block.getExceptionHandlers()) {
                handlers.add(new ImmutableExceptionHandler(handler.getExceptionType(),
                        mapped(handler.getHandlerCodeAddress())));
            }
            result.add(new ImmutableTryBlock(start, end - start, handlers));
        }
        return result;
    }

    private static List<DebugItem> relocatedDebug(MethodImplementation source, MethodImplementation mutable) {
        List<DebugItem> result = new ArrayList<>();
        var moved = mutable.getDebugItems().iterator();
        for (DebugItem old : source.getDebugItems()) {
            require(moved.hasNext(), "Finish-attach debug event missing");
            DebugItem item = moved.next();
            int pc = mapped(old.getCodeAddress());
            require(item.getCodeAddress() == pc && item.getDebugItemType() == old.getDebugItemType(),
                    "Finish-attach debug label drifted");
            // End/restart opcodes carry a register. Their decoded metadata comes from the local history.
            if (old instanceof EndLocal end) {
                require(((EndLocal) item).getRegister() == end.getRegister(), "Finish-attach local register drifted");
                item = new ImmutableEndLocal(pc, end.getRegister(), end.getName(), end.getType(), end.getSignature());
            } else if (old instanceof RestartLocal restart) {
                require(((RestartLocal) item).getRegister() == restart.getRegister(),
                        "Finish-attach local register drifted");
                item = new ImmutableRestartLocal(pc, restart.getRegister(), restart.getName(), restart.getType(),
                        restart.getSignature());
            }
            require(debugPayload(old).equals(debugPayload(item)), "Finish-attach debug payload drifted");
            result.add(item);
        }
        require(!moved.hasNext() && result.size() == 260, "Unexpected finish-attach debug count");
        return result;
    }

    private static String debugPayload(DebugItem item) {
        String local = item instanceof LocalInfo info ? SecurityDexReader.q(info.getName()) + ":"
                + SecurityDexReader.q(info.getType()) + ":" + SecurityDexReader.q(info.getSignature()) : "";
        if (item instanceof StartLocal start) return start.getRegister() + ":" + local;
        if (item instanceof EndLocal end) return end.getRegister() + ":" + local;
        if (item instanceof RestartLocal restart) return restart.getRegister() + ":" + local;
        if (item instanceof LineNumber line) return Integer.toString(line.getLineNumber());
        if (item instanceof SetSourceFile file) return SecurityDexReader.q(file.getSourceFile());
        require(item instanceof PrologueEnd || item instanceof EpilogueBegin, "Unknown debug item");
        return "";
    }

    private static boolean debugLive(MethodImplementation body, int pc, int register) {
        boolean[] active = new boolean[body.getRegisterCount()];
        String[] type = new String[active.length];
        for (DebugItem item : body.getDebugItems()) {
            if (item.getCodeAddress() > pc) break;
            if (item instanceof StartLocal start) {
                active[start.getRegister()] = true;
                type[start.getRegister()] = start.getType();
            } else if (item instanceof EndLocal end) {
                active[end.getRegister()] = false;
            } else if (item instanceof RestartLocal restart) {
                active[restart.getRegister()] = true;
            }
        }
        return active[register] || (register > 0 && active[register - 1]
                && ("J".equals(type[register - 1]) || "D".equals(type[register - 1])));
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
