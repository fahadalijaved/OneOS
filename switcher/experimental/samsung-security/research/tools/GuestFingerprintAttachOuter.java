import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderTryBlock;
import com.android.tools.smali.dexlib2.builder.MutableMethodImplementation;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction11x;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.Method;
import com.android.tools.smali.dexlib2.iface.MethodImplementation;
import com.android.tools.smali.dexlib2.iface.debug.DebugItem;
import com.android.tools.smali.dexlib2.iface.debug.EndLocal;
import com.android.tools.smali.dexlib2.iface.debug.RestartLocal;
import com.android.tools.smali.dexlib2.iface.debug.StartLocal;
import com.android.tools.smali.dexlib2.iface.instruction.Instruction;
import com.android.tools.smali.dexlib2.iface.instruction.OffsetInstruction;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethod;
import com.android.tools.smali.dexlib2.immutable.ImmutableMethodImplementation;
import com.android.tools.smali.dexlib2.immutable.debug.ImmutableEndLocal;
import com.android.tools.smali.dexlib2.immutable.debug.ImmutableRestartLocal;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;

/** Retargets the exact staged public attach call and retains its closed result locally. */
final class GuestFingerprintAttachOuter {
    private static final String AMS = "Lcom/android/server/am/ActivityManagerService;";
    private static final String OUTER = "finishAttachApplication(JJ)V";
    private static final String SOURCE_BODY =
            "c8bc5a01d3ccf8f06426efa7e429c666509cbe5b88ed68425519f368e2546af3";
    private static final int INVOKE_PC = 67;
    private static final int RESTORE_PC = 70;
    private static final int HANDLER_PC = 94;
    private static final int SCRATCH = 0;
    private static final ImmutableMethodReference TYPED_ATTACH = new ImmutableMethodReference(
            AMS, "finishAttachApplicationForFingerprintObservation", List.of("J", "I", "I"),
            "Lcom/android/server/am/PreparedGuestFingerprintAttach$Observation;");

    private GuestFingerprintAttachOuter() {}

    static boolean target(Method method) {
        return method != null && AMS.equals(method.getDefiningClass())
                && OUTER.equals(SecurityDexReader.signature(method));
    }

    static Method edit(Method original) throws Exception {
        require(target(original) && original.getAccessFlags() == 17, "Unexpected public attach method");
        MethodImplementation source = original.getImplementation();
        require(source != null && source.getRegisterCount() == 15, "Unexpected public attach frame");
        requireCatch(source, HANDLER_PC);

        List<Instruction> instructions = new ArrayList<>();
        List<String> normalized = new ArrayList<>();
        int pc = 0;
        int invokeIndex = -1;
        for (Instruction instruction : source.getInstructions()) {
            if (pc == INVOKE_PC) invokeIndex = instructions.size();
            instructions.add(instruction);
            normalized.add(SecurityDexReader.instruction(instruction, pc));
            pc += instruction.getCodeUnits();
        }
        String body = "{\"owner\":" + SecurityDexReader.q(AMS)
                + ",\"signature\":" + SecurityDexReader.q(OUTER)
                + ",\"accessFlags\":17,\"registerCount\":15,\"hasCode\":true,\"instructions\":["
                + String.join(",", normalized) + "],\"catches\":["
                + "{\"startPc\":67,\"codeUnits\":3,\"exceptionType\":null,\"handlerPc\":94}]}";
        require(pc == 101 && instructions.size() == 54 && invokeIndex >= 0
                && SOURCE_BODY.equals(SecurityDexReader.sha(body.getBytes(StandardCharsets.UTF_8))),
                "Unexpected public attach instructions");
        MutableMethodImplementation mutable = new MutableMethodImplementation(source);
        var invoke = new BuilderInstruction35c(Opcode.INVOKE_DIRECT, 5, 10, 11, 12, 7, 1, TYPED_ATTACH);
        var result = new BuilderInstruction11x(Opcode.MOVE_RESULT_OBJECT, SCRATCH);
        mutable.replaceInstruction(invokeIndex, invoke);
        // v0 is unnamed. Restore uses v8:v9, and the original CMP_LONG next defines v0.
        mutable.addInstruction(invokeIndex + 1, result);

        BuilderTryBlock oldCatch = mutable.getTryBlocks().get(0);
        require(oldCatch.start.getCodeAddress() == INVOKE_PC
                && oldCatch.end.getCodeAddress() == RESTORE_PC + 1
                && oldCatch.exceptionHandler.getHandlerCodeAddress() == HANDLER_PC + 1,
                "Unexpected public attach label relocation");
        // Keep the catch limited to the call and leave the original line event on restore.
        BuilderTryBlock exactCatch = new BuilderTryBlock(oldCatch.start,
                mutable.newLabelForIndex(invokeIndex + 1), oldCatch.exceptionHandler.getHandler());
        var changed = new ImmutableMethodImplementation(source.getRegisterCount(), mutable.getInstructions(),
                List.of(exactCatch), relocatedDebug(source, mutable));
        requireCatch(changed, HANDLER_PC + 1);

        List<? extends Instruction> emitted = changed.getInstructions();
        require(emitted.size() == instructions.size() + 1, "Unexpected public attach instruction count");
        require(SecurityDexReader.instruction(invoke, INVOKE_PC).equals(
                        SecurityDexReader.instruction(emitted.get(invokeIndex), INVOKE_PC))
                && SecurityDexReader.instruction(result, RESTORE_PC).equals(
                        SecurityDexReader.instruction(emitted.get(invokeIndex + 1), RESTORE_PC)),
                "Unexpected public attach call or immediate result");
        pc = 0;
        for (int i = 0; i < instructions.size(); i++) {
            Instruction old = instructions.get(i);
            if (i != invokeIndex) {
                int newIndex = i > invokeIndex ? i + 1 : i;
                int newPc = shiftedPc(pc);
                require(SecurityDexReader.instruction(old, newPc).equals(
                                SecurityDexReader.instruction(emitted.get(newIndex), newPc)),
                        "Original public attach instruction changed at PC " + pc);
                if (old instanceof OffsetInstruction branch) {
                    int target = shiftedPc(pc + branch.getCodeOffset());
                    var moved = (OffsetInstruction) emitted.get(newIndex);
                    require(newPc + moved.getCodeOffset() == target, "Original public attach target drifted");
                }
            }
            pc += old.getCodeUnits();
        }
        return new ImmutableMethod(AMS, original.getName(), original.getParameters(), original.getReturnType(),
                original.getAccessFlags(), original.getAnnotations(), original.getHiddenApiRestrictions(), changed);
    }

    private static int shiftedPc(int pc) {
        return pc >= RESTORE_PC ? pc + 1 : pc;
    }

    private static void requireCatch(MethodImplementation body, int handlerPc) {
        var tries = body.getTryBlocks();
        require(tries.size() == 1, "Unexpected public attach try count");
        var block = tries.get(0);
        var handlers = block.getExceptionHandlers();
        require(block.getStartCodeAddress() == INVOKE_PC && block.getCodeUnitCount() == 3
                && handlers.size() == 1 && handlers.get(0).getExceptionType() == null
                && handlers.get(0).getHandlerCodeAddress() == handlerPc,
                "Unexpected public attach catch range");
    }

    private static List<DebugItem> relocatedDebug(MethodImplementation source, MethodImplementation mutable) {
        List<DebugItem> result = new ArrayList<>();
        var moved = mutable.getDebugItems().iterator();
        for (DebugItem original : source.getDebugItems()) {
            require(moved.hasNext(), "Public attach debug event missing");
            DebugItem item = moved.next();
            int oldPc = original.getCodeAddress();
            int newPc = shiftedPc(oldPc);
            require(item.getCodeAddress() == newPc && item.getDebugItemType() == original.getDebugItemType(),
                    "Public attach debug label drifted");
            // The builder retains the END_LOCAL and RESTART_LOCAL registers and labels.
            // Supply the original reader's decoded local metadata on those events.
            if (original instanceof EndLocal end) {
                require(((EndLocal) item).getRegister() == end.getRegister(), "Public attach local register drifted");
                item = new ImmutableEndLocal(newPc, end.getRegister(), end.getName(), end.getType(),
                        end.getSignature());
            } else if (original instanceof RestartLocal restart) {
                require(((RestartLocal) item).getRegister() == restart.getRegister(),
                        "Public attach local register drifted");
                item = new ImmutableRestartLocal(newPc, restart.getRegister(), restart.getName(),
                        restart.getType(), restart.getSignature());
            } else if (original instanceof StartLocal start) {
                require(start.getRegister() != SCRATCH, "Public attach scratch holds a debug local");
            }
            String originalRow = ProbeSamsungDex041.debug(original);
            String prefix = "\"" + original.getDebugItemType() + ":";
            String expected = prefix + newPc
                    + originalRow.substring(prefix.length() + Integer.toString(oldPc).length());
            require(expected.equals(ProbeSamsungDex041.debug(item)), "Public attach debug payload drifted");
            result.add(item);
        }
        require(!moved.hasNext() && result.size() == 33, "Unexpected public attach debug count");
        return result;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
}
