.class public final Loneos/camera/OneOSRecordProgress;
.super Ljava/lang/Object;
.source "OneOSRecordProgress.java"

# interfaces
.implements Ljava/lang/Runnable;


# static fields
.field private static final ACTIVE:Ljava/util/WeakHashMap;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/WeakHashMap<",
            "Landroid/media/MediaRecorder;",
            "Loneos/camera/OneOSRecordProgress;",
            ">;"
        }
    .end annotation
.end field


# instance fields
.field private final handler:Landroid/os/Handler;

.field private final recorder:Landroid/media/MediaRecorder;

.field private final session:Landroid/media/MediaRecorder$OnInfoListener;

.field private final start:J

.field private started:Z

.field private volatile stopped:Z

.field private ticks:I


# direct methods
.method static constructor <clinit>()V
    .locals 1

    .line 18
    new-instance v0, Ljava/util/WeakHashMap;

    invoke-direct {v0}, Ljava/util/WeakHashMap;-><init>()V

    sput-object v0, Loneos/camera/OneOSRecordProgress;->ACTIVE:Ljava/util/WeakHashMap;

    return-void
.end method

.method private constructor <init>(Landroid/media/MediaRecorder$OnInfoListener;Landroid/media/MediaRecorder;Landroid/os/Handler;)V
    .locals 2

    .line 27
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    .line 22
    invoke-static {}, Landroid/os/SystemClock;->elapsedRealtime()J

    move-result-wide v0

    iput-wide v0, p0, Loneos/camera/OneOSRecordProgress;->start:J

    .line 28
    iput-object p1, p0, Loneos/camera/OneOSRecordProgress;->session:Landroid/media/MediaRecorder$OnInfoListener;

    .line 29
    iput-object p2, p0, Loneos/camera/OneOSRecordProgress;->recorder:Landroid/media/MediaRecorder;

    .line 30
    iput-object p3, p0, Loneos/camera/OneOSRecordProgress;->handler:Landroid/os/Handler;

    .line 31
    return-void
.end method

.method public static start(Landroid/media/MediaRecorder$OnInfoListener;Landroid/media/MediaRecorder;Landroid/os/Handler;)V
    .locals 2

    .line 34
    new-instance v0, Loneos/camera/OneOSRecordProgress;

    invoke-direct {v0, p0, p1, p2}, Loneos/camera/OneOSRecordProgress;-><init>(Landroid/media/MediaRecorder$OnInfoListener;Landroid/media/MediaRecorder;Landroid/os/Handler;)V

    .line 35
    sget-object p0, Loneos/camera/OneOSRecordProgress;->ACTIVE:Ljava/util/WeakHashMap;

    monitor-enter p0

    .line 36
    :try_start_0
    sget-object v1, Loneos/camera/OneOSRecordProgress;->ACTIVE:Ljava/util/WeakHashMap;

    invoke-virtual {v1, p1, v0}, Ljava/util/WeakHashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p1

    check-cast p1, Loneos/camera/OneOSRecordProgress;

    .line 37
    if-eqz p1, :cond_0

    const/4 v1, 0x1

    iput-boolean v1, p1, Loneos/camera/OneOSRecordProgress;->stopped:Z

    .line 38
    :cond_0
    monitor-exit p0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    .line 39
    const-wide/16 p0, 0x15e

    invoke-virtual {p2, v0, p0, p1}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    .line 40
    return-void

    .line 38
    :catchall_0
    move-exception p1

    :try_start_1
    monitor-exit p0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    throw p1
.end method

.method public static stop(Landroid/media/MediaRecorder;)V
    .locals 4

    .line 45
    sget-object v0, Loneos/camera/OneOSRecordProgress;->ACTIVE:Ljava/util/WeakHashMap;

    monitor-enter v0

    :try_start_0
    sget-object v1, Loneos/camera/OneOSRecordProgress;->ACTIVE:Ljava/util/WeakHashMap;

    invoke-virtual {v1, p0}, Ljava/util/WeakHashMap;->remove(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Loneos/camera/OneOSRecordProgress;

    monitor-exit v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    .line 46
    if-eqz v1, :cond_0

    .line 47
    const/4 v0, 0x1

    iput-boolean v0, v1, Loneos/camera/OneOSRecordProgress;->stopped:Z

    .line 48
    const-string v0, "OneOSCamera"

    iget v1, v1, Loneos/camera/OneOSRecordProgress;->ticks:I

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "recording progress: stopped after "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, " reports"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 50
    :cond_0
    invoke-virtual {p0}, Landroid/media/MediaRecorder;->stop()V

    .line 51
    return-void

    .line 45
    :catchall_0
    move-exception p0

    :try_start_1
    monitor-exit v0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    throw p0
.end method


# virtual methods
.method public run()V
    .locals 6

    .line 55
    iget-boolean v0, p0, Loneos/camera/OneOSRecordProgress;->stopped:Z

    if-eqz v0, :cond_0

    return-void

    .line 56
    :cond_0
    invoke-static {}, Landroid/os/SystemClock;->elapsedRealtime()J

    move-result-wide v0

    iget-wide v2, p0, Loneos/camera/OneOSRecordProgress;->start:J

    sub-long/2addr v0, v2

    .line 58
    :try_start_0
    iget-object v2, p0, Loneos/camera/OneOSRecordProgress;->session:Landroid/media/MediaRecorder$OnInfoListener;

    iget-object v3, p0, Loneos/camera/OneOSRecordProgress;->recorder:Landroid/media/MediaRecorder;

    iget-boolean v4, p0, Loneos/camera/OneOSRecordProgress;->started:Z

    if-eqz v4, :cond_1

    const-wide/16 v4, 0x1

    invoke-static {v0, v1, v4, v5}, Ljava/lang/Math;->max(JJ)J

    move-result-wide v4

    long-to-int v4, v4

    goto :goto_0

    :cond_1
    const/4 v4, 0x0

    :goto_0
    const/16 v5, 0x385

    invoke-interface {v2, v3, v5, v4}, Landroid/media/MediaRecorder$OnInfoListener;->onInfo(Landroid/media/MediaRecorder;II)V
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    .line 62
    nop

    .line 63
    const/4 v2, 0x1

    iput-boolean v2, p0, Loneos/camera/OneOSRecordProgress;->started:Z

    .line 64
    iget v3, p0, Loneos/camera/OneOSRecordProgress;->ticks:I

    add-int/2addr v3, v2

    iput v3, p0, Loneos/camera/OneOSRecordProgress;->ticks:I

    .line 65
    const-wide/32 v3, 0x2932e00

    cmp-long v0, v0, v3

    if-gez v0, :cond_3

    iget-object v0, p0, Loneos/camera/OneOSRecordProgress;->handler:Landroid/os/Handler;

    iget-boolean v1, p0, Loneos/camera/OneOSRecordProgress;->started:Z

    if-eqz v1, :cond_2

    iget v1, p0, Loneos/camera/OneOSRecordProgress;->ticks:I

    if-ne v1, v2, :cond_2

    const-wide/16 v1, 0x96

    goto :goto_1

    :cond_2
    const-wide/16 v1, 0x1f4

    :goto_1
    invoke-virtual {v0, p0, v1, v2}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    .line 66
    :cond_3
    return-void

    .line 59
    :catch_0
    move-exception v0

    .line 60
    const-string v1, "OneOSCamera"

    const-string v2, "recording progress report failed"

    invoke-static {v1, v2, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 61
    return-void
.end method
