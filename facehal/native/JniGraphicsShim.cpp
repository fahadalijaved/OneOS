#include <android/bitmap.h>

extern "C" int AndroidBitmap_getInfo(JNIEnv*, jobject, AndroidBitmapInfo*) {
    return ANDROID_BITMAP_RESULT_BAD_PARAMETER;
}

extern "C" int AndroidBitmap_lockPixels(JNIEnv*, jobject, void**) {
    return ANDROID_BITMAP_RESULT_BAD_PARAMETER;
}

extern "C" int AndroidBitmap_unlockPixels(JNIEnv*, jobject) {
    return ANDROID_BITMAP_RESULT_BAD_PARAMETER;
}
