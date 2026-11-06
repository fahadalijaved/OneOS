.class Loneos/sysui/OneOSDt2s$1;
.super Landroid/content/BroadcastReceiver;
.source "OneOSDt2s.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Loneos/sysui/OneOSDt2s;->register(Landroid/view/View;)V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic val$c:Landroid/content/Context;


# direct methods
.method constructor <init>(Landroid/content/Context;)V
    .locals 0

    .line 41
    iput-object p1, p0, Loneos/sysui/OneOSDt2s$1;->val$c:Landroid/content/Context;

    invoke-direct {p0}, Landroid/content/BroadcastReceiver;-><init>()V

    return-void
.end method


# virtual methods
.method public onReceive(Landroid/content/Context;Landroid/content/Intent;)V
    .locals 1

    .line 44
    invoke-virtual {p0}, Loneos/sysui/OneOSDt2s$1;->getSentFromPackage()Ljava/lang/String;

    move-result-object p1

    .line 45
    const-string p2, "com.google.android.apps.nexuslauncher"

    invoke-virtual {p2, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p2

    if-nez p2, :cond_0

    .line 46
    new-instance p2, Ljava/lang/StringBuilder;

    invoke-direct {p2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v0, "double tap to sleep asked by "

    invoke-virtual {p2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p2

    invoke-virtual {p2, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string p2, ": ignored"

    invoke-virtual {p1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    const-string p2, "OneOSDt2s"

    invoke-static {p2, p1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    .line 47
    return-void

    .line 49
    :cond_0
    iget-object p1, p0, Loneos/sysui/OneOSDt2s$1;->val$c:Landroid/content/Context;

    const-string p2, "home screen"

    invoke-static {p1, p2}, Loneos/sysui/OneOSDt2s;->sleep(Landroid/content/Context;Ljava/lang/String;)V

    .line 50
    return-void
.end method
