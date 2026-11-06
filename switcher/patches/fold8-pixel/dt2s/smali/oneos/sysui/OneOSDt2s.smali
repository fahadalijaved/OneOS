.class public final Loneos/sysui/OneOSDt2s;
.super Ljava/lang/Object;
.source "OneOSDt2s.java"


# static fields
.field public static final ACTION:Ljava/lang/String; = "oneos.intent.action.DOUBLE_TAP_SLEEP"

.field private static final LAUNCHER:Ljava/lang/String; = "com.google.android.apps.nexuslauncher"

.field private static final TAG:Ljava/lang/String; = "OneOSDt2s"

.field private static blocker:Ljava/lang/String;

.field private static downTime:J

.field private static downX:F

.field private static downY:F

.field private static dozing:Z

.field private static lastTapOk:Z

.field private static lastUpTime:J

.field private static lastUpX:F

.field private static lastUpY:F

.field private static moved:Z

.field private static onEmpty:Z

.field private static registered:Z


# direct methods
.method private constructor <init>()V
    .locals 0

    .line 34
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method private static clickableAt(Landroid/view/View;IIJ)Z
    .locals 9

    .line 127
    instance-of v0, p0, Landroid/view/ViewGroup;

    const/4 v1, 0x0

    if-nez v0, :cond_0

    return v1

    .line 128
    :cond_0
    check-cast p0, Landroid/view/ViewGroup;

    .line 129
    new-instance v0, Landroid/graphics/Rect;

    invoke-direct {v0}, Landroid/graphics/Rect;-><init>()V

    .line 130
    invoke-virtual {p0}, Landroid/view/ViewGroup;->getChildCount()I

    move-result v2

    const/4 v3, 0x1

    sub-int/2addr v2, v3

    :goto_0
    if-ltz v2, :cond_5

    .line 131
    invoke-virtual {p0, v2}, Landroid/view/ViewGroup;->getChildAt(I)Landroid/view/View;

    move-result-object v4

    .line 132
    invoke-virtual {v4}, Landroid/view/View;->getVisibility()I

    move-result v5

    if-nez v5, :cond_4

    invoke-virtual {v4}, Landroid/view/View;->getAlpha()F

    move-result v5

    const/4 v6, 0x0

    cmpl-float v5, v5, v6

    if-nez v5, :cond_1

    goto :goto_1

    .line 133
    :cond_1
    invoke-virtual {v4, v0}, Landroid/view/View;->getGlobalVisibleRect(Landroid/graphics/Rect;)Z

    move-result v5

    if-eqz v5, :cond_4

    invoke-virtual {v0, p1, p2}, Landroid/graphics/Rect;->contains(II)Z

    move-result v5

    if-nez v5, :cond_2

    goto :goto_1

    .line 134
    :cond_2
    invoke-virtual {v4}, Landroid/view/View;->isClickable()Z

    move-result v5

    if-eqz v5, :cond_3

    invoke-virtual {v0}, Landroid/graphics/Rect;->width()I

    move-result v5

    int-to-long v5, v5

    invoke-virtual {v0}, Landroid/graphics/Rect;->height()I

    move-result v7

    int-to-long v7, v7

    mul-long/2addr v5, v7

    cmp-long v5, v5, p3

    if-gez v5, :cond_3

    .line 135
    invoke-virtual {v4}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/Class;->getSimpleName()Ljava/lang/String;

    move-result-object p0

    sput-object p0, Loneos/sysui/OneOSDt2s;->blocker:Ljava/lang/String;

    .line 136
    return v3

    .line 138
    :cond_3
    invoke-static {v4, p1, p2, p3, p4}, Loneos/sysui/OneOSDt2s;->clickableAt(Landroid/view/View;IIJ)Z

    move-result v4

    if-eqz v4, :cond_4

    return v3

    .line 130
    :cond_4
    :goto_1
    add-int/lit8 v2, v2, -0x1

    goto :goto_0

    .line 140
    :cond_5
    return v1
.end method

.method public static register(Landroid/view/View;)V
    .locals 3

    .line 38
    sget-boolean v0, Loneos/sysui/OneOSDt2s;->registered:Z

    if-eqz v0, :cond_0

    return-void

    .line 39
    :cond_0
    invoke-virtual {p0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object p0

    invoke-virtual {p0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    move-result-object p0

    .line 41
    :try_start_0
    new-instance v0, Loneos/sysui/OneOSDt2s$1;

    invoke-direct {v0, p0}, Loneos/sysui/OneOSDt2s$1;-><init>(Landroid/content/Context;)V

    new-instance v1, Landroid/content/IntentFilter;

    const-string v2, "oneos.intent.action.DOUBLE_TAP_SLEEP"

    invoke-direct {v1, v2}, Landroid/content/IntentFilter;-><init>(Ljava/lang/String;)V

    const/4 v2, 0x2

    invoke-virtual {p0, v0, v1, v2}, Landroid/content/Context;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;I)Landroid/content/Intent;

    .line 52
    const/4 p0, 0x1

    sput-boolean p0, Loneos/sysui/OneOSDt2s;->registered:Z
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    .line 55
    goto :goto_0

    .line 53
    :catch_0
    move-exception p0

    .line 54
    const-string v0, "OneOSDt2s"

    const-string v1, "no receiver for the home screen\'s double tap"

    invoke-static {v0, v1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 56
    :goto_0
    return-void
.end method

.method public static shadeTouch(Landroid/view/View;Landroid/view/MotionEvent;)V
    .locals 12

    .line 61
    const-string v0, "OneOSDt2s"

    :try_start_0
    invoke-virtual {p0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object v1

    const-class v2, Landroid/app/KeyguardManager;

    invoke-virtual {v1, v2}, Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Landroid/app/KeyguardManager;

    .line 62
    const-wide/16 v2, 0x190

    const/4 v4, 0x1

    const/4 v5, 0x0

    if-eqz v1, :cond_a

    invoke-virtual {v1}, Landroid/app/KeyguardManager;->isKeyguardLocked()Z

    move-result v1

    if-nez v1, :cond_0

    goto/16 :goto_5

    .line 69
    :cond_0
    invoke-virtual {p0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object v1

    invoke-static {v1}, Landroid/view/ViewConfiguration;->get(Landroid/content/Context;)Landroid/view/ViewConfiguration;

    move-result-object v1

    invoke-virtual {v1}, Landroid/view/ViewConfiguration;->getScaledTouchSlop()I

    move-result v1

    .line 70
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getActionMasked()I

    move-result v6

    packed-switch v6, :pswitch_data_0

    :pswitch_0
    goto/16 :goto_4

    .line 88
    :pswitch_1
    sput-boolean v4, Loneos/sysui/OneOSDt2s;->moved:Z

    .line 89
    sput-boolean v5, Loneos/sysui/OneOSDt2s;->lastTapOk:Z

    .line 90
    goto/16 :goto_4

    .line 84
    :pswitch_2
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getRawX()F

    move-result p0

    sget v2, Loneos/sysui/OneOSDt2s;->downX:F

    sub-float/2addr p0, v2

    invoke-static {p0}, Ljava/lang/Math;->abs(F)F

    move-result p0

    int-to-float v1, v1

    cmpl-float p0, p0, v1

    if-gtz p0, :cond_1

    invoke-virtual {p1}, Landroid/view/MotionEvent;->getRawY()F

    move-result p0

    sget p1, Loneos/sysui/OneOSDt2s;->downY:F

    sub-float/2addr p0, p1

    invoke-static {p0}, Ljava/lang/Math;->abs(F)F

    move-result p0

    cmpl-float p0, p0, v1

    if-lez p0, :cond_9

    :cond_1
    sput-boolean v4, Loneos/sysui/OneOSDt2s;->moved:Z

    goto/16 :goto_4

    .line 92
    :pswitch_3
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getEventTime()J

    move-result-wide v6

    .line 93
    sget-boolean v8, Loneos/sysui/OneOSDt2s;->moved:Z

    if-nez v8, :cond_2

    sget-boolean v8, Loneos/sysui/OneOSDt2s;->onEmpty:Z

    if-eqz v8, :cond_2

    sget-wide v8, Loneos/sysui/OneOSDt2s;->downTime:J

    sub-long v8, v6, v8

    const-wide/16 v10, 0xfa

    cmp-long v8, v8, v10

    if-gez v8, :cond_2

    goto :goto_0

    :cond_2
    move v4, v5

    .line 94
    :goto_0
    if-eqz v4, :cond_4

    sget-boolean v8, Loneos/sysui/OneOSDt2s;->lastTapOk:Z

    if-eqz v8, :cond_4

    sget-wide v8, Loneos/sysui/OneOSDt2s;->downTime:J

    sget-wide v10, Loneos/sysui/OneOSDt2s;->lastUpTime:J

    sub-long/2addr v8, v10

    cmp-long v8, v8, v2

    if-gez v8, :cond_4

    sget v8, Loneos/sysui/OneOSDt2s;->downX:F

    sget v9, Loneos/sysui/OneOSDt2s;->lastUpX:F

    sub-float/2addr v8, v9

    .line 95
    invoke-static {v8}, Ljava/lang/Math;->abs(F)F

    move-result v8

    mul-int/lit8 v1, v1, 0x6

    int-to-float v1, v1

    cmpg-float v8, v8, v1

    if-gez v8, :cond_4

    sget v8, Loneos/sysui/OneOSDt2s;->downY:F

    sget v9, Loneos/sysui/OneOSDt2s;->lastUpY:F

    sub-float/2addr v8, v9

    invoke-static {v8}, Ljava/lang/Math;->abs(F)F

    move-result v8

    cmpg-float v1, v8, v1

    if-gez v1, :cond_4

    .line 96
    sput-boolean v5, Loneos/sysui/OneOSDt2s;->lastTapOk:Z

    .line 97
    sget-boolean p1, Loneos/sysui/OneOSDt2s;->dozing:Z

    if-eqz p1, :cond_3

    .line 98
    invoke-virtual {p0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object p0

    const-string p1, "always-on display"

    invoke-static {p0, p1}, Loneos/sysui/OneOSDt2s;->wake(Landroid/content/Context;Ljava/lang/String;)V

    goto :goto_1

    .line 100
    :cond_3
    invoke-virtual {p0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object p0

    const-string p1, "lock screen"

    invoke-static {p0, p1}, Loneos/sysui/OneOSDt2s;->sleep(Landroid/content/Context;Ljava/lang/String;)V

    .line 102
    :goto_1
    return-void

    .line 104
    :cond_4
    sget-boolean p0, Loneos/sysui/OneOSDt2s;->onEmpty:Z

    if-nez p0, :cond_5

    sget-wide v8, Loneos/sysui/OneOSDt2s;->downTime:J

    sget-wide v10, Loneos/sysui/OneOSDt2s;->lastUpTime:J

    sub-long/2addr v8, v10

    cmp-long p0, v8, v2

    if-gez p0, :cond_5

    .line 105
    sget-object p0, Loneos/sysui/OneOSDt2s;->blocker:Ljava/lang/String;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "lock screen double tap on "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    const-string v1, ": ignored (a control is there)"

    invoke-virtual {p0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v0, p0}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 107
    :cond_5
    sput-boolean v4, Loneos/sysui/OneOSDt2s;->lastTapOk:Z

    .line 108
    sput-wide v6, Loneos/sysui/OneOSDt2s;->lastUpTime:J

    .line 109
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getRawX()F

    move-result p0

    sput p0, Loneos/sysui/OneOSDt2s;->lastUpX:F

    .line 110
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getRawY()F

    move-result p0

    sput p0, Loneos/sysui/OneOSDt2s;->lastUpY:F

    .line 111
    goto :goto_4

    .line 72
    :pswitch_4
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getEventTime()J

    move-result-wide v1

    sput-wide v1, Loneos/sysui/OneOSDt2s;->downTime:J

    .line 73
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getRawX()F

    move-result v1

    sput v1, Loneos/sysui/OneOSDt2s;->downX:F

    .line 74
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getRawY()F

    move-result p1

    sput p1, Loneos/sysui/OneOSDt2s;->downY:F

    .line 75
    sput-boolean v5, Loneos/sysui/OneOSDt2s;->moved:Z

    .line 76
    const/4 p1, 0x0

    sput-object p1, Loneos/sysui/OneOSDt2s;->blocker:Ljava/lang/String;

    .line 79
    invoke-virtual {p0}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object p1

    const-class v1, Landroid/os/PowerManager;

    invoke-virtual {p1, v1}, Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p1

    check-cast p1, Landroid/os/PowerManager;

    .line 80
    if-eqz p1, :cond_6

    invoke-virtual {p1}, Landroid/os/PowerManager;->isInteractive()Z

    move-result p1

    if-nez p1, :cond_6

    move p1, v4

    goto :goto_2

    :cond_6
    move p1, v5

    :goto_2
    sput-boolean p1, Loneos/sysui/OneOSDt2s;->dozing:Z

    .line 81
    sget-boolean p1, Loneos/sysui/OneOSDt2s;->dozing:Z

    if-nez p1, :cond_8

    sget p1, Loneos/sysui/OneOSDt2s;->downX:F

    float-to-int p1, p1

    sget v1, Loneos/sysui/OneOSDt2s;->downY:F

    float-to-int v1, v1

    invoke-virtual {p0}, Landroid/view/View;->getWidth()I

    move-result v2

    int-to-long v2, v2

    invoke-virtual {p0}, Landroid/view/View;->getHeight()I

    move-result v6

    int-to-long v6, v6

    mul-long/2addr v2, v6

    const-wide/16 v6, 0x2

    div-long/2addr v2, v6

    invoke-static {p0, p1, v1, v2, v3}, Loneos/sysui/OneOSDt2s;->clickableAt(Landroid/view/View;IIJ)Z

    move-result p0

    if-nez p0, :cond_7

    goto :goto_3

    :cond_7
    move v4, v5

    :cond_8
    :goto_3
    sput-boolean v4, Loneos/sysui/OneOSDt2s;->onEmpty:Z

    .line 82
    nop

    .line 117
    :cond_9
    :goto_4
    goto :goto_6

    .line 63
    :cond_a
    :goto_5
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getActionMasked()I

    move-result p0

    if-ne p0, v4, :cond_b

    sget-boolean p0, Loneos/sysui/OneOSDt2s;->lastTapOk:Z

    if-eqz p0, :cond_b

    invoke-virtual {p1}, Landroid/view/MotionEvent;->getEventTime()J

    move-result-wide p0

    sget-wide v6, Loneos/sysui/OneOSDt2s;->lastUpTime:J

    sub-long/2addr p0, v6

    cmp-long p0, p0, v2

    if-gez p0, :cond_b

    .line 64
    const-string p0, "lock screen double tap: keyguard not locked, ignored"

    invoke-static {v0, p0}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    .line 66
    :cond_b
    sput-boolean v5, Loneos/sysui/OneOSDt2s;->lastTapOk:Z
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    .line 67
    return-void

    .line 115
    :catch_0
    move-exception p0

    .line 116
    const-string p1, "lock screen double tap"

    invoke-static {v0, p1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 118
    :goto_6
    return-void

    :pswitch_data_0
    .packed-switch 0x0
        :pswitch_4
        :pswitch_3
        :pswitch_2
        :pswitch_1
        :pswitch_0
        :pswitch_1
    .end packed-switch
.end method

.method static sleep(Landroid/content/Context;Ljava/lang/String;)V
    .locals 7

    .line 162
    const-string v0, "double tap on the "

    const-string v1, "OneOSDt2s"

    :try_start_0
    const-class v2, Landroid/os/PowerManager;

    invoke-virtual {p0, v2}, Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p0

    check-cast p0, Landroid/os/PowerManager;

    .line 163
    const-class v2, Landroid/os/PowerManager;

    const-string v3, "goToSleep"

    const/4 v4, 0x1

    new-array v4, v4, [Ljava/lang/Class;

    sget-object v5, Ljava/lang/Long;->TYPE:Ljava/lang/Class;

    const/4 v6, 0x0

    aput-object v5, v4, v6

    invoke-virtual {v2, v3, v4}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v2

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v3

    invoke-static {v3, v4}, Ljava/lang/Long;->valueOf(J)Ljava/lang/Long;

    move-result-object v3

    filled-new-array {v3}, [Ljava/lang/Object;

    move-result-object v3

    invoke-virtual {v2, p0, v3}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    .line 164
    new-instance p0, Ljava/lang/StringBuilder;

    invoke-direct {p0}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {p0, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    const-string v2, ": sleep"

    invoke-virtual {p0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v1, p0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/ReflectiveOperationException; {:try_start_0 .. :try_end_0} :catch_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    .line 167
    goto :goto_0

    .line 165
    :catch_0
    move-exception p0

    .line 166
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v0, ": goToSleep failed"

    invoke-virtual {p1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {v1, p1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 168
    :goto_0
    return-void
.end method

.method static wake(Landroid/content/Context;Ljava/lang/String;)V
    .locals 8

    .line 146
    const-string v0, "double tap on the "

    const-string v1, "OneOSDt2s"

    :try_start_0
    const-class v2, Landroid/os/PowerManager;

    invoke-virtual {p0, v2}, Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p0

    check-cast p0, Landroid/os/PowerManager;
    :try_end_0
    .catch Ljava/lang/ReflectiveOperationException; {:try_start_0 .. :try_end_0} :catch_1
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_1

    .line 147
    nop

    .line 149
    :try_start_1
    const-class v2, Landroid/os/PowerManager;

    const-string v3, "WAKE_REASON_TAP"

    invoke-virtual {v2, v3}, Ljava/lang/Class;->getField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v2

    const/4 v3, 0x0

    invoke-virtual {v2, v3}, Ljava/lang/reflect/Field;->getInt(Ljava/lang/Object;)I

    move-result v2
    :try_end_1
    .catch Ljava/lang/ReflectiveOperationException; {:try_start_1 .. :try_end_1} :catch_0
    .catch Ljava/lang/RuntimeException; {:try_start_1 .. :try_end_1} :catch_1

    .line 151
    goto :goto_0

    .line 150
    :catch_0
    move-exception v2

    const/4 v2, 0x4

    .line 152
    :goto_0
    :try_start_2
    const-class v3, Landroid/os/PowerManager;

    const-string v4, "wakeUp"

    const/4 v5, 0x3

    new-array v5, v5, [Ljava/lang/Class;

    sget-object v6, Ljava/lang/Long;->TYPE:Ljava/lang/Class;

    const/4 v7, 0x0

    aput-object v6, v5, v7

    sget-object v6, Ljava/lang/Integer;->TYPE:Ljava/lang/Class;

    const/4 v7, 0x1

    aput-object v6, v5, v7

    const-class v6, Ljava/lang/String;

    const/4 v7, 0x2

    aput-object v6, v5, v7

    invoke-virtual {v3, v4, v5}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v3

    .line 153
    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v4

    invoke-static {v4, v5}, Ljava/lang/Long;->valueOf(J)Ljava/lang/Long;

    move-result-object v4

    invoke-static {v2}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v2

    const-string v5, "oneos:double-tap"

    filled-new-array {v4, v2, v5}, [Ljava/lang/Object;

    move-result-object v2

    invoke-virtual {v3, p0, v2}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    .line 154
    new-instance p0, Ljava/lang/StringBuilder;

    invoke-direct {p0}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {p0, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    const-string v2, ": wake"

    invoke-virtual {p0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v1, p0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_2
    .catch Ljava/lang/ReflectiveOperationException; {:try_start_2 .. :try_end_2} :catch_1
    .catch Ljava/lang/RuntimeException; {:try_start_2 .. :try_end_2} :catch_1

    .line 157
    goto :goto_1

    .line 155
    :catch_1
    move-exception p0

    .line 156
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v0, ": wakeUp failed"

    invoke-virtual {p1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {v1, p1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 158
    :goto_1
    return-void
.end method
