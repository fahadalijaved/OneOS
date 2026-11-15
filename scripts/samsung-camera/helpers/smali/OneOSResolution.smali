.class public final Loneos/camera/OneOSResolution;
.super Ljava/lang/Object;
.source "OneOSResolution.java"

# interfaces
.implements Ljava/util/function/BiFunction;


# annotations
.annotation system Ldalvik/annotation/Signature;
    value = {
        "Ljava/lang/Object;",
        "Ljava/util/function/BiFunction<",
        "Ljava/lang/Object;",
        "Ljava/lang/Object;",
        "Ljava/lang/Object;",
        ">;"
    }
.end annotation


# static fields
.field static CATCHERS:Ljava/lang/String; = null

.field private static final DEFAULT:Ljava/lang/String; = "RESOLUTION_4000X3000"

.field public static final LOOKUP:Ljava/util/function/BiFunction;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/function/BiFunction<",
            "Ljava/lang/Object;",
            "Ljava/lang/Object;",
            "Ljava/lang/Object;",
            ">;"
        }
    .end annotation
.end field

.field private static final PREFIX:Ljava/lang/String; = "RESOLUTION_"

.field private static said:Ljava/lang/String;


# direct methods
.method static constructor <clinit>()V
    .locals 1

    .line 27
    new-instance v0, Loneos/camera/OneOSResolution;

    invoke-direct {v0}, Loneos/camera/OneOSResolution;-><init>()V

    sput-object v0, Loneos/camera/OneOSResolution;->LOOKUP:Ljava/util/function/BiFunction;

    .line 32
    const-string v0, " @oneos-callers-that-catch@ "

    sput-object v0, Loneos/camera/OneOSResolution;->CATCHERS:Ljava/lang/String;

    .line 35
    const-string v0, ""

    sput-object v0, Loneos/camera/OneOSResolution;->said:Ljava/lang/String;

    return-void
.end method

.method private constructor <init>()V
    .locals 0

    .line 37
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method private static caller(Ljava/lang/String;)Ljava/lang/String;
    .locals 4

    .line 66
    new-instance v0, Ljava/lang/Throwable;

    invoke-direct {v0}, Ljava/lang/Throwable;-><init>()V

    invoke-virtual {v0}, Ljava/lang/Throwable;->getStackTrace()[Ljava/lang/StackTraceElement;

    move-result-object v0

    .line 67
    const-class v1, Loneos/camera/OneOSResolution;

    invoke-virtual {v1}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object v1

    .line 68
    const/4 v2, 0x0

    .line 69
    :goto_0
    array-length v3, v0

    if-ge v2, v3, :cond_0

    aget-object v3, v0, v2

    invoke-virtual {v3}, Ljava/lang/StackTraceElement;->getClassName()Ljava/lang/String;

    move-result-object v3

    invoke-virtual {v1, v3}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v3

    if-eqz v3, :cond_0

    add-int/lit8 v2, v2, 0x1

    goto :goto_0

    .line 70
    :cond_0
    add-int/lit8 v1, v2, 0x1

    array-length v3, v0

    if-ge v1, v3, :cond_2

    aget-object v2, v0, v2

    invoke-virtual {v2}, Ljava/lang/StackTraceElement;->getClassName()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {p0, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p0

    if-nez p0, :cond_1

    goto :goto_1

    .line 71
    :cond_1
    aget-object p0, v0, v1

    invoke-virtual {p0}, Ljava/lang/StackTraceElement;->getClassName()Ljava/lang/String;

    move-result-object p0

    aget-object v0, v0, v1

    invoke-virtual {v0}, Ljava/lang/StackTraceElement;->getMethodName()Ljava/lang/String;

    move-result-object v0

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    const-string v1, "."

    invoke-virtual {p0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    return-object p0

    .line 70
    :cond_2
    :goto_1
    const/4 p0, 0x0

    return-object p0
.end method

.method static nearest(Ljava/lang/String;[Ljava/lang/Enum;)Ljava/lang/Enum;
    .locals 18
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Ljava/lang/String;",
            "[",
            "Ljava/lang/Enum<",
            "*>;)",
            "Ljava/lang/Enum<",
            "*>;"
        }
    .end annotation

    .line 82
    move-object/from16 v0, p1

    const/4 v1, 0x0

    move-object/from16 v2, p0

    invoke-static {v2, v1}, Loneos/camera/OneOSResolution;->size(Ljava/lang/String;I)[J

    move-result-object v2

    .line 83
    const/4 v3, 0x0

    if-nez v2, :cond_0

    return-object v3

    .line 84
    :cond_0
    nop

    .line 85
    nop

    .line 86
    nop

    .line 87
    array-length v4, v0

    const-wide/16 v5, 0x0

    move v7, v1

    move v8, v7

    :goto_0
    if-ge v7, v4, :cond_7

    aget-object v9, v0, v7

    .line 88
    if-eqz v9, :cond_6

    invoke-virtual {v9}, Ljava/lang/Enum;->name()Ljava/lang/String;

    move-result-object v10

    const-string v11, "RESOLUTION_"

    invoke-virtual {v10, v11}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z

    move-result v10

    if-nez v10, :cond_1

    goto :goto_2

    .line 89
    :cond_1
    invoke-virtual {v9}, Ljava/lang/Enum;->name()Ljava/lang/String;

    move-result-object v10

    invoke-virtual {v11}, Ljava/lang/String;->length()I

    move-result v11

    invoke-static {v10, v11}, Loneos/camera/OneOSResolution;->size(Ljava/lang/String;I)[J

    move-result-object v10

    .line 90
    if-nez v10, :cond_2

    goto :goto_2

    .line 91
    :cond_2
    aget-wide v11, v10, v1

    const/4 v13, 0x1

    aget-wide v14, v2, v13

    mul-long/2addr v11, v14

    aget-wide v14, v10, v13

    aget-wide v16, v2, v1

    mul-long v14, v14, v16

    sub-long/2addr v11, v14

    invoke-static {v11, v12}, Ljava/lang/Math;->abs(J)J

    move-result-wide v11

    const-wide/16 v14, 0x64

    mul-long/2addr v11, v14

    aget-wide v14, v10, v13

    aget-wide v16, v2, v1

    mul-long v14, v14, v16

    cmp-long v11, v11, v14

    if-gtz v11, :cond_3

    move v11, v13

    goto :goto_1

    :cond_3
    move v11, v1

    .line 92
    :goto_1
    aget-wide v14, v10, v1

    aget-wide v16, v10, v13

    mul-long v14, v14, v16

    aget-wide v16, v2, v1

    aget-wide v12, v2, v13

    mul-long v16, v16, v12

    sub-long v14, v14, v16

    invoke-static {v14, v15}, Ljava/lang/Math;->abs(J)J

    move-result-wide v12

    .line 93
    if-eqz v3, :cond_5

    if-eqz v11, :cond_4

    if-eqz v8, :cond_5

    :cond_4
    if-ne v11, v8, :cond_6

    cmp-long v10, v12, v5

    if-gez v10, :cond_6

    .line 94
    :cond_5
    nop

    .line 95
    nop

    .line 96
    move-object v3, v9

    move v8, v11

    move-wide v5, v12

    .line 87
    :cond_6
    :goto_2
    add-int/lit8 v7, v7, 0x1

    goto :goto_0

    .line 99
    :cond_7
    return-object v3
.end method

.method private static declared-synchronized say(Ljava/lang/String;Ljava/lang/String;)V
    .locals 3

    const-class v0, Loneos/camera/OneOSResolution;

    monitor-enter v0

    .line 138
    :try_start_0
    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "OneOSCamera: no entry for "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    const-string v1, " in this camera\'s size table: "

    invoke-virtual {p0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    .line 139
    sget-object p1, Loneos/camera/OneOSResolution;->said:Ljava/lang/String;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "\n"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, "\n"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {p1, v1}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result p1

    if-nez p1, :cond_1

    sget-object p1, Loneos/camera/OneOSResolution;->said:Ljava/lang/String;

    invoke-virtual {p1}, Ljava/lang/String;->length()I

    move-result p1

    const/16 v1, 0xfa0

    if-le p1, v1, :cond_0

    goto :goto_0

    .line 140
    :cond_0
    sget-object p1, Loneos/camera/OneOSResolution;->said:Ljava/lang/String;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v1, "\n"

    invoke-virtual {p1, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v1, "\n"

    invoke-virtual {p1, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    sput-object p1, Loneos/camera/OneOSResolution;->said:Ljava/lang/String;

    .line 141
    sget-object p1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    invoke-virtual {p1, p0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    .line 142
    monitor-exit v0

    return-void

    .line 139
    :cond_1
    :goto_0
    monitor-exit v0

    return-void

    .line 137
    :catchall_0
    move-exception p0

    :try_start_1
    monitor-exit v0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    throw p0
.end method

.method private static size(Ljava/lang/String;I)[J
    .locals 7

    .line 116
    const/4 v0, 0x0

    if-nez p0, :cond_0

    return-object v0

    .line 117
    :cond_0
    const/16 v1, 0x5f

    invoke-virtual {p0, v1, p1}, Ljava/lang/String;->indexOf(II)I

    move-result v1

    .line 118
    if-gez v1, :cond_1

    invoke-virtual {p0}, Ljava/lang/String;->length()I

    move-result v1

    .line 119
    :cond_1
    nop

    .line 120
    const/4 v2, -0x1

    move v3, p1

    :goto_0
    if-ge v3, v1, :cond_7

    .line 121
    invoke-virtual {p0, v3}, Ljava/lang/String;->charAt(I)C

    move-result v4

    .line 122
    const/16 v5, 0x78

    if-eq v4, v5, :cond_4

    const/16 v5, 0x58

    if-ne v4, v5, :cond_2

    goto :goto_1

    .line 125
    :cond_2
    const/16 v5, 0x30

    if-lt v4, v5, :cond_3

    const/16 v5, 0x39

    if-le v4, v5, :cond_6

    .line 126
    :cond_3
    return-object v0

    .line 123
    :cond_4
    :goto_1
    if-ltz v2, :cond_5

    return-object v0

    .line 124
    :cond_5
    move v2, v3

    .line 120
    :cond_6
    add-int/lit8 v3, v3, 0x1

    goto :goto_0

    .line 130
    :cond_7
    if-le v2, p1, :cond_a

    add-int/lit8 v3, v1, -0x1

    if-ge v2, v3, :cond_a

    sub-int v4, v2, p1

    const/4 v5, 0x5

    if-gt v4, v5, :cond_a

    sub-int/2addr v3, v2

    if-le v3, v5, :cond_8

    goto :goto_2

    .line 131
    :cond_8
    invoke-virtual {p0, p1, v2}, Ljava/lang/String;->substring(II)Ljava/lang/String;

    move-result-object p1

    invoke-static {p1}, Ljava/lang/Long;->parseLong(Ljava/lang/String;)J

    move-result-wide v3

    .line 132
    const/4 p1, 0x1

    add-int/2addr v2, p1

    invoke-virtual {p0, v2, v1}, Ljava/lang/String;->substring(II)Ljava/lang/String;

    move-result-object p0

    invoke-static {p0}, Ljava/lang/Long;->parseLong(Ljava/lang/String;)J

    move-result-wide v1

    .line 133
    const-wide/16 v5, 0x0

    cmp-long p0, v3, v5

    if-lez p0, :cond_9

    cmp-long p0, v1, v5

    if-lez p0, :cond_9

    const/4 p0, 0x2

    new-array v0, p0, [J

    const/4 p0, 0x0

    aput-wide v3, v0, p0

    aput-wide v1, v0, p1

    :cond_9
    return-object v0

    .line 130
    :cond_a
    :goto_2
    return-object v0
.end method

.method static unknownId([Ljava/lang/Enum;)Ljava/lang/Enum;
    .locals 5
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "([",
            "Ljava/lang/Enum<",
            "*>;)",
            "Ljava/lang/Enum<",
            "*>;"
        }
    .end annotation

    .line 108
    array-length v0, p0

    const/4 v1, 0x0

    :goto_0
    if-ge v1, v0, :cond_1

    aget-object v2, p0, v1

    .line 109
    if-eqz v2, :cond_0

    const-string v3, "RESOLUTION_4000X3000"

    invoke-virtual {v2}, Ljava/lang/Enum;->name()Ljava/lang/String;

    move-result-object v4

    invoke-virtual {v3, v4}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v3

    if-eqz v3, :cond_0

    return-object v2

    .line 108
    :cond_0
    add-int/lit8 v1, v1, 0x1

    goto :goto_0

    .line 111
    :cond_1
    const/4 p0, 0x0

    return-object p0
.end method


# virtual methods
.method public apply(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
    .locals 7

    .line 42
    const-string v0, " "

    const/4 v1, 0x0

    :try_start_0
    instance-of v2, p2, [Ljava/lang/Enum;

    if-nez v2, :cond_0

    return-object v1

    .line 43
    :cond_0
    instance-of v2, p1, Ljava/lang/Integer;

    .line 44
    if-nez v2, :cond_1

    instance-of v3, p1, Ljava/lang/String;

    if-nez v3, :cond_1

    return-object v1

    .line 45
    :cond_1
    if-eqz v2, :cond_2

    const-string v3, "id "

    goto :goto_0

    :cond_2
    const-string v3, "size "

    :goto_0
    invoke-static {p1}, Ljava/lang/String;->valueOf(Ljava/lang/Object;)Ljava/lang/String;

    move-result-object v4

    new-instance v5, Ljava/lang/StringBuilder;

    invoke-direct {v5}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v5, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    .line 46
    invoke-virtual {p2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v4

    invoke-virtual {v4}, Ljava/lang/Class;->getComponentType()Ljava/lang/Class;

    move-result-object v4

    invoke-virtual {v4}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object v4

    invoke-static {v4}, Loneos/camera/OneOSResolution;->caller(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v4

    .line 47
    if-nez v4, :cond_3

    return-object v1

    .line 48
    :cond_3
    sget-object v5, Loneos/camera/OneOSResolution;->CATCHERS:Ljava/lang/String;

    new-instance v6, Ljava/lang/StringBuilder;

    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v6, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v6, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v6

    invoke-virtual {v6, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v5, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v0

    if-eqz v0, :cond_4

    .line 49
    new-instance p1, Ljava/lang/StringBuilder;

    invoke-direct {p1}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {p1, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string p2, " deals with that itself"

    invoke-virtual {p1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {v3, p1}, Loneos/camera/OneOSResolution;->say(Ljava/lang/String;Ljava/lang/String;)V

    .line 50
    return-object v1

    .line 52
    :cond_4
    if-eqz v2, :cond_5

    check-cast p2, [Ljava/lang/Enum;

    invoke-static {p2}, Loneos/camera/OneOSResolution;->unknownId([Ljava/lang/Enum;)Ljava/lang/Enum;

    move-result-object p1

    goto :goto_1

    :cond_5
    check-cast p1, Ljava/lang/String;

    check-cast p2, [Ljava/lang/Enum;

    invoke-static {p1, p2}, Loneos/camera/OneOSResolution;->nearest(Ljava/lang/String;[Ljava/lang/Enum;)Ljava/lang/Enum;

    move-result-object p1

    .line 53
    :goto_1
    if-nez p1, :cond_6

    const-string p2, "nothing to offer, the camera\'s own error follows"

    goto :goto_2

    :cond_6
    invoke-virtual {p1}, Ljava/lang/Enum;->name()Ljava/lang/String;

    move-result-object p2

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "using "

    invoke-virtual {v0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p2

    invoke-virtual {p2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p2

    :goto_2
    invoke-static {v3, p2}, Loneos/camera/OneOSResolution;->say(Ljava/lang/String;Ljava/lang/String;)V
    :try_end_0
    .catch Ljava/lang/RuntimeException; {:try_start_0 .. :try_end_0} :catch_0

    .line 54
    return-object p1

    .line 55
    :catch_0
    move-exception p1

    .line 56
    return-object v1
.end method
