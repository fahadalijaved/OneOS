.class public final Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;
.super Ljava/lang/Object;
.source "go/retraceme 35a97f398b6cfa1a7421a322b9cfa3ff6567976d57b6389918337185ab04a49a"

# interfaces
.implements Lcom/android/systemui/Dumpable;


# static fields
.field public static final Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

.field public static final FINGERPRINT_BLOCK_POLICY_ENABLED:Z

.field private static final PERSIST_KEY_BLOCK_FINGERPRINT:Ljava/lang/String; = "persist.sys.block.fingerprint"

.field private static final TAG:Ljava/lang/String; = "OnScreenFingerprintUiMech"

.field private static final shouldResetDisplayPowerOnAuthFailure:Ljava/util/concurrent/atomic/AtomicBoolean;


# instance fields
.field private final bottomAreaControllerLazy:Ldagger/Lazy;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ldagger/Lazy;"
        }
    .end annotation
.end field

.field public bouncerShowing:Z

.field public colorOverride:I

.field private final configurationController:Lcom/android/systemui/statusbar/policy/ConfigurationController;

.field private final configurationListener:Lcom/android/systemui/statusbar/policy/ConfigurationController$ConfigurationListener;

.field private context:Landroid/content/Context;

.field public currentFpIconColor:I

.field private dimLayer:Landroid/widget/ImageView;

.field private final displayListener:Landroid/hardware/display/DisplayManager$DisplayListener;

.field private displayMgr:Landroid/hardware/display/DisplayManager;

.field private final dreamingRunnable:Ljava/lang/Runnable;

.field private final dumpManager:Lcom/android/systemui/dump/DumpManager;

.field private volatile fadeInAlphaAnimation:Landroid/view/animation/AlphaAnimation;

.field private volatile fadeInAlphaAnimationListener:Landroid/view/animation/Animation$AnimationListener;

.field private fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

.field private final fadeInAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

.field private volatile fadeOutAlphaAnimation:Landroid/view/animation/AlphaAnimation;

.field private fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

.field private final fadeOutAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

.field public fadeOutFlag:Z

.field private fingerPrintAnimator:Landroid/animation/AnimatorSet;

.field private fingerPrintColorAnimator:Landroid/animation/Animator;

.field private fpAlphaSpringAnimation:Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

.field public fpColorForOtherAppNoDimLayer:I

.field private fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

.field public fpIconColor:I

.field private fpIconLayout:Landroid/widget/FrameLayout;

.field private fpIconShadow:Landroid/widget/ImageView;

.field private fpIconShadowDrawable:Landroid/graphics/drawable/Drawable;

.field private fpIconShadowDrawableOther:Landroid/graphics/drawable/Drawable;

.field private fpIconShadowOther:Landroid/widget/ImageView;

.field private volatile fpLocation:[I

.field public volatile fpShowReason:I

.field private final fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/concurrent/CopyOnWriteArrayList<",
            "Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$IFpSizeCallback;",
            ">;"
        }
    .end annotation
.end field

.field public hasHideIconByQs:Z

.field public hasInitFp:Z

.field private final hideFingerprintIconRunnable:Ljava/lang/Runnable;

.field public volatile hideImmediately:Z

.field private highLightControl:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

.field private imMobileDrawable:Landroid/graphics/drawable/Drawable;

.field private imMobileDrawableHY:Landroid/graphics/drawable/Drawable;

.field public isFingerprintIconShow:Z

.field public volatile isGoingToSleep:Z

.field public isServiceRequest:Z

.field public isShowFpWhenBouncer:Z

.field public isTPDisable:Z

.field public isTouchDownNow:Z

.field private final keyguardStateCallback:Lcom/android/systemui/statusbar/policy/KeyguardStateController$Callback;

.field private final keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

.field private final keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

.field private final lockScreenExtStateControllerLazy:Ldagger/Lazy;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ldagger/Lazy;"
        }
    .end annotation
.end field

.field private final lockScreenNotificationExtStateManagerLazy:Ldagger/Lazy;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ldagger/Lazy;"
        }
    .end annotation
.end field

.field public mAdjustmentBrightness:Z

.field private mCurBrightness:Ljava/lang/String;

.field public mFingerprintFailCode:I

.field private mFingerprintTouchListener:Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$IFingerprintTouchListener;

.field public volatile needDoFadeInAnimation:Z

.field public volatile notificationDisplayBottom:F

.field private final notificationDisplayRectCallback:Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallback;

.field public volatile notificationDisplayTop:F

.field private final notificationStackScrollLayoutControllerLazy:Ldagger/Lazy;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ldagger/Lazy;"
        }
    .end annotation
.end field

.field public onDozeState:Z

.field public onDreamingStart:Z

.field private final oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

.field private final oplusKeyguardStyleBaseUIControllerLazy:Ldagger/Lazy;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ldagger/Lazy;"
        }
    .end annotation
.end field

.field private opticalUiUpdateHandler:Landroid/os/Handler;

.field private overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

.field public panelExpanded:Z

.field public pendingHide:Z

.field public oneosWakeAt:J

.field private final pictorialMediator:Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;

.field public platformAnimationLevel:I

.field private pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

.field private pressedAnimDrawableTmp:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

.field private final pressedAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

.field private pressedIcon:Landroid/widget/ImageView;

.field private realHideRunnable:Ljava/lang/Runnable;

.field private final screenLifecycle:Lcom/android/systemui/keyguard/ScreenLifecycle;

.field private screenObserver:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$screenObserver$1;

.field public screenTurnedOff:Z

.field private final shadeExpansionListener:Lcom/android/systemui/shade/ShadeExpansionListener;

.field private final shadeExpansionStateManager:Lcom/android/systemui/shade/ShadeExpansionStateManager;

.field public showFingerprintIconDelayedCount:I

.field private showFingerprintIconReason:Ljava/lang/String;

.field private final showFingerprintIconRunnable:Ljava/lang/Runnable;

.field public showForEnroll:Z

.field public showInAOD:I

.field public suggestColor:I

.field private switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

.field private volatile talkToSurfaceFlingerRunable:Ljava/lang/Runnable;

.field private final themeOverlayController:Lcom/android/systemui/theme/ThemeOverlayControllerEx;

.field private touchRunnable:Ljava/lang/Runnable;

.field public touchable:Z

.field private final updateFpIconAlphaRunnable:Ljava/lang/Runnable;

.field private final updateMonitorCallback:Lcom/android/keyguard/KeyguardUpdateMonitorCallback;

.field private final visibilityListeners:Ljava/util/concurrent/CopyOnWriteArrayList;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/concurrent/CopyOnWriteArrayList<",
            "Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$OnFingerprintVisibilityListener;",
            ">;"
        }
    .end annotation
.end field

.field private volatile visibilityRunnable:Ljava/lang/Runnable;

.field private final wakefulnessLifecycle:Lcom/android/systemui/keyguard/WakefulnessLifecycle;

.field private final wakefulnessObserver:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wakefulnessObserver$1;

.field private final wallpaperColorManagerCallback:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wallpaperColorManagerCallback$1;

.field public final windowHideDelayDuration:J

.field private windowManager:Landroid/view/WindowManager;

.field private workerHandler:Landroid/os/Handler;


# direct methods
.method static constructor <clinit>()V
    .locals 2

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-direct {v0}, Ljava/lang/Object;-><init>()V

    sput-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    const-string/jumbo v0, "persist.sys.block.fingerprint"

    const/4 v1, 0x0

    invoke-static {v0, v1}, Landroid/os/SystemProperties;->getBoolean(Ljava/lang/String;Z)Z

    move-result v0

    sput-boolean v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->FINGERPRINT_BLOCK_POLICY_ENABLED:Z

    new-instance v0, Ljava/util/concurrent/atomic/AtomicBoolean;

    invoke-direct {v0, v1}, Ljava/util/concurrent/atomic/AtomicBoolean;-><init>(Z)V

    sput-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->shouldResetDisplayPowerOnAuthFailure:Ljava/util/concurrent/atomic/AtomicBoolean;

    return-void
.end method

.method public constructor <init>(Landroid/content/Context;Lcom/android/keyguard/KeyguardUpdateMonitor;Lcom/android/systemui/keyguard/WakefulnessLifecycle;Lcom/android/systemui/keyguard/ScreenLifecycle;Lcom/android/systemui/statusbar/policy/ConfigurationController;Lcom/android/systemui/statusbar/policy/KeyguardStateController;Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;Lcom/android/systemui/shade/ShadeExpansionStateManager;Lcom/android/systemui/dump/DumpManager;Lcom/android/systemui/theme/ThemeOverlayControllerEx;Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;Ldagger/Lazy;Ldagger/Lazy;Ldagger/Lazy;Ldagger/Lazy;Ldagger/Lazy;)V
    .locals 16
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Landroid/content/Context;",
            "Lcom/android/keyguard/KeyguardUpdateMonitor;",
            "Lcom/android/systemui/keyguard/WakefulnessLifecycle;",
            "Lcom/android/systemui/keyguard/ScreenLifecycle;",
            "Lcom/android/systemui/statusbar/policy/ConfigurationController;",
            "Lcom/android/systemui/statusbar/policy/KeyguardStateController;",
            "Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;",
            "Lcom/android/systemui/shade/ShadeExpansionStateManager;",
            "Lcom/android/systemui/dump/DumpManager;",
            "Lcom/android/systemui/theme/ThemeOverlayControllerEx;",
            "Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;",
            "Ldagger/Lazy;",
            "Ldagger/Lazy;",
            "Ldagger/Lazy;",
            "Ldagger/Lazy;",
            "Ldagger/Lazy;",
            ")V"
        }
    .end annotation

    move-object/from16 v0, p0

    move-object/from16 v1, p2

    move-object/from16 v2, p3

    move-object/from16 v3, p4

    move-object/from16 v4, p5

    move-object/from16 v5, p6

    move-object/from16 v6, p8

    move-object/from16 v7, p9

    move-object/from16 v8, p11

    invoke-direct {v0}, Ljava/lang/Object;-><init>()V

    move-object/from16 v9, p1

    iput-object v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    iput-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    iput-object v2, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->wakefulnessLifecycle:Lcom/android/systemui/keyguard/WakefulnessLifecycle;

    iput-object v3, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenLifecycle:Lcom/android/systemui/keyguard/ScreenLifecycle;

    iput-object v4, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->configurationController:Lcom/android/systemui/statusbar/policy/ConfigurationController;

    iput-object v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    move-object/from16 v10, p7

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    iput-object v6, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->shadeExpansionStateManager:Lcom/android/systemui/shade/ShadeExpansionStateManager;

    iput-object v7, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dumpManager:Lcom/android/systemui/dump/DumpManager;

    move-object/from16 v10, p10

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->themeOverlayController:Lcom/android/systemui/theme/ThemeOverlayControllerEx;

    iput-object v8, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pictorialMediator:Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;

    move-object/from16 v10, p12

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationStackScrollLayoutControllerLazy:Ldagger/Lazy;

    move-object/from16 v10, p13

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->bottomAreaControllerLazy:Ldagger/Lazy;

    move-object/from16 v10, p14

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusKeyguardStyleBaseUIControllerLazy:Ldagger/Lazy;

    move-object/from16 v10, p15

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->lockScreenNotificationExtStateManagerLazy:Ldagger/Lazy;

    move-object/from16 v10, p16

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->lockScreenExtStateControllerLazy:Ldagger/Lazy;

    invoke-static {v9}, Lcom/oplusos/systemui/common/util/ScrimUtil;->isLowGaussianLevel(Landroid/content/Context;)Z

    move-result v9

    if-eqz v9, :cond_0

    const-wide/16 v9, 0x190

    goto :goto_0

    :cond_0
    const-wide/16 v9, 0x64

    :goto_0
    iput-wide v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowHideDelayDuration:J

    new-instance v9, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v10, 0xd

    invoke-direct {v9, v10}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object v0, v9, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIconRunnable:Ljava/lang/Runnable;

    new-instance v9, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$shadeExpansionListener$1;

    invoke-direct {v9}, Ljava/lang/Object;-><init>()V

    iput-object v0, v9, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$shadeExpansionListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->shadeExpansionListener:Lcom/android/systemui/shade/ShadeExpansionListener;

    new-instance v10, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    const/4 v11, 0x7

    invoke-direct {v10, v11}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object v0, v10, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    const/4 v10, 0x1

    iput-boolean v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    const/4 v11, -0x1

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->suggestColor:I

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconColor:I

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->currentFpIconColor:I

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->platformAnimationLevel:I

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mFingerprintFailCode:I

    new-instance v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/4 v13, 0x6

    invoke-direct {v12, v13}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object v0, v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dreamingRunnable:Ljava/lang/Runnable;

    new-instance v12, Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-direct {v12}, Ljava/util/concurrent/CopyOnWriteArrayList;-><init>()V

    iput-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;

    new-instance v12, Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-direct {v12}, Ljava/util/concurrent/CopyOnWriteArrayList;-><init>()V

    iput-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityListeners:Ljava/util/concurrent/CopyOnWriteArrayList;

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showInAOD:I

    const/4 v12, 0x2

    new-array v13, v12, [I

    iput-object v13, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpLocation:[I

    const/high16 v13, -0x40800000    # -1.0f

    iput v13, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayTop:F

    iput v13, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayBottom:F

    new-instance v13, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$displayListener$1;

    invoke-direct {v13}, Ljava/lang/Object;-><init>()V

    iput-object v0, v13, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$displayListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v13, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayListener:Landroid/hardware/display/DisplayManager$DisplayListener;

    new-instance v13, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$configurationListener$1;

    invoke-direct {v13}, Ljava/lang/Object;-><init>()V

    iput-object v0, v13, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$configurationListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v13, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->configurationListener:Lcom/android/systemui/statusbar/policy/ConfigurationController$ConfigurationListener;

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    iput v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpColorForOtherAppNoDimLayer:I

    new-instance v11, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v14, 0x14

    invoke-direct {v11, v14}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object v0, v11, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconRunnable:Ljava/lang/Runnable;

    new-instance v11, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$keyguardStateCallback$1;

    invoke-direct {v11}, Ljava/lang/Object;-><init>()V

    iput-object v0, v11, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$keyguardStateCallback$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateCallback:Lcom/android/systemui/statusbar/policy/KeyguardStateController$Callback;

    new-instance v14, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$notificationDisplayRectCallback$1;

    invoke-direct {v14}, Ljava/lang/Object;-><init>()V

    iput-object v0, v14, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$notificationDisplayRectCallback$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v14, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayRectCallback:Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallback;

    new-instance v14, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateMonitorCallback$1;

    invoke-direct {v14}, Ljava/lang/Object;-><init>()V

    iput-object v0, v14, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateMonitorCallback$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v14, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateMonitorCallback:Lcom/android/keyguard/KeyguardUpdateMonitorCallback;

    new-instance v14, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wakefulnessObserver$1;

    invoke-direct {v14}, Ljava/lang/Object;-><init>()V

    iput-object v0, v14, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wakefulnessObserver$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v14, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->wakefulnessObserver:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wakefulnessObserver$1;

    new-instance v15, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$screenObserver$1;

    invoke-direct {v15}, Ljava/lang/Object;-><init>()V

    iput-object v0, v15, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$screenObserver$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v15, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenObserver:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$screenObserver$1;

    new-instance v15, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;

    invoke-direct {v15, v12}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;-><init>(I)V

    iput-object v0, v15, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v15, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    new-instance v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;

    const/4 v15, 0x0

    invoke-direct {v12, v15}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;-><init>(I)V

    iput-object v0, v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    new-instance v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;

    invoke-direct {v12, v10}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;-><init>(I)V

    iput-object v0, v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fadeInAnimationDrawableListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    new-instance v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wallpaperColorManagerCallback$1;

    invoke-direct {v12}, Ljava/lang/Object;-><init>()V

    iput-object v0, v12, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wallpaperColorManagerCallback$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->wallpaperColorManagerCallback:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wallpaperColorManagerCallback$1;

    sget-object v12, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v12}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getWorkHandler()Landroid/os/Handler;

    move-result-object v10

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->workerHandler:Landroid/os/Handler;

    invoke-virtual {v12}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getOpticalUiUpdateHandler()Landroid/os/Handler;

    move-result-object v10

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    invoke-static {}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->initFingerSizeProp()V

    iget-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const-string/jumbo v12, "window"

    invoke-virtual {v10, v12}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v10

    check-cast v10, Landroid/view/WindowManager;

    iput-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    check-cast v5, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    invoke-virtual {v5, v11}, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->addCallback(Ljava/lang/Object;)V

    new-instance v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    iget-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v5, v10, v1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;-><init>(Landroid/content/Context;Lcom/android/keyguard/KeyguardUpdateMonitor;Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    iput-object v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->highLightControl:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    sget-object v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper$Companion;

    iget-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v5, v10}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    move-result-object v5

    iput-object v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    iget-object v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const-string/jumbo v10, "power"

    invoke-virtual {v5, v10}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v5

    check-cast v5, Landroid/os/PowerManager;

    invoke-virtual {v5}, Landroid/os/PowerManager;->isInteractive()Z

    move-result v10

    xor-int/lit8 v11, v10, 0x1

    iput-boolean v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenTurnedOff:Z

    if-nez v10, :cond_1

    const-string v10, "OnScreenFingerprintUiMech"

    const-string v11, "SystemUI reboot while screen off !!!"

    invoke-static {v10, v11}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v10

    iget-object v12, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const v15, 0x7f1315f5

    invoke-virtual {v12, v15}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    move-result-object v12

    const/16 v15, 0xb

    invoke-virtual {v5, v10, v11, v15, v12}, Landroid/os/PowerManager;->wakeUp(JILjava/lang/String;)V

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v10

    const/4 v12, 0x0

    invoke-virtual {v5, v10, v11, v15, v12}, Landroid/os/PowerManager;->goToSleep(JII)V

    sget-object v5, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->Companion:Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;

    iget-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v5, v10}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;->isFingerprintSwitchOn(Landroid/content/Context;)Z

    move-result v5

    if-eqz v5, :cond_1

    const/4 v5, 0x1

    iput-boolean v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    :cond_1
    iget-object v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v5}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->initNavigationBarAdjust(Landroid/content/Context;)V

    new-instance v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/4 v12, 0x0

    invoke-direct {v5, v12}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object v0, v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v5}, Lcom/oplusos/systemui/common/util/SystemUIThreadUtil;->runOnUiThread(Ljava/lang/Runnable;)Z

    new-instance v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    iget-object v10, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v5, v10, v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;-><init>(Landroid/content/Context;Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Lcom/android/keyguard/KeyguardUpdateMonitor;)V

    iput-object v5, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    invoke-virtual {v2, v14}, Lcom/android/systemui/keyguard/Lifecycle;->addObserver(Ljava/lang/Object;)V

    iget-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenObserver:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$screenObserver$1;

    invoke-virtual {v3, v1}, Lcom/android/systemui/keyguard/Lifecycle;->addObserver(Ljava/lang/Object;)V

    invoke-interface {v4, v13}, Lcom/android/systemui/statusbar/policy/CallbackController;->addCallback(Ljava/lang/Object;)V

    invoke-virtual {v6, v9}, Lcom/android/systemui/shade/ShadeExpansionStateManager;->addExpansionListener(Lcom/android/systemui/shade/ShadeExpansionListener;)Lcom/android/systemui/shade/ShadeExpansionChangeEvent;

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v2, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v1

    invoke-virtual {v1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->setOnScreenFingerprintUiMech(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    invoke-virtual {v8, v0}, Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;->setOnScreenFingerprintUiMech(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    iget-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->calculateFpIconSizeParams(Landroid/content/Context;)V

    invoke-interface {v7, v0}, Lcom/android/systemui/dump/DumpManager;->registerDumpable(Lcom/android/systemui/Dumpable;)V

    iget-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const-string v2, "display"

    invoke-virtual {v1, v2}, Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v1

    instance-of v2, v1, Landroid/hardware/display/DisplayManager;

    if-eqz v2, :cond_2

    check-cast v1, Landroid/hardware/display/DisplayManager;

    goto :goto_1

    :cond_2
    const/4 v1, 0x0

    :goto_1
    iput-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayMgr:Landroid/hardware/display/DisplayManager;

    new-instance v1, Landroid/view/animation/AlphaAnimation;

    const/4 v2, 0x0

    const/high16 v3, 0x3f800000    # 1.0f

    invoke-direct {v1, v2, v3}, Landroid/view/animation/AlphaAnimation;-><init>(FF)V

    iput-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$2;

    invoke-direct {v1}, Ljava/lang/Object;-><init>()V

    iput-object v0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$2;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAlphaAnimationListener:Landroid/view/animation/Animation$AnimationListener;

    iget-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    if-eqz v1, :cond_3

    iget-object v4, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAlphaAnimationListener:Landroid/view/animation/Animation$AnimationListener;

    invoke-virtual {v1, v4}, Landroid/view/animation/AlphaAnimation;->setAnimationListener(Landroid/view/animation/Animation$AnimationListener;)V

    :cond_3
    iget-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    const-wide/16 v4, 0x1f4

    if-eqz v1, :cond_4

    invoke-virtual {v1, v4, v5}, Landroid/view/animation/AlphaAnimation;->setDuration(J)V

    :cond_4
    new-instance v1, Landroid/view/animation/AlphaAnimation;

    invoke-direct {v1, v3, v2}, Landroid/view/animation/AlphaAnimation;-><init>(FF)V

    iput-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    iget-object v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    if-eqz v0, :cond_5

    invoke-virtual {v0, v4, v5}, Landroid/view/animation/AlphaAnimation;->setDuration(J)V

    :cond_5
    return-void
.end method

.method public static final access$addNotificationDisplayRectCallback(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->lockScreenNotificationExtStateManagerLazy:Ldagger/Lazy;

    invoke-interface {v0}, Ldagger/Lazy;->get()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/oplus/systemui/notification/lockscreen/statemanager/LockScreenNotificationExtStateManager;

    invoke-virtual {v0}, Lcom/oplus/systemui/notification/lockscreen/statemanager/LockScreenNotificationExtStateManager;->getNotificationDisplayRectCallbackWrapper()Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallbackWrapper;

    move-result-object v0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayRectCallback:Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallback;

    sget-object v1, Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallbackWrapper;->Companion:Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallbackWrapper$Companion;

    const/4 v1, 0x1

    invoke-virtual {v0, p0, v1}, Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallbackWrapper;->addNotificationDisplayRectCallback(Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallback;Z)V

    return-void
.end method

.method public static final access$delayHide(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 4

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIconRunnable:Ljava/lang/Runnable;

    invoke-virtual {v0, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_1

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIconRunnable:Ljava/lang/Runnable;

    iget-wide v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowHideDelayDuration:J

    invoke-virtual {v0, v1, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_1
    return-void
.end method

.method public static final synthetic access$getBottomAreaRect(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/Rect;
    .locals 0

    invoke-direct {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getBottomAreaRect()Landroid/graphics/Rect;

    move-result-object p0

    return-object p0
.end method

.method public static final synthetic access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    return-object p0
.end method

.method public static final synthetic access$getDisplayMgr$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/hardware/display/DisplayManager;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayMgr:Landroid/hardware/display/DisplayManager;

    return-object p0
.end method

.method public static final synthetic access$getDreamingRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/Runnable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dreamingRunnable:Ljava/lang/Runnable;

    return-object p0
.end method

.method public static final synthetic access$getFadeInAlphaAnimation$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/view/animation/AlphaAnimation;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    return-object p0
.end method

.method public static final synthetic access$getFadeInAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    return-object p0
.end method

.method public static final synthetic access$getFadeInAnimationDrawableListener$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    return-object p0
.end method

.method public static final synthetic access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    return-object p0
.end method

.method public static final synthetic access$getFadeOutAnimationDrawableListener$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    return-object p0
.end method

.method public static final synthetic access$getFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/AnimatorSet;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fingerPrintAnimator:Landroid/animation/AnimatorSet;

    return-object p0
.end method

.method public static final synthetic access$getFingerPrintColorAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/Animator;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fingerPrintColorAnimator:Landroid/animation/Animator;

    return-object p0
.end method

.method public static final synthetic access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    return-object p0
.end method

.method public static final synthetic access$getFpIconRect(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/Rect;
    .locals 0

    invoke-direct {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getFpIconRect()Landroid/graphics/Rect;

    move-result-object p0

    return-object p0
.end method

.method public static final synthetic access$getFpIconShadow$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    return-object p0
.end method

.method public static final synthetic access$getFpIconShadowDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowDrawable:Landroid/graphics/drawable/Drawable;

    return-object p0
.end method

.method public static final synthetic access$getFpIconShadowOther$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    return-object p0
.end method

.method public static final synthetic access$getFpLocation$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)[I
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpLocation:[I

    return-object p0
.end method

.method public static final synthetic access$getHideFingerprintIconRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/Runnable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIconRunnable:Ljava/lang/Runnable;

    return-object p0
.end method

.method public static final synthetic access$getHighLightControl$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->highLightControl:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    return-object p0
.end method

.method public static final synthetic access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawable:Landroid/graphics/drawable/Drawable;

    return-object p0
.end method

.method public static final synthetic access$getKeyguardStateController$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/android/systemui/statusbar/policy/KeyguardStateController;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    return-object p0
.end method

.method public static final synthetic access$getKeyguardUpdateMonitor$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/android/keyguard/KeyguardUpdateMonitor;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    return-object p0
.end method

.method public static final synthetic access$getLockScreenExtStateControllerLazy$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ldagger/Lazy;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->lockScreenExtStateControllerLazy:Ldagger/Lazy;

    return-object p0
.end method

.method public static final synthetic access$getOplusBiometricAuthController$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    return-object p0
.end method

.method public static final synthetic access$getOpticalUiUpdateHandler$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/os/Handler;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    return-object p0
.end method

.method public static final synthetic access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    return-object p0
.end method

.method public static final synthetic access$getPressedAnimDrawableTmp$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawableTmp:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    return-object p0
.end method

.method public static final synthetic access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    return-object p0
.end method

.method public static final synthetic access$getShouldResetDisplayPowerOnAuthFailure$cp()Ljava/util/concurrent/atomic/AtomicBoolean;
    .locals 1

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->shouldResetDisplayPowerOnAuthFailure:Ljava/util/concurrent/atomic/AtomicBoolean;

    return-object v0
.end method

.method public static final synthetic access$getShowFingerprintIconReason$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/String;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconReason:Ljava/lang/String;

    return-object p0
.end method

.method public static final synthetic access$getSwitchHelper$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    return-object p0
.end method

.method public static final synthetic access$getUpdateFpIconAlphaRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/Runnable;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    return-object p0
.end method

.method public static final synthetic access$getUpdateMonitorCallback$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/android/keyguard/KeyguardUpdateMonitorCallback;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateMonitorCallback:Lcom/android/keyguard/KeyguardUpdateMonitorCallback;

    return-object p0
.end method

.method public static final synthetic access$getWorkerHandler$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/os/Handler;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->workerHandler:Landroid/os/Handler;

    return-object p0
.end method

.method public static final access$initWindow(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 18

    move-object/from16 v2, p0

    const-string v6, "OnScreenFingerprintUiMech"

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_0

    return-void

    :cond_0
    const-string v0, "init window"

    invoke-static {v6, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v0

    const/4 v7, -0x2

    invoke-virtual {v0, v7}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->registerObserver(I)V

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportOpticalFps()Z

    move-result v0

    const/16 v8, 0x8

    const/4 v9, -0x1

    const v10, 0x20000010

    const/16 v11, 0x90b

    const/4 v13, 0x1

    if-eqz v0, :cond_6

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isDisableAppDimLayer()Z

    move-result v0

    if-eqz v0, :cond_1

    goto :goto_1

    :cond_1
    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v0

    if-eqz v0, :cond_2

    goto :goto_1

    :cond_2
    const-string v0, "initDimLayerWin"

    invoke-static {v6, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    new-instance v0, Landroid/view/WindowManager$LayoutParams;

    invoke-direct {v0}, Landroid/view/WindowManager$LayoutParams;-><init>()V

    const-string v1, "OnScreenFingerprintDimLayer"

    invoke-virtual {v0, v1}, Landroid/view/WindowManager$LayoutParams;->setTitle(Ljava/lang/CharSequence;)V

    iput v11, v0, Landroid/view/WindowManager$LayoutParams;->type:I

    iput v7, v0, Landroid/view/WindowManager$LayoutParams;->format:I

    iget v1, v0, Landroid/view/WindowManager$LayoutParams;->flags:I

    const v3, 0x9000518

    or-int/2addr v1, v3

    iput v1, v0, Landroid/view/WindowManager$LayoutParams;->flags:I

    iget v1, v0, Landroid/view/WindowManager$LayoutParams;->privateFlags:I

    or-int/2addr v1, v10

    iput v1, v0, Landroid/view/WindowManager$LayoutParams;->privateFlags:I

    iput v13, v0, Landroid/view/WindowManager$LayoutParams;->layoutInDisplayCutoutMode:I

    iput v9, v0, Landroid/view/WindowManager$LayoutParams;->windowAnimations:I

    new-instance v1, Landroid/widget/ImageView;

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v1, v3}, Landroid/widget/ImageView;-><init>(Landroid/content/Context;)V

    iput-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dimLayer:Landroid/widget/ImageView;

    new-instance v3, Landroid/graphics/drawable/ColorDrawable;

    const/high16 v4, -0x1000000

    invoke-direct {v3, v4}, Landroid/graphics/drawable/ColorDrawable;-><init>(I)V

    invoke-virtual {v1, v3}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dimLayer:Landroid/widget/ImageView;

    if-eqz v1, :cond_4

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->highLightControl:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    if-eqz v3, :cond_3

    monitor-enter v3

    :try_start_0
    iget-boolean v4, v3, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;->isHighlightEnable:Z
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    monitor-exit v3

    if-ne v4, v13, :cond_3

    const/4 v3, 0x0

    goto :goto_0

    :catchall_0
    move-exception v0

    :try_start_1
    monitor-exit v3
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    throw v0

    :cond_3
    move v3, v8

    :goto_0
    invoke-virtual {v1, v3}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_4
    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz v1, :cond_5

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dimLayer:Landroid/widget/ImageView;

    invoke-interface {v1, v3, v0}, Landroid/view/WindowManager;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_5
    invoke-static {v13}, Lcom/oplus/systemui/aod/aodclock/util/CommonUtils;->setHasDimLayer(Z)V

    :cond_6
    :goto_1
    const-string v0, "initFpIconWin"

    invoke-static {v6, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v0

    if-nez v0, :cond_7

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUltrasonicFps()Z

    move-result v0

    if-eqz v0, :cond_8

    :cond_7
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const v1, 0x7f0607b9

    invoke-virtual {v0, v1}, Landroid/content/Context;->getColor(I)I

    move-result v0

    iput v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpColorForOtherAppNoDimLayer:I

    :cond_8
    new-instance v14, Landroid/view/WindowManager$LayoutParams;

    invoke-direct {v14}, Landroid/view/WindowManager$LayoutParams;-><init>()V

    const-string v0, "OnScreenFingerprintIcon"

    invoke-virtual {v14, v0}, Landroid/view/WindowManager$LayoutParams;->setTitle(Ljava/lang/CharSequence;)V

    const/16 v0, 0x438

    iput v0, v14, Landroid/view/WindowManager$LayoutParams;->width:I

    iput v0, v14, Landroid/view/WindowManager$LayoutParams;->height:I

    sget-object v15, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v15}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v0

    add-int/lit16 v0, v0, -0x21c

    iput v0, v14, Landroid/view/WindowManager$LayoutParams;->y:I

    const/16 v0, 0x51

    iput v0, v14, Landroid/view/WindowManager$LayoutParams;->gravity:I

    iput v7, v14, Landroid/view/WindowManager$LayoutParams;->format:I

    iput v9, v14, Landroid/view/WindowManager$LayoutParams;->windowAnimations:I

    iput v11, v14, Landroid/view/WindowManager$LayoutParams;->type:I

    iget v1, v14, Landroid/view/WindowManager$LayoutParams;->flags:I

    or-int/lit16 v1, v1, 0x738

    const v3, -0x1000001

    and-int/2addr v1, v3

    iput v1, v14, Landroid/view/WindowManager$LayoutParams;->flags:I

    iget v1, v14, Landroid/view/WindowManager$LayoutParams;->privateFlags:I

    or-int/2addr v1, v10

    iput v1, v14, Landroid/view/WindowManager$LayoutParams;->privateFlags:I

    iput v13, v14, Landroid/view/WindowManager$LayoutParams;->screenOrientation:I

    new-instance v1, Landroid/widget/FrameLayout;

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v1, v3}, Landroid/widget/FrameLayout;-><init>(Landroid/content/Context;)V

    iput-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    new-instance v1, Landroid/view/ViewGroup$LayoutParams;

    invoke-direct {v1, v9, v9}, Landroid/view/ViewGroup$LayoutParams;-><init>(II)V

    new-instance v3, Landroid/widget/ImageView;

    iget-object v4, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v3, v4}, Landroid/widget/ImageView;-><init>(Landroid/content/Context;)V

    iput-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v3}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v3

    sget-object v4, Landroidx/core/content/res/ResourcesCompat;->sTempTypedValue:Ljava/lang/ThreadLocal;

    const v4, 0x7f08116a

    const/4 v5, 0x0

    invoke-virtual {v3, v4, v5}, Landroid/content/res/Resources;->getDrawable(ILandroid/content/res/Resources$Theme;)Landroid/graphics/drawable/Drawable;

    move-result-object v3

    iput-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowDrawable:Landroid/graphics/drawable/Drawable;

    if-eqz v3, :cond_9

    iget-object v4, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v4, :cond_9

    invoke-virtual {v4, v3}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_9
    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v3, :cond_a

    invoke-virtual {v3, v1}, Landroid/widget/ImageView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    :cond_a
    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v3, :cond_b

    invoke-virtual {v3, v8}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_b
    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v3, :cond_c

    iget-object v4, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    if-eqz v4, :cond_c

    invoke-virtual {v4, v3}, Landroid/widget/FrameLayout;->addView(Landroid/view/View;)V

    :cond_c
    new-instance v3, Landroid/view/ViewGroup$LayoutParams;

    invoke-direct {v3, v9, v9}, Landroid/view/ViewGroup$LayoutParams;-><init>(II)V

    new-instance v4, Landroid/widget/ImageView;

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v4, v0}, Landroid/widget/ImageView;-><init>(Landroid/content/Context;)V

    iput-object v4, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    const v4, 0x7f08111e

    invoke-virtual {v0, v4, v5}, Landroid/content/res/Resources;->getDrawable(ILandroid/content/res/Resources$Theme;)Landroid/graphics/drawable/Drawable;

    move-result-object v0

    iput-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowDrawableOther:Landroid/graphics/drawable/Drawable;

    if-eqz v0, :cond_d

    iget-object v4, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v4, :cond_d

    invoke-virtual {v4, v0}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_d
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v0, :cond_e

    invoke-virtual {v0, v3}, Landroid/widget/ImageView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    :cond_e
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v0, :cond_f

    invoke-virtual {v0, v8}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_f
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v0, :cond_10

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    if-eqz v3, :cond_10

    invoke-virtual {v3, v0}, Landroid/widget/FrameLayout;->addView(Landroid/view/View;)V

    :cond_10
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-object v3, v1

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    move-object v4, v3

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    move-object v5, v4

    iget-object v4, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    move-object/from16 v16, v5

    iget-object v5, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    move/from16 v17, v10

    move-object/from16 v10, v16

    const/16 v12, 0x51

    invoke-direct/range {v0 .. v5}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;-><init>(Landroid/content/Context;Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Lcom/android/keyguard/KeyguardUpdateMonitor;Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;Landroid/widget/FrameLayout;)V

    iput-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$initFpIconWin$5;

    invoke-direct {v1}, Ljava/lang/Object;-><init>()V

    iput-object v2, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$initFpIconWin$5;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->addOnLayoutChangeListener(Landroid/view/View$OnLayoutChangeListener;)V

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_11

    invoke-virtual {v0, v10}, Landroid/widget/ImageView;->setLayoutParams(Landroid/view/ViewGroup$LayoutParams;)V

    :cond_11
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_12

    invoke-virtual {v0, v8}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->setVisibility(I)V

    :cond_12
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_13

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    if-eqz v1, :cond_13

    invoke-virtual {v1, v0}, Landroid/widget/FrameLayout;->addView(Landroid/view/View;)V

    :cond_13
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz v0, :cond_14

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    invoke-interface {v0, v1, v14}, Landroid/view/WindowManager;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_14
    const-string v0, "initPressedIconWin"

    invoke-static {v6, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {v15}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getPressedIconSize()I

    move-result v0

    new-instance v1, Landroid/view/WindowManager$LayoutParams;

    invoke-direct {v1}, Landroid/view/WindowManager$LayoutParams;-><init>()V

    const-string v3, "OnScreenFingerprintPressedIcon"

    invoke-virtual {v1, v3}, Landroid/view/WindowManager$LayoutParams;->setTitle(Ljava/lang/CharSequence;)V

    add-int/lit8 v3, v0, 0x64

    iput v3, v1, Landroid/view/WindowManager$LayoutParams;->width:I

    iput v3, v1, Landroid/view/WindowManager$LayoutParams;->height:I

    invoke-virtual {v15}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v3

    div-int/lit8 v0, v0, 0x2

    sub-int/2addr v3, v0

    iput v3, v1, Landroid/view/WindowManager$LayoutParams;->y:I

    iput v12, v1, Landroid/view/WindowManager$LayoutParams;->gravity:I

    iput v7, v1, Landroid/view/WindowManager$LayoutParams;->format:I

    iput v9, v1, Landroid/view/WindowManager$LayoutParams;->windowAnimations:I

    iput v11, v1, Landroid/view/WindowManager$LayoutParams;->type:I

    iget v0, v1, Landroid/view/WindowManager$LayoutParams;->flags:I

    or-int/lit16 v0, v0, 0x518

    iput v0, v1, Landroid/view/WindowManager$LayoutParams;->flags:I

    iget v0, v1, Landroid/view/WindowManager$LayoutParams;->privateFlags:I

    or-int v0, v0, v17

    iput v0, v1, Landroid/view/WindowManager$LayoutParams;->privateFlags:I

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintPressedIcon;

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v0, v3}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintPressedIcon;-><init>(Landroid/content/Context;)V

    iput-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    invoke-virtual {v0, v8}, Landroid/widget/ImageView;->setVisibility(I)V

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz v0, :cond_15

    iget-object v3, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    invoke-interface {v0, v3, v1}, Landroid/view/WindowManager;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_15
    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconSize()V

    new-instance v0, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    sget-object v3, Lcom/coui/appcompat/animation/dynamicanimation/COUIDynamicAnimation;->ALPHA:Lcom/coui/appcompat/animation/dynamicanimation/COUIDynamicAnimation$1;

    invoke-direct {v0, v3, v1}, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;-><init>(Landroidx/dynamicanimation/animation/FloatPropertyCompat;Ljava/lang/Object;)V

    iput-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpAlphaSpringAnimation:Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    invoke-virtual {v0, v13}, Lcom/coui/appcompat/animation/dynamicanimation/COUIDynamicAnimation;->setEnableNonMainThread(Z)Lcom/coui/appcompat/animation/dynamicanimation/COUIDynamicAnimation;

    move-result-object v0

    check-cast v0, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpAlphaSpringAnimation:Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    if-eqz v0, :cond_16

    new-instance v1, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;

    invoke-direct {v1}, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;-><init>()V

    const/4 v3, 0x0

    invoke-virtual {v1, v3}, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;->setBounce(F)Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;

    move-result-object v1

    const/high16 v3, 0x3f000000    # 0.5f

    invoke-virtual {v1, v3}, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;->setResponse(F)Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;

    move-result-object v1

    invoke-virtual {v0, v1}, Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;->setSpring(Lcom/coui/appcompat/animation/dynamicanimation/COUISpringForce;)Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    :cond_16
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$initWindow$endListener$1;

    invoke-direct {v0}, Ljava/lang/Object;-><init>()V

    iput-object v2, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$initWindow$endListener$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpAlphaSpringAnimation:Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    if-eqz v1, :cond_17

    invoke-virtual {v1, v0}, Lcom/coui/appcompat/animation/dynamicanimation/COUIDynamicAnimation;->addEndListener(Lcom/coui/appcompat/animation/dynamicanimation/COUIDynamicAnimation$OnAnimationEndListener;)V

    :cond_17
    iput-boolean v13, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasInitFp:Z

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_19

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isNewStyle:Z

    if-ne v0, v13, :cond_19

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v0, :cond_18

    const-string/jumbo v1, "optical_fp_anim_style_icon"

    const/4 v3, 0x0

    invoke-virtual {v0, v3, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->enableOrCheckOverlayAnim(ZLjava/lang/String;)V

    goto :goto_2

    :cond_18
    const/4 v3, 0x0

    :goto_2
    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v0, :cond_1a

    const-string/jumbo v1, "optical_fp_anim_style_press"

    invoke-virtual {v0, v3, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->enableOrCheckOverlayAnim(ZLjava/lang/String;)V

    goto :goto_3

    :cond_19
    const/4 v3, 0x0

    iget-object v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v0, :cond_1a

    const-string/jumbo v1, "optical_fp_anim_style"

    invoke-virtual {v0, v3, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->enableOrCheckOverlayAnim(ZLjava/lang/String;)V

    :cond_1a
    :goto_3
    sget-object v0, Lcom/oplus/systemui/keyguard/wallpaper/OplusWallpaperColorManager;->INSTANCE:Lcom/oplus/systemui/keyguard/wallpaper/OplusWallpaperColorManager;

    iget-object v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    iget-object v2, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->wallpaperColorManagerCallback:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$wallpaperColorManagerCallback$1;

    invoke-virtual {v0, v1, v2}, Lcom/oplus/systemui/keyguard/wallpaper/OplusWallpaperColorManager;->addCallback(Landroid/content/Context;Lcom/oplus/systemui/keyguard/wallpaper/OplusWallpaperColorManagerCallback;)V

    return-void
.end method

.method public static final access$needInterruptAnim(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Z
    .locals 1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {p0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintAuthenticated()Z

    move-result p0

    const/4 v0, 0x1

    if-eqz p0, :cond_1

    sget-object p0, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    invoke-virtual {p0}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getANIM_LEVEL()I

    move-result p0

    if-ne p0, v0, :cond_1

    sget-object p0, Lcom/oplusos/systemui/common/feature/FeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/FeatureOption;

    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/FeatureOption;->isLightOs()Z

    move-result p0

    if-eqz p0, :cond_0

    goto :goto_0

    :cond_0
    const/4 p0, 0x0

    return p0

    :cond_1
    :goto_0
    return v0
.end method

.method public static final access$onDreamingStart(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    iget-boolean v0, v0, Lcom/android/keyguard/KeyguardUpdateMonitor;->mIsDreaming:Z

    if-nez v0, :cond_0

    const-string p0, "OnScreenFingerprintUiMech"

    const-string/jumbo v0, "onDreamingStart just call on dreaming state"

    invoke-static {p0, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return-void

    :cond_0
    const-string v0, "OnScreenFingerprintUiMech"

    const-string/jumbo v1, "onDreamingStart()"

    invoke-static {v0, v1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    const/4 v0, 0x0

    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isGoingToSleep:Z

    const/4 v1, 0x1

    iput-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDozeState:Z

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v1}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result v1

    if-eqz v1, :cond_1

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v1}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isFpClientStop()Z

    move-result v1

    if-nez v1, :cond_1

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v1

    invoke-virtual {v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isFpDelayUntilDozeAodProcessType()Z

    move-result v1

    if-nez v1, :cond_1

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconAnimation(Z)V

    :cond_1
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayListener:Landroid/hardware/display/DisplayManager$DisplayListener;

    monitor-enter v0

    :try_start_0
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v1, :cond_2

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayMgr:Landroid/hardware/display/DisplayManager;

    if-eqz v2, :cond_2

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayListener:Landroid/hardware/display/DisplayManager$DisplayListener;

    invoke-virtual {v2, p0, v1}, Landroid/hardware/display/DisplayManager;->registerDisplayListener(Landroid/hardware/display/DisplayManager$DisplayListener;Landroid/os/Handler;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception p0

    goto :goto_1

    :cond_2
    :goto_0
    monitor-exit v0

    return-void

    :goto_1
    monitor-exit v0

    throw p0
.end method

.method public static final access$onDreamingStopped(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 5

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/4 v1, 0x0

    const/4 v2, 0x1

    if-eqz v0, :cond_0

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    if-ne v0, v2, :cond_0

    goto :goto_0

    :cond_0
    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    sget-boolean v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isFpBlindUnlockEnabled:Z

    if-eqz v0, :cond_2

    :goto_0
    const-string v0, "OnScreenFingerprintUiMech"

    const-string/jumbo v3, "onDreamingStop()"

    invoke-static {v0, v3}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iput-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isGoingToSleep:Z

    iput-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    iput-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDozeState:Z

    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v3}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->updateFingerprintIconAlpha()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayListener:Landroid/hardware/display/DisplayManager$DisplayListener;

    monitor-enter v0

    :try_start_0
    iget-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayMgr:Landroid/hardware/display/DisplayManager;

    if-eqz v3, :cond_1

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->displayListener:Landroid/hardware/display/DisplayManager$DisplayListener;

    invoke-virtual {v3, v4}, Landroid/hardware/display/DisplayManager;->unregisterDisplayListener(Landroid/hardware/display/DisplayManager$DisplayListener;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_1

    :catchall_0
    move-exception p0

    goto :goto_2

    :cond_1
    :goto_1
    monitor-exit v0

    goto :goto_3

    :goto_2
    monitor-exit v0

    throw p0

    :cond_2
    :goto_3
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result v0

    if-eqz v0, :cond_3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isFpClientStop()Z

    move-result v0

    if-nez v0, :cond_3

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-nez v0, :cond_3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isKeyguardVisible$1()Z

    move-result v0

    if-eqz v0, :cond_3

    invoke-virtual {p0, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconAnimation(Z)V

    goto :goto_4

    :cond_3
    const-string/jumbo v0, "onDreamingStopped"

    new-instance v3, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;

    const/4 v4, 0x2

    invoke-direct {v3, v4}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;-><init>(I)V

    iput-object p0, v3, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-object v0, v3, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;->$filter:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v3}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :goto_4
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v2, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->$focus:Z

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void
.end method

.method public static final access$onPressedAnimEnd(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 3

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    const-string/jumbo v1, "onPressedAnimEnd paddingHide="

    const-string v2, "OnScreenFingerprintUiMech"

    invoke-static {v1, v2, v0}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Z)V

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2, v1}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    if-eqz v0, :cond_0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIcon()V

    :cond_0
    return-void
.end method

.method public static final access$onScreenTurnedOff(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 2

    const-string v0, "OnScreenFingerprintUiMech"

    const-string/jumbo v1, "onScreenTurnedOff()"

    invoke-static {v0, v1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->updateFingerprintIconAlpha()V

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-nez v0, :cond_0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopOpticalAnimation()V

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    check-cast v0, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    iget-boolean v0, v0, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->mOccluded:Z

    if-eqz v0, :cond_1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result v0

    if-nez v0, :cond_1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    const/4 v0, 0x2

    invoke-virtual {p0, v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->updateFingerprintListeningState(I)V

    :cond_1
    return-void
.end method

.method public static final access$onScreenTurnedOn(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 2

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z

    const-string v1, "OnScreenFingerprintUiMech"

    if-eqz v0, :cond_1

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-nez v0, :cond_1

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-nez v0, :cond_1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isKeyguardVisible$1()Z

    move-result v0

    if-eqz v0, :cond_1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Landroid/widget/ImageView;->getVisibility()I

    move-result v0

    if-nez v0, :cond_0

    goto :goto_0

    :cond_0
    const-string/jumbo v0, "onScreenTurnedOn, but fp icon not visible, check again."

    invoke-static {v1, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    const/4 v0, 0x1

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconAnimation(Z)V

    return-void

    :cond_1
    :goto_0
    const-string/jumbo p0, "onScreenTurnedOn()"

    invoke-static {v1, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method

.method public static final access$removeNotificationDisplayRectCallback(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->lockScreenNotificationExtStateManagerLazy:Ldagger/Lazy;

    invoke-interface {v0}, Ldagger/Lazy;->get()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/oplus/systemui/notification/lockscreen/statemanager/LockScreenNotificationExtStateManager;

    invoke-virtual {v0}, Lcom/oplus/systemui/notification/lockscreen/statemanager/LockScreenNotificationExtStateManager;->getNotificationDisplayRectCallbackWrapper()Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallbackWrapper;

    move-result-object v0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayRectCallback:Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallback;

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallbackWrapper;->removeNotificationDisplayRectCallback(Lcom/oplus/systemui/notification/lockscreen/statemanager/NotificationDisplayRectCallback;)V

    const/high16 v0, -0x40800000    # -1.0f

    iput v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayTop:F

    iput v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayBottom:F

    return-void
.end method

.method public static final synthetic access$setFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Landroid/animation/AnimatorSet;)V
    .locals 0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fingerPrintAnimator:Landroid/animation/AnimatorSet;

    return-void
.end method

.method public static final synthetic access$setFingerPrintColorAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Landroid/animation/Animator;)V
    .locals 0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fingerPrintColorAnimator:Landroid/animation/Animator;

    return-void
.end method

.method public static final synthetic access$setPressedAnimDrawableTmp$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 1

    const/4 v0, 0x0

    iput-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawableTmp:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    return-void
.end method

.method public static final synthetic access$setPressedIconTouchable(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;I)V
    .locals 0

    invoke-direct {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setPressedIconTouchable(I)V

    return-void
.end method

.method public static final synthetic access$setVisibilityRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 1

    const/4 v0, 0x0

    iput-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    return-void
.end method

.method public static final access$shouldShowFpIconShadow(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Z
    .locals 7

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v0

    const/4 v1, 0x0

    if-nez v0, :cond_0

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUltrasonicFps()Z

    move-result v0

    if-nez v0, :cond_0

    return v1

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    const-string v2, "OnScreenFingerprintUiMech"

    if-eqz v0, :cond_8

    invoke-virtual {v0}, Landroid/widget/ImageView;->getVisibility()I

    move-result v0

    if-nez v0, :cond_8

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    const/4 v3, 0x0

    if-eqz v0, :cond_1

    invoke-virtual {v0}, Landroid/widget/ImageView;->getDrawable()Landroid/graphics/drawable/Drawable;

    move-result-object v0

    goto :goto_0

    :cond_1
    move-object v0, v3

    :goto_0
    if-nez v0, :cond_2

    goto/16 :goto_2

    :cond_2
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-eqz v0, :cond_3

    const-string/jumbo p0, "shouldShowFpIconShadow return false, mOnDreamingStart"

    invoke-static {v2, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return v1

    :cond_3
    const-class v0, Lcom/android/keyguard/OplusKeyguardDependencyEx;

    sget-object v4, Lcom/android/systemui/DependencyEx;->sDependency:Lcom/android/systemui/DependencyEx;

    invoke-virtual {v4, v0}, Lcom/android/systemui/DependencyEx;->getDependency(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/android/keyguard/OplusKeyguardDependencyEx;

    invoke-virtual {v0}, Lcom/android/keyguard/OplusKeyguardDependencyEx;->getOplusLockScreenWallpaperController()Lcom/android/keyguard/wallpaper/OplusLockScreenWallpaper;

    move-result-object v0

    invoke-virtual {v0}, Lcom/android/keyguard/wallpaper/OplusLockScreenWallpaper;->getCurrentWallpaperInfo()Lcom/android/keyguard/wallpaper/KeyguardWallpaperInfo;

    move-result-object v0

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    iget-boolean v4, v4, Lcom/android/keyguard/KeyguardUpdateMonitor;->mKeyguardShowing:Z

    if-eqz v4, :cond_7

    const/4 v4, 0x1

    if-eqz v0, :cond_4

    invoke-virtual {v0}, Lcom/android/keyguard/wallpaper/KeyguardWallpaperInfo;->isPictorialType()Z

    move-result v5

    if-ne v5, v4, :cond_4

    goto :goto_1

    :cond_4
    if-eqz v0, :cond_5

    iget v5, v0, Lcom/android/keyguard/wallpaper/KeyguardWallpaperInfo;->mType:I

    const/4 v6, 0x2

    if-ne v5, v6, :cond_5

    goto :goto_1

    :cond_5
    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v5}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isNeedNotificationOverlayFingerPrint()Z

    move-result v5

    if-eqz v5, :cond_7

    :goto_1
    if-eqz v0, :cond_6

    invoke-virtual {v0}, Lcom/android/keyguard/wallpaper/KeyguardWallpaperInfo;->getMType()I

    move-result p0

    invoke-static {p0}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v3

    :cond_6
    new-instance p0, Ljava/lang/StringBuilder;

    const-string/jumbo v0, "shouldShowFpIconShadow return true,  keyguardWallpaper Type is: "

    invoke-direct {p0, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p0, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v2, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return v4

    :cond_7
    iget p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    new-instance v3, Ljava/lang/StringBuilder;

    const-string/jumbo v4, "shouldShowFpIconShadow,keyguardWallpaperInfo: "

    invoke-direct {v3, v4}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    const-string v0, ", fpShowReason: "

    invoke-virtual {v3, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v3, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v2, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return v1

    :cond_8
    :goto_2
    const-string/jumbo p0, "shouldShowFpIconShadow return false, fpIcon invisible"

    invoke-static {v2, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return v1
.end method

.method public static final access$shouldUseFpIconRect(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Z
    .locals 2

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUdfps()Z

    move-result v0

    if-eqz v0, :cond_0

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->Companion:Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->isFingerprintUnlockEnable()Z

    move-result v0

    if-eqz v0, :cond_0

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->getUdfpsIconBottomPaddingStatic()F

    move-result v0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {p0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object p0

    const v1, 0x7f0701a1

    invoke-virtual {p0, v1}, Landroid/content/res/Resources;->getDimensionPixelSize(I)I

    move-result p0

    int-to-float p0, p0

    cmpg-float p0, v0, p0

    if-gez p0, :cond_0

    const/4 p0, 0x0

    return p0

    :cond_0
    const/4 p0, 0x1

    return p0
.end method

.method public static final access$updateScreenBrightness(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Z)V
    .locals 7

    sget-object v0, Lcom/oplusos/systemui/common/feature/FlavorOneFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/FlavorOneFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/FlavorOneFeatureOption;->isFlavorOneDevice()Z

    move-result v0

    if-nez v0, :cond_0

    goto/16 :goto_0

    :cond_0
    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v0

    if-nez v0, :cond_1

    goto/16 :goto_0

    :cond_1
    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportLocalHbmBrighten()Z

    move-result v0

    if-nez v0, :cond_2

    goto/16 :goto_0

    :cond_2
    const-string v0, "OnScreenFingerprintUiMech-->"

    const-string v1, "SystemUi--Keyguard"

    const-string v2, "Keyguard"

    if-eqz p1, :cond_5

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isScreenOn()Z

    move-result p1

    if-eqz p1, :cond_7

    iget p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const/4 v3, 0x3

    if-eq p1, v3, :cond_3

    iget p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const/4 v3, 0x5

    if-ne p1, v3, :cond_7

    :cond_3
    new-instance p1, Landroid/os/OplusPowerManager;

    invoke-direct {p1}, Landroid/os/OplusPowerManager;-><init>()V

    sget-object v3, Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper;->Companion:Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper$Companion;

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const-string/jumbo v5, "screen_brightness"

    const/4 v6, -0x2

    invoke-virtual {v3, v4, v5, v6}, Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper$Companion;->getSystemStringValue(Landroid/content/Context;Ljava/lang/String;I)Ljava/lang/String;

    move-result-object v3

    iput-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    sget-object v3, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v3, v4}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v3

    const/high16 v4, 0x41700000    # 15.0f

    invoke-virtual {v3, p1, v4}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->getBrightnessByNit(Landroid/os/OplusPowerManager;F)I

    move-result p1

    invoke-static {}, Lcom/oplusos/systemui/common/util/LogUtil;->getNormalDebug()Z

    move-result v3

    if-eqz v3, :cond_4

    invoke-static {v2}, Lcom/oplusos/systemui/common/util/LogUtil;->isTagValid(Ljava/lang/String;)Z

    move-result v2

    if-eqz v2, :cond_4

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    new-instance v3, Ljava/lang/StringBuilder;

    const-string/jumbo v4, "set 15nit brightness, mCurBrightness = "

    invoke-direct {v3, v4}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v2, ", BrightnessByNit = "

    invoke-virtual {v3, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v3, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v0, v2}, Ljava/lang/String;->concat(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    invoke-static {v1, v0}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    :cond_4
    :try_start_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    invoke-static {v0}, Ljava/lang/Integer;->parseInt(Ljava/lang/String;)I

    move-result v0
    :try_end_0
    .catch Ljava/lang/NumberFormatException; {:try_start_0 .. :try_end_0} :catch_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    if-eqz v1, :cond_7

    const/4 v1, -0x1

    if-eq p1, v1, :cond_7

    if-ge v0, p1, :cond_7

    invoke-static {p1}, Ljava/lang/String;->valueOf(I)Ljava/lang/String;

    move-result-object p1

    invoke-direct {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setScreenBrightness(Ljava/lang/String;)V

    const/4 p1, 0x1

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mAdjustmentBrightness:Z

    return-void

    :catch_0
    move-exception p0

    new-instance p1, Ljava/lang/StringBuilder;

    const-string v0, "NumberFormatException : "

    invoke-direct {p1, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    const-string p1, "OnScreenFingerprintUiMech"

    invoke-static {p1, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->e(Ljava/lang/String;Ljava/lang/String;)V

    return-void

    :cond_5
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    if-eqz p1, :cond_7

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mAdjustmentBrightness:Z

    if-eqz p1, :cond_7

    invoke-static {}, Lcom/oplusos/systemui/common/util/LogUtil;->getNormalDebug()Z

    move-result p1

    if-eqz p1, :cond_6

    invoke-static {v2}, Lcom/oplusos/systemui/common/util/LogUtil;->isTagValid(Ljava/lang/String;)Z

    move-result p1

    if-eqz p1, :cond_6

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    const-string/jumbo v2, "restore mCurBrightness = "

    invoke-static {v2, p1, v0, v1}, Lcom/android/systemui/media/controls/domain/pipeline/MediaTimeoutListener$PlaybackStateListener$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    :cond_6
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    invoke-static {p1}, Ljava/lang/String;->valueOf(Ljava/lang/Object;)Ljava/lang/String;

    move-result-object p1

    invoke-direct {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setScreenBrightness(Ljava/lang/String;)V

    const/4 p1, 0x0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mCurBrightness:Ljava/lang/String;

    const/4 p1, 0x0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->mAdjustmentBrightness:Z

    :cond_7
    :goto_0
    return-void
.end method

.method private final getBottomAreaRect()Landroid/graphics/Rect;
    .locals 4

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v1

    iget v1, v1, Landroid/util/DisplayMetrics;->widthPixels:I

    invoke-virtual {v0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v0

    iget v0, v0, Landroid/util/DisplayMetrics;->heightPixels:I

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->getUdfpsIconPaddingStatic()F

    move-result v2

    iget-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusKeyguardStyleBaseUIControllerLazy:Ldagger/Lazy;

    invoke-interface {v3}, Ldagger/Lazy;->get()Ljava/lang/Object;

    move-result-object v3

    check-cast v3, Lcom/oplus/systemui/keyguard/clockstyle/OplusKeyguardStyleBaseUIControllerImpl;

    invoke-virtual {v3}, Lcom/oplus/systemui/keyguard/clockstyle/OplusKeyguardStyleBaseUIControllerImpl;->getCapsuleFingerprintInterval()I

    move-result v3

    int-to-float v3, v3

    add-float/2addr v2, v3

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {p0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object p0

    const v3, 0x7f0702db

    invoke-virtual {p0, v3}, Landroid/content/res/Resources;->getDimensionPixelSize(I)I

    move-result p0

    int-to-float p0, p0

    add-float/2addr v2, p0

    float-to-int p0, v2

    sub-int p0, v0, p0

    new-instance v2, Landroid/graphics/Rect;

    const/4 v3, 0x0

    invoke-direct {v2, v3, p0, v1, v0}, Landroid/graphics/Rect;-><init>(IIII)V

    new-instance p0, Ljava/lang/StringBuilder;

    const-string v0, "fpIconRect use rect = "

    invoke-direct {p0, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    const-string v0, "OnScreenFingerprintUiMech"

    invoke-static {v0, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return-object v2
.end method

.method private final getFadeOutAnimTime()I
    .locals 2

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    const/4 v0, 0x0

    if-eqz p0, :cond_0

    invoke-virtual {p0}, Landroid/graphics/drawable/AnimationDrawable;->getNumberOfFrames()I

    move-result v1

    invoke-virtual {p0, v0}, Landroid/graphics/drawable/AnimationDrawable;->getDuration(I)I

    move-result p0

    mul-int/2addr p0, v1

    return p0

    :cond_0
    return v0
.end method

.method private final getFpIconRect()Landroid/graphics/Rect;
    .locals 4

    sget-object p0, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    invoke-virtual {p0}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getRealScreenWidth()I

    move-result v0

    div-int/lit8 v0, v0, 0x2

    invoke-virtual {p0}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getRealScreenHeight()I

    move-result p0

    add-int/lit8 v1, v0, -0x57

    add-int/lit8 v0, v0, 0x57

    sget-object v2, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v2

    sub-int/2addr p0, v2

    add-int/lit8 v2, p0, 0x57

    add-int/lit8 p0, p0, -0x57

    new-instance v3, Landroid/graphics/Rect;

    invoke-direct {v3, v1, p0, v0, v2}, Landroid/graphics/Rect;-><init>(IIII)V

    new-instance p0, Ljava/lang/StringBuilder;

    const-string v0, "getFpIconRect = "

    invoke-direct {p0, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p0, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    const-string v0, "OnScreenFingerprintUiMech"

    invoke-static {v0, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return-object v3
.end method

.method private final getScalePressedAnim()F
    .locals 4

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUdfps()Z

    move-result v0

    const/4 v1, 0x1

    const/high16 v2, 0x3f800000    # 1.0f

    if-nez v0, :cond_0

    goto :goto_0

    :cond_0
    sget v0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->iconMarginBottomProp:I

    sget v3, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->gestureHotAreaHeight:I

    if-ge v0, v3, :cond_1

    if-lez v0, :cond_1

    goto :goto_1

    :cond_1
    :goto_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :cond_7

    invoke-virtual {v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->getDrawableWH()[I

    move-result-object v0

    if-eqz v0, :cond_7

    aget v0, v0, v1

    div-int/lit8 v0, v0, 0x2

    sget-object v3, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v3}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v3

    if-le v0, v3, :cond_7

    :goto_1
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :cond_2

    invoke-virtual {v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->getDrawableWH()[I

    move-result-object v0

    goto :goto_2

    :cond_2
    const/4 v0, 0x0

    :goto_2
    if-eqz v0, :cond_7

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz p0, :cond_7

    aget p0, v0, v1

    if-gtz p0, :cond_3

    goto :goto_4

    :cond_3
    int-to-float v0, p0

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottomProp()I

    move-result v1

    mul-int/lit8 v1, v1, 0x2

    int-to-float v1, v1

    div-float/2addr v0, v1

    new-instance v1, Ljava/lang/StringBuilder;

    const-string/jumbo v3, "tryToScalePressedAnim, mPressedAnimScaleRate before = "

    invoke-direct {v1, v3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    const-string v3, " , drawableHeight="

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    const-string v1, "OnScreenFingerprintUiMech"

    invoke-static {v1, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    cmpl-float p0, v0, v2

    if-lez p0, :cond_4

    div-float/2addr v2, v0

    const p0, 0x3f4ccccd    # 0.8f

    invoke-static {v2, p0}, Ljava/lang/Math;->max(FF)F

    move-result v2

    goto :goto_3

    :cond_4
    const p0, 0x3f733333    # 0.95f

    cmpl-float p0, v0, p0

    if-lez p0, :cond_5

    const v2, 0x3f666666    # 0.9f

    goto :goto_3

    :cond_5
    const/high16 p0, 0x3f000000    # 0.5f

    cmpg-float p0, v0, p0

    if-gtz p0, :cond_6

    goto :goto_3

    :cond_6
    move v2, v0

    :goto_3
    new-instance p0, Ljava/lang/StringBuilder;

    const-string/jumbo v0, "tryToScalePressedAnim, mPressedAnimScaleRate after = "

    invoke-direct {p0, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p0, v2}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v1, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    :cond_7
    :goto_4
    return v2
.end method

.method private final getTextColorOnWallpaper()I
    .locals 4

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0}, Landroid/content/Context;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object v0

    const/4 v1, -0x1

    if-eqz v0, :cond_0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {p0}, Landroid/content/Context;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object p0

    const v0, 0x7f040d7d

    filled-new-array {v0}, [I

    move-result-object v0

    const/4 v2, 0x0

    const/4 v3, 0x0

    invoke-virtual {p0, v2, v0, v3, v3}, Landroid/content/res/Resources$Theme;->obtainStyledAttributes(Landroid/util/AttributeSet;[III)Landroid/content/res/TypedArray;

    move-result-object p0

    invoke-virtual {p0, v3, v1}, Landroid/content/res/TypedArray;->getColor(II)I

    move-result v0

    invoke-static {v0}, Landroid/graphics/Color;->red(I)I

    move-result v1

    invoke-static {v0}, Landroid/graphics/Color;->green(I)I

    move-result v2

    invoke-static {v0}, Landroid/graphics/Color;->blue(I)I

    move-result v0

    const/16 v3, 0xff

    invoke-static {v3, v1, v2, v0}, Landroid/graphics/Color;->argb(IIII)I

    move-result v0

    invoke-virtual {p0}, Landroid/content/res/TypedArray;->recycle()V

    return v0

    :cond_0
    return v1
.end method

.method public static final resetDisplayPowerOnAuthFailureIfNeeded(Landroid/content/Context;)V
    .locals 1

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {v0, p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;->resetDisplayPowerOnAuthFailureIfNeeded(Landroid/content/Context;)V

    return-void
.end method

.method private final setPressedIconTouchable(I)V
    .locals 2

    const/4 v0, 0x4

    if-eq p1, v0, :cond_0

    const/4 v0, -0x1

    if-eq p1, v0, :cond_0

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz p1, :cond_0

    invoke-virtual {p1}, Landroid/widget/ImageView;->getVisibility()I

    move-result p1

    if-nez p1, :cond_0

    const/4 p1, 0x1

    goto :goto_0

    :cond_0
    const/4 p1, 0x0

    :goto_0
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->touchable:Z

    if-ne v0, p1, :cond_1

    goto :goto_3

    :cond_1
    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->touchable:Z

    const-string v0, "OnScreenFingerprintUiMech"

    const-string/jumbo v1, "setTouchable touchable="

    invoke-static {v1, v0, p1}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Z)V

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-nez p1, :cond_2

    goto :goto_3

    :cond_2
    const/4 v0, 0x0

    if-eqz p1, :cond_3

    invoke-virtual {p1}, Landroid/widget/ImageView;->getLayoutParams()Landroid/view/ViewGroup$LayoutParams;

    move-result-object p1

    goto :goto_1

    :cond_3
    move-object p1, v0

    :goto_1
    instance-of v1, p1, Landroid/view/WindowManager$LayoutParams;

    if-eqz v1, :cond_4

    move-object v0, p1

    check-cast v0, Landroid/view/WindowManager$LayoutParams;

    :cond_4
    if-nez v0, :cond_5

    goto :goto_3

    :cond_5
    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->touchable:Z

    iget v1, v0, Landroid/view/WindowManager$LayoutParams;->flags:I

    if-eqz p1, :cond_6

    and-int/lit8 p1, v1, -0x11

    iput p1, v0, Landroid/view/WindowManager$LayoutParams;->flags:I

    goto :goto_2

    :cond_6
    or-int/lit8 p1, v1, 0x10

    iput p1, v0, Landroid/view/WindowManager$LayoutParams;->flags:I

    :goto_2
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz p1, :cond_7

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    invoke-interface {p1, p0, v0}, Landroid/view/WindowManager;->updateViewLayout(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_7
    :goto_3
    return-void
.end method

.method private final setScreenBrightness(Ljava/lang/String;)V
    .locals 3

    sget-object v0, Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper;->Companion:Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const-string/jumbo v2, "screen_brightness"

    invoke-virtual {v0, v1, v2, p1}, Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper$Companion;->setSystemStringValue(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;)V

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const-string/jumbo v1, "screen_auto_brightness_adj"

    invoke-virtual {v0, p0, v1, p1}, Lcom/oplusos/systemui/common/multiuser/MultiUserContentHelper$Companion;->setSystemStringValue(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method

.method private final setTpStatus(I)V
    .locals 3

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTPDisable:Z

    const/4 v1, 0x1

    if-nez v0, :cond_0

    if-ne p1, v1, :cond_0

    return-void

    :cond_0
    const/4 v0, 0x0

    if-nez p1, :cond_1

    move v2, v1

    goto :goto_0

    :cond_1
    move v2, v0

    :goto_0
    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTPDisable:Z

    int-to-byte p1, p1

    new-array v1, v1, [B

    aput-byte p1, v1, v0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    const/4 p1, -0x1

    const/16 v0, 0x3fe

    invoke-virtual {p0, p1, v0, v1}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->sendFingerprintCmd(II[B)V

    return-void
.end method

.method public static updateFpIconAlpha$default(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 2

    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;

    const/4 v1, 0x0

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->$focus:Z

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void
.end method


# virtual methods
.method public final addFpSizeCallback(Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$IFpSizeCallback;)V
    .locals 1

    if-nez p1, :cond_0

    return-void

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {v0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->contains(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :cond_1

    const-string p0, "OnScreenFingerprintUiMech"

    const-string p1, "add the same callback"

    invoke-static {p0, p1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return-void

    :cond_1
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {p0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->add(Ljava/lang/Object;)Z

    check-cast p1, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    new-instance p0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;

    const/4 v0, 0x0

    invoke-direct {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;-><init>(I)V

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;->f$0:Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {p1, p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->runOnUIThread(Lkotlin/jvm/functions/Function0;)V

    return-void
.end method

.method public final addVisibilityListener(Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$OnFingerprintVisibilityListener;)V
    .locals 1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityListeners:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {v0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->contains(Ljava/lang/Object;)Z

    move-result v0

    if-nez v0, :cond_0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityListeners:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {p0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->add(Ljava/lang/Object;)Z

    :cond_0
    return-void
.end method

.method public final cancelFpPendingHideAnimator()V
    .locals 2

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/4 v1, 0x2

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void
.end method

.method public final cancelRealHideRunnable()V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->realHideRunnable:Ljava/lang/Runnable;

    if-eqz v0, :cond_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v1, :cond_0

    invoke-virtual {v1, v0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_0
    const/4 v0, 0x0

    iput-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->realHideRunnable:Ljava/lang/Runnable;

    return-void
.end method

.method public final checkHasPressedAnimation()Z
    .locals 1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    const/4 v0, 0x0

    if-eqz p0, :cond_1

    if-eqz p0, :cond_0

    invoke-virtual {p0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->getOptions()Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object p0

    goto :goto_0

    :cond_0
    const/4 p0, 0x0

    :goto_0
    if-eqz p0, :cond_1

    invoke-virtual {p0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;->getFrames()I

    move-result p0

    if-lez p0, :cond_1

    const/4 p0, 0x1

    return p0

    :cond_1
    return v0
.end method

.method public dump(Ljava/io/PrintWriter;[Ljava/lang/String;)V
    .locals 3

    new-instance p2, Ljava/lang/StringBuilder;

    const-string v0, "  sIconMarginBottom: "

    invoke-direct {p2, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v1, "\n  sIconMarginBottomProp: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottomProp()I

    move-result v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v1, "\n  sPressedIconSize: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getPressedIconSize()I

    move-result v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v1, "\n  sPressedIconSizeProp: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getPressedIconSizeProp()I

    move-result v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v1, "\n  sAnimIconSize: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getAnimIconSize()I

    move-result v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v1, "\n  mFpIcon scale: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    const/4 v2, 0x0

    if-eqz v1, :cond_0

    invoke-virtual {v1}, Landroid/widget/ImageView;->getScaleY()F

    move-result v1

    invoke-static {v1}, Ljava/lang/Float;->valueOf(F)Ljava/lang/Float;

    move-result-object v1

    goto :goto_0

    :cond_0
    move-object v1, v2

    :goto_0
    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    const-string v1, "\n  mFpIcon log: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v1, :cond_1

    invoke-virtual {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->getLogStr()Ljava/lang/String;

    move-result-object v2

    :cond_1
    invoke-virtual {p2, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v1, "\n  stableDisplayWidth: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    sget-object v1, Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper;->Companion:Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper$Companion;

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1, v2}, Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper;

    move-result-object v2

    invoke-virtual {v2}, Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper;->getStableDisplayWidth()I

    move-result v2

    invoke-virtual {p2, v2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v2, "\n  baseScreenWidth: "

    invoke-virtual {p2, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1, v2}, Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper;

    move-result-object v1

    invoke-virtual {v1}, Lcom/oplus/systemui/keyguard/helper/ScreenResolutionHelper;->getBaseDisplayWidth()I

    move-result v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v1, "\n  sGestureHotAreaHeight: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getGestureHotAreaHeight()I

    move-result v0

    invoke-virtual {p2, v0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v0, "\n  mFpType: "

    invoke-virtual {p2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {p0}, Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx;->getFpType()I

    move-result p0

    invoke-virtual {p2, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string p0, "\n"

    invoke-virtual {p2, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string p0, "\nDump optical fingerprint : "

    invoke-virtual {p1, p0}, Ljava/io/PrintWriter;->println(Ljava/lang/String;)V

    invoke-virtual {p2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {p1, p0}, Ljava/io/PrintWriter;->println(Ljava/lang/String;)V

    return-void
.end method

.method public final fpIconHide(I)V
    .locals 5

    const-string v0, "fpIconHide "

    const-string v1, "OnScreenFingerprintUiMech"

    invoke-static {p1, v0, v1}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(ILjava/lang/String;Ljava/lang/String;)V

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v2, :cond_0

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    :cond_0
    const/4 v0, 0x0

    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isServiceRequest:Z

    iget-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasHideIconByQs:Z

    if-eqz v2, :cond_1

    const/4 v2, 0x2

    if-eq p1, v2, :cond_1

    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasHideIconByQs:Z

    :cond_1
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->checkHasPressedAnimation()Z

    move-result p1

    const/4 v2, 0x1

    if-eqz p1, :cond_4

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    if-nez p1, :cond_4

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-eqz p1, :cond_4

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideImmediately:Z

    if-nez p1, :cond_4

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isPressAnimRunning()Z

    move-result p1

    if-nez p1, :cond_2

    goto :goto_0

    :cond_2
    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    const-string/jumbo p1, "mPendingHide:true"

    invoke-virtual {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    const-string/jumbo v3, "mPendingHide:"

    invoke-static {v3, v1, p1}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Z)V

    sget-object p1, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    invoke-virtual {p1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getANIM_LEVEL()I

    move-result p1

    if-ne p1, v2, :cond_3

    sget-object p1, Lcom/oplusos/systemui/common/feature/FeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/FeatureOption;

    invoke-virtual {p1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/FeatureOption;->isLightOs()Z

    move-result p1

    if-eqz p1, :cond_5

    :cond_3
    const-string/jumbo p1, "startFingerprintGradientsAnim"

    invoke-static {v1, p1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v2, 0x18

    invoke-direct {p1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    goto :goto_1

    :cond_4
    :goto_0
    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    iget-boolean v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    xor-int/2addr v2, v3

    const-string v3, " mShowForEnroll:"

    const-string v4, ";!isTouchDownNow():"

    invoke-static {v3, v4, v1, p1, v2}, Lcom/android/systemui/statusbar/OlockStateUtil$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ZZ)V

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIcon()V

    :cond_5
    :goto_1
    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {p1, v0}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isFaceAuthStayOnKeyguard(Z)Z

    move-result p1

    if-eqz p1, :cond_6

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {p1}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getIsFaceAuthenticated()Z

    move-result p1

    if-eqz p1, :cond_6

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {p1}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isKeyguardVisible$1()Z

    move-result p1

    if-eqz p1, :cond_6

    const-string p0, "don\'t cancel highlight when faceUnlock stayOn."

    invoke-static {v1, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return-void

    :cond_6
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p1, :cond_7

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/4 v1, 0x7

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {p1, v0}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_7
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->workerHandler:Landroid/os/Handler;

    if-eqz p1, :cond_8

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0x8

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {p1, v0}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_8
    return-void
.end method

.method public final fpIconShow(IZ)V
    .locals 4

    const-string/jumbo v0, "waiting for closing of status bar"

    const-string v1, "OnScreenFingerprintUiMech"

    new-instance v2, Ljava/lang/StringBuilder;

    const-string v3, "fpIconShow "

    invoke-direct {v2, v3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-static {v1, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2, v3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {p0, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    const/4 v2, 0x4

    const/4 v3, 0x1

    if-ne p1, v2, :cond_0

    iget v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showInAOD:I

    if-ne v2, v3, :cond_0

    monitor-enter p0

    const/4 v2, -0x1

    :try_start_0
    iput v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showInAOD:I
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    monitor-exit p0

    goto :goto_0

    :catchall_0
    move-exception p1

    monitor-exit p0

    throw p1

    :cond_0
    :goto_0
    invoke-direct {p0, v3}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setTpStatus(I)V

    const/4 v2, 0x0

    if-eqz p2, :cond_1

    iput-boolean v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    goto :goto_1

    :cond_1
    iget-boolean p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    if-eqz p2, :cond_2

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopPressedAnimation()V

    :cond_2
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->cancelFpPendingHideAnimator()V

    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    :goto_1
    iget-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    check-cast p2, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    iget-boolean p2, p2, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->mShowing:Z

    if-nez p2, :cond_3

    iget-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {p2}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isBiometricPromptShowing()Z

    move-result p2

    if-eqz p2, :cond_4

    :cond_3
    move v2, v3

    :cond_4
    iget-boolean p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasHideIconByQs:Z

    if-eqz p2, :cond_5

    if-nez v2, :cond_5

    invoke-static {v1, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    goto :goto_2

    :cond_5
    iput-boolean v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isServiceRequest:Z

    iget-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p2, :cond_6

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0x9

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {p2, v0}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_6
    const-string p2, ""

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->talkToSurfaceFlingerRunable:Ljava/lang/Runnable;

    if-eqz v0, :cond_7

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v1, :cond_7

    invoke-virtual {v1, v0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_7
    sget-object v0, Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils$Companion;

    const-string v1, "OnScreenFingerprintIcon"

    invoke-virtual {v0, v1, v3, p2}, Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils$Companion;->talkToSurfaceFlingerForLayer(Ljava/lang/String;ZLjava/lang/String;)V

    sget-object v1, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportOpticalFps()Z

    move-result v1

    if-eqz v1, :cond_8

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v1

    if-nez v1, :cond_8

    const-string v1, "OnScreenFingerprintPressedIcon"

    invoke-virtual {v0, v1, v3, p2}, Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils$Companion;->talkToSurfaceFlingerForLayer(Ljava/lang/String;ZLjava/lang/String;)V

    :cond_8
    iget-boolean p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isServiceRequest:Z

    if-nez p2, :cond_9

    goto :goto_2

    :cond_9
    iget-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    if-eqz p2, :cond_a

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_a

    invoke-virtual {v0, p2}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_a
    new-instance p2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v0, 0x13

    invoke-direct {p2, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, p2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    iput-boolean v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z

    iget-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    if-eqz p2, :cond_b

    invoke-static {p2}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_b
    :goto_2
    iget-object p2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p2, :cond_c

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fpIconShow$2;

    invoke-direct {v0}, Ljava/lang/Object;-><init>()V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fpIconShow$2;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput p1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$fpIconShow$2;->$reason:I

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {p2, v0}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_c
    return-void
.end method

.method public final getFadeInAnimState()Z
    .locals 1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz p0, :cond_1

    const/4 v0, 0x1

    if-eqz p0, :cond_0

    invoke-virtual {p0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result p0

    if-ne p0, v0, :cond_0

    goto :goto_0

    :cond_0
    return v0

    :cond_1
    :goto_0
    const/4 p0, 0x0

    return p0
.end method

.method public final getFingerprintIcon()Landroid/view/View;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    return-object p0
.end method

.method public final getFingerprintPressedIcon()Landroid/view/View;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    return-object p0
.end method

.method public final getFpAlphaSpringAnimation()Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpAlphaSpringAnimation:Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    return-object p0
.end method

.method public final getHasInitFp()Z
    .locals 0

    iget-boolean p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasInitFp:Z

    return p0
.end method

.method public final getImMobileDrawable(Landroid/content/res/Resources;)Landroid/graphics/drawable/Drawable;
    .locals 2

    sget-object v0, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v1

    invoke-virtual {v0, v1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object v0

    iget-boolean v0, v0, Lcom/oplus/keyguard/utils/KeyguardUtils;->isFpGlobalThemeEnable:Z

    if-eqz v0, :cond_0

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v0

    invoke-static {v0}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result v0

    if-nez v0, :cond_0

    const v0, 0x7f081124

    invoke-virtual {p0, p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->loadDrawableFromBitmap(Landroid/content/res/Resources;I)Landroid/graphics/drawable/Drawable;

    move-result-object p0

    return-object p0

    :cond_0
    const v0, 0x7f081168

    invoke-virtual {p0, p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->loadDrawableFromBitmap(Landroid/content/res/Resources;I)Landroid/graphics/drawable/Drawable;

    move-result-object p0

    return-object p0
.end method

.method public final getOnDozeState()Z
    .locals 0

    iget-boolean p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDozeState:Z

    return p0
.end method

.method public final getOnDreamingStart()Z
    .locals 0

    iget-boolean p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    return p0
.end method

.method public final getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;
    .locals 7

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v0

    invoke-virtual {v0}, Landroid/content/Context;->getUserId()I

    move-result v1

    invoke-static {}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getCurrentUser()I

    move-result v2

    const/4 v3, 0x0

    if-ne v1, v2, :cond_0

    goto :goto_0

    :cond_0
    invoke-static {}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getCurrentUser()I

    move-result v1

    invoke-static {v1}, Landroid/os/UserHandle;->of(I)Landroid/os/UserHandle;

    move-result-object v1

    invoke-virtual {v0, v1, v3}, Landroid/content/Context;->createContextAsUser(Landroid/os/UserHandle;I)Landroid/content/Context;

    move-result-object v0

    :goto_0
    invoke-virtual {v0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v0

    iget v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->platformAnimationLevel:I

    const/4 v2, -0x1

    if-ne v1, v2, :cond_1

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v1}, Lcom/oplus/util/OplusPlatformLevelUtils;->getInstance(Landroid/content/Context;)Lcom/oplus/util/OplusPlatformLevelUtils;

    move-result-object v1

    invoke-virtual {v1}, Lcom/oplus/util/OplusPlatformLevelUtils;->getPlatformAnimationLevel()I

    move-result v1

    iput v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->platformAnimationLevel:I

    :cond_1
    const/4 v1, 0x2

    if-eq p1, v1, :cond_a

    const/4 v4, 0x4

    if-eq p1, v4, :cond_8

    const/16 v4, 0x8

    if-eq p1, v4, :cond_2

    const-string p0, ""

    goto/16 :goto_5

    :cond_2
    sget-object p1, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v2}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v2

    invoke-virtual {p1, v2}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object v2

    iget-boolean v2, v2, Lcom/oplus/keyguard/utils/KeyguardUtils;->isFpGlobalThemeEnable:Z

    const/4 v4, 0x3

    const/16 v5, 0x12

    const/16 v6, 0x24

    if-eqz v2, :cond_6

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v2}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v2

    invoke-static {v2}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result v2

    if-nez v2, :cond_6

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v2}, Lcom/oplusos/systemui/common/util/ScrimUtil;->isMiddleOrHighAnimLevel(Landroid/content/Context;)Z

    move-result v2

    if-eqz v2, :cond_4

    const v1, 0x7f1309bb

    invoke-virtual {v0, v1}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object v1

    const v2, 0x7f0b00d3

    invoke-virtual {v0, v2}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v0

    if-le v0, v6, :cond_3

    :goto_1
    move v2, v6

    goto :goto_4

    :cond_3
    :goto_2
    move v2, v0

    goto :goto_4

    :cond_4
    const v2, 0x7f1309bc

    invoke-virtual {v0, v2}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object v2

    const v4, 0x7f0b00d4

    invoke-virtual {v0, v4}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v0

    if-le v0, v5, :cond_5

    :goto_3
    move v4, v1

    move-object v1, v2

    move v2, v5

    goto :goto_4

    :cond_5
    move v4, v1

    move-object v1, v2

    goto :goto_2

    :cond_6
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v2}, Lcom/oplusos/systemui/common/util/ScrimUtil;->isMiddleOrHighAnimLevel(Landroid/content/Context;)Z

    move-result v2

    if-eqz v2, :cond_7

    const v1, 0x7f1309c6

    invoke-virtual {v0, v1}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object v1

    const v2, 0x7f0b00db

    invoke-virtual {v0, v2}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v0

    if-le v0, v6, :cond_3

    goto :goto_1

    :cond_7
    const v2, 0x7f1309c7

    invoke-virtual {v0, v2}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object v2

    const v4, 0x7f0b00dc

    invoke-virtual {v0, v4}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v0

    if-le v0, v5, :cond_5

    goto :goto_3

    :goto_4
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->platformAnimationLevel:I

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {p0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object p0

    invoke-virtual {p1, p0}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object p0

    iget-boolean p0, p0, Lcom/oplus/keyguard/utils/KeyguardUtils;->isFpGlobalThemeEnable:Z

    const-string p1, ",drawableFrames:"

    const-string v5, ",drawableRate:"

    const-string v6, "getOptions ANIM_TYPE_PRESSED, drawableName:"

    invoke-static {v2, v6, v1, p1, v5}, Landroidx/constraintlayout/widget/ConstraintSet$$ExternalSyntheticOutline0;->m(ILjava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v5, ",mPlatformAnimationLevel:"

    const-string v6, ",isFpGlobalThemeEnable:"

    invoke-static {v4, v0, v5, v6, p1}, Landroidx/compose/ui/spatial/RectList$$ExternalSyntheticOutline0;->m(IILjava/lang/String;Ljava/lang/String;Ljava/lang/StringBuilder;)V

    const-string v0, "OnScreenFingerprintUiMech"

    invoke-static {v0, p1, p0}, Lcom/oplus/charge/viewmodel/OplusChargeAnimController$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/StringBuilder;Z)V

    move-object p0, v1

    move v1, v4

    goto/16 :goto_5

    :cond_8
    sget-object p1, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v1

    invoke-virtual {p1, v1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object p1

    iget-boolean p1, p1, Lcom/oplus/keyguard/utils/KeyguardUtils;->isFpGlobalThemeEnable:Z

    if-eqz p1, :cond_9

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {p0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object p0

    invoke-static {p0}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result p0

    if-nez p0, :cond_9

    const p0, 0x7f1309be

    invoke-virtual {v0, p0}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object p0

    const p1, 0x7f0b00d8

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v2

    const p1, 0x7f0b00d7

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v1

    goto :goto_5

    :cond_9
    const p0, 0x7f1309c9

    invoke-virtual {v0, p0}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object p0

    const p1, 0x7f0b00e0

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v2

    const p1, 0x7f0b00e1

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v1

    goto :goto_5

    :cond_a
    sget-object p1, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v1

    invoke-virtual {p1, v1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object p1

    iget-boolean p1, p1, Lcom/oplus/keyguard/utils/KeyguardUtils;->isFpGlobalThemeEnable:Z

    if-eqz p1, :cond_b

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {p0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object p0

    invoke-static {p0}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result p0

    if-nez p0, :cond_b

    const p0, 0x7f1309bd

    invoke-virtual {v0, p0}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object p0

    const p1, 0x7f0b00d6

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v2

    const p1, 0x7f0b00d5

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v1

    goto :goto_5

    :cond_b
    const p0, 0x7f1309c8

    invoke-virtual {v0, p0}, Landroid/content/res/Resources;->getString(I)Ljava/lang/String;

    move-result-object p0

    const p1, 0x7f0b00de

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v2

    const p1, 0x7f0b00df

    invoke-virtual {v0, p1}, Landroid/content/res/Resources;->getInteger(I)I

    move-result v1

    :goto_5
    new-instance p1, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    invoke-direct {p1, v2, v1, p0, v3}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;-><init>(IILjava/lang/String;Z)V

    invoke-virtual {p1, v3}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;->setNecessaryScale(Z)V

    return-object p1
.end method

.method public final getOverlayUtils()Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    return-object p0
.end method

.method public final getPrimaryBouncerShowing()Z
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    check-cast p0, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    iget-boolean p0, p0, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->mPrimaryBouncerShowing:Z

    return p0
.end method

.method public final getScreenTurnedOff()Z
    .locals 0

    iget-boolean p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenTurnedOff:Z

    return p0
.end method

.method public final getSupportDarkDesResult()Ljava/lang/Boolean;
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz p0, :cond_0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->isSupportDarkRes()Z

    move-result p0

    invoke-static {p0}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object p0

    return-object p0

    :cond_0
    const/4 p0, 0x0

    return-object p0
.end method

.method public final getUdfpsIconBottomPadding()F
    .locals 2

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasUdfpsIconPadding()Z

    move-result p0

    if-nez p0, :cond_0

    const/4 p0, 0x0

    return p0

    :cond_0
    sget-object p0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v0

    int-to-float v0, v0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getPressedIconSize()I

    move-result p0

    int-to-float p0, p0

    const/high16 v1, 0x3f000000    # 0.5f

    mul-float/2addr p0, v1

    sub-float/2addr v0, p0

    return v0
.end method

.method public final getUdfpsIconPadding()F
    .locals 2

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasUdfpsIconPadding()Z

    move-result p0

    if-nez p0, :cond_0

    const/4 p0, 0x0

    return p0

    :cond_0
    sget-object p0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v0

    int-to-float v0, v0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getPressedIconSize()I

    move-result p0

    int-to-float p0, p0

    const/high16 v1, 0x3f000000    # 0.5f

    mul-float/2addr p0, v1

    add-float/2addr p0, v0

    return p0
.end method

.method public final getWindowHideDelayDuration()J
    .locals 2

    iget-wide v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowHideDelayDuration:J

    return-wide v0
.end method

.method public final handleResolutionChanged()V
    .locals 4

    sget-object v0, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const/4 v2, 0x0

    const/4 v3, 0x6

    invoke-static {v0, v1, v2, v3}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->updateDisplayConfiguration$default(Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;Landroid/content/Context;ZI)Landroid/content/Context;

    move-result-object v1

    if-nez v1, :cond_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    :cond_0
    iput-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->updateScreenWH(Landroid/content/Context;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_1

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v2, 0xa

    invoke-direct {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_1
    return-void
.end method

.method public final hasUdfpsIconPadding()Z
    .locals 5

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUdfps()Z

    move-result v0

    const/4 v1, 0x0

    const/4 v2, 0x1

    if-eqz v0, :cond_0

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->Companion:Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;

    iget-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v3}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->isFingerprintUnlockEnable()Z

    move-result v0

    if-eqz v0, :cond_0

    move v0, v2

    goto :goto_0

    :cond_0
    move v0, v1

    :goto_0
    iget-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-static {}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getCurrentUser()I

    move-result v4

    invoke-virtual {v3, v4}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getUserHasTrust(I)Z

    move-result v3

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {p0, v2}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->getFpType(Z)I

    move-result p0

    const/4 v4, 0x2

    if-ne p0, v4, :cond_1

    return v0

    :cond_1
    if-eqz v0, :cond_2

    if-nez v3, :cond_2

    return v2

    :cond_2
    return v1
.end method

.method public final hideFingerprintIcon()V
    .locals 5

    const/4 v0, 0x0

    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-nez v1, :cond_0

    return-void

    :cond_0
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    if-eqz v1, :cond_1

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v2, :cond_1

    invoke-virtual {v2, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_1
    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v2, 0xc

    invoke-direct {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityRunnable:Ljava/lang/Runnable;

    if-eqz v1, :cond_2

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v2, :cond_2

    invoke-virtual {v2, v1}, Landroid/os/Handler;->postAtFrontOfQueue(Ljava/lang/Runnable;)Z

    :cond_2
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->talkToSurfaceFlingerRunable:Ljava/lang/Runnable;

    if-eqz v1, :cond_3

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v2, :cond_3

    invoke-virtual {v2, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_3
    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$hideFingerprintIcon$5;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$hideFingerprintIcon$5;

    iput-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->talkToSurfaceFlingerRunable:Ljava/lang/Runnable;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->talkToSurfaceFlingerRunable:Ljava/lang/Runnable;

    if-eqz v1, :cond_4

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v2, :cond_4

    const-wide/16 v3, 0x14

    invoke-virtual {v2, v1, v3, v4}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_4
    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    return-void
.end method

.method public final hideFingerprintIconTemporarily(Ljava/lang/String;)V
    .locals 5

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    iget-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    const-string v2, " ShowForEnroll "

    const-string v3, " mPendingHide "

    const-string v4, "hideFingerprintIconTemporarily for reason: "

    invoke-static {v4, p1, v2, v0, v3}, Lcom/android/keyguard/logging/KeyguardLogger$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ZLjava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v0, "OnScreenFingerprintUiMech"

    invoke-static {v0, p1, v1}, Lcom/oplus/charge/viewmodel/OplusChargeAnimController$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/StringBuilder;Z)V

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    const/4 v0, 0x0

    if-eqz p1, :cond_0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hideFingerprintIcon()V

    invoke-direct {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setTpStatus(I)V

    goto :goto_0

    :cond_0
    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z

    if-nez p1, :cond_1

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    if-eqz p1, :cond_2

    :cond_1
    const/4 p1, 0x2

    invoke-virtual {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconHide(I)V

    invoke-direct {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setTpStatus(I)V

    :cond_2
    const/4 p1, 0x1

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasHideIconByQs:Z

    :goto_0
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p1, :cond_3

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconRunnable:Ljava/lang/Runnable;

    invoke-virtual {p1, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_3
    const/4 p1, 0x0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconReason:Ljava/lang/String;

    iput v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconDelayedCount:I

    return-void
.end method

.method public final hideUdfpsOverlay$1()V
    .locals 6

    const/4 v0, -0x1

    iput v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getScreenTurnedOff()Z

    move-result v1

    if-nez v1, :oneos_native_hide

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v1, :oneos_native_hide

    iget-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    if-nez v1, :oneos_native_hide

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isPressAnimRunning()Z

    move-result v1

    if-nez v1, :oneos_native_hide

    const/4 v1, 0x1

    iput-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    const-string v1, "OnScreenFingerprintUiMech"

    const-string v2, "OneOS auth wave"

    invoke-static {v1, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oneosStartWave()V

    return-void

    :oneos_native_hide
    const/4 v0, 0x0

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconHide(I)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result v0

    if-nez v0, :cond_0

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isFpClientStop()Z

    move-result v0

    if-eqz v0, :cond_0

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-eqz v0, :cond_0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {p0}, Lcom/oplus/systemui/aod/aodclock/constant/AodData;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/aodclock/constant/AodData;

    move-result-object p0

    iget-boolean p0, p0, Lcom/oplus/systemui/aod/aodclock/constant/AodData;->mAodIsInShow:Z

    if-nez p0, :cond_0

    const-string p0, "OnScreenFingerprintUiMech"

    const-string v0, "hideUdfpsOverlay onFpTouchUp"

    invoke-static {p0, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-static {}, Lcom/oplus/systemui/aod/common/DreamHelper;->getInstance()Lcom/oplus/systemui/aod/common/DreamHelper;

    move-result-object p0

    iget-object p0, p0, Lcom/oplus/systemui/aod/common/DreamHelper;->mDreamPolicy:Lcom/oplus/systemui/aod/common/IDreamPolicy;

    if-eqz p0, :cond_0

    invoke-interface {p0}, Lcom/oplus/systemui/aod/common/IDreamPolicy;->onFpTouchUp()V

    :cond_0
    return-void
.end method

.method public final highlightControl(Landroid/content/Context;ZLjava/lang/String;)V
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->workerHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;

    const/4 v2, 0x0

    invoke-direct {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;-><init>(I)V

    iput-object p0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-object p1, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->$context:Landroid/content/Context;

    iput-boolean p2, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->$enable:Z

    iput-object p3, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->$reason:Ljava/lang/String;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_0
    return-void
.end method

.method public final isFingerprintIconReallyVisible()Z
    .locals 1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_1

    if-eqz v0, :cond_1

    invoke-virtual {v0}, Landroid/widget/ImageView;->getVisibility()I

    move-result v0

    if-nez v0, :cond_1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz p0, :cond_0

    invoke-virtual {p0}, Landroid/widget/ImageView;->getDrawable()Landroid/graphics/drawable/Drawable;

    move-result-object p0

    goto :goto_0

    :cond_0
    const/4 p0, 0x0

    :goto_0
    if-eqz p0, :cond_1

    const/4 p0, 0x1

    return p0

    :cond_1
    const/4 p0, 0x0

    return p0
.end method

.method public final isHighlightEnable()Z
    .locals 1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->highLightControl:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    if-eqz p0, :cond_0

    monitor-enter p0

    :try_start_0
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;->isHighlightEnable:Z
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    monitor-exit p0

    const/4 p0, 0x1

    if-ne v0, p0, :cond_0

    return p0

    :catchall_0
    move-exception v0

    :try_start_1
    monitor-exit p0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    throw v0

    :cond_0
    const/4 p0, 0x0

    return p0
.end method

.method public final isInFingerViewArea(II)Z
    .locals 10

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    const/16 v1, 0x8

    const-string v2, "OnScreenFingerprintUiMechLimit"

    const-string v3, "OnScreenFingerprintUiMech"

    const/4 v4, 0x0

    if-eqz v0, :cond_a

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawable:Landroid/graphics/drawable/Drawable;

    if-nez v0, :cond_0

    goto/16 :goto_0

    :cond_0
    sget-object v0, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->Companion:Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v5}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/FingerSwitchHelper;->isFingerprintUnlockEnable()Z

    move-result v0

    const/4 v5, 0x1

    if-nez v0, :cond_1

    new-instance p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$$ExternalSyntheticLambda0;

    invoke-direct {p0, v5}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$$ExternalSyntheticLambda0;-><init>(I)V

    invoke-static {v3, v2, v1, v4, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;IZLkotlin/jvm/functions/Function0;)V

    return v4

    :cond_1
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    move-object v1, v0

    check-cast v1, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    iget-boolean v1, v1, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->mPrimaryBouncerShowing:Z

    if-eqz v1, :cond_2

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isShowFpWhenBouncer:Z

    if-nez v0, :cond_3

    const-string/jumbo p0, "not in finger area in bouncer"

    invoke-static {v3, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return v4

    :cond_2
    invoke-interface {v0}, Lcom/android/systemui/statusbar/policy/KeyguardStateController;->getEx()Lcom/android/systemui/statusbar/policy/OplusKeyguardStateControllerEx;

    move-result-object v0

    invoke-virtual {v0}, Lcom/android/systemui/statusbar/policy/OplusKeyguardStateControllerEx;->isKeyguardFpSuppressed()Z

    move-result v0

    if-eqz v0, :cond_3

    const-string/jumbo p0, "not in finger area with suppress finger showing"

    invoke-static {v3, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return v4

    :cond_3
    invoke-static {}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getCurrentUser()I

    move-result v0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v1, v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getUserCanSkipBouncer(I)Z

    move-result v0

    if-eqz v0, :cond_4

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconReallyVisible()Z

    move-result v0

    if-nez v0, :cond_4

    const-string/jumbo p0, "not in finger area can skip bouncer"

    invoke-static {v3, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return v4

    :cond_4
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    iget-boolean v1, v0, Lcom/android/keyguard/KeyguardUpdateMonitor;->mKeyguardShowing:Z

    if-nez v1, :cond_5

    const-string/jumbo p0, "not in finger area user unlock now in launcher"

    invoke-static {v3, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return v4

    :cond_5
    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result v0

    if-nez v0, :cond_6

    const-string/jumbo p0, "not in finger area isFingerprintDetectionRunning is false"

    invoke-static {v3, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return v4

    :cond_6
    new-instance v0, Landroid/graphics/Rect;

    invoke-direct {v0}, Landroid/graphics/Rect;-><init>()V

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpLocation:[I

    invoke-virtual {v1}, Ljava/lang/Object;->clone()Ljava/lang/Object;

    move-result-object v1

    check-cast v1, [I

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v2, :cond_9

    invoke-virtual {v2}, Landroid/widget/ImageView;->getMeasuredWidth()I

    move-result v6

    invoke-virtual {v2}, Landroid/widget/ImageView;->getMeasuredHeight()I

    move-result v2

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawable:Landroid/graphics/drawable/Drawable;

    if-eqz p0, :cond_9

    invoke-virtual {p0}, Landroid/graphics/drawable/Drawable;->getIntrinsicWidth()I

    move-result v7

    int-to-float v7, v7

    sget-object v8, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v8}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getZoomOut()F

    move-result v9

    mul-float/2addr v9, v7

    float-to-int v7, v9

    invoke-virtual {p0}, Landroid/graphics/drawable/Drawable;->getIntrinsicHeight()I

    move-result p0

    int-to-float p0, p0

    invoke-virtual {v8}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getZoomOut()F

    move-result v8

    mul-float/2addr v8, p0

    float-to-int p0, v8

    aget v8, v1, v4

    if-gez v8, :cond_7

    aget v9, v1, v5

    invoke-static {v8}, Ljava/lang/Math;->abs(I)I

    move-result v8

    add-int/2addr v8, v9

    aput v8, v1, v5

    aput v4, v1, v4

    :cond_7
    aget v4, v1, v4

    div-int/lit8 v6, v6, 0x2

    div-int/lit8 v8, v7, 0x2

    sub-int/2addr v6, v8

    add-int/2addr v6, v4

    iput v6, v0, Landroid/graphics/Rect;->left:I

    aget v1, v1, v5

    div-int/lit8 v2, v2, 0x2

    div-int/lit8 v4, p0, 0x2

    sub-int/2addr v2, v4

    add-int/2addr v2, v1

    iput v2, v0, Landroid/graphics/Rect;->top:I

    add-int/2addr v6, v7

    iput v6, v0, Landroid/graphics/Rect;->right:I

    add-int/2addr v2, p0

    iput v2, v0, Landroid/graphics/Rect;->bottom:I

    invoke-virtual {v0, p1, p2}, Landroid/graphics/Rect;->contains(II)Z

    move-result p0

    if-eqz p0, :cond_8

    const-string p1, "isInFingerViewArea"

    invoke-static {v3, p1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    :cond_8
    return p0

    :cond_9
    return v4

    :cond_a
    :goto_0
    new-instance p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$$ExternalSyntheticLambda0;

    invoke-direct {p0, v4}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$$ExternalSyntheticLambda0;-><init>(I)V

    invoke-static {v3, v2, v1, v4, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;IZLkotlin/jvm/functions/Function0;)V

    return v4
.end method

.method public final isNotificationOverlayFingerPrint()Z
    .locals 8

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->lockScreenNotificationExtStateManagerLazy:Ldagger/Lazy;

    invoke-interface {v0}, Ldagger/Lazy;->get()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/oplus/systemui/notification/lockscreen/statemanager/LockScreenNotificationExtStateManager;

    invoke-virtual {v0}, Lcom/oplus/systemui/notification/lockscreen/statemanager/LockScreenNotificationExtStateManager;->getExtStateEvent()Lkotlinx/coroutines/flow/StateFlow;

    move-result-object v0

    invoke-interface {v0}, Lkotlinx/coroutines/flow/StateFlow;->getValue()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/oplus/systemui/notification/lockscreen/ILockScreenExtStateController$ExtStateEvent;

    invoke-virtual {v0}, Lcom/oplus/systemui/notification/lockscreen/ILockScreenExtStateController$ExtStateEvent;->getNewState()I

    move-result v0

    const/4 v1, 0x0

    const/4 v2, 0x1

    if-ne v0, v2, :cond_0

    return v1

    :cond_0
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayTop:F

    iget v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->notificationDisplayBottom:F

    const/high16 v4, -0x40800000    # -1.0f

    cmpg-float v5, v0, v4

    if-nez v5, :cond_1

    goto :goto_0

    :cond_1
    cmpg-float v4, v3, v4

    if-nez v4, :cond_2

    goto :goto_0

    :cond_2
    cmpg-float v4, v3, v0

    if-gtz v4, :cond_3

    :goto_0
    return v1

    :cond_3
    const/4 v4, 0x2

    new-array v4, v4, [I

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-eqz v5, :cond_4

    invoke-virtual {v5, v4}, Landroid/widget/ImageView;->getLocationOnScreen([I)V

    :cond_4
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-eqz p0, :cond_5

    invoke-virtual {p0}, Landroid/widget/ImageView;->getHeight()I

    move-result p0

    int-to-float p0, p0

    goto :goto_1

    :cond_5
    const/high16 p0, 0x42c80000    # 100.0f

    :goto_1
    const/4 v5, 0x0

    cmpg-float v5, p0, v5

    if-gtz v5, :cond_6

    return v1

    :cond_6
    aget v4, v4, v2

    int-to-float v4, v4

    add-float/2addr p0, v4

    invoke-static {}, Lcom/oplusos/systemui/common/util/LogUtil;->getNormalDebug()Z

    move-result v5

    if-eqz v5, :cond_7

    const-string v5, "Keyguard"

    invoke-static {v5}, Lcom/oplusos/systemui/common/util/LogUtil;->isTagValid(Ljava/lang/String;)Z

    move-result v5

    if-eqz v5, :cond_7

    const-string v5, ", bottom="

    const-string v6, ", fpIconTop="

    const-string v7, "isNotificationOverlayFingerPrint top="

    invoke-static {v7, v0, v5, v3, v6}, Landroidx/compose/animation/core/MonoSpline$$ExternalSyntheticOutline0;->m(Ljava/lang/String;FLjava/lang/String;FLjava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v5

    const-string v6, ", fpIconBottom="

    const-string v7, "OnScreenFingerprintUiMech-->"

    invoke-static {v5, v4, v6, p0, v7}, Lcom/oplus/keyguard/VFXController$stopAnim$1$$ExternalSyntheticOutline0;->m(Ljava/lang/StringBuilder;FLjava/lang/String;FLjava/lang/String;)Ljava/lang/String;

    move-result-object v5

    const-string v6, "SystemUi--Keyguard"

    invoke-static {v6, v5}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    :cond_7
    cmpg-float v3, v4, v3

    if-gez v3, :cond_8

    cmpl-float p0, p0, v0

    if-lez p0, :cond_8

    return v2

    :cond_8
    return v1
.end method

.method public final isPressAnimRunning()Z
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    const/4 v1, 0x1

    const/4 v2, 0x0

    if-eqz v0, :cond_1

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result p0

    if-ne p0, v1, :cond_0

    return v1

    :cond_0
    return v2

    :cond_1
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawableTmp:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz p0, :cond_2

    if-eqz p0, :cond_2

    invoke-virtual {p0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result p0

    if-ne p0, v1, :cond_2

    return v1

    :cond_2
    return v2
.end method

.method public final isScreenOn()Z
    .locals 1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenLifecycle:Lcom/android/systemui/keyguard/ScreenLifecycle;

    if-eqz p0, :cond_0

    invoke-virtual {p0}, Lcom/android/systemui/keyguard/ScreenLifecycle;->getScreenState()I

    move-result p0

    const/4 v0, 0x2

    if-ne p0, v0, :cond_0

    const/4 p0, 0x1

    return p0

    :cond_0
    const/4 p0, 0x0

    return p0
.end method

.method public final isShowInScreenOff()Z
    .locals 2

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/4 v0, 0x0

    if-eqz p0, :cond_0

    iget-boolean p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    const/4 v1, 0x1

    if-ne p0, v1, :cond_0

    return v1

    :cond_0
    return v0
.end method

.method public final loadAnimDrawables()V
    .locals 13

    const-string v0, "OnScreenFingerprintUiMech"

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v1

    invoke-virtual {v1}, Landroid/content/Context;->getUserId()I

    move-result v2

    invoke-static {}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getCurrentUser()I

    move-result v3

    const/4 v4, 0x0

    if-ne v2, v3, :cond_0

    goto :goto_0

    :cond_0
    invoke-static {}, Lcom/android/keyguard/KeyguardUpdateMonitor;->getCurrentUser()I

    move-result v2

    invoke-static {v2}, Landroid/os/UserHandle;->of(I)Landroid/os/UserHandle;

    move-result-object v2

    invoke-virtual {v1, v2, v4}, Landroid/content/Context;->createContextAsUser(Landroid/os/UserHandle;I)Landroid/content/Context;

    move-result-object v1

    :goto_0
    sget-object v2, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v3, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v3}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v3

    invoke-virtual {v2, v3}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object v3

    invoke-virtual {v3}, Lcom/oplus/keyguard/utils/KeyguardUtils;->updateGlobalThemeFeature()V

    invoke-virtual {v1}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v3

    :try_start_0
    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/4 v6, 0x1

    if-eqz v5, :cond_2

    iget-boolean v5, v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v5, v6, :cond_2

    sget-object v5, Lcom/oplus/systemui/biometrics/finger/udfps/CustomFingerprintStyleUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/CustomFingerprintStyleUtils$Companion;

    invoke-virtual {v5}, Lcom/oplus/systemui/biometrics/finger/udfps/CustomFingerprintStyleUtils$Companion;->getBitmapFromFPDirectory()Landroid/graphics/Bitmap;

    move-result-object v5

    if-eqz v5, :cond_1

    new-instance v7, Landroid/graphics/drawable/BitmapDrawable;

    invoke-direct {v7, v3, v5}, Landroid/graphics/drawable/BitmapDrawable;-><init>(Landroid/content/res/Resources;Landroid/graphics/Bitmap;)V

    goto :goto_1

    :cond_1
    invoke-virtual {v3}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-virtual {p0, v3}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getImMobileDrawable(Landroid/content/res/Resources;)Landroid/graphics/drawable/Drawable;

    move-result-object v7

    goto :goto_1

    :cond_2
    invoke-virtual {v3}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-virtual {p0, v3}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getImMobileDrawable(Landroid/content/res/Resources;)Landroid/graphics/drawable/Drawable;

    move-result-object v7

    :goto_1
    iput-object v7, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawable:Landroid/graphics/drawable/Drawable;
    :try_end_0
    .catch Landroid/content/res/Resources$NotFoundException; {:try_start_0 .. :try_end_0} :catch_0

    const v5, 0x7f081169

    const/4 v7, 0x0

    invoke-virtual {v3, v5, v7}, Landroid/content/res/Resources;->getDrawable(ILandroid/content/res/Resources$Theme;)Landroid/graphics/drawable/Drawable;

    move-result-object v5

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawableHY:Landroid/graphics/drawable/Drawable;

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v5}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v5

    invoke-virtual {v2, v5}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object v5

    iget-boolean v5, v5, Lcom/oplus/keyguard/utils/KeyguardUtils;->isFpGlobalThemeEnable:Z

    if-nez v5, :cond_4

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v5}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isThirdTheme()Z

    move-result v5

    if-eqz v5, :cond_4

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v5, :cond_4

    iget-boolean v5, v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->isSupportDarkResValue:Z

    if-ne v5, v6, :cond_4

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v5, :cond_5

    iget-object v8, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawable:Landroid/graphics/drawable/Drawable;

    invoke-static {v8}, Lcom/android/systemui/biometrics/Utils;->toBitmap(Landroid/graphics/drawable/Drawable;)Landroid/graphics/Bitmap;

    move-result-object v8

    if-eqz v8, :cond_3

    iget-object v9, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawableHY:Landroid/graphics/drawable/Drawable;

    invoke-static {v9}, Lcom/android/systemui/biometrics/Utils;->toBitmap(Landroid/graphics/drawable/Drawable;)Landroid/graphics/Bitmap;

    move-result-object v9

    invoke-virtual {v8, v9}, Landroid/graphics/Bitmap;->sameAs(Landroid/graphics/Bitmap;)Z

    move-result v8

    if-ne v8, v6, :cond_3

    move v8, v6

    goto :goto_2

    :cond_3
    move v8, v4

    :goto_2
    xor-int/2addr v8, v6

    invoke-virtual {v5, v8}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->setThirdThemeWithFP(Z)V

    goto :goto_3

    :cond_4
    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v5, :cond_5

    invoke-virtual {v5, v4}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->setThirdThemeWithFP(Z)V

    :cond_5
    :goto_3
    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/4 v8, 0x2

    if-eqz v5, :cond_6

    iget-boolean v5, v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v5, v6, :cond_6

    goto :goto_4

    :cond_6
    new-instance v5, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    invoke-virtual {p0, v8}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v9

    invoke-direct {v5, v1, v9}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iget-object v9, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    invoke-virtual {v5, v9}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setOnAnimationDrawableListener(Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;)V

    new-instance v5, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    const/4 v9, 0x4

    invoke-virtual {p0, v9}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v9

    invoke-direct {v5, v1, v9}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iget-object v9, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    invoke-virtual {v5, v9}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setOnAnimationDrawableListener(Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;)V

    invoke-virtual {v1}, Landroid/content/Context;->getUserId()I

    move-result v5

    iget-object v9, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iget-object v10, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    new-instance v11, Ljava/lang/StringBuilder;

    const-string/jumbo v12, "loadAnimDrawables,current userId:"

    invoke-direct {v11, v12}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v11, v5}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v5, ", fadeInAnimDrawable: "

    invoke-virtual {v11, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v11, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    const-string v5, ", fadeOutAnimDrawable: "

    invoke-virtual {v11, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v11, v10}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v11}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v5

    invoke-static {v0, v5}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    :goto_4
    sget-object v5, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-direct {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getFadeOutAnimTime()I

    move-result v9

    int-to-float v9, v9

    const v10, 0x3fa66666    # 1.3f

    mul-float/2addr v9, v10

    float-to-long v9, v9

    invoke-virtual {v5, v9, v10}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->setFadeOutAnimTime(J)V

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v5, :cond_7

    invoke-virtual {v5}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v5

    if-ne v5, v6, :cond_7

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawableTmp:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v5, :cond_7

    invoke-virtual {v5}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->stop()V

    :cond_7
    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const-string/jumbo v9, "optical_fp_anim_style"

    if-eqz v5, :cond_8

    iget-boolean v5, v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isNewStyle:Z

    if-ne v5, v6, :cond_8

    const-string/jumbo v5, "optical_fp_anim_style_press"

    goto :goto_5

    :cond_8
    move-object v5, v9

    :goto_5
    invoke-virtual {v2, v5}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getEnableFingerprintAnimPkg(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v5

    if-eqz v5, :cond_9

    const-string v10, "com.android.systemui.overlay.fingerprint.anim.halo"

    invoke-static {v5, v10, v4}, Lkotlin/text/StringsKt__StringsKt;->contains(Ljava/lang/CharSequence;Ljava/lang/CharSequence;Z)Z

    move-result v10

    if-ne v10, v6, :cond_9

    move v10, v6

    goto :goto_6

    :cond_9
    move v10, v4

    :goto_6
    if-eqz v5, :cond_a

    const-string v11, "com.android.systemui.overlay.fingerprint.anim.huanying"

    invoke-static {v5, v11, v4}, Lkotlin/text/StringsKt__StringsKt;->contains(Ljava/lang/CharSequence;Ljava/lang/CharSequence;Z)Z

    move-result v5

    if-ne v5, v6, :cond_a

    move v5, v6

    goto :goto_7

    :cond_a
    move v5, v4

    :goto_7
    const/16 v11, 0x8

    if-eqz v10, :cond_b

    invoke-virtual {v2}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getANIM_LEVEL()I

    move-result v12

    if-ne v12, v6, :cond_b

    new-instance v5, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;

    invoke-virtual {p0, v11}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v8

    invoke-direct {v5, v1, v8}, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    goto :goto_8

    :cond_b
    if-eqz v5, :cond_c

    invoke-virtual {v2}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getANIM_LEVEL()I

    move-result v5

    if-ne v5, v6, :cond_c

    new-instance v5, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;

    invoke-virtual {p0, v11}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v10

    invoke-direct {v5, v1, v10}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v7, v5, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCoeSysEffect:Lcom/coe/syseffect/COESysEffect;

    new-array v8, v8, [F

    iput-object v8, v5, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCenter:[F

    iput-object v1, v5, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mContext:Landroid/content/Context;

    new-instance v8, Lcom/coe/syseffect/COESysEffect;

    invoke-direct {v8, v1}, Lcom/coe/syseffect/COESysEffect;-><init>(Landroid/content/Context;)V

    iput-object v8, v5, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCoeSysEffect:Lcom/coe/syseffect/COESysEffect;

    const-string v10, "WaterRippleAnimation.coz"

    invoke-virtual {v8, v10, v4, v4}, Lcom/oplus/vfxsdk/common/COELoader;->load(Ljava/lang/String;ZZ)V

    iget-object v8, v5, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCoeSysEffect:Lcom/coe/syseffect/COESysEffect;

    invoke-virtual {v1}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;

    move-result-object v1

    invoke-virtual {v1}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object v1

    iget v1, v1, Landroid/util/DisplayMetrics;->density:F

    invoke-virtual {v8, v1}, Lcom/coe/syseffect/COESysEffect;->setDensity(F)V

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v1, :cond_e

    invoke-virtual {v5, v1}, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->setTargetView(Landroid/view/View;)V

    goto :goto_8

    :cond_c
    if-eqz v10, :cond_d

    sget-object v5, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v5}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    sget-boolean v5, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportWaterRipple:Z

    if-eqz v5, :cond_d

    invoke-virtual {v2}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getUPGRADE_ANIM_LEVEL()I

    move-result v5

    if-ne v5, v6, :cond_d

    new-instance v5, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;

    invoke-virtual {p0, v11}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v8

    invoke-direct {v5, v1, v8}, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    goto :goto_8

    :cond_d
    new-instance v5, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    invoke-virtual {p0, v11}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v8

    invoke-direct {v5, v1, v8}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    :cond_e
    :goto_8
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v1, :cond_f

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    invoke-virtual {v1, v5}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setOnAnimationDrawableListener(Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;)V

    :cond_f
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v1, :cond_10

    invoke-virtual {v1}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->getOptions()Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v7

    :cond_10
    if-eqz v7, :cond_11

    invoke-direct {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getScalePressedAnim()F

    move-result v1

    invoke-virtual {v7, v1}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;->setScaleRate(F)V

    :cond_11
    sget-object v1, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    sget-boolean v1, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportCPF:Z

    if-eqz v1, :cond_13

    if-eqz v7, :cond_13

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v5, :cond_12

    iget-boolean v5, v5, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isNewStyle:Z

    if-ne v5, v6, :cond_12

    const-string/jumbo v9, "optical_fp_anim_style_icon"

    :cond_12
    invoke-virtual {v2, v1, v9}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getOnScreenFingerprintAnimStyle(Landroid/content/Context;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v1

    const-string v2, "anim_199"

    invoke-static {v1, v2}, Landroid/text/TextUtils;->equals(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Z

    move-result v1

    if-eqz v1, :cond_13

    const v1, 0x7f0607b0

    invoke-virtual {v3, v1}, Landroid/content/res/Resources;->getColor(I)I

    move-result v1

    iput v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->colorOverride:I

    invoke-static {v1}, Ljava/lang/Integer;->toHexString(I)Ljava/lang/String;

    move-result-object v1

    const-string/jumbo v2, "override color to "

    invoke-static {v2, v1, v0}, Lcom/oplus/keyguard/VFXController$stopAnim$1$$ExternalSyntheticOutline0;->m$1(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    goto :goto_9

    :cond_13
    iput v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->colorOverride:I

    :goto_9
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isPressAnimRunning()Z

    move-result v0

    if-nez v0, :cond_14

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z

    if-eqz v0, :cond_14

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0xf

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_14
    return-void

    :catch_0
    const-string/jumbo p0, "loadAnimDrawables imMobileDrawable,NotFoundException"

    invoke-static {v0, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method

.method public final loadDrawableFromBitmap(Landroid/content/res/Resources;I)Landroid/graphics/drawable/Drawable;
    .locals 1

    new-instance p0, Landroid/graphics/BitmapFactory$Options;

    invoke-direct {p0}, Landroid/graphics/BitmapFactory$Options;-><init>()V

    const/4 v0, 0x0

    iput-boolean v0, p0, Landroid/graphics/BitmapFactory$Options;->inScaled:Z

    invoke-static {p1, p2, p0}, Landroid/graphics/BitmapFactory;->decodeResource(Landroid/content/res/Resources;ILandroid/graphics/BitmapFactory$Options;)Landroid/graphics/Bitmap;

    move-result-object p0

    if-eqz p0, :cond_0

    new-instance p2, Landroid/graphics/drawable/BitmapDrawable;

    invoke-direct {p2, p1, p0}, Landroid/graphics/drawable/BitmapDrawable;-><init>(Landroid/content/res/Resources;Landroid/graphics/Bitmap;)V

    return-object p2

    :cond_0
    const/4 p0, 0x0

    invoke-virtual {p1, p2, p0}, Landroid/content/res/Resources;->getDrawable(ILandroid/content/res/Resources$Theme;)Landroid/graphics/drawable/Drawable;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    return-object p0
.end method

.method public final notifyFpVisibilityChange(Z)V
    .locals 1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityListeners:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {p0}, Ljava/util/concurrent/CopyOnWriteArrayList;->iterator()Ljava/util/Iterator;

    move-result-object p0

    :cond_0
    :goto_0
    invoke-interface {p0}, Ljava/util/Iterator;->hasNext()Z

    move-result v0

    if-eqz v0, :cond_1

    invoke-interface {p0}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$OnFingerprintVisibilityListener;

    if-eqz v0, :cond_0

    invoke-interface {v0, p1}, Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$OnFingerprintVisibilityListener;->onFingerprintVisibilityChange(Z)V

    goto :goto_0

    :cond_1
    return-void
.end method

.method public final notifyHideAodIcon()V
    .locals 8

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_c

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showInAOD:I

    const/4 v1, 0x1

    if-ne v0, v1, :cond_0

    goto/16 :goto_5

    :cond_0
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-eqz v0, :cond_b

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_1

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    if-ne v0, v1, :cond_1

    goto :goto_0

    :cond_1
    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    sget-boolean v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isFpBlindUnlockEnabled:Z

    if-nez v0, :cond_2

    goto/16 :goto_4

    :cond_2
    :goto_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->realHideRunnable:Ljava/lang/Runnable;

    if-eqz v0, :cond_3

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v2, :cond_3

    invoke-virtual {v2, v0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_3
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v2, 0xb

    invoke-direct {v0, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->realHideRunnable:Ljava/lang/Runnable;

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const-wide/16 v2, 0x1f4

    if-eqz v0, :cond_4

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v0, v1, :cond_4

    move-wide v4, v2

    goto :goto_1

    :cond_4
    sget-object v0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getFadeOutAnimTime()J

    move-result-wide v4

    :goto_1
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconReallyVisible()Z

    move-result v0

    if-eqz v0, :cond_5

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    iget-object v6, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    const/4 v7, 0x3

    invoke-virtual {v0, v6, v7, v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->requestScreenState(Landroid/view/View;IZ)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    const-string v6, "FP-FadeOut"

    long-to-int v7, v4

    invoke-virtual {v0, v1, v7, v6}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->requestScreenState(IILjava/lang/String;)V

    :cond_5
    sget-object v0, Lcom/oplusos/systemui/common/feature/AodFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/AodFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/AodFeatureOption;->isSupportRamLessAod()Z

    move-result v0

    if-eqz v0, :cond_6

    goto :goto_3

    :cond_6
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :cond_7

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    if-ne v0, v1, :cond_7

    goto :goto_3

    :cond_7
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_8

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v0, v1, :cond_8

    const-wide/16 v2, 0x3e8

    goto :goto_2

    :cond_8
    sget-object v0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getFadeOutAnimTime()J

    move-result-wide v6

    add-long/2addr v2, v6

    :goto_2
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    const/4 v6, 0x7

    invoke-virtual {v0, v6, v2, v3}, Lcom/oplus/systemui/aod/display/BaseDisplayUtil;->acquireWakeLockInWorkThread(IJ)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_9

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v0, v1, :cond_9

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_a

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAlphaAnimation:Landroid/view/animation/AlphaAnimation;

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->startAnimation(Landroid/view/animation/Animation;)V

    goto :goto_3

    :cond_9
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0x17

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_a
    :goto_3
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->realHideRunnable:Ljava/lang/Runnable;

    if-eqz v0, :cond_b

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p0, :cond_b

    invoke-virtual {p0, v0, v4, v5}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_b
    :goto_4
    return-void

    :cond_c
    :goto_5
    const-string p0, "OnScreenFingerprintUiMech"

    const-string/jumbo v0, "no need to hide : fpIcon is null or not showing"

    invoke-static {p0, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method

.method public final notifyHighlightVisibleUpdate(Z)V
    .locals 1

    return-void

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isDisableAppDimLayer()Z

    move-result v0

    if-nez v0, :cond_1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dimLayer:Landroid/widget/ImageView;

    if-eqz p0, :cond_1

    if-eqz p1, :cond_0

    const/4 p1, 0x0

    goto :goto_0

    :cond_0
    const/16 p1, 0x8

    :goto_0
    invoke-virtual {p0, p1}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_1
    return-void
.end method

.method public final notifyShowAodIcon()V
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    const-string v1, "OnScreenFingerprintUiMech"

    if-eqz v0, :cond_2

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showInAOD:I

    const/4 v2, 0x1

    if-nez v0, :cond_0

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    if-nez v0, :cond_0

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_2

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->continueUsingFp:Z

    if-ne v0, v2, :cond_2

    :cond_0
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-eqz v0, :cond_1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_1

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    if-ne v0, v2, :cond_1

    const-string/jumbo v0, "show"

    invoke-static {v1, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->cancelRealHideRunnable()V

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopFadeOutAnimation()V

    const/4 v0, 0x0

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setVisibilityInAOD(I)V

    :cond_1
    return-void

    :cond_2
    const-string/jumbo p0, "no need to show : fpIcon is showing"

    invoke-static {v1, p0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    return-void
.end method

.method public final onFpTouch(Z)V
    .locals 5

    const-string/jumbo v0, "requestDisplayPower() in touchdown, deviceDisplayState:"

    const-string/jumbo v1, "touchEvent isDown "

    monitor-enter p0

    :try_start_0
    iget-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    if-nez v2, :cond_0

    monitor-exit p0

    return-void

    :cond_0
    :try_start_1
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    if-nez v2, :cond_1

    monitor-exit p0

    return-void

    :cond_1
    :try_start_2
    iget-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-eq v2, p1, :cond_4

    const-string v2, "OnScreenFingerprintUiMech"

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3, v1}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3, p1}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v2, v1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->touchRunnable:Ljava/lang/Runnable;

    if-eqz p1, :cond_2

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v1, :cond_2

    invoke-virtual {v1, p1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    goto :goto_0

    :catchall_0
    move-exception p1

    goto :goto_1

    :cond_2
    :goto_0
    sget-boolean p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->FINGERPRINT_BLOCK_POLICY_ENABLED:Z

    const/4 v1, 0x2

    if-nez p1, :cond_3

    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-eqz p1, :cond_3

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {p1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object p1

    invoke-virtual {p1}, Lcom/oplus/systemui/aod/display/BaseDisplayUtil;->getDeviceDisplayState()I

    move-result p1

    const-string v2, "OnScreenFingerprintUiMech"

    sget-object v3, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->shouldResetDisplayPowerOnAuthFailure:Ljava/util/concurrent/atomic/AtomicBoolean;

    invoke-virtual {v3}, Ljava/util/concurrent/atomic/AtomicBoolean;->get()Z

    move-result v3

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v4, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v0, ",  shouldResetDisplayPowerOnAuthFailure:"

    invoke-virtual {v4, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v4, v3}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v2, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-eqz v0, :cond_3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/aod/display/BaseDisplayUtil;->isDreaming()Z

    move-result v0

    if-eqz v0, :cond_3

    if-eq p1, v1, :cond_3

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    const/4 v0, 0x0

    invoke-direct {p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->runOnWorkThread(Ljava/lang/Runnable;)V

    :cond_3
    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    invoke-direct {p1, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->touchRunnable:Ljava/lang/Runnable;

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_4

    invoke-virtual {v0, p1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z
    :try_end_2
    .catchall {:try_start_2 .. :try_end_2} :catchall_0

    :cond_4
    monitor-exit p0

    return-void

    :goto_1
    :try_start_3
    monitor-exit p0
    :try_end_3
    .catchall {:try_start_3 .. :try_end_3} :catchall_0

    throw p1
.end method

.method public final onKeyguardExitFinished(Landroid/content/Context;)V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-nez v0, :cond_0

    goto :goto_0

    :cond_0
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const/4 v1, 0x5

    if-ne v0, v1, :cond_1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    iget-boolean v0, v0, Lcom/android/keyguard/KeyguardUpdateMonitor;->mKeyguardShowing:Z

    if-nez v0, :cond_1

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isServiceRequest:Z

    if-eqz v0, :cond_1

    const-string v0, "auth other before keyguard exit finished"

    invoke-virtual {p0, p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateHighlightState(Landroid/content/Context;Ljava/lang/String;)V

    :cond_1
    :goto_0
    return-void
.end method

.method public final removeFpSizeCallback(Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$IFpSizeCallback;)V
    .locals 1

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {v0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->contains(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :cond_0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {p0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->remove(Ljava/lang/Object;)Z

    :cond_0
    return-void
.end method

.method public final removeVisibilityListener(Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$OnFingerprintVisibilityListener;)V
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->visibilityListeners:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {p0, p1}, Ljava/util/concurrent/CopyOnWriteArrayList;->remove(Ljava/lang/Object;)Z

    return-void
.end method

.method public final restoreIconDrawable(Z)V
    .locals 2

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-eqz v0, :cond_0

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showForEnroll:Z

    if-nez v0, :cond_0

    return-void

    :cond_0
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;

    const/4 v1, 0x1

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean p1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->$focus:Z

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void
.end method

.method public final saveFpIconLog(Ljava/lang/String;)V
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz p0, :cond_0

    invoke-virtual {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->saveLog(Ljava/lang/String;)V

    :cond_0
    return-void
.end method

.method public final setFingerprintIconShow(Z)V
    .locals 0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconShow:Z

    return-void
.end method

.method public final setFingerprintTouchListener(Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$IFingerprintTouchListener;)V
    .locals 0

    return-void
.end method

.method public final setFpAlphaSpringAnimation(Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;)V
    .locals 0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpAlphaSpringAnimation:Lcom/coui/appcompat/animation/dynamicanimation/COUISpringAnimation;

    return-void
.end method

.method public final setIsOverlayReplacingValue(I)V
    .locals 0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz p0, :cond_0

    invoke-virtual {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->setIsOverlayReplacingValue(I)V

    :cond_0
    return-void
.end method

.method public final setNeedDoFadeInAnimation(Z)V
    .locals 0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    return-void
.end method

.method public final setOnDozeState(Z)V
    .locals 0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDozeState:Z

    return-void
.end method

.method public final setOnDreamingStart(Z)V
    .locals 0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    return-void
.end method

.method public final setOverlayUtils(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;)V
    .locals 0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    return-void
.end method

.method public final setShowFpWhenBouncer(Z)V
    .locals 0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isShowFpWhenBouncer:Z

    return-void
.end method

.method public final setTouchDownNow(Z)V
    .locals 0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    return-void
.end method

.method public final setVisibilityInAOD(I)V
    .locals 3

    const-string/jumbo v0, "setVisibilityInAOD state="

    monitor-enter p0

    :try_start_0
    iput p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showInAOD:I

    const-string v1, "OnScreenFingerprintUiMech"

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v1, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    if-nez p1, :cond_1

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {p1}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result p1

    if-eqz p1, :cond_0

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {p1}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isFpClientStop()Z

    move-result p1

    if-nez p1, :cond_0

    const/4 p1, 0x0

    invoke-virtual {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->restoreIconDrawable(Z)V

    goto :goto_0

    :catchall_0
    move-exception p1

    goto :goto_1

    :cond_0
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isPressAnimRunning()Z

    move-result p1

    if-nez p1, :cond_2

    const/4 p1, 0x1

    invoke-virtual {p0, p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->restoreIconDrawable(Z)V

    goto :goto_0

    :cond_1
    iget-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-nez p1, :cond_2

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v0, 0x12

    invoke-direct {p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    :cond_2
    :goto_0
    monitor-exit p0

    return-void

    :goto_1
    monitor-exit p0

    throw p1
.end method

.method public final showFingerprintIconAnimation(Z)V
    .locals 2

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;

    const/4 v1, 0x2

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean p1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpIconAlpha$1;->$focus:Z

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void
.end method

.method public final showFingerprintIconTemporarily(Ljava/lang/String;)V
    .locals 5

    sget-object v0, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->isSwitchUserDialogShow(Landroid/content/Context;)Z

    move-result v1

    if-eqz v1, :cond_0

    goto :goto_0

    :cond_0
    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconReason:Ljava/lang/String;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v1, :cond_1

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconRunnable:Ljava/lang/Runnable;

    invoke-virtual {v1, v2}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_1
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0, v1}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->isDarkModeAnimPlaying(Landroid/content/Context;)Z

    move-result v0

    const-string v1, "OnScreenFingerprintUiMech"

    if-eqz v0, :cond_3

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconDelayedCount:I

    const/16 v2, 0xa

    if-gt v0, v2, :cond_3

    const-string/jumbo p1, "showFingerprintIconTemporarily postDelayed,isDarkModeAnimPlaying,delayedCount:"

    invoke-static {v0, p1, v1}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(ILjava/lang/String;Ljava/lang/String;)V

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p1, :cond_2

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconRunnable:Ljava/lang/Runnable;

    const-wide/16 v0, 0x12c

    invoke-virtual {p1, p0, v0, v1}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_2
    :goto_0
    return-void

    :cond_3
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasHideIconByQs:Z

    const/4 v2, 0x0

    if-eqz v0, :cond_6

    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->hasHideIconByQs:Z

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    new-instance v3, Ljava/lang/StringBuilder;

    const-string/jumbo v4, "showFingerprintIconTemporarily for reason: "

    invoke-direct {v3, v4}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string p1, " fpShowReason: "

    invoke-virtual {v3, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v3, v0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {v1, p1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const/4 v0, -0x1

    if-eq p1, v0, :cond_6

    iget p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const/4 v0, 0x1

    if-eqz p1, :cond_5

    if-eq p1, v0, :cond_5

    const/4 v1, 0x2

    if-ne p1, v1, :cond_4

    goto :goto_1

    :cond_4
    move v0, v2

    :cond_5
    :goto_1
    const/16 p1, 0x65

    invoke-virtual {p0, p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShow(IZ)V

    :cond_6
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz p1, :cond_7

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconRunnable:Ljava/lang/Runnable;

    invoke-virtual {p1, v0}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_7
    const/4 p1, 0x0

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconReason:Ljava/lang/String;

    iput v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconDelayedCount:I

    return-void
.end method

.method public final startToAnimInDream()V
    .locals 4

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/common/AodManager;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/common/AodManager;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/aod/common/AodManager;->isPortrait()Z

    move-result v0

    if-nez v0, :cond_0

    goto :goto_3

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/4 v1, 0x1

    if-eqz v0, :cond_1

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    if-ne v0, v1, :cond_1

    goto :goto_0

    :cond_1
    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    sget-boolean v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isFpBlindUnlockEnabled:Z

    if-eqz v0, :cond_6

    :goto_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getDreamingDelay(Landroid/content/Context;)I

    move-result v0

    const-string v2, "OnScreenFingerprintUiMech"

    const-string/jumbo v3, "startToAnimInDream,delay:"

    invoke-static {v0, v3, v2}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(ILjava/lang/String;Ljava/lang/String;)V

    iput-boolean v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v2}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v2

    invoke-virtual {v2}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isPanoramicProcessType()Z

    move-result v2

    if-eqz v2, :cond_3

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v2, :cond_2

    iget-boolean v2, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v2, v1, :cond_2

    goto :goto_1

    :cond_2
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getFadeInAnimState()Z

    move-result v2

    if-eqz v2, :cond_4

    :cond_3
    :goto_1
    move v2, v1

    goto :goto_2

    :cond_4
    const/4 v2, 0x0

    :goto_2
    iput-boolean v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    if-lez v0, :cond_5

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v2, :cond_5

    iget-boolean v2, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    if-ne v2, v1, :cond_5

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v1

    invoke-virtual {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->updateFingerprintIconAlpha()V

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v1, :cond_6

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dreamingRunnable:Ljava/lang/Runnable;

    int-to-long v2, v0

    invoke-virtual {v1, p0, v2, v3}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    return-void

    :cond_5
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->dreamingRunnable:Ljava/lang/Runnable;

    invoke-interface {p0}, Ljava/lang/Runnable;->run()V

    :cond_6
    :goto_3
    return-void
.end method

.method public final stopFadeOutAnimation()V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :cond_0

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    const/4 v1, 0x1

    if-ne v0, v1, :cond_0

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0x1b

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_0
    return-void
.end method

.method public final stopOpticalAnimation()V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    const/4 v1, 0x1

    if-ne v0, v1, :cond_0

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0x1a

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_0
    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopFadeOutAnimation()V

    return-void
.end method

.method public final stopPressedAnimation()V
    .locals 3

    const/4 v0, 0x0

    iput-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    const/4 v1, 0x1

    if-eqz v0, :cond_0

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    if-ne v0, v1, :cond_0

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v2, 0x1c

    invoke-direct {v0, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawableTmp:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :cond_1

    if-eqz v0, :cond_1

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    if-ne v0, v1, :cond_1

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    const/16 v1, 0x1d

    invoke-direct {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_1
    return-void
.end method

.method public final updateDisplayIRISAndColorMode(Landroid/content/Context;ZLjava/lang/String;)V
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->workerHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;

    const/4 v2, 0x1

    invoke-direct {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;-><init>(I)V

    iput-object p0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-object p1, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->$context:Landroid/content/Context;

    iput-boolean p2, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->$enable:Z

    iput-object p3, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$highlightControl$1;->$reason:Ljava/lang/String;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_0
    return-void
.end method

.method public final updateFingerIconOrientation(Z)V
    .locals 4

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    if-eqz v0, :cond_5

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-nez v1, :cond_0

    goto :goto_2

    :cond_0
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    iget-boolean v2, v1, Lcom/android/keyguard/KeyguardUpdateMonitor;->mKeyguardShowing:Z

    if-eqz v2, :cond_1

    iget-boolean v1, v1, Lcom/android/keyguard/KeyguardUpdateMonitor;->mKeyguardGoingAway:Z

    if-nez v1, :cond_1

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    check-cast v1, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    iget-boolean v1, v1, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->mOccluded:Z

    if-nez v1, :cond_1

    const/4 v1, -0x1

    goto :goto_0

    :cond_1
    const/4 v1, 0x1

    :goto_0
    invoke-virtual {v0}, Landroid/widget/FrameLayout;->getLayoutParams()Landroid/view/ViewGroup$LayoutParams;

    move-result-object v0

    instance-of v2, v0, Landroid/view/WindowManager$LayoutParams;

    if-eqz v2, :cond_3

    move-object v2, v0

    check-cast v2, Landroid/view/WindowManager$LayoutParams;

    iget v3, v2, Landroid/view/WindowManager$LayoutParams;->screenOrientation:I

    if-ne v3, v1, :cond_2

    if-eqz p1, :cond_3

    :cond_2
    iput v1, v2, Landroid/view/WindowManager$LayoutParams;->screenOrientation:I

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz p1, :cond_3

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    invoke-interface {p1, v2, v0}, Landroid/view/WindowManager;->updateViewLayout(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_3
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-eqz p1, :cond_4

    invoke-virtual {p1}, Landroid/widget/ImageView;->getLayoutParams()Landroid/view/ViewGroup$LayoutParams;

    move-result-object p1

    goto :goto_1

    :cond_4
    const/4 p1, 0x0

    :goto_1
    instance-of v0, p1, Landroid/view/WindowManager$LayoutParams;

    if-eqz v0, :cond_5

    move-object v0, p1

    check-cast v0, Landroid/view/WindowManager$LayoutParams;

    iget v2, v0, Landroid/view/WindowManager$LayoutParams;->screenOrientation:I

    if-eq v2, v1, :cond_5

    iput v1, v0, Landroid/view/WindowManager$LayoutParams;->screenOrientation:I

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz v0, :cond_5

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    invoke-interface {v0, p0, p1}, Landroid/view/WindowManager;->updateViewLayout(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_5
    :goto_2
    return-void
.end method

.method public final updateFpColor(I)V
    .locals 3

    sget-object v0, Lcom/oplusos/systemui/common/feature/FlavorOneFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/FlavorOneFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/FlavorOneFeatureOption;->isFlavorOneDevice()Z

    move-result v0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/4 v2, 0x1

    if-eqz v0, :cond_0

    if-eqz v1, :cond_1

    iget-boolean v0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v0, v2, :cond_1

    invoke-virtual {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomSystemFpIcon()Ljava/lang/Boolean;

    move-result-object v0

    sget-object v1, Ljava/lang/Boolean;->TRUE:Ljava/lang/Boolean;

    invoke-static {v0, v1}, Lkotlin/jvm/internal/Intrinsics;->areEqual(Ljava/lang/Object;Ljava/lang/Object;)Z

    move-result v0

    if-nez v0, :cond_1

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    const/4 v0, 0x3

    invoke-direct {p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void

    :cond_0
    if-eqz v1, :cond_1

    iget-boolean v0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v0, v2, :cond_1

    invoke-virtual {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomCharFpIcon()Ljava/lang/Boolean;

    move-result-object v0

    sget-object v1, Ljava/lang/Boolean;->TRUE:Ljava/lang/Boolean;

    invoke-static {v0, v1}, Lkotlin/jvm/internal/Intrinsics;->areEqual(Ljava/lang/Object;Ljava/lang/Object;)Z

    move-result v0

    if-nez v0, :cond_1

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    const/4 v0, 0x4

    invoke-direct {p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    return-void

    :cond_1
    const/high16 v0, -0x1000000

    if-ne p1, v0, :cond_2

    const p1, -0xcccccd

    :cond_2
    new-instance v0, Landroid/graphics/PorterDuffColorFilter;

    sget-object v1, Landroid/graphics/PorterDuff$Mode;->SRC_ATOP:Landroid/graphics/PorterDuff$Mode;

    invoke-direct {v0, p1, v1}, Landroid/graphics/PorterDuffColorFilter;-><init>(ILandroid/graphics/PorterDuff$Mode;)V

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->imMobileDrawable:Landroid/graphics/drawable/Drawable;

    if-eqz p1, :cond_5

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz p1, :cond_3

    iget-boolean p1, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne p1, v2, :cond_3

    goto :goto_0

    :cond_3
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz p1, :cond_4

    invoke-virtual {p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->isSupportDarkRes()Z

    move-result p1

    if-ne p1, v2, :cond_4

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    const/4 v1, 0x5

    invoke-direct {p1, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    goto :goto_1

    :cond_4
    :goto_0
    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;

    const/4 v1, 0x0

    invoke-direct {p1, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-object v0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateFpColor$3;->$filter:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_5
    :goto_1
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz p1, :cond_7

    invoke-virtual {p1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->isSupportDarkRes()Z

    move-result p1

    if-ne p1, v2, :cond_7

    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz p1, :cond_6

    invoke-virtual {p1}, Landroid/graphics/drawable/AnimationDrawable;->clearColorFilter()V

    :cond_6
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz p1, :cond_9

    invoke-virtual {p1}, Landroid/graphics/drawable/AnimationDrawable;->clearColorFilter()V

    goto :goto_2

    :cond_7
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeInAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz p1, :cond_8

    invoke-virtual {p1, v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setColorFilter(Landroid/graphics/ColorFilter;)V

    :cond_8
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz p1, :cond_9

    invoke-virtual {p1, v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setColorFilter(Landroid/graphics/ColorFilter;)V

    :cond_9
    :goto_2
    iget-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz p1, :cond_a

    new-instance p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;

    const/4 v0, 0x6

    invoke-direct {p1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;-><init>(I)V

    iput-object p0, p1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$touchEvent$2;->this$0:Ljava/lang/Object;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {p1}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    :cond_a
    return-void
.end method

.method public final declared-synchronized updateFpColorForWhiteBackground()V
    .locals 1

    monitor-enter p0

    :try_start_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v0, :cond_0

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpColorForOtherAppNoDimLayer:I

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpColor(I)V

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpColorForOtherAppNoDimLayer:I

    iput v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->currentFpIconColor:I
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    goto :goto_0

    :catchall_0
    move-exception v0

    goto :goto_1

    :cond_0
    :goto_0
    monitor-exit p0

    return-void

    :goto_1
    :try_start_1
    monitor-exit p0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    throw v0
.end method

.method public final updateFpIconAlphaDelay()V
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    invoke-virtual {v0, v1}, Landroid/os/Handler;->hasCallbacks(Ljava/lang/Runnable;)Z

    move-result v0

    const/4 v1, 0x1

    if-ne v0, v1, :cond_0

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    invoke-virtual {v0, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    const-wide/16 v1, 0xbb8

    invoke-virtual {v0, p0, v1, v2}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    :cond_1
    return-void
.end method

.method public final updateFpIconAlphaRunnable()V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    invoke-virtual {v0, v1}, Landroid/os/Handler;->hasCallbacks(Ljava/lang/Runnable;)Z

    move-result v0

    const/4 v1, 0x1

    if-ne v0, v1, :cond_0

    return-void

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->opticalUiUpdateHandler:Landroid/os/Handler;

    if-eqz v0, :cond_1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlphaRunnable:Ljava/lang/Runnable;

    invoke-virtual {v0, p0}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_1
    return-void
.end method

.method public final updateFpIconColor()V
    .locals 8

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v0

    const/4 v1, 0x0

    const/4 v2, 0x5

    const/4 v3, 0x1

    if-nez v0, :cond_0

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUltrasonicFps()Z

    move-result v0

    if-eqz v0, :cond_1

    :cond_0
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    if-ne v0, v2, :cond_1

    move v0, v3

    goto :goto_0

    :cond_1
    move v0, v1

    :goto_0
    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportUltrasonicFps()Z

    move-result v4

    const/4 v5, 0x2

    if-eqz v4, :cond_2

    iget v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    if-ne v4, v5, :cond_2

    move v1, v3

    :cond_2
    if-eqz v0, :cond_3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isBiometricPromptShowing()Z

    move-result v0

    if-nez v0, :cond_3

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpColorForWhiteBackground()V

    return-void

    :cond_3
    if-eqz v1, :cond_4

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpColorForWhiteBackground()V

    return-void

    :cond_4
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->suggestColor:I

    const/4 v1, -0x1

    if-eq v0, v1, :cond_5

    goto :goto_2

    :cond_5
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->colorOverride:I

    if-eqz v0, :cond_6

    goto :goto_2

    :cond_6
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-eqz v0, :cond_8

    :cond_7
    :goto_1
    move v0, v1

    goto :goto_2

    :cond_8
    sget-object v0, Lcom/oplus/keyguard/utils/KeyguardUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v4}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v4

    invoke-virtual {v0, v4}, Lcom/oplus/keyguard/utils/KeyguardUtils$Companion;->getKeyguardUtils(Landroid/content/Context;)Lcom/oplus/keyguard/utils/KeyguardUtils;

    move-result-object v0

    iget-boolean v0, v0, Lcom/oplus/keyguard/utils/KeyguardUtils;->isClockGlobalThemeEnable:Z

    if-nez v0, :cond_7

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardUpdateMonitor:Lcom/android/keyguard/KeyguardUpdateMonitor;

    invoke-virtual {v0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->isFingerprintDetectionRunning()Z

    move-result v0

    if-eqz v0, :cond_7

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->screenLifecycle:Lcom/android/systemui/keyguard/ScreenLifecycle;

    invoke-virtual {v0}, Lcom/android/systemui/keyguard/ScreenLifecycle;->getScreenState()I

    move-result v0

    if-eq v0, v5, :cond_9

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isPanoramicProcessType()Z

    move-result v0

    if-eqz v0, :cond_7

    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->onDreamingStart:Z

    if-nez v0, :cond_7

    :cond_9
    iget-boolean v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->bouncerShowing:Z

    if-eqz v0, :cond_a

    goto :goto_1

    :cond_a
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconColor:I

    :goto_2
    iget v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const-string v5, "OnScreenFingerprintUiMech"

    const-string v6, "fpShowReason: "

    if-ne v4, v2, :cond_b

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isBiometricPromptShowing()Z

    move-result v2

    if-nez v2, :cond_b

    sget-object v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v2, v4}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;

    move-result-object v2

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenBrightnessUtils;->getCurrentBrightnessPercentage()F

    move-result v2

    const v4, 0x3f59999a    # 0.85f

    cmpl-float v2, v2, v4

    if-lez v2, :cond_b

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isBiometricPromptShowing()Z

    move-result v2

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4, v6}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v4, v0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v0, ",isBiometricPromptShowing: "

    invoke-virtual {v4, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v4, v2}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v5, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    const v2, 0x7f0607b8

    invoke-virtual {v0, v2}, Landroid/content/Context;->getColor(I)I

    move-result v0

    :cond_b
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oplusBiometricAuthController:Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/OplusBiometricAuthController;->isBiometricPromptShowing()Z

    move-result v2

    if-nez v2, :cond_c

    iget v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    const/4 v4, 0x3

    if-ne v2, v4, :cond_f

    :cond_c
    iget v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpShowReason:I

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v4}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v4

    invoke-static {v4}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result v4

    new-instance v7, Ljava/lang/StringBuilder;

    invoke-direct {v7, v6}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v7, v2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v2, ",isNightMode: "

    invoke-virtual {v7, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v7, v4}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    invoke-virtual {v7}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-static {v5, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    const/high16 v4, -0x1000000

    if-eqz v2, :cond_d

    iget-boolean v2, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v2, v3, :cond_d

    goto :goto_3

    :cond_d
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v2, :cond_10

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->isSupportDarkRes()Z

    move-result v2

    if-ne v2, v3, :cond_10

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v1}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v1

    invoke-static {v1}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result v1

    if-nez v1, :cond_f

    :cond_e
    move v1, v4

    goto :goto_4

    :cond_f
    move v1, v0

    goto :goto_4

    :cond_10
    :goto_3
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-virtual {v0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object v0

    invoke-static {v0}, Lcom/oplus/util/OplusDarkModeUtil;->isNightMode(Landroid/content/Context;)Z

    move-result v0

    if-eqz v0, :cond_e

    :goto_4
    invoke-static {v1}, Ljava/lang/Integer;->toHexString(I)Ljava/lang/String;

    move-result-object v0

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->overlayUtils:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;

    if-eqz v2, :cond_11

    invoke-virtual {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerOverlayUtils;->isSupportDarkRes()Z

    move-result v2

    invoke-static {v2}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object v2

    goto :goto_5

    :cond_11
    const/4 v2, 0x0

    :goto_5
    new-instance v4, Ljava/lang/StringBuilder;

    const-string/jumbo v6, "updateFpIconColor, color=0x"

    invoke-direct {v4, v6}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v4, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v0, ", isSupportDarkRes = "

    invoke-virtual {v4, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v4, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v5, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->currentFpIconColor:I

    if-eq v0, v1, :cond_12

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isFingerprintIconReallyVisible()Z

    move-result v0

    if-eqz v0, :cond_12

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isPanoramicProcessType()Z

    move-result v0

    if-eqz v0, :cond_12

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->switchHelper:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    if-eqz v0, :cond_12

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->showInScreenOff:Z

    if-ne v0, v3, :cond_12

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->currentFpIconColor:I

    const-string/jumbo v2, "startFingerprintColorGradientsAnim"

    invoke-static {v5, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    new-instance v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$startFingerprintColorGradientsAnim$1;

    invoke-direct {v2}, Ljava/lang/Object;-><init>()V

    iput-object p0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$startFingerprintColorGradientsAnim$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput v0, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$startFingerprintColorGradientsAnim$1;->$start:I

    iput v1, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$startFingerprintColorGradientsAnim$1;->$end:I

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    goto :goto_6

    :cond_12
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;

    invoke-direct {v0, v3}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->updateOpticalUI(Ljava/lang/Runnable;)V

    invoke-virtual {p0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpColor(I)V

    :goto_6
    iput v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->currentFpIconColor:I

    return-void
.end method

.method public final updateFpIconSize()V
    .locals 6

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    if-nez v0, :cond_0

    goto/16 :goto_2

    :cond_0
    const-string v0, "OnScreenFingerprintUiMech"

    const-string/jumbo v1, "updateFpIconSize"

    invoke-static {v0, v1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->calculateFpIconSizeParams(Landroid/content/Context;)V

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->INSTANCE:Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getZoomOut()F

    move-result v1

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v2, :cond_1

    invoke-virtual {v2, v1}, Landroid/widget/ImageView;->setScaleX(F)V

    :cond_1
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v2, :cond_2

    invoke-virtual {v2, v1}, Landroid/widget/ImageView;->setScaleY(F)V

    :cond_2
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v2, :cond_3

    sget-object v3, Landroid/widget/ImageView$ScaleType;->CENTER:Landroid/widget/ImageView$ScaleType;

    invoke-virtual {v2, v3}, Landroid/widget/ImageView;->setScaleType(Landroid/widget/ImageView$ScaleType;)V

    :cond_3
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v2, :cond_4

    invoke-virtual {v2, v1}, Landroid/widget/ImageView;->setScaleX(F)V

    :cond_4
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v2, :cond_5

    invoke-virtual {v2, v1}, Landroid/widget/ImageView;->setScaleY(F)V

    :cond_5
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadow:Landroid/widget/ImageView;

    if-eqz v2, :cond_6

    sget-object v3, Landroid/widget/ImageView$ScaleType;->CENTER:Landroid/widget/ImageView$ScaleType;

    invoke-virtual {v2, v3}, Landroid/widget/ImageView;->setScaleType(Landroid/widget/ImageView$ScaleType;)V

    :cond_6
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v2, :cond_7

    invoke-virtual {v2, v1}, Landroid/widget/ImageView;->setScaleX(F)V

    :cond_7
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v2, :cond_8

    invoke-virtual {v2, v1}, Landroid/widget/ImageView;->setScaleY(F)V

    :cond_8
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconShadowOther:Landroid/widget/ImageView;

    if-eqz v1, :cond_9

    sget-object v2, Landroid/widget/ImageView$ScaleType;->CENTER:Landroid/widget/ImageView$ScaleType;

    invoke-virtual {v1, v2}, Landroid/widget/ImageView;->setScaleType(Landroid/widget/ImageView$ScaleType;)V

    :cond_9
    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getIconMarginBottom()I

    move-result v1

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    const/4 v3, 0x0

    if-eqz v2, :cond_a

    invoke-virtual {v2}, Landroid/widget/FrameLayout;->getLayoutParams()Landroid/view/ViewGroup$LayoutParams;

    move-result-object v2

    goto :goto_0

    :cond_a
    move-object v2, v3

    :goto_0
    instance-of v4, v2, Landroid/view/WindowManager$LayoutParams;

    if-eqz v4, :cond_b

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getAnimIconSize()I

    move-result v4

    move-object v5, v2

    check-cast v5, Landroid/view/WindowManager$LayoutParams;

    iput v4, v5, Landroid/view/WindowManager$LayoutParams;->width:I

    iput v4, v5, Landroid/view/WindowManager$LayoutParams;->height:I

    div-int/lit8 v4, v4, 0x2

    sub-int v4, v1, v4

    iput v4, v5, Landroid/view/WindowManager$LayoutParams;->y:I

    iget-object v4, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz v4, :cond_b

    iget-object v5, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIconLayout:Landroid/widget/FrameLayout;

    invoke-interface {v4, v5, v2}, Landroid/view/WindowManager;->updateViewLayout(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_b
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    if-eqz v2, :cond_c

    invoke-virtual {v2}, Landroid/widget/ImageView;->getLayoutParams()Landroid/view/ViewGroup$LayoutParams;

    move-result-object v3

    :cond_c
    instance-of v2, v3, Landroid/view/WindowManager$LayoutParams;

    if-eqz v2, :cond_d

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/KeyguardFingerprintUtils;->getPressedIconSize()I

    move-result v0

    move-object v2, v3

    check-cast v2, Landroid/view/WindowManager$LayoutParams;

    iput v0, v2, Landroid/view/WindowManager$LayoutParams;->width:I

    iput v0, v2, Landroid/view/WindowManager$LayoutParams;->height:I

    div-int/lit8 v0, v0, 0x2

    sub-int/2addr v1, v0

    iput v1, v2, Landroid/view/WindowManager$LayoutParams;->y:I

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->windowManager:Landroid/view/WindowManager;

    if-eqz v0, :cond_d

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedIcon:Landroid/widget/ImageView;

    invoke-interface {v0, v1, v3}, Landroid/view/WindowManager;->updateViewLayout(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V

    :cond_d
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpSizeCallback:Ljava/util/concurrent/CopyOnWriteArrayList;

    invoke-virtual {p0}, Ljava/util/concurrent/CopyOnWriteArrayList;->iterator()Ljava/util/Iterator;

    move-result-object p0

    :cond_e
    :goto_1
    invoke-interface {p0}, Ljava/util/Iterator;->hasNext()Z

    move-result v0

    if-eqz v0, :cond_f

    invoke-interface {p0}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Lcom/android/systemui/biometrics/OplusBiometricAuthControllerEx$IFpSizeCallback;

    if-eqz v0, :cond_e

    check-cast v0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;

    const/4 v2, 0x0

    invoke-direct {v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;-><init>(I)V

    iput-object v0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;->f$0:Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->runOnUIThread(Lkotlin/jvm/functions/Function0;)V

    goto :goto_1

    :cond_f
    :goto_2
    return-void
.end method

.method public final updateHighlightState(Landroid/content/Context;Ljava/lang/String;)V
    .locals 2

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->workerHandler:Landroid/os/Handler;

    if-eqz v0, :cond_0

    new-instance v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateHighlightState$1;

    invoke-direct {v1}, Ljava/lang/Object;-><init>()V

    iput-object p0, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateHighlightState$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-object p1, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateHighlightState$1;->$context:Landroid/content/Context;

    iput-object p2, v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$updateHighlightState$1;->$reason:Ljava/lang/String;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_0
    return-void
.end method

.method public final updateIsShowFpWhenBouncer(Z)V
    .locals 2

    const-string/jumbo v0, "updateIsShowFpWhenBouncer(), isShow="

    const-string v1, "OnScreenFingerprintUiMech"

    invoke-static {v0, v1, p1}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Z)V

    if-eqz p1, :cond_0

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->keyguardStateController:Lcom/android/systemui/statusbar/policy/KeyguardStateController;

    check-cast v0, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;

    iget-boolean v0, v0, Lcom/android/systemui/statusbar/policy/KeyguardStateControllerImpl;->mPrimaryBouncerShowing:Z

    if-nez v0, :cond_0

    const-string p1, "isShow true but bouncer not showing"

    invoke-static {v1, p1}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    const/4 p1, 0x0

    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isShowFpWhenBouncer:Z

    return-void

    :cond_0
    iput-boolean p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isShowFpWhenBouncer:Z

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlpha$default(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    return-void
.end method

.method public final oneosStartWave()V
    .locals 3

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v1, :oneos_end

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :oneos_have

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    if-eqz v0, :oneos_end

    const/16 v2, 0x8

    invoke-virtual {p0, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOptions(I)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;

    move-result-object v2

    const/16 v0, 0x10

    iput v0, v2, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;->mDuration:I

    new-instance v0, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->context:Landroid/content/Context;

    invoke-direct {v0, v1, v2}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;-><init>(Landroid/content/Context;Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$Options;)V

    iput-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimationDrawableListener:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setOnAnimationDrawableListener(Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;)V

    :oneos_have
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v1, :oneos_end

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pressedAnimDrawable:Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    if-eqz v0, :oneos_end

    const/4 v2, 0x0

    invoke-virtual {v1, v2}, Landroid/view/View;->setVisibility(I)V

    const/high16 v2, 0x3f800000    # 1.0f

    invoke-virtual {v1, v2}, Landroid/view/View;->setAlpha(F)V

    invoke-virtual {v1, v0}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    invoke-virtual {v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->start()V

    :oneos_end
    return-void
.end method
