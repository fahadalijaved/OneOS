.class public interface abstract Loneos/camera/OneOSMp4$Io;
.super Ljava/lang/Object;
.source "OneOSMp4.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Loneos/camera/OneOSMp4;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x609
    name = "Io"
.end annotation


# virtual methods
.method public abstract read(J[BI)I
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation
.end method

.method public abstract size()J
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation
.end method

.method public abstract write(J[B)V
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Ljava/io/IOException;
        }
    .end annotation
.end method
