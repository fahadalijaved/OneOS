"""Generate Loneos/semcompat/Sem; from out/shims.txt: one static method per missing member."""
import re, sys

shims = [l.split() for l in open(sys.argv[1])]
out = sys.argv[2]


def split_params(p):
    return re.findall(r"\[*(?:L[^;]+;|[ZBSCIJFD])", p)


def regs(params):
    n = 0
    for t in params:
        n += 2 if t in ("J", "D") else 1
    return n


# Bodies for members that need a real answer; p0.. are the shim's parameters
# (receiver first for instance members). {arg0} is the member's own first
# argument: p0 for a static member, p1 after the receiver (run 14: "return p1"
# in a static one-int shim, "register index out of range (5 >= 5)", rejected
# the whole class). Everything else gets a default.
SPECIAL = {
    "Landroid/os/Build$VERSION;->SEM_PLATFORM_INT": ["const v0, 0x2bf20", "return v0"],      # One UI 9 (sep 180000)
    "Landroid/os/Build$VERSION;->SEM_FIRST_SDK_INT": ["const/16 v0, 0x24", "return v0"],     # first API 36
    "Landroid/os/UserHandle;->SEM_ALL": ["const/4 v0, -0x1", "invoke-static {v0}, Landroid/os/UserHandle;->of(I)Landroid/os/UserHandle;", "move-result-object v0", "return-object v0"],
    "Landroid/os/UserHandle;->SEM_CURRENT": ["const/4 v0, -0x2", "invoke-static {v0}, Landroid/os/UserHandle;->of(I)Landroid/os/UserHandle;", "move-result-object v0", "return-object v0"],
    "Landroid/os/UserHandle;->SEM_OWNER": ["const/4 v0, 0x0", "invoke-static {v0}, Landroid/os/UserHandle;->of(I)Landroid/os/UserHandle;", "move-result-object v0", "return-object v0"],
    "Landroid/os/UserHandle;->semGetMyUserId": ["invoke-static {}, Landroid/os/Process;->myUid()I", "move-result v0", "const v1, 0x186a0", "div-int/2addr v0, v1", "return v0"],
    "Landroid/app/ActivityManager;->semGetCurrentUser": ["invoke-static {}, Landroid/os/Process;->myUid()I", "move-result v0", "const v1, 0x186a0", "div-int/2addr v0, v1", "return v0"],
    # 0 = SEM_DISPLAY_DEVICE_TYPE_MAIN (the inner panel), 5 = _SUB (the cover).
    # A phone with fewer than two device states (a bar phone) has only a main
    # screen: by the width alone (under 600dp = the cover) the S25 Ultra's
    # camera took itself for a Fold's cover, with its layout and rotation
    # (0.4.36 report: shutter off the left edge, icons turned).
    "Landroid/content/res/Configuration;->semDisplayDeviceType": ["const/4 v2, 0x0", ":try_start", "const-string v0, \"device_state\"", "invoke-static {v0}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;", "move-result-object v0", "invoke-static {v0}, Landroid/hardware/devicestate/IDeviceStateManager$Stub;->asInterface(Landroid/os/IBinder;)Landroid/hardware/devicestate/IDeviceStateManager;", "move-result-object v0", "invoke-interface {v0}, Landroid/hardware/devicestate/IDeviceStateManager;->getDeviceStateInfo()Landroid/hardware/devicestate/DeviceStateInfo;", "move-result-object v0", "iget-object v1, v0, Landroid/hardware/devicestate/DeviceStateInfo;->supportedStates:Ljava/util/ArrayList;", "invoke-virtual {v1}, Ljava/util/ArrayList;->size()I", "move-result v1", "add-int/lit8 v1, v1, -0x2", "if-gez v1, :fold", "const/4 v2, 0x1", ":fold", "nop", ":try_end", ".catch Ljava/lang/Exception; {:try_start .. :try_end} :cfg", "goto :decide", ":cfg", "const/4 v2, 0x0", ":decide", "if-nez v2, :main", "iget v0, p0, Landroid/content/res/Configuration;->smallestScreenWidthDp:I", "const/16 v1, 0x258", "if-ge v0, v1, :main", "const/4 v0, 0x5", "return v0", ":main", "const/4 v0, 0x0", "return v0"],
    # One UI: new OutputConfiguration(group, surface, rotation) / (size, class),
    # then mStreamUseCase = scenario << 16, a vendor stream use case that
    # Samsung's HAL reads as the stream's scenario type. Up to run 17 the
    # rotation and the scenario were dropped: "scenarioType(NOT_MATCHED)",
    # "Duplicated ScenarioType", configuring the streams failed (-38) and the
    # camera closed on every mode or lens switch. setStreamUseCase is public.
    "Landroid/hardware/camera2/params/OutputConfiguration;->semCreateOutputConfiguration(ILandroid/view/Surface;II)": ["new-instance v0, Landroid/hardware/camera2/params/OutputConfiguration;", "invoke-direct {v0, p0, p1, p2}, Landroid/hardware/camera2/params/OutputConfiguration;-><init>(ILandroid/view/Surface;I)V", "invoke-static {p3}, Ljava/lang/Integer;->toUnsignedLong(I)J", "move-result-wide v1", "const/16 v3, 0x10", "shl-long/2addr v1, v3", "invoke-virtual {v0, v1, v2}, Landroid/hardware/camera2/params/OutputConfiguration;->setStreamUseCase(J)V", "return-object v0"],
    "Landroid/hardware/camera2/params/OutputConfiguration;->semCreateOutputConfiguration(Landroid/util/Size;Ljava/lang/Class;I)": ["new-instance v0, Landroid/hardware/camera2/params/OutputConfiguration;", "invoke-direct {v0, p0, p1}, Landroid/hardware/camera2/params/OutputConfiguration;-><init>(Landroid/util/Size;Ljava/lang/Class;)V", "invoke-static {p2}, Ljava/lang/Integer;->toUnsignedLong(I)J", "move-result-wide v1", "const/16 v3, 0x10", "shl-long/2addr v1, v3", "invoke-virtual {v0, v1, v2}, Landroid/hardware/camera2/params/OutputConfiguration;->setStreamUseCase(J)V", "return-object v0"],
    "Landroid/view/ViewGroup$MarginLayoutParams;->semSetMarginsRelative": ["invoke-virtual {p0, p1}, Landroid/view/ViewGroup$MarginLayoutParams;->setMarginStart(I)V", "iput p2, p0, Landroid/view/ViewGroup$MarginLayoutParams;->topMargin:I", "invoke-virtual {p0, p3}, Landroid/view/ViewGroup$MarginLayoutParams;->setMarginEnd(I)V", "iput p4, p0, Landroid/view/ViewGroup$MarginLayoutParams;->bottomMargin:I", "return-void"],
    "Landroid/widget/FrameLayout$LayoutParams;->semSetMarginsRelative": ["invoke-virtual {p0, p1}, Landroid/widget/FrameLayout$LayoutParams;->setMarginStart(I)V", "iput p2, p0, Landroid/widget/FrameLayout$LayoutParams;->topMargin:I", "invoke-virtual {p0, p3}, Landroid/widget/FrameLayout$LayoutParams;->setMarginEnd(I)V", "iput p4, p0, Landroid/widget/FrameLayout$LayoutParams;->bottomMargin:I", "return-void"],
    "Landroid/media/AudioManager;->semGetStreamType": ["return {arg0}"],
    "Landroid/media/AudioManager;->semGetSituationVolume": ["const/high16 v0, 0x3f800000", "return v0"],
    "Landroid/media/MediaRecorder;->semGetInputSource": ["return {arg0}"],
    "Landroid/media/MediaRecorder;->semCreateSemPersistentSurface": ["invoke-static {}, Landroid/media/MediaCodec;->createPersistentInputSurface()Landroid/view/Surface;", "move-result-object v0", "return-object v0"],
    "Landroid/view/HapticFeedbackConstants;->semGetVibrationIndex": ["return p0"],
    "Landroid/os/VibrationEffect;->semCreateWaveform": ["const/4 v0, 0x2", "invoke-static {v0}, Landroid/os/VibrationEffect;->createPredefined(I)Landroid/os/VibrationEffect;", "move-result-object v0", "return-object v0"],
    "Landroid/os/Vibrator;->semGetSupportedVibrationType": ["const/4 v0, 0x1", "return v0"],
    # The fold from the device state manager's current state (0, closed: the
    # cover; a phone with fewer than two device states, a bar phone, is
    # never folded: its one state may well be 0), the service
    # looked up by name (DeviceStateManagerGlobal's binder
    # field is private: IllegalAccessError, run 22), else from the screen the
    # system is on. One UI: SEM_LID_STATE_CLOSED 1, SEM_LID_STATE_OPEN 0. A
    # constant 1 said closed on both panels (run 17); the screen alone could say
    # open on the cover (run 21), and run 22 had the values inverted: the camera
    # took the cover for the unfolded phone (Rear Selfie: a mirrored back camera,
    # no lens switch, a layout loop) and unfolded opened the cover's selfie camera.
    "Landroid/hardware/input/InputManager;->semGetLidState": ["const/4 v3, 0x0", "const/4 v2, 0x0", ":try_start", "const-string v0, \"device_state\"", "invoke-static {v0}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;", "move-result-object v0", "invoke-static {v0}, Landroid/hardware/devicestate/IDeviceStateManager$Stub;->asInterface(Landroid/os/IBinder;)Landroid/hardware/devicestate/IDeviceStateManager;", "move-result-object v0", "invoke-interface {v0}, Landroid/hardware/devicestate/IDeviceStateManager;->getDeviceStateInfo()Landroid/hardware/devicestate/DeviceStateInfo;", "move-result-object v0", "iget-object v1, v0, Landroid/hardware/devicestate/DeviceStateInfo;->supportedStates:Ljava/util/ArrayList;", "invoke-virtual {v1}, Ljava/util/ArrayList;->size()I", "move-result v1", "add-int/lit8 v1, v1, -0x2", "if-ltz v1, :decided", "iget-object v0, v0, Landroid/hardware/devicestate/DeviceStateInfo;->currentState:Landroid/hardware/devicestate/DeviceState;", "invoke-virtual {v0}, Landroid/hardware/devicestate/DeviceState;->getIdentifier()I", "move-result v0", ":try_end", ".catch Ljava/lang/Exception; {:try_start .. :try_end} :cfg", "if-nez v0, :decided", "const/4 v3, 0x1", "goto :decided", ":cfg", "const/4 v2, 0x1", "invoke-static {}, Landroid/content/res/Resources;->getSystem()Landroid/content/res/Resources;", "move-result-object v0", "invoke-virtual {v0}, Landroid/content/res/Resources;->getConfiguration()Landroid/content/res/Configuration;", "move-result-object v0", "iget v0, v0, Landroid/content/res/Configuration;->smallestScreenWidthDp:I", "const/16 v1, 0x258", "if-ge v0, v1, :decided", "const/4 v3, 0x1", ":decided", "if-eqz v3, :open", "const/4 v0, 0x1", "return v0", ":open", "const/4 v0, 0x0", "return v0"],
    # isFolded (SemWindowManager.isFolded; the camera's layout everywhere, its
    # q0.p() = !isFolded, 133 callers): 0.4.40, a bar phone reads as folded. This
    # camera is the Z Fold8 Ultra's, and "not folded" is its inner-screen layout:
    # preview on one side, every control in a side column, the shutter cut off
    # (S25+ screenshot, 0.4.40). Folded is its cover layout, a phone's. The lid
    # state above (which camera opens, Rear Selfie) stays open on a bar phone.
    "Landroid/view/IWindowManager;->isFolded": ["const/4 v3, 0x0", "const/4 v2, 0x0", ":try_start", "const-string v0, \"device_state\"", "invoke-static {v0}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;", "move-result-object v0", "invoke-static {v0}, Landroid/hardware/devicestate/IDeviceStateManager$Stub;->asInterface(Landroid/os/IBinder;)Landroid/hardware/devicestate/IDeviceStateManager;", "move-result-object v0", "invoke-interface {v0}, Landroid/hardware/devicestate/IDeviceStateManager;->getDeviceStateInfo()Landroid/hardware/devicestate/DeviceStateInfo;", "move-result-object v0", "iget-object v1, v0, Landroid/hardware/devicestate/DeviceStateInfo;->supportedStates:Ljava/util/ArrayList;", "invoke-virtual {v1}, Ljava/util/ArrayList;->size()I", "move-result v1", "add-int/lit8 v1, v1, -0x2", "if-gez v1, :foldable", "const/4 v3, 0x1", "goto :decided", ":foldable", "iget-object v0, v0, Landroid/hardware/devicestate/DeviceStateInfo;->currentState:Landroid/hardware/devicestate/DeviceState;", "invoke-virtual {v0}, Landroid/hardware/devicestate/DeviceState;->getIdentifier()I", "move-result v0", ":try_end", ".catch Ljava/lang/Exception; {:try_start .. :try_end} :cfg", "if-nez v0, :decided", "const/4 v3, 0x1", "goto :decided", ":cfg", "const/4 v2, 0x1", "invoke-static {}, Landroid/content/res/Resources;->getSystem()Landroid/content/res/Resources;", "move-result-object v0", "invoke-virtual {v0}, Landroid/content/res/Resources;->getConfiguration()Landroid/content/res/Configuration;", "move-result-object v0", "iget v0, v0, Landroid/content/res/Configuration;->smallestScreenWidthDp:I", "const/16 v1, 0x258", "if-ge v0, v1, :decided", "const/4 v3, 0x1", ":decided", "const-string v1, \"OneOSSem\"", "if-eqz v2, :state", "if-eqz v3, :scr_open", "const-string v0, \"isFolded true (screen)\"", "goto :log", ":scr_open", "const-string v0, \"isFolded false (screen)\"", "goto :log", ":state", "if-eqz v3, :st_open", "const-string v0, \"isFolded true (device state)\"", "goto :log", ":st_open", "const-string v0, \"isFolded false (device state)\"", ":log", "invoke-static {v1, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I", "return v3"],
    # Told the current state once; nothing calls it again on a fold (the
    # activity restarts with the new screen).
    "Landroid/hardware/devicestate/DeviceStateManagerGlobal;->registerFoldStateListener": ["if-eqz p1, :done", "const/4 v3, 0x0", "const/4 v2, 0x0", ":try_start", "const-string v0, \"device_state\"", "invoke-static {v0}, Landroid/os/ServiceManager;->getService(Ljava/lang/String;)Landroid/os/IBinder;", "move-result-object v0", "invoke-static {v0}, Landroid/hardware/devicestate/IDeviceStateManager$Stub;->asInterface(Landroid/os/IBinder;)Landroid/hardware/devicestate/IDeviceStateManager;", "move-result-object v0", "invoke-interface {v0}, Landroid/hardware/devicestate/IDeviceStateManager;->getDeviceStateInfo()Landroid/hardware/devicestate/DeviceStateInfo;", "move-result-object v0", "iget-object v1, v0, Landroid/hardware/devicestate/DeviceStateInfo;->supportedStates:Ljava/util/ArrayList;", "invoke-virtual {v1}, Ljava/util/ArrayList;->size()I", "move-result v1", "add-int/lit8 v1, v1, -0x2", "if-ltz v1, :decided", "iget-object v0, v0, Landroid/hardware/devicestate/DeviceStateInfo;->currentState:Landroid/hardware/devicestate/DeviceState;", "invoke-virtual {v0}, Landroid/hardware/devicestate/DeviceState;->getIdentifier()I", "move-result v0", ":try_end", ".catch Ljava/lang/Exception; {:try_start .. :try_end} :cfg", "if-nez v0, :decided", "const/4 v3, 0x1", "goto :decided", ":cfg", "const/4 v2, 0x1", "invoke-static {}, Landroid/content/res/Resources;->getSystem()Landroid/content/res/Resources;", "move-result-object v0", "invoke-virtual {v0}, Landroid/content/res/Resources;->getConfiguration()Landroid/content/res/Configuration;", "move-result-object v0", "iget v0, v0, Landroid/content/res/Configuration;->smallestScreenWidthDp:I", "const/16 v1, 0x258", "if-ge v0, v1, :decided", "const/4 v3, 0x1", ":decided", "invoke-interface {p1, v3}, Lcom/samsung/android/view/SemWindowManager$FoldStateListener;->onFoldStateChanged(Z)V", ":done", "return-void"],
    "Landroid/content/pm/PackageManager;->semGetPackageInfoAsUser": ["invoke-virtual {p0, p1, p2}, Landroid/content/pm/PackageManager;->getPackageInfo(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;", "move-result-object v0", "return-object v0"],
    "Landroid/content/pm/PackageManager;->semGetApplicationIconForIconTray": ["invoke-virtual {p0, p1}, Landroid/content/pm/PackageManager;->getApplicationIcon(Ljava/lang/String;)Landroid/graphics/drawable/Drawable;", "move-result-object v0", "return-object v0"],
    "Landroid/content/pm/PackageManager;->semGetDrawableForIconTray": ["return-object p1"],
    # A File and a String never share a register: the verifier merges them to Object (run 14).
    "Landroid/os/storage/StorageVolume;->semGetPath": ["invoke-virtual {p0}, Landroid/os/storage/StorageVolume;->getDirectory()Ljava/io/File;", "move-result-object v0", "if-nez v0, :have", "const/4 v1, 0x0", "return-object v1", ":have", "invoke-virtual {v0}, Ljava/io/File;->getPath()Ljava/lang/String;", "move-result-object v1", "return-object v1"],
    # The camera writes each picture to a temporary file and moves it into
    # DCIM with this; One UI's StorageManager does the move, the default false
    # dropped every picture (run 19: nothing saved). A plain move (a copy and
    # delete across file systems), replacing what is there.
    "Landroid/os/storage/StorageManager;->semMoveFileAtData": ["const/4 v1, 0x1", "new-array v2, v1, [Ljava/nio/file/CopyOption;", "sget-object v1, Ljava/nio/file/StandardCopyOption;->REPLACE_EXISTING:Ljava/nio/file/StandardCopyOption;", "const/4 v3, 0x0", "aput-object v1, v2, v3", ":try_start", "new-instance v0, Ljava/io/File;", "invoke-direct {v0, p1}, Ljava/io/File;-><init>(Ljava/lang/String;)V", "invoke-virtual {v0}, Ljava/io/File;->toPath()Ljava/nio/file/Path;", "move-result-object v0", "new-instance v1, Ljava/io/File;", "invoke-direct {v1, p2}, Ljava/io/File;-><init>(Ljava/lang/String;)V", "invoke-virtual {v1}, Ljava/io/File;->toPath()Ljava/nio/file/Path;", "move-result-object v1", "invoke-static {v0, v1, v2}, Ljava/nio/file/Files;->move(Ljava/nio/file/Path;Ljava/nio/file/Path;[Ljava/nio/file/CopyOption;)Ljava/nio/file/Path;", ":try_end", ".catch Ljava/lang/Exception; {:try_start .. :try_end} :fail", "const/4 v0, 0x1", "return v0", ":fail", "const/4 v0, 0x0", "return v0"],
    "Landroid/app/Activity;->semIsResumed": ["invoke-virtual {p0}, Landroid/app/Activity;->isResumed()Z", "move-result v0", "return v0"],
    "Landroid/view/accessibility/AccessibilityManager;->semIsScreenReaderEnabled": ["invoke-virtual {p0}, Landroid/view/accessibility/AccessibilityManager;->isTouchExplorationEnabled()Z", "move-result v0", "return v0"],
    "Landroid/os/UserManager;->semIsManagedProfile": ["invoke-virtual {p0}, Landroid/os/UserManager;->isManagedProfile()Z", "move-result v0", "return v0"],
    "Landroid/view/Display;->semGetType": ["invoke-virtual {p0}, Landroid/view/Display;->getType()I", "move-result v0", "return v0"],
}


def default(ret, static, params, owner):
    if ret == "V":
        return ["return-void"]
    if ret in ("J",):
        return ["const-wide/16 v0, 0x0", "return-wide v0"]
    if ret in ("D",):
        return ["const-wide/16 v0, 0x0", "return-wide v0"]
    if ret in ("Z", "B", "S", "C", "I", "F"):
        return ["const/4 v0, 0x0", "return v0"]
    if ret == "Ljava/lang/String;":
        return ['const-string v0, ""', "return-object v0"]
    if ret in ("Ljava/util/List;", "Ljava/util/ArrayList;", "Ljava/util/Collection;"):
        return ["new-instance v0, Ljava/util/ArrayList;", "invoke-direct {v0}, Ljava/util/ArrayList;-><init>()V", "return-object v0"]
    if not static and ret == owner:
        return ["return-object p0"]          # builders and fluent setters
    return ["const/4 v0, 0x0", "return-object v0"]


lines = [".class public final " + "Loneos/semcompat/Sem;", ".super Ljava/lang/Object;", "",
         "# Generated by gen_sem.py: Samsung (sem*) members of the platform's classes that a",
         "# non-Samsung guest framework lacks, as static shims. Rewritten call sites pass the",
         "# receiver first. Safe values only; see SPECIAL for the ones that answer for real.", ""]
seen = set()
for kind, name, sig, ref, what in shims:
    if (name, sig) in seen:
        continue
    seen.add((name, sig))
    owner = ref.split("->")[0]
    member = ref.split("->")[1]
    params = split_params(sig[1:sig.index(")")])
    ret = sig[sig.index(")") + 1:]
    static = kind == "S"
    keyname = owner + "->" + re.split(r"[(]", member)[0]
    keysig = owner + "->" + member[:member.index(")") + 1] if "(" in member else keyname
    body = SPECIAL.get(keysig) or SPECIAL.get(keyname) or default(ret, static, params, owner)
    body = [b.replace("{arg0}", "p0" if static else "p1") for b in body]
    lines.append(".method public static %s%s" % (name, sig))
    lines.append("    .registers %d" % (2 + regs(params) + 2))
    lines += ["    " + b for b in body]
    lines.append(".end method")
    lines.append("")
open(out, "w").write("\n".join(lines))
print("methods:", len(seen))
