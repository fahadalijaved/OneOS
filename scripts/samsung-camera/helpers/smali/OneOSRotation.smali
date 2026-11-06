.class public final Loneos/camera/OneOSRotation;
.super Ljava/lang/Object;
.source "OneOSRotation.java"


# static fields
.field private static final OUT:Ljava/util/WeakHashMap;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/WeakHashMap<",
            "Landroid/media/MediaRecorder;",
            "Ljava/lang/Object;",
            ">;"
        }
    .end annotation
.end field

.field private static final ROT:Ljava/util/WeakHashMap;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/WeakHashMap<",
            "Landroid/media/MediaRecorder;",
            "Ljava/lang/Integer;",
            ">;"
        }
    .end annotation
.end field

.field private static final TAG:Ljava/lang/String; = "OneOSCamera"


# direct methods
.method static constructor <clinit>()V
    .locals 1

    .line 24
    new-instance v0, Ljava/util/WeakHashMap;

    invoke-direct {v0}, Ljava/util/WeakHashMap;-><init>()V

    sput-object v0, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    .line 25
    new-instance v0, Ljava/util/WeakHashMap;

    invoke-direct {v0}, Ljava/util/WeakHashMap;-><init>()V

    sput-object v0, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    return-void
.end method

.method private constructor <init>()V
    .locals 0

    .line 27
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method private static fd(Ljava/io/FileDescriptor;)Loneos/camera/OneOSMp4$Io;
    .locals 1

    .line 83
    new-instance v0, Loneos/camera/OneOSRotation$2;

    invoke-direct {v0, p0}, Loneos/camera/OneOSRotation$2;-><init>(Ljava/io/FileDescriptor;)V

    return-object v0
.end method

.method private static file(Ljava/io/RandomAccessFile;)Loneos/camera/OneOSMp4$Io;
    .locals 1

    .line 75
    new-instance v0, Loneos/camera/OneOSRotation$1;

    invoke-direct {v0, p0}, Loneos/camera/OneOSRotation$1;-><init>(Ljava/io/RandomAccessFile;)V

    return-object v0
.end method

.method public static setOrientationHint(Landroid/media/MediaRecorder;I)V
    .locals 2

    .line 42
    :try_start_0
    invoke-virtual {p0, p1}, Landroid/media/MediaRecorder;->setOrientationHint(I)V

    .line 43
    sget-object v0, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    monitor-enter v0
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    :try_start_1
    sget-object v1, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    invoke-virtual {v1, p0}, Ljava/util/WeakHashMap;->remove(Ljava/lang/Object;)Ljava/lang/Object;

    monitor-exit v0

    .line 46
    goto :goto_0

    .line 43
    :catchall_0
    move-exception v1

    monitor-exit v0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    :try_start_2
    throw v1
    :try_end_2
    .catch Ljava/lang/RuntimeException; {:try_start_2 .. :try_end_2} :catch_0

    .line 44
    :catch_0
    move-exception v0

    .line 45
    sget-object v0, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    monitor-enter v0

    :try_start_3
    sget-object v1, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    invoke-static {p1}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object p1

    invoke-virtual {v1, p0, p1}, Ljava/util/WeakHashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    monitor-exit v0

    .line 47
    :goto_0
    return-void

    .line 45
    :catchall_1
    move-exception p0

    monitor-exit v0
    :try_end_3
    .catchall {:try_start_3 .. :try_end_3} :catchall_1

    throw p0
.end method

.method public static setOutputFile(Landroid/media/MediaRecorder;Ljava/io/FileDescriptor;)V
    .locals 2

    .line 35
    invoke-virtual {p0, p1}, Landroid/media/MediaRecorder;->setOutputFile(Ljava/io/FileDescriptor;)V

    .line 36
    sget-object v0, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    monitor-enter v0

    :try_start_0
    sget-object v1, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    invoke-virtual {v1, p0, p1}, Ljava/util/WeakHashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    monitor-exit v0

    .line 37
    return-void

    .line 36
    :catchall_0
    move-exception p0

    monitor-exit v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    throw p0
.end method

.method public static setOutputFile(Landroid/media/MediaRecorder;Ljava/lang/String;)V
    .locals 2

    .line 30
    invoke-virtual {p0, p1}, Landroid/media/MediaRecorder;->setOutputFile(Ljava/lang/String;)V

    .line 31
    sget-object v0, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    monitor-enter v0

    :try_start_0
    sget-object v1, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    invoke-virtual {v1, p0, p1}, Ljava/util/WeakHashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    monitor-exit v0

    .line 32
    return-void

    .line 31
    :catchall_0
    move-exception p0

    monitor-exit v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    throw p0
.end method

.method public static stop(Landroid/media/MediaRecorder;)V
    .locals 4

    .line 51
    invoke-static {p0}, Loneos/camera/OneOSRecordProgress;->stop(Landroid/media/MediaRecorder;)V

    .line 54
    sget-object v0, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    monitor-enter v0

    :try_start_0
    sget-object v1, Loneos/camera/OneOSRotation;->ROT:Ljava/util/WeakHashMap;

    invoke-virtual {v1, p0}, Ljava/util/WeakHashMap;->remove(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Ljava/lang/Integer;

    monitor-exit v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_3

    .line 55
    sget-object v2, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    monitor-enter v2

    :try_start_1
    sget-object v0, Loneos/camera/OneOSRotation;->OUT:Ljava/util/WeakHashMap;

    invoke-virtual {v0, p0}, Ljava/util/WeakHashMap;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p0

    monitor-exit v2
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_2

    .line 56
    if-eqz v1, :cond_4

    invoke-virtual {v1}, Ljava/lang/Integer;->intValue()I

    move-result v0

    invoke-static {v0}, Loneos/camera/OneOSMp4;->matrix(I)[I

    move-result-object v0

    if-nez v0, :cond_0

    goto/16 :goto_4

    .line 57
    :cond_0
    if-nez p0, :cond_1

    .line 58
    const-string p0, "OneOSCamera"

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "video rotation "

    invoke-virtual {v0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v0

    const-string v1, ": the output is not known, not written"

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {p0, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    .line 59
    return-void

    .line 63
    :cond_1
    :try_start_2
    instance-of v0, p0, Ljava/lang/String;

    if-eqz v0, :cond_2

    .line 64
    new-instance v0, Ljava/io/RandomAccessFile;

    check-cast p0, Ljava/lang/String;

    const-string v2, "rw"

    invoke-direct {v0, p0, v2}, Ljava/io/RandomAccessFile;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    :try_end_2
    .catch Ljava/io/IOException; {:try_start_2 .. :try_end_2} :catch_0
    .catch Ljava/lang/RuntimeException; {:try_start_2 .. :try_end_2} :catch_0

    :try_start_3
    invoke-static {v0}, Loneos/camera/OneOSRotation;->file(Ljava/io/RandomAccessFile;)Loneos/camera/OneOSMp4$Io;

    move-result-object p0

    invoke-virtual {v1}, Ljava/lang/Integer;->intValue()I

    move-result v2

    invoke-static {p0, v2}, Loneos/camera/OneOSMp4;->setRotation(Loneos/camera/OneOSMp4$Io;I)Z

    move-result p0
    :try_end_3
    .catchall {:try_start_3 .. :try_end_3} :catchall_0

    :try_start_4
    invoke-virtual {v0}, Ljava/io/RandomAccessFile;->close()V
    :try_end_4
    .catch Ljava/io/IOException; {:try_start_4 .. :try_end_4} :catch_0
    .catch Ljava/lang/RuntimeException; {:try_start_4 .. :try_end_4} :catch_0

    goto :goto_1

    :catchall_0
    move-exception p0

    :try_start_5
    invoke-virtual {v0}, Ljava/io/RandomAccessFile;->close()V
    :try_end_5
    .catchall {:try_start_5 .. :try_end_5} :catchall_1

    goto :goto_0

    :catchall_1
    move-exception v0

    :try_start_6
    invoke-virtual {p0, v0}, Ljava/lang/Throwable;->addSuppressed(Ljava/lang/Throwable;)V

    :goto_0
    throw p0

    .line 66
    :cond_2
    check-cast p0, Ljava/io/FileDescriptor;

    invoke-static {p0}, Loneos/camera/OneOSRotation;->fd(Ljava/io/FileDescriptor;)Loneos/camera/OneOSMp4$Io;

    move-result-object p0

    invoke-virtual {v1}, Ljava/lang/Integer;->intValue()I

    move-result v0

    invoke-static {p0, v0}, Loneos/camera/OneOSMp4;->setRotation(Loneos/camera/OneOSMp4$Io;I)Z

    move-result p0

    .line 68
    :goto_1
    const-string v0, "OneOSCamera"

    if-eqz p0, :cond_3

    const-string p0, " written into the video track"

    goto :goto_2

    :cond_3
    const-string p0, ": no video track header at the identity matrix, left alone"

    :goto_2
    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "video rotation "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v0, p0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_6
    .catch Ljava/io/IOException; {:try_start_6 .. :try_end_6} :catch_0
    .catch Ljava/lang/RuntimeException; {:try_start_6 .. :try_end_6} :catch_0

    .line 71
    goto :goto_3

    .line 69
    :catch_0
    move-exception p0

    .line 70
    const-string v0, "OneOSCamera"

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "video rotation "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, " not written"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    .line 72
    :goto_3
    return-void

    .line 56
    :cond_4
    :goto_4
    return-void

    .line 55
    :catchall_2
    move-exception p0

    :try_start_7
    monitor-exit v2
    :try_end_7
    .catchall {:try_start_7 .. :try_end_7} :catchall_2

    throw p0

    .line 54
    :catchall_3
    move-exception p0

    :try_start_8
    monitor-exit v0
    :try_end_8
    .catchall {:try_start_8 .. :try_end_8} :catchall_3

    throw p0
.end method
