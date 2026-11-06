.class public final Loneos/launcher/OneOSDt2s;
.super Ljava/lang/Object;
.source "OneOSDt2s.java"


# static fields
.field private static final ACTION:Ljava/lang/String; = "oneos.intent.action.DOUBLE_TAP_SLEEP"

.field private static last:J

.field private static lastX:I

.field private static lastY:I


# direct methods
.method private constructor <init>()V
    .locals 0

    .line 22
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static wallpaperTap(Ljava/lang/String;IILandroid/view/View;)V
    .locals 9

    .line 27
    const-string v0, "OneOSDt2s"

    :try_start_0
    const-string v1, "android.wallpaper.tap"

    invoke-virtual {v1, p0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p0

    if-nez p0, :cond_0

    return-void

    .line 28
    :cond_0
    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v1

    .line 29
    invoke-virtual {p3}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object p0

    invoke-static {p0}, Landroid/view/ViewConfiguration;->get(Landroid/content/Context;)Landroid/view/ViewConfiguration;

    move-result-object p0

    invoke-virtual {p0}, Landroid/view/ViewConfiguration;->getScaledTouchSlop()I

    move-result p0

    mul-int/lit8 p0, p0, 0x6

    .line 30
    sget-wide v3, Loneos/launcher/OneOSDt2s;->last:J

    const-wide/16 v5, 0x0

    cmp-long v3, v3, v5

    if-eqz v3, :cond_1

    sget-wide v3, Loneos/launcher/OneOSDt2s;->last:J

    sub-long v3, v1, v3

    const-wide/16 v7, 0x190

    cmp-long v3, v3, v7

    if-gez v3, :cond_1

    sget v3, Loneos/launcher/OneOSDt2s;->lastX:I

    sub-int v3, p1, v3

    invoke-static {v3}, Ljava/lang/Math;->abs(I)I

    move-result v3

    if-ge v3, p0, :cond_1

    sget v3, Loneos/launcher/OneOSDt2s;->lastY:I

    sub-int v3, p2, v3

    invoke-static {v3}, Ljava/lang/Math;->abs(I)I

    move-result v3

    if-ge v3, p0, :cond_1

    .line 31
    sput-wide v5, Loneos/launcher/OneOSDt2s;->last:J

    .line 32
    invoke-static {}, Landroid/app/BroadcastOptions;->makeBasic()Landroid/app/BroadcastOptions;

    move-result-object p0

    .line 33
    const/4 p1, 0x1

    invoke-virtual {p0, p1}, Landroid/app/BroadcastOptions;->setShareIdentityEnabled(Z)Landroid/app/BroadcastOptions;

    .line 34
    invoke-virtual {p3}, Landroid/view/View;->getContext()Landroid/content/Context;

    move-result-object p1

    new-instance p2, Landroid/content/Intent;

    const-string p3, "oneos.intent.action.DOUBLE_TAP_SLEEP"

    invoke-direct {p2, p3}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string p3, "com.android.systemui"

    invoke-virtual {p2, p3}, Landroid/content/Intent;->setPackage(Ljava/lang/String;)Landroid/content/Intent;

    move-result-object p2

    invoke-virtual {p0}, Landroid/app/BroadcastOptions;->toBundle()Landroid/os/Bundle;

    move-result-object p0

    const/4 p3, 0x0

    invoke-virtual {p1, p2, p3, p0}, Landroid/content/Context;->sendBroadcast(Landroid/content/Intent;Ljava/lang/String;Landroid/os/Bundle;)V

    .line 35
    const-string p0, "double tap on the home screen: sleep asked"

    invoke-static {v0, p0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 36
    return-void

    .line 38
    :cond_1
    sput-wide v1, Loneos/launcher/OneOSDt2s;->last:J

    .line 39
    sput p1, Loneos/launcher/OneOSDt2s;->lastX:I

    .line 40
    sput p2, Loneos/launcher/OneOSDt2s;->lastY:I
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    .line 43
    goto :goto_0

    .line 41
    :catch_0
    move-exception p0

    .line 42
    const-string p1, "home screen double tap"

    invoke-static {v0, p1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 44
    :goto_0
    return-void
.end method
