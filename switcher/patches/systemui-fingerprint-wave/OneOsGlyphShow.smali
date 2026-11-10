.class public final Lcom/oplus/systemui/biometrics/finger/udfps/OneOsGlyphShow;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;

.field public final mech:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

.method public constructor <init>(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OneOsGlyphShow;->mech:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    return-void
.end method

.method public final run()V
    .locals 3

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OneOsGlyphShow;->mech:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    if-eqz v0, :end

    const-string v1, "OnScreenFingerprintUiMech"

    const-string v2, "OneOS glyph delayed"

    invoke-static {v1, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconTemporarily(Ljava/lang/String;)V

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v1

    if-eqz v1, :end

    const/4 v2, 0x0

    invoke-virtual {v1, v2}, Landroid/view/View;->setVisibility(I)V

    const/high16 v2, 0x3f800000    # 1.0f

    invoke-virtual {v1, v2}, Landroid/view/View;->setAlpha(F)V

    const-string v1, "OnScreenFingerprintUiMech"

    const-string v2, "OneOS glyph forced"

    invoke-static {v1, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    :end
    return-void
.end method
