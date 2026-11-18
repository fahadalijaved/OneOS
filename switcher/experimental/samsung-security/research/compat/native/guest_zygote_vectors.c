#include "guest_zygote_vectors.h"

#include "guest_classpath_environment.h"

#include <errno.h>

enum { CLASSPATH_ENV_START = 9 };

int guest_zygote_build_vectors(const struct guest_classpath_sample *sample,
        const void *exports, size_t export_bytes, int force_jit, char *buffer,
        size_t capacity, struct guest_zygote_vectors *out) {
    if (!out || (force_jit != 0 && force_jit != 1)) {
        errno = EINVAL;
        return -1;
    }
    struct guest_classpath_environment classpath;
    if (guest_classpath_copy_environment(sample, exports, export_bytes, buffer, capacity, &classpath) < 0)
        return -1;

    struct guest_zygote_vectors result = {
        .program = "/system/bin/app_process64",
        .argv = { "zygote64", "-Xzygote" },
        .envp = {
            "ANDROID_SOCKET_zygote=3",
            "ANDROID_SOCKET_usap_pool_primary=4",
            "PATH=/system/bin:/system/xbin",
            "ANDROID_ROOT=/system",
            "ANDROID_DATA=/data",
            "ANDROID_STORAGE=/storage",
            "ANDROID_ART_ROOT=/apex/com.android.art",
            "ANDROID_I18N_ROOT=/apex/com.android.i18n",
            "ANDROID_TZDATA_ROOT=/apex/com.android.tzdata",
            NULL, NULL, NULL, NULL,
            "EXTERNAL_STORAGE=/sdcard",
            "ASEC_MOUNTPOINT=/mnt/asec",
            "ANDROID_ASSETS=/system/app",
            NULL,
        },
    };
    size_t index = 2;
    if (force_jit) result.argv[index++] = "-Xforcejitzygote";
    result.argv[index++] = "/system/bin";
    result.argv[index++] = "--zygote";
    result.argv[index++] = "--start-system-server";
    result.argv[index] = "--socket-name=zygote";
    for (size_t i = 0; i < GUEST_CLASSPATH_ENV_KEYS; ++i)
        result.envp[CLASSPATH_ENV_START + i] = classpath.entries[i];

    *out = result;
    return 0;
}
