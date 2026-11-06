.class public final Loneos/camera/OneOSMp4;
.super Ljava/lang/Object;
.source "OneOSMp4.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Loneos/camera/OneOSMp4$Io;
    }
.end annotation


# static fields
.field private static final HDLR:I = 0x68646c72

.field private static final IDENTITY:[I

.field private static final MDIA:I = 0x6d646961

.field private static final MOOV:I = 0x6d6f6f76

.field private static final TKHD:I = 0x746b6864

.field private static final TRAK:I = 0x7472616b

.field private static final VIDE:I = 0x76696465


# direct methods
.method static constructor <clinit>()V
    .locals 1

    .line 20
    const/16 v0, 0x9

    new-array v0, v0, [I

    fill-array-data v0, :array_0

    sput-object v0, Loneos/camera/OneOSMp4;->IDENTITY:[I

    return-void

    :array_0
    .array-data 4
        0x10000
        0x0
        0x0
        0x0
        0x10000
        0x0
        0x0
        0x0
        0x40000000    # 2.0f
    .end array-data
.end method

.method private constructor <init>()V
    .locals 0

    .line 22
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method static box(Loneos/camera/OneOSMp4$Io;JJ)[J
    .locals 14
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 51
    move-wide v0, p1

    const/16 v2, 0x8

    new-array v3, v2, [B

    .line 52
    invoke-interface {p0, v0, v1, v3, v2}, Loneos/camera/OneOSMp4$Io;->read(J[BI)I

    move-result v4

    const/4 v5, 0x0

    if-ge v4, v2, :cond_0

    return-object v5

    .line 53
    :cond_0
    const/4 v4, 0x0

    invoke-static {v3, v4}, Loneos/camera/OneOSMp4;->u32([BI)J

    move-result-wide v6

    .line 54
    const/4 v8, 0x4

    invoke-static {v3, v8}, Loneos/camera/OneOSMp4;->u32([BI)J

    move-result-wide v9

    .line 55
    nop

    .line 56
    const-wide/16 v11, 0x1

    cmp-long v11, v6, v11

    const-wide/16 v12, 0x8

    if-nez v11, :cond_2

    .line 57
    add-long v6, v0, v12

    invoke-interface {p0, v6, v7, v3, v2}, Loneos/camera/OneOSMp4$Io;->read(J[BI)I

    move-result p0

    if-ge p0, v2, :cond_1

    return-object v5

    .line 58
    :cond_1
    invoke-static {v3, v4}, Loneos/camera/OneOSMp4;->u32([BI)J

    move-result-wide v6

    const/16 p0, 0x20

    shl-long/2addr v6, p0

    invoke-static {v3, v8}, Loneos/camera/OneOSMp4;->u32([BI)J

    move-result-wide v2

    or-long/2addr v6, v2

    .line 59
    const-wide/16 v12, 0x10

    goto :goto_0

    .line 60
    :cond_2
    const-wide/16 v2, 0x0

    cmp-long p0, v6, v2

    if-nez p0, :cond_3

    .line 61
    sub-long v6, p3, v0

    .line 63
    :cond_3
    :goto_0
    cmp-long p0, v6, v12

    if-ltz p0, :cond_5

    add-long v2, v0, v6

    cmp-long p0, v2, p3

    if-lez p0, :cond_4

    goto :goto_1

    .line 64
    :cond_4
    add-long v5, v0, v12

    new-array p0, v8, [J

    aput-wide v0, p0, v4

    const/4 v0, 0x1

    aput-wide v5, p0, v0

    const/4 v0, 0x2

    aput-wide v2, p0, v0

    const/4 v0, 0x3

    aput-wide v9, p0, v0

    return-object p0

    .line 63
    :cond_5
    :goto_1
    return-object v5
.end method

.method static child(Loneos/camera/OneOSMp4$Io;JJI)[J
    .locals 4
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 68
    nop

    :goto_0
    const-wide/16 v0, 0x8

    add-long/2addr v0, p1

    cmp-long v0, v0, p3

    const/4 v1, 0x0

    if-gtz v0, :cond_2

    .line 69
    invoke-static {p0, p1, p2, p3, p4}, Loneos/camera/OneOSMp4;->box(Loneos/camera/OneOSMp4$Io;JJ)[J

    move-result-object p1

    .line 70
    if-nez p1, :cond_0

    return-object v1

    .line 71
    :cond_0
    const/4 p2, 0x3

    aget-wide v0, p1, p2

    int-to-long v2, p5

    cmp-long p2, v0, v2

    if-nez p2, :cond_1

    return-object p1

    .line 72
    :cond_1
    const/4 p2, 0x2

    aget-wide p1, p1, p2

    .line 73
    goto :goto_0

    .line 74
    :cond_2
    return-object v1
.end method

.method static isVideo(Loneos/camera/OneOSMp4$Io;[J)Z
    .locals 8
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 78
    const/4 v0, 0x1

    aget-wide v2, p1, v0

    const/4 v7, 0x2

    aget-wide v4, p1, v7

    const v6, 0x6d646961

    move-object v1, p0

    invoke-static/range {v1 .. v6}, Loneos/camera/OneOSMp4;->child(Loneos/camera/OneOSMp4$Io;JJI)[J

    move-result-object p0

    .line 79
    if-nez p0, :cond_0

    const/4 p0, 0x0

    goto :goto_0

    :cond_0
    aget-wide v2, p0, v0

    aget-wide v4, p0, v7

    const v6, 0x68646c72    # 4.3148E24f

    invoke-static/range {v1 .. v6}, Loneos/camera/OneOSMp4;->child(Loneos/camera/OneOSMp4$Io;JJI)[J

    move-result-object p0

    .line 80
    :goto_0
    const/4 p1, 0x0

    if-eqz p0, :cond_3

    aget-wide v2, p0, v0

    const-wide/16 v4, 0xc

    add-long/2addr v2, v4

    aget-wide v4, p0, v7

    cmp-long v2, v2, v4

    if-lez v2, :cond_1

    goto :goto_2

    .line 81
    :cond_1
    const/4 v2, 0x4

    new-array v3, v2, [B

    .line 82
    aget-wide v4, p0, v0

    const-wide/16 v6, 0x8

    add-long/2addr v4, v6

    invoke-interface {v1, v4, v5, v3, v2}, Loneos/camera/OneOSMp4$Io;->read(J[BI)I

    move-result p0

    if-ne p0, v2, :cond_2

    invoke-static {v3, p1}, Loneos/camera/OneOSMp4;->u32([BI)J

    move-result-wide v1

    const-wide/32 v3, 0x76696465

    cmp-long p0, v1, v3

    if-nez p0, :cond_2

    goto :goto_1

    :cond_2
    move v0, p1

    :goto_1
    return v0

    .line 80
    :cond_3
    :goto_2
    return p1
.end method

.method static matrix(I)[I
    .locals 1

    .line 41
    rem-int/lit16 p0, p0, 0x168

    add-int/lit16 p0, p0, 0x168

    rem-int/lit16 p0, p0, 0x168

    const/16 v0, 0x9

    sparse-switch p0, :sswitch_data_0

    .line 45
    const/4 p0, 0x0

    return-object p0

    .line 44
    :sswitch_0
    new-array p0, v0, [I

    fill-array-data p0, :array_0

    return-object p0

    .line 43
    :sswitch_1
    new-array p0, v0, [I

    fill-array-data p0, :array_1

    return-object p0

    .line 42
    :sswitch_2
    new-array p0, v0, [I

    fill-array-data p0, :array_2

    return-object p0

    nop

    :sswitch_data_0
    .sparse-switch
        0x5a -> :sswitch_2
        0xb4 -> :sswitch_1
        0x10e -> :sswitch_0
    .end sparse-switch

    :array_0
    .array-data 4
        0x0
        -0x10000
        0x0
        0x10000
        0x0
        0x0
        0x0
        0x0
        0x40000000    # 2.0f
    .end array-data

    :array_1
    .array-data 4
        -0x10000
        0x0
        0x0
        0x0
        -0x10000
        0x0
        0x0
        0x0
        0x40000000    # 2.0f
    .end array-data

    :array_2
    .array-data 4
        0x0
        0x10000
        0x0
        -0x10000
        0x0
        0x0
        0x0
        0x0
        0x40000000    # 2.0f
    .end array-data
.end method

.method public static setRotation(Loneos/camera/OneOSMp4$Io;I)Z
    .locals 9
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 26
    invoke-static {p1}, Loneos/camera/OneOSMp4;->matrix(I)[I

    move-result-object p1

    .line 27
    const/4 v0, 0x0

    if-nez p1, :cond_0

    return v0

    .line 28
    :cond_0
    invoke-interface {p0}, Loneos/camera/OneOSMp4$Io;->size()J

    move-result-wide v4

    const v6, 0x6d6f6f76

    const-wide/16 v2, 0x0

    move-object v1, p0

    invoke-static/range {v1 .. v6}, Loneos/camera/OneOSMp4;->child(Loneos/camera/OneOSMp4$Io;JJI)[J

    move-result-object p0

    .line 29
    if-nez p0, :cond_1

    return v0

    .line 30
    :cond_1
    nop

    .line 31
    const/4 v2, 0x1

    aget-wide v2, p0, v2

    :goto_0
    const-wide/16 v4, 0x8

    add-long/2addr v4, v2

    const/4 v6, 0x2

    aget-wide v7, p0, v6

    cmp-long v4, v4, v7

    if-gtz v4, :cond_4

    .line 32
    aget-wide v4, p0, v6

    invoke-static {v1, v2, v3, v4, v5}, Loneos/camera/OneOSMp4;->box(Loneos/camera/OneOSMp4$Io;JJ)[J

    move-result-object v2

    .line 33
    if-nez v2, :cond_2

    goto :goto_1

    .line 34
    :cond_2
    const/4 v3, 0x3

    aget-wide v3, v2, v3

    const-wide/32 v7, 0x7472616b

    cmp-long v3, v3, v7

    if-nez v3, :cond_3

    invoke-static {v1, v2}, Loneos/camera/OneOSMp4;->isVideo(Loneos/camera/OneOSMp4$Io;[J)Z

    move-result v3

    if-eqz v3, :cond_3

    invoke-static {v1, v2, p1}, Loneos/camera/OneOSMp4;->write(Loneos/camera/OneOSMp4$Io;[J[I)Z

    move-result v3

    or-int/2addr v0, v3

    .line 35
    :cond_3
    aget-wide v2, v2, v6

    .line 36
    goto :goto_0

    .line 37
    :cond_4
    :goto_1
    return v0
.end method

.method private static u32([BI)J
    .locals 7

    .line 107
    aget-byte v0, p0, p1

    int-to-long v0, v0

    const-wide/16 v2, 0xff

    and-long/2addr v0, v2

    const/16 v4, 0x18

    shl-long/2addr v0, v4

    add-int/lit8 v4, p1, 0x1

    aget-byte v4, p0, v4

    int-to-long v4, v4

    and-long/2addr v4, v2

    const/16 v6, 0x10

    shl-long/2addr v4, v6

    or-long/2addr v0, v4

    add-int/lit8 v4, p1, 0x2

    aget-byte v4, p0, v4

    int-to-long v4, v4

    and-long/2addr v4, v2

    const/16 v6, 0x8

    shl-long/2addr v4, v6

    or-long/2addr v0, v4

    add-int/lit8 p1, p1, 0x3

    aget-byte p0, p0, p1

    int-to-long p0, p0

    and-long/2addr p0, v2

    or-long/2addr p0, v0

    return-wide p0
.end method

.method static write(Loneos/camera/OneOSMp4$Io;[J[I)Z
    .locals 12
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 86
    const/4 v0, 0x1

    aget-wide v2, p1, v0

    const/4 v7, 0x2

    aget-wide v4, p1, v7

    const v6, 0x746b6864

    move-object v1, p0

    invoke-static/range {v1 .. v6}, Loneos/camera/OneOSMp4;->child(Loneos/camera/OneOSMp4$Io;JJI)[J

    move-result-object p0

    .line 87
    const/4 p1, 0x0

    if-nez p0, :cond_0

    return p1

    .line 88
    :cond_0
    new-array v2, v0, [B

    .line 89
    aget-wide v3, p0, v0

    invoke-interface {v1, v3, v4, v2, v0}, Loneos/camera/OneOSMp4$Io;->read(J[BI)I

    move-result v3

    if-ge v3, v0, :cond_1

    return p1

    .line 90
    :cond_1
    aget-wide v3, p0, v0

    aget-byte v2, v2, p1

    const/16 v5, 0x18

    const/16 v6, 0x24

    if-ne v2, v0, :cond_2

    move v2, v6

    goto :goto_0

    :cond_2
    move v2, v5

    :goto_0
    int-to-long v8, v2

    add-long/2addr v3, v8

    const-wide/16 v8, 0x10

    add-long/2addr v3, v8

    .line 91
    const-wide/16 v8, 0x24

    add-long/2addr v8, v3

    aget-wide v10, p0, v7

    cmp-long p0, v8, v10

    if-lez p0, :cond_3

    return p1

    .line 92
    :cond_3
    new-array p0, v6, [B

    .line 93
    invoke-interface {v1, v3, v4, p0, v6}, Loneos/camera/OneOSMp4$Io;->read(J[BI)I

    move-result v2

    if-ge v2, v6, :cond_4

    return p1

    .line 94
    :cond_4
    move v2, p1

    :goto_1
    const/16 v7, 0x9

    if-ge v2, v7, :cond_6

    mul-int/lit8 v7, v2, 0x4

    invoke-static {p0, v7}, Loneos/camera/OneOSMp4;->u32([BI)J

    move-result-wide v7

    long-to-int v7, v7

    sget-object v8, Loneos/camera/OneOSMp4;->IDENTITY:[I

    aget v8, v8, v2

    if-eq v7, v8, :cond_5

    return p1

    :cond_5
    add-int/lit8 v2, v2, 0x1

    goto :goto_1

    .line 95
    :cond_6
    new-array p0, v6, [B

    .line 96
    nop

    :goto_2
    if-ge p1, v7, :cond_7

    .line 97
    mul-int/lit8 v2, p1, 0x4

    aget v6, p2, p1

    ushr-int/2addr v6, v5

    int-to-byte v6, v6

    aput-byte v6, p0, v2

    .line 98
    add-int/lit8 v6, v2, 0x1

    aget v8, p2, p1

    ushr-int/lit8 v8, v8, 0x10

    int-to-byte v8, v8

    aput-byte v8, p0, v6

    .line 99
    add-int/lit8 v6, v2, 0x2

    aget v8, p2, p1

    ushr-int/lit8 v8, v8, 0x8

    int-to-byte v8, v8

    aput-byte v8, p0, v6

    .line 100
    add-int/lit8 v2, v2, 0x3

    aget v6, p2, p1

    int-to-byte v6, v6

    aput-byte v6, p0, v2

    .line 96
    add-int/lit8 p1, p1, 0x1

    goto :goto_2

    .line 102
    :cond_7
    invoke-interface {v1, v3, v4, p0}, Loneos/camera/OneOSMp4$Io;->write(J[B)V

    .line 103
    return v0
.end method
