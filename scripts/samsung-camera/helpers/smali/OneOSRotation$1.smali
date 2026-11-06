.class Loneos/camera/OneOSRotation$1;
.super Ljava/lang/Object;
.source "OneOSRotation.java"

# interfaces
.implements Loneos/camera/OneOSMp4$Io;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Loneos/camera/OneOSRotation;->file(Ljava/io/RandomAccessFile;)Loneos/camera/OneOSMp4$Io;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic val$f:Ljava/io/RandomAccessFile;


# direct methods
.method constructor <init>(Ljava/io/RandomAccessFile;)V
    .locals 0
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "()V"
        }
    .end annotation

    .line 75
    iput-object p1, p0, Loneos/camera/OneOSRotation$1;->val$f:Ljava/io/RandomAccessFile;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public read(J[BI)I
    .locals 1
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 76
    iget-object v0, p0, Loneos/camera/OneOSRotation$1;->val$f:Ljava/io/RandomAccessFile;

    invoke-virtual {v0, p1, p2}, Ljava/io/RandomAccessFile;->seek(J)V

    iget-object p1, p0, Loneos/camera/OneOSRotation$1;->val$f:Ljava/io/RandomAccessFile;

    const/4 p2, 0x0

    invoke-virtual {p1, p3, p2, p4}, Ljava/io/RandomAccessFile;->read([BII)I

    move-result p1

    return p1
.end method

.method public size()J
    .locals 2
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 78
    iget-object v0, p0, Loneos/camera/OneOSRotation$1;->val$f:Ljava/io/RandomAccessFile;

    invoke-virtual {v0}, Ljava/io/RandomAccessFile;->length()J

    move-result-wide v0

    return-wide v0
.end method

.method public write(J[B)V
    .locals 1
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation

    .line 77
    iget-object v0, p0, Loneos/camera/OneOSRotation$1;->val$f:Ljava/io/RandomAccessFile;

    invoke-virtual {v0, p1, p2}, Ljava/io/RandomAccessFile;->seek(J)V

    iget-object p1, p0, Loneos/camera/OneOSRotation$1;->val$f:Ljava/io/RandomAccessFile;

    invoke-virtual {p1, p3}, Ljava/io/RandomAccessFile;->write([B)V

    return-void
.end method
