/* Authored SID metadata extraction/registration. No credential verification. */
#include <jni.h>
#include <stdint.h>

static volatile jint attempted;
static volatile jint ready;
static jclass loading_anchor;
static jclass target_anchor;

#if defined(SID_BINDING_TESTING)
static jint test_failure;
#endif

static void fail(JNIEnv *env, const char *type, const char *message) {
    if ((*env)->ExceptionCheck(env)) return;
    jclass exception = (*env)->FindClass(env, type);
    if (exception != 0) {
        (*env)->ThrowNew(env, exception, message);
        (*env)->DeleteLocalRef(env, exception);
    }
}

static jlong extract_sid(JNIEnv *env, jobject receiver, jbyteArray handle) {
    (void)receiver;
    if (__atomic_load_n(&ready, __ATOMIC_ACQUIRE) != 1) {
        fail(env, "java/lang/IllegalStateException", "SID binding is unavailable");
        return 0;
    }
    if (handle == 0) {
        fail(env, "java/lang/NullPointerException", 0);
        return 0;
    }
    jsize length = (*env)->GetArrayLength(env, handle);
    if ((*env)->ExceptionCheck(env)) return 0;
    if (length < 9) {
        fail(env, "java/lang/IllegalArgumentException", "Password handle is too short");
        return 0;
    }
    const unsigned char *bytes = (*env)->GetPrimitiveArrayCritical(env, handle, 0);
    if (bytes == 0) {
        fail(env, "java/lang/OutOfMemoryError", "SID array acquisition failed");
        return 0;
    }
    uint64_t bits = 0;
    for (unsigned int index = 0; index < 8; ++index) {
        bits |= ((uint64_t)bytes[index + 1]) << (index * 8);
    }
    (*env)->ReleasePrimitiveArrayCritical(env, handle, (void *)bytes, JNI_ABORT);
    /* Both admitted targets use two's complement; preserve all 64 result bits. */
    union { uint64_t bits; jlong value; } result;
    result.bits = bits;
    return result.value;
}

JNIEXPORT void JNICALL
Java_com_appleexploit_oneos_security_compat_SidNativeBinding_bind0(
        JNIEnv *env, jclass loading_class, jclass target_class) {
    jint expected = 0;
    if (!__atomic_compare_exchange_n(&attempted, &expected, 1, 0,
            __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        fail(env, "java/lang/IllegalStateException", "SID binding already attempted");
        return;
    }
    if (target_class == 0) {
        fail(env, "java/lang/NullPointerException", 0);
        return;
    }
#if defined(SID_BINDING_TESTING)
    if (test_failure == 1) {
        fail(env, "java/lang/OutOfMemoryError", "Synthetic loading anchor failure");
        return;
    }
#endif
    loading_anchor = (*env)->NewGlobalRef(env, loading_class);
    if (loading_anchor == 0 || (*env)->ExceptionCheck(env)) {
        fail(env, "java/lang/OutOfMemoryError", "SID loading anchor unavailable");
        return;
    }
#if defined(SID_BINDING_TESTING)
    if (test_failure == 2) {
        fail(env, "java/lang/OutOfMemoryError", "Synthetic target anchor failure");
        return;
    }
#endif
    target_anchor = (*env)->NewGlobalRef(env, target_class);
    if (target_anchor == 0 || (*env)->ExceptionCheck(env)) {
        fail(env, "java/lang/OutOfMemoryError", "SID target anchor unavailable");
        return;
    }
#if defined(SID_BINDING_TESTING)
    if (test_failure == 3) {
        fail(env, "java/lang/IllegalStateException", "Synthetic preregistration failure");
        return;
    }
#endif
    JNINativeMethod method = {"nativeSidFromPasswordHandle", "([B)J", (void *)extract_sid};
    jint outcome = (*env)->RegisterNatives(env, target_class, &method, 1);
    if (outcome != JNI_OK || (*env)->ExceptionCheck(env)) {
        /* Progress can be uncertain: both class anchors are deliberately retained. */
        fail(env, "java/lang/IllegalStateException", "SID registration failed");
        return;
    }
#if defined(SID_BINDING_TESTING)
    if (test_failure == 4) {
        fail(env, "java/lang/IllegalStateException", "Synthetic postregistration failure");
        return;
    }
#endif
    __atomic_store_n(&ready, 1, __ATOMIC_RELEASE);
    /* Process-lifetime anchors: no unregister, DeleteGlobalRef or unload API. */
}

#if defined(SID_BINDING_TESTING)
JNIEXPORT void JNICALL
Java_com_appleexploit_oneos_security_compat_SidNativeBindingTest_configureFailure0(
        JNIEnv *env, jclass type, jint stage) {
    (void)type;
    if (__atomic_load_n(&attempted, __ATOMIC_ACQUIRE) != 0 || stage < 0 || stage > 4) {
        fail(env, "java/lang/IllegalStateException", "Synthetic stage unavailable");
        return;
    }
    test_failure = stage;
}

JNIEXPORT jint JNICALL
Java_com_appleexploit_oneos_security_compat_SidNativeBindingTest_anchors0(
        JNIEnv *env, jclass type, jclass helper, jclass target) {
    (void)type;
    jint result = __atomic_load_n(&attempted, __ATOMIC_ACQUIRE) ? 4 : 0;
    if (__atomic_load_n(&ready, __ATOMIC_ACQUIRE)) result |= 8;
    if (loading_anchor != 0) {
        result |= 1;
        if ((*env)->GetObjectRefType(env, loading_anchor) == JNIGlobalRefType
                && (*env)->IsSameObject(env, loading_anchor, helper)) result |= 16;
    }
    if (target_anchor != 0) {
        result |= 2;
        if ((*env)->GetObjectRefType(env, target_anchor) == JNIGlobalRefType
                && (*env)->IsSameObject(env, target_anchor, target)) result |= 32;
    }
    return result;
}
#endif
