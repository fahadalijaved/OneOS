# One UI Design 0.9.13+oneui8's ImmersiveScrollHelper names SeslImmersiveScrollBehavior, which the pinned
# SESL Material (1.14.0+1.0.47-sesl9) does not have. The helper only runs with immersive scroll on, which
# no guest layout or ToolbarLayout use turns on; R8 otherwise refuses the release build (missing class).
-dontwarn com.google.android.material.appbar.SeslImmersiveScrollBehavior
