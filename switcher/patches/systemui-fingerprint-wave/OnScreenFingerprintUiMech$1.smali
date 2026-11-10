.class public final Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;
.super Ljava/lang/Object;
.source "go/retraceme 35a97f398b6cfa1a7421a322b9cfa3ff6567976d57b6389918337185ab04a49a"

# interfaces
.implements Ljava/lang/Runnable;


# instance fields
.field public final synthetic $r8$classId:I

.field public synthetic this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;


# direct methods
.method public synthetic constructor <init>(I)V
    .locals 0

    iput p1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->$r8$classId:I

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public final run()V
    .locals 13

    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->$r8$classId:I

    const/16 v1, 0x8

    const-class v2, Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;

    const-string v3, "OplusHYWaterAnimationDrawable"

    const/4 v4, 0x2

    const/4 v5, 0x0

    const/4 v6, 0x5

    const/4 v7, 0x0

    const/4 v8, 0x0

    const/4 v9, 0x1

    const-string v10, "OnScreenFingerprintUiMech"

    packed-switch v0, :pswitch_data_0

    const-string/jumbo v0, "stopPressedAnimation, mPressedAnimDrawableTmp"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawableTmp$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_0

    invoke-virtual {v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->stop()V

    :cond_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$setPressedAnimDrawableTmp$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_1

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object p0

    invoke-virtual {v0, p0}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_1
    return-void

    :pswitch_0
    const-string/jumbo v0, "stopPressedAnimation"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->cancelFpPendingHideAnimator()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_2

    invoke-virtual {v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->stop()V

    :cond_2
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_3

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object p0

    invoke-virtual {v0, p0}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_3
    return-void

    :pswitch_1
    const-string/jumbo v0, "stopFadeOutAnimation"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v9, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object p0

    if-eqz p0, :cond_4

    invoke-virtual {p0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->stop()V

    :cond_4
    return-void

    :pswitch_2
    const-string/jumbo v0, "stopFadeInAnimation"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object p0

    if-eqz p0, :cond_5

    invoke-virtual {p0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->stop()V

    :cond_5
    return-void

    :pswitch_3
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iget-wide v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oneosWakeAt:J

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v1

    sub-long/2addr v1, v11

    const-wide/16 v11, 0x4b0

    cmp-long v1, v1, v11

    if-ltz v1, :oneos_pswitch3_glyph

    goto :oneos_pswitch3_go

    :oneos_pswitch3_glyph
    const/4 v1, 0x1

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->restoreIconDrawable(Z)V

    iget-object v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fpIcon:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    if-eqz v1, :oneos_glyph_novis

    const/4 v3, 0x0

    const-string v2, "startPressedAnimation"

    invoke-virtual {v1, v3, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->setVisibility(ILjava/lang/String;)V

    const/high16 v2, 0x3f800000    # 1.0f

    invoke-virtual {v1, v2}, Landroid/view/View;->setAlpha(F)V

    :oneos_glyph_novis
    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getOpticalUiUpdateHandler$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/os/Handler;

    move-result-object v1

    if-eqz v1, :oneos_glyph_nopost

    new-instance v2, Lcom/oplus/systemui/biometrics/finger/udfps/OneOsGlyphShow;

    invoke-direct {v2, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OneOsGlyphShow;-><init>(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    const-wide/16 v3, 0x12c

    invoke-virtual {v1, v2, v3, v4}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    const-string v1, "OnScreenFingerprintUiMech"

    const-string v2, "OneOS glyph post"

    invoke-static {v1, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    :oneos_glyph_nopost
    const-string v1, "OnScreenFingerprintUiMech"

    const-string v2, "OneOS glyph first"

    invoke-static {v1, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    return-void

    :oneos_pswitch3_go
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getOpticalUiUpdateHandler$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/os/Handler;

    move-result-object v0

    if-eqz v0, :cond_6

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getHideFingerprintIconRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/Runnable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_6
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    const-string/jumbo v1, "startPressedAnimation"

    if-eqz v0, :cond_7

    invoke-virtual {v0, v8, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->setVisibility(ILjava/lang/String;)V

    :cond_7
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_8

    invoke-virtual {v0, v8}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_8
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->checkHasPressedAnimation()Z

    move-result v0

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    if-nez v0, :cond_9

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_14

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v8, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_14

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object p0

    invoke-virtual {v0, p0}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    goto/16 :goto_1

    :cond_9
    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_14

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_14

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_a

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    if-ne v0, v9, :cond_a

    goto/16 :goto_1

    :cond_a
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    instance-of v0, v0, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    const/high16 v6, 0x40000000    # 2.0f

    const-string v7, "invalid parameter in calculateVFXParameter"

    const/high16 v11, 0x42c80000    # 100.0f

    if-eqz v0, :cond_e

    new-array v0, v4, [I

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v2

    if-eqz v2, :cond_b

    invoke-virtual {v2, v0}, Landroid/widget/ImageView;->getLocationOnScreen([I)V

    :cond_b
    const-string v2, " start WaterRippleAnimation"

    invoke-static {v10, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v2

    if-eqz v2, :cond_c

    invoke-virtual {v2}, Landroid/widget/ImageView;->getHeight()I

    move-result v2

    int-to-float v11, v2

    :cond_c
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v2

    check-cast v2, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;

    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    cmpg-float v3, v11, v5

    if-gtz v3, :cond_d

    const-string v0, "OplusWaterRippleAnimationDrawable"

    invoke-static {v0, v7}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->e(Ljava/lang/String;Ljava/lang/String;)V

    goto/16 :goto_0

    :cond_d
    iget-object v2, v2, Lcom/oplus/systemui/keyguard/view/OplusWaterRippleAnimationDrawable;->mCenter:[F

    aget v3, v0, v8

    int-to-float v3, v3

    div-float/2addr v11, v6

    add-float/2addr v3, v11

    aput v3, v2, v8

    aget v0, v0, v9

    int-to-float v0, v0

    add-float/2addr v0, v11

    aput v0, v2, v9

    goto/16 :goto_0

    :cond_e
    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    instance-of v0, v0, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;

    if-eqz v0, :cond_12

    new-array v0, v4, [I

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v2

    if-eqz v2, :cond_f

    invoke-virtual {v2, v0}, Landroid/widget/ImageView;->getLocationOnScreen([I)V

    :cond_f
    const-string v2, " start HY WaterRippleAnimation"

    invoke-static {v10, v2}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v2

    if-eqz v2, :cond_10

    invoke-virtual {v2}, Landroid/widget/ImageView;->getHeight()I

    move-result v2

    int-to-float v11, v2

    :cond_10
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v2

    check-cast v2, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;

    sget-object v4, Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper;->Companion:Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper$Companion;

    iget-object v10, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v10}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object v10

    invoke-virtual {v4, v10}, Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper;

    move-result-object v10

    invoke-virtual {v10}, Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper;->getBaseDisplayWidthSize()I

    move-result v10

    iget-object v12, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v12}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object v12

    invoke-virtual {v4, v12}, Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper;

    move-result-object v4

    invoke-virtual {v4}, Lcom/oplus/systemui/keyguard/helper/ScreenSizeHelper;->getBaseDisplayHeightSize()I

    move-result v4

    invoke-virtual {v2}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    cmpg-float v5, v11, v5

    if-gtz v5, :cond_11

    invoke-static {v3, v7}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->e(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, v2, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCenter:[F

    const/high16 v2, 0x3f000000    # 0.5f

    aput v2, v0, v8

    const v2, 0x3f666666    # 0.9f

    aput v2, v0, v9

    goto :goto_0

    :cond_11
    iget-object v5, v2, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCenter:[F

    aget v7, v0, v8

    int-to-float v7, v7

    div-float/2addr v11, v6

    add-float/2addr v7, v11

    int-to-float v6, v10

    div-float/2addr v7, v6

    aput v7, v5, v8

    aget v0, v0, v9

    int-to-float v0, v0

    add-float/2addr v0, v11

    int-to-float v4, v4

    div-float/2addr v0, v4

    aput v0, v5, v9

    new-instance v0, Ljava/lang/StringBuilder;

    const-string v4, "calculateVFXParameter ("

    invoke-direct {v0, v4}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    iget-object v4, v2, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCenter:[F

    aget v4, v4, v8

    invoke-virtual {v0, v4}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    const-string v4, ","

    invoke-virtual {v0, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    iget-object v2, v2, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCenter:[F

    aget v2, v2, v9

    invoke-virtual {v0, v2}, Ljava/lang/StringBuilder;->append(F)Ljava/lang/StringBuilder;

    const-string v2, ")"

    invoke-virtual {v0, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v3, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->d(Ljava/lang/String;Ljava/lang/String;)V

    :cond_12
    :goto_0
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v8, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_13

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_13
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object p0

    if-eqz p0, :cond_14

    invoke-virtual {p0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->start()V

    :cond_14
    :goto_1
    return-void

    :pswitch_4
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->cancelFpPendingHideAnimator()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iget-boolean v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    if-nez v1, :cond_15

    goto :goto_2

    :cond_15
    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_16

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Landroid/widget/ImageView;->getAlpha()F

    move-result v1

    new-array v2, v4, [F

    aput v1, v2, v8

    aput v5, v2, v9

    const-string v1, "alpha"

    invoke-static {v0, v1, v2}, Landroid/animation/ObjectAnimator;->ofFloat(Ljava/lang/Object;Ljava/lang/String;[F)Landroid/animation/ObjectAnimator;

    move-result-object v0

    new-instance v1, Landroid/animation/AnimatorSet;

    invoke-direct {v1}, Landroid/animation/AnimatorSet;-><init>()V

    new-array v2, v9, [Landroid/animation/Animator;

    aput-object v0, v2, v8

    invoke-virtual {v1, v2}, Landroid/animation/AnimatorSet;->playTogether([Landroid/animation/Animator;)V

    const-wide/16 v2, 0x96

    invoke-virtual {v1, v2, v3}, Landroid/animation/AnimatorSet;->setDuration(J)Landroid/animation/AnimatorSet;

    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$startFingerprintGradientsAnim$1$1$1;

    invoke-direct {v0}, Ljava/lang/Object;-><init>()V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$startFingerprintGradientsAnim$1$1$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {v1, v0}, Landroid/animation/AnimatorSet;->addListener(Landroid/animation/Animator$AnimatorListener;)V

    invoke-static {p0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$setFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Landroid/animation/AnimatorSet;)V

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/AnimatorSet;

    move-result-object p0

    if-eqz p0, :cond_16

    invoke-virtual {p0}, Landroid/animation/AnimatorSet;->start()V

    :cond_16
    :goto_2
    return-void

    :pswitch_5
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_18

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_17

    invoke-virtual {v0}, Landroid/graphics/drawable/AnimationDrawable;->isRunning()Z

    move-result v0

    if-ne v0, v9, :cond_17

    goto :goto_3

    :cond_17
    move v8, v9

    :cond_18
    :goto_3
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_1b

    if-eqz v8, :cond_1b

    const-string/jumbo v0, "startFadeOutAnimation"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->saveFpIconLog(Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    const-string/jumbo v0, "startFadeOutAnimation, setFadeOutAnimDrawable"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_19

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_19
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_1a

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimationDrawableListener$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    move-result-object v1

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setOnAnimationDrawableListener(Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;)V

    :cond_1a
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeOutAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object p0

    if-eqz p0, :cond_1b

    invoke-virtual {p0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->start()V

    :cond_1b
    return-void

    :pswitch_6
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getFadeInAnimState()Z

    move-result v0

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v1

    if-eqz v1, :cond_1c

    invoke-virtual {v1}, Landroid/widget/ImageView;->getDrawable()Landroid/graphics/drawable/Drawable;

    move-result-object v1

    goto :goto_4

    :cond_1c
    move-object v1, v7

    :goto_4
    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v2

    invoke-static {v1, v2}, Lkotlin/jvm/internal/Intrinsics;->areEqual(Ljava/lang/Object;Ljava/lang/Object;)Z

    move-result v1

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v2

    if-eqz v2, :cond_2d

    if-nez v0, :cond_1d

    if-eqz v1, :cond_1d

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getSwitchHelper$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    move-result-object v2

    if-eqz v2, :cond_2d

    iget-boolean v2, v2, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v2, v9, :cond_2d

    :cond_1d
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v8, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->fadeOutFlag:Z

    sget-object v0, Lcom/oplusos/systemui/common/feature/AodFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/AodFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/AodFeatureOption;->isSupportRamLessAod()Z

    move-result v0

    if-nez v0, :cond_29

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    if-eqz v0, :cond_29

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iget-boolean v1, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-nez v1, :cond_29

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_1e

    invoke-virtual {v0}, Landroid/widget/ImageView;->getDrawable()Landroid/graphics/drawable/Drawable;

    move-result-object v7

    :cond_1e
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object v0

    if-ne v7, v0, :cond_1f

    move v0, v9

    goto :goto_5

    :cond_1f
    move v0, v8

    :goto_5
    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object v1

    invoke-static {v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v1

    invoke-virtual {v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isPanoramicProcessType()Z

    move-result v1

    if-eqz v1, :cond_20

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object v1

    invoke-static {v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v1

    invoke-virtual {v1}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isNoneLocalHbmPanoramicTypeHasMask()Z

    move-result v1

    if-nez v1, :cond_20

    move v1, v9

    goto :goto_6

    :cond_20
    move v1, v8

    :goto_6
    if-eqz v0, :cond_23

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOnDreamingStart()Z

    move-result v0

    if-eqz v0, :cond_21

    if-eqz v1, :cond_23

    :cond_21
    const-string/jumbo v0, "unnecessary to start fade in animation"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->w(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_22

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_22
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v8, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    goto/16 :goto_8

    :cond_23
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOnDreamingStart()Z

    move-result v0

    const-string/jumbo v1, "startFadeInAnimation,mOnDreamingStart:"

    invoke-static {v1, v10, v0}, Lcom/android/keyguard/OplusLockIconView$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Z)V

    sget-object v0, Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr;->Companion:Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr$Companion;

    invoke-virtual {v0}, Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr$Companion;->getInstance()Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr;

    move-result-object v0

    sget-object v1, Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr$UafSceneEvent;->SYSTEMUI_SHOW_DIMLAYER:Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr$UafSceneEvent;

    invoke-virtual {v0, v1}, Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr;->requestSysResource(Lcom/oplusos/systemui/common/sched/OplusSysUiSchedMgr$UafSceneEvent;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getSwitchHelper$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;

    move-result-object v0

    if-eqz v0, :cond_25

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFpSwitchHelper;->isCustomFpIcon:Z

    if-ne v0, v9, :cond_25

    const-string/jumbo v0, "startFadeInAnimation, setFadeInAlphaAnimation"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_24

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_24
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_28

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAlphaAnimation$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/view/animation/AlphaAnimation;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->startAnimation(Landroid/view/animation/Animation;)V

    goto :goto_7

    :cond_25
    const-string/jumbo v0, "startFadeInAnimation, setFadeInAnimDrawable"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_26

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_26
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_27

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAnimationDrawableListener$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;

    move-result-object v1

    invoke-virtual {v0, v1}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->setOnAnimationDrawableListener(Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable$OnAnimationDrawableListener;)V

    :cond_27
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFadeInAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    if-eqz v0, :cond_28

    invoke-virtual {v0}, Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;->start()V

    :cond_28
    :goto_7
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOnDreamingStart()Z

    move-result v0

    if-eqz v0, :cond_2e

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v8, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    goto :goto_8

    :cond_29
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iget-boolean v0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isTouchDownNow:Z

    if-nez v0, :cond_2e

    const-string/jumbo v0, "show last frame in FadeInAnimation "

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getScreenTurnedOff()Z

    move-result v0

    if-eqz v0, :cond_2a

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOnDreamingStart()Z

    move-result v0

    if-nez v0, :cond_2b

    :cond_2a
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    :cond_2b
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_2c

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_2c
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconAlpha$default(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    goto :goto_8

    :cond_2d
    invoke-static {}, Lcom/oplusos/systemui/common/util/LogUtil;->getNormalDebug()Z

    move-result p0

    if-eqz p0, :cond_2e

    const-string p0, "Keyguard"

    invoke-static {p0}, Lcom/oplusos/systemui/common/util/LogUtil;->isTagValid(Ljava/lang/String;)Z

    move-result p0

    if-eqz p0, :cond_2e

    const-string p0, " isFpIconDrawable: "

    const-string v2, "OnScreenFingerprintUiMech-->"

    const-string v3, "fadeInAnimState:"

    invoke-static {v3, p0, v2, v0, v1}, Lcom/android/systemui/application/impl/SystemUIApplicationImpl$$ExternalSyntheticOutline0;->m(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;ZZ)Ljava/lang/String;

    move-result-object p0

    const-string v0, "SystemUi--Keyguard"

    invoke-static {v0, p0}, Landroid/util/Log;->d(Ljava/lang/String;Ljava/lang/String;)I

    :cond_2e
    :goto_8
    return-void

    :pswitch_7
    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$Companion;

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object p0

    invoke-virtual {v0, p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    move-result-object p0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->notifyFpTouchDown()V

    return-void

    :pswitch_8
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getShowFingerprintIconReason$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/String;

    move-result-object v0

    invoke-static {v0}, Landroid/text/TextUtils;->isEmpty(Ljava/lang/CharSequence;)Z

    move-result v0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    if-eqz v0, :cond_2f

    iput v8, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconDelayedCount:I

    goto :goto_9

    :cond_2f
    iget v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconDelayedCount:I

    add-int/2addr v0, v9

    iput v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconDelayedCount:I

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getShowFingerprintIconReason$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/String;

    move-result-object v0

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconTemporarily(Ljava/lang/String;)V

    :goto_9
    return-void

    :pswitch_9
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$initWindow(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0, v8}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFingerIconOrientation(Z)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$setVisibilityRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0, v8}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->showFingerprintIconAnimation(Z)V

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$Companion;

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object p0

    invoke-virtual {v0, p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    move-result-object p0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->isQuickLaunchAppEnable()Z

    move-result v0

    if-nez v0, :cond_30

    goto :goto_a

    :cond_30
    new-instance v0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;

    invoke-direct {v0, v6}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;-><init>(I)V

    iput-object p0, v0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$$ExternalSyntheticLambda0;->f$0:Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    invoke-static {}, Ljava/lang/invoke/VarHandle;->storeStoreFence()V

    invoke-virtual {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->runOnUIThread(Lkotlin/jvm/functions/Function0;)V

    :goto_a
    sget-object p0, Lcom/android/systemui/DependencyEx;->sDependency:Lcom/android/systemui/DependencyEx;

    invoke-virtual {p0, v2}, Lcom/android/systemui/DependencyEx;->getDependency(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p0

    check-cast p0, Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;

    iget-object p0, p0, Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;->mHandler:Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator$3;

    invoke-virtual {p0, v6}, Landroid/os/Handler;->sendEmptyMessage(I)Z

    return-void

    :pswitch_a
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_34

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getOpticalUiUpdateHandler$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/os/Handler;

    move-result-object v0

    if-eqz v0, :cond_31

    iget-object v2, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getHideFingerprintIconRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/Runnable;

    move-result-object v2

    invoke-virtual {v0, v2}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_31
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_32

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_32
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_33

    invoke-virtual {v0}, Landroid/widget/ImageView;->invalidate()V

    :cond_33
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object p0

    if-eqz p0, :cond_34

    const-string/jumbo v0, "setVisibilityInAOD"

    invoke-virtual {p0, v1, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->setVisibility(ILjava/lang/String;)V

    :cond_34
    return-void

    :pswitch_b
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v11

    iput-wide v11, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->oneosWakeAt:J

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopFadeOutAnimation()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOnDreamingStart()Z

    move-result v0

    if-nez v0, :cond_36

    const-string/jumbo v0, "onStartedWakingUp with screen on,just call onDreamingStopped "

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getOpticalUiUpdateHandler$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/os/Handler;

    move-result-object v0

    if-eqz v0, :cond_35

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getDreamingRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Ljava/lang/Runnable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/os/Handler;->removeCallbacks(Ljava/lang/Runnable;)V

    :cond_35
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$onDreamingStopped(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    :cond_36
    return-void

    :pswitch_c
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_38

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->getOnDreamingStart()Z

    move-result v0

    if-nez v0, :cond_38

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopOpticalAnimation()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object v0

    invoke-static {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/aod/display/AODDisplayUtil;

    move-result-object v0

    invoke-virtual {v0}, Lcom/oplus/systemui/aod/display/AODDisplayUtil;->isPanoramicProcessType()Z

    move-result v0

    if-eqz v0, :cond_37

    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isNonLocalHbmSupportOpticalFp()Z

    move-result v0

    if-eqz v0, :cond_38

    :cond_37
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object p0

    if-eqz p0, :cond_38

    invoke-virtual {p0, v7}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_38
    return-void

    :pswitch_d
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_3a

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_39

    iget-object v1, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getImMobileDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/graphics/drawable/Drawable;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_39
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconColor()V

    :cond_3a
    return-void

    :pswitch_e
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_3b

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpLocation$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)[I

    move-result-object p0

    invoke-virtual {v0, p0}, Landroid/widget/ImageView;->getLocationOnScreen([I)V

    :cond_3b
    return-void

    :pswitch_f
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_43

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isPressAnimRunning()Z

    move-result v0

    if-eqz v0, :cond_3c

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->isPressAnimRunning()Z

    move-result v0

    if-eqz v0, :cond_43

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$needInterruptAnim(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Z

    move-result v0

    if-eqz v0, :cond_43

    :cond_3c
    const-string/jumbo v0, "visibilityHide"

    const-wide/16 v4, 0x8

    invoke-static {v4, v5, v0}, Landroid/os/Trace;->traceBegin(JLjava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedAnimDrawable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/keyguard/view/OplusAnimationDrawable;

    move-result-object v0

    instance-of v2, v0, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;

    if-eqz v2, :cond_3d

    move-object v7, v0

    check-cast v7, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;

    :cond_3d
    if-eqz v7, :cond_3e

    :try_start_0
    const-string/jumbo v0, "stopEffect"

    invoke-static {v3, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->d(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, v7, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCoeSysEffect:Lcom/coe/syseffect/COESysEffect;

    if-eqz v0, :cond_3e

    invoke-virtual {v0}, Lcom/coe/syseffect/COESysEffect;->stopAllAnim()V

    iget-object v0, v7, Lcom/oplus/systemui/keyguard/view/OplusHyWaterAnimationDrawable;->mCoeSysEffect:Lcom/coe/syseffect/COESysEffect;

    const-string v2, "animator1"

    invoke-virtual {v0, v2}, Lcom/coe/syseffect/COESysEffect;->seekAnimToEnd(Ljava/lang/String;)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    goto :goto_b

    :catch_0
    move-exception v0

    new-instance v2, Ljava/lang/StringBuilder;

    const-string/jumbo v6, "stopEffect e:"

    invoke-direct {v2, v6}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v3, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->e(Ljava/lang/String;Ljava/lang/String;)V

    :cond_3e
    :goto_b
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_3f

    const-string/jumbo v2, "mHideIconRunnable run"

    invoke-virtual {v0, v1, v2}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;->setVisibility(ILjava/lang/String;)V

    :cond_3f
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIconShadow$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_40

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_40
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIconShadowOther$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_41

    invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_41
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getPressedIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object p0

    if-eqz p0, :cond_42

    invoke-virtual {p0, v1}, Landroid/widget/ImageView;->setVisibility(I)V

    :cond_42
    invoke-static {v4, v5}, Landroid/os/Trace;->traceEnd(J)V

    :cond_43
    return-void

    :pswitch_10
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    iput-boolean v8, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->pendingHide:Z

    iput-boolean v9, v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->needDoFadeInAnimation:Z

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$setVisibilityRunnable$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    const-string v0, "hideFingerprintIcon"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopPressedAnimation()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->stopOpticalAnimation()V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIcon$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintIcon;

    move-result-object v0

    if-eqz v0, :cond_44

    invoke-virtual {v0, v7}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_44
    sget-object v0, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->INSTANCE:Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;

    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isSupportOpticalFps()Z

    move-result v0

    if-eqz v0, :cond_45

    invoke-static {}, Lcom/oplusos/systemui/common/feature/KeyguardFeatureOption;->isLocalHBM()Z

    move-result v0

    if-nez v0, :cond_45

    sget-object v0, Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils;->Companion:Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils$Companion;

    const-string v1, "OnScreenFingerprintPressedIcon"

    const-string v3, ""

    invoke-virtual {v0, v1, v8, v3}, Lcom/oplus/keyguard/utils/KeyguardRapidUnlockUtils$Companion;->talkToSurfaceFlingerForLayer(Ljava/lang/String;ZLjava/lang/String;)V

    :cond_45
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIconShadow$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_46

    invoke-virtual {v0, v7}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_46
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFpIconShadowOther$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/widget/ImageView;

    move-result-object v0

    if-eqz v0, :cond_47

    invoke-virtual {v0, v7}, Landroid/widget/ImageView;->setImageDrawable(Landroid/graphics/drawable/Drawable;)V

    :cond_47
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$delayHide(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0, v8}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$updateScreenBrightness(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;Z)V

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$Companion;

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object p0

    invoke-virtual {v0, p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager$Companion;->getInstance(Landroid/content/Context;)Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;

    move-result-object p0

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->isQuickLaunchAppEnable()Z

    move-result p0

    if-nez p0, :cond_48

    goto :goto_c

    :cond_48
    invoke-static {}, Lcom/oplus/systemui/biometrics/finger/udfps/fpquicklaunch/quicklaunch/QuickLaunchManager;->dismissQuickLaunchTips()V

    :goto_c
    sget-object p0, Lcom/android/systemui/DependencyEx;->sDependency:Lcom/android/systemui/DependencyEx;

    invoke-virtual {p0, v2}, Lcom/android/systemui/DependencyEx;->getDependency(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p0

    check-cast p0, Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;

    iget-object p0, p0, Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator;->mHandler:Lcom/oplus/systemui/keyguard/wallpaper/pictorial/PictorialMediator$3;

    invoke-virtual {p0, v6}, Landroid/os/Handler;->sendEmptyMessage(I)Z

    return-void

    :pswitch_11
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    sget-object v1, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->cancelRealHideRunnable()V

    const-string/jumbo v0, "realHide "

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {p0, v9}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->setVisibilityInAOD(I)V

    return-void

    :pswitch_12
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFpIconSize()V

    return-void

    :pswitch_13
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getHighLightControl$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    move-result-object v0

    if-eqz v0, :cond_49

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object p0

    const-string v1, "FS request show"

    invoke-virtual {v0, p0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;->updateHighlightState(Landroid/content/Context;Ljava/lang/String;)V

    :cond_49
    return-void

    :pswitch_14
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getHighLightControl$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;

    move-result-object v0

    if-eqz v0, :cond_4a

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getContext$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/content/Context;

    move-result-object p0

    const-string v1, "FS request hide"

    invoke-virtual {v0, p0, v1}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenHighLightControl;->updateHighlightState(Landroid/content/Context;Ljava/lang/String;)V

    :cond_4a
    return-void

    :pswitch_15
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    const/4 v0, -0x1

    invoke-static {p0, v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$setPressedIconTouchable(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;I)V

    return-void

    :pswitch_16
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$onDreamingStart(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)V

    return-void

    :pswitch_17
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->loadAnimDrawables()V

    return-void

    :pswitch_18
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-virtual {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->loadAnimDrawables()V

    return-void

    :pswitch_19
    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    sget-object v0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->Companion:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$Companion;

    invoke-virtual {p0, v9}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->updateFingerIconOrientation(Z)V

    return-void

    :pswitch_1a
    const-string v0, "cancelFingerprintAnimator"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/AnimatorSet;

    move-result-object v0

    if-eqz v0, :cond_4b

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/AnimatorSet;

    move-result-object v0

    if-eqz v0, :cond_4b

    invoke-virtual {v0}, Landroid/animation/AnimatorSet;->isRunning()Z

    move-result v0

    if-ne v0, v9, :cond_4b

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/AnimatorSet;

    move-result-object p0

    if-eqz p0, :cond_4b

    invoke-virtual {p0}, Landroid/animation/AnimatorSet;->cancel()V

    :cond_4b
    return-void

    :pswitch_1b
    const-string v0, "cancelFpPendingColorAnimator"

    invoke-static {v10, v0}, Lcom/oplusos/keyguard/utils/KgdLogUtil;->i(Ljava/lang/String;Ljava/lang/String;)V

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintColorAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/Animator;

    move-result-object v0

    if-eqz v0, :cond_4c

    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintColorAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/Animator;

    move-result-object v0

    if-eqz v0, :cond_4c

    invoke-virtual {v0}, Landroid/animation/Animator;->isRunning()Z

    move-result v0

    if-ne v0, v9, :cond_4c

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getFingerPrintColorAnimator$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Landroid/animation/Animator;

    move-result-object p0

    if-eqz p0, :cond_4c

    invoke-virtual {p0}, Landroid/animation/Animator;->cancel()V

    :cond_4c
    return-void

    :pswitch_1c
    iget-object v0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {v0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getKeyguardUpdateMonitor$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/android/keyguard/KeyguardUpdateMonitor;

    move-result-object v0

    iget-object p0, p0, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech$1;->this$0:Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;

    invoke-static {p0}, Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;->access$getUpdateMonitorCallback$p(Lcom/oplus/systemui/biometrics/finger/udfps/OnScreenFingerprintUiMech;)Lcom/android/keyguard/KeyguardUpdateMonitorCallback;

    move-result-object p0

    invoke-virtual {v0, p0}, Lcom/android/keyguard/KeyguardUpdateMonitor;->registerCallback(Lcom/android/keyguard/KeyguardUpdateMonitorCallback;)V

    return-void

    nop

    :pswitch_data_0
    .packed-switch 0x0
        :pswitch_1c
        :pswitch_1b
        :pswitch_1a
        :pswitch_19
        :pswitch_18
        :pswitch_17
        :pswitch_16
        :pswitch_15
        :pswitch_14
        :pswitch_13
        :pswitch_12
        :pswitch_11
        :pswitch_10
        :pswitch_f
        :pswitch_e
        :pswitch_d
        :pswitch_c
        :pswitch_b
        :pswitch_a
        :pswitch_9
        :pswitch_8
        :pswitch_7
        :pswitch_6
        :pswitch_5
        :pswitch_4
        :pswitch_3
        :pswitch_2
        :pswitch_1
        :pswitch_0
    .end packed-switch
.end method
