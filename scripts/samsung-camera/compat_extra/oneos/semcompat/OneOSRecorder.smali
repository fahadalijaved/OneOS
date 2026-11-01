.class public final Loneos/semcompat/OneOSRecorder;
.super Ljava/lang/Object;

# MediaRecorder calls One UI's recorder takes at any time and AOSP's does not.
# setLocation is setParameters, which AOSP refuses once the recorder is prepared
# (INVALID_OPERATION, IllegalStateException); One UI's camera sets the video's
# location after that, and every recording crashed the camera (Nothing run 24).
# Without a location then: the video still records.

.method public static setLocation(Landroid/media/MediaRecorder;FF)V
    .registers 3
    :try_start
    invoke-virtual {p0, p1, p2}, Landroid/media/MediaRecorder;->setLocation(FF)V
    :try_end
    .catch Ljava/lang/RuntimeException; {:try_start .. :try_end} :ignored
    :ignored
    return-void
.end method

# setOrientationHint the same (run 25, after setLocation): without it the video
# keeps the recorder's default rotation tag.
.method public static setOrientationHint(Landroid/media/MediaRecorder;I)V
    .registers 2
    :try_start
    invoke-virtual {p0, p1}, Landroid/media/MediaRecorder;->setOrientationHint(I)V
    :try_end
    .catch Ljava/lang/RuntimeException; {:try_start .. :try_end} :ignored
    :ignored
    return-void
.end method
