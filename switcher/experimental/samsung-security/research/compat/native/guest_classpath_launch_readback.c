#include "guest_classpath_launch_readback.h"

#include "guest_classpath_environment.h"
#include "guest_tree_sha256.h"

#include <errno.h>
#include <string.h>

enum { MAX_TOTAL_JAR_BYTES = 256 * 1024 * 1024 };

static int refuse(int error) {
    errno = error;
    return -1;
}

static void hash_exports(const void *exports, size_t bytes, unsigned char digest[32]) {
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, exports, bytes);
    guest_tree_sha256_final(&hash, digest);
}

static int recheck_jars(const struct guest_classpath_launch_start *start) {
    for (size_t i = 0; i < start->jar_count; ++i) {
        const struct guest_classpath_launch_jar *jar = &start->jars[i];
        if (guest_classpath_jar_recheck(jar->path, jar->ancestors, jar->ancestor_count,
                    jar->fd, &start->samples[i]) < 0) return -1;
    }
    return 0;
}

int guest_classpath_launch_begin(const struct guest_classpath_directories *directories,
        const struct guest_classpath_launch_jar *jars, size_t jar_count,
        const void *exports, size_t export_bytes, struct guest_classpath_jar_sample *samples,
        size_t sample_capacity, struct guest_classpath_launch_start *out) {
    if (!directories || directories->root_fd < 0 || !jars || !jar_count
            || !exports || !export_bytes || !samples || !out) return refuse(EINVAL);
    if (jar_count > GUEST_CLASSPATH_MAX_JARS || export_bytes > GUEST_CLASSPATH_MAX_BYTES)
        return refuse(EFBIG);
    if (sample_capacity < jar_count) return refuse(ENOBUFS);

    const char *paths[GUEST_CLASSPATH_MAX_JARS];
    uint64_t total_bytes = 0;
    for (size_t i = 0; i < jar_count; ++i) {
        const struct guest_classpath_launch_jar *jar = &jars[i];
        if (!jar->path || !jar->ancestors || jar->ancestor_count < 3
                || jar->ancestor_count > GUEST_CLASSPATH_JAR_MAX_ANCESTORS
                || jar->fd < 0 || !jar->pin.bytes) return refuse(EINVAL);
        if (jar->ancestors[0] != directories->root_fd) return refuse(EXDEV);
        if (jar->pin.bytes > GUEST_CLASSPATH_JAR_MAX_BYTES
                || jar->pin.bytes > MAX_TOTAL_JAR_BYTES - total_bytes) return refuse(EFBIG);
        total_bytes += jar->pin.bytes;
        paths[i] = jar->path;
    }
    if (guest_classpath_verify_jar_paths(exports, export_bytes, paths, jar_count) < 0) return -1;

    struct guest_classpath_launch_start result = {
        .jars = jars, .samples = samples, .jar_count = jar_count,
        .exports = exports, .export_bytes = export_bytes,
    };
    hash_exports(exports, export_bytes, result.export_sha256);
    for (size_t i = 0; i < jar_count; ++i) {
        const struct guest_classpath_launch_jar *jar = &jars[i];
        if (guest_classpath_jar_readback(jar->path, jar->ancestors, jar->ancestor_count,
                    jar->fd, &jar->pin, &samples[i]) < 0) return -1;
    }
    if (guest_classpath_begin(directories, &result.file) < 0 || recheck_jars(&result) < 0) return -1;
    *out = result;
    return 0;
}

static int read_final_export(const struct guest_classpath_launch_start *start,
        int export_fd, struct guest_classpath_sample *result) {
    if (!start || !start->jars || !start->samples || !start->jar_count || !start->exports
            || !start->export_bytes) return refuse(EINVAL);
    if (start->jar_count > GUEST_CLASSPATH_MAX_JARS || start->export_bytes > GUEST_CLASSPATH_MAX_BYTES)
        return refuse(EFBIG);
    unsigned char digest[32];
    hash_exports(start->exports, start->export_bytes, digest);
    if (memcmp(digest, start->export_sha256, sizeof(digest))) return refuse(ESTALE);

    if (guest_classpath_readback(&start->file, export_fd, start->exports, start->export_bytes, result) < 0) return -1;
    return memcmp(result->sha256, start->export_sha256, sizeof(result->sha256)) ? refuse(ESTALE) : 0;
}

static int recheck_final(const struct guest_classpath_launch_start *start, int export_fd,
        const struct guest_classpath_sample *result, const char *const envp[], size_t env_count) {
    if (recheck_jars(start) < 0 || guest_classpath_recheck_file(&start->file, export_fd, result) < 0) return -1;
    return guest_classpath_verify_environment(result, start->exports, start->export_bytes, envp, env_count);
}

int guest_classpath_launch_finish(const struct guest_classpath_launch_start *start,
        int export_fd, const char *const envp[], size_t env_count,
        struct guest_classpath_sample *out) {
    if (!envp || !out) return refuse(EINVAL);
    struct guest_classpath_sample result;
    if (read_final_export(start, export_fd, &result) < 0
            || recheck_final(start, export_fd, &result, envp, env_count) < 0) return -1;
    *out = result;
    return 0;
}

int guest_classpath_launch_finish_zygote(const struct guest_classpath_launch_start *start,
        int export_fd, int force_jit, char *buffer, size_t capacity,
        struct guest_zygote_vectors *out) {
    if (!buffer || !out || (force_jit != 0 && force_jit != 1)) return refuse(EINVAL);
    struct guest_classpath_sample sample;
    struct guest_zygote_vectors vectors;
    if (read_final_export(start, export_fd, &sample) < 0
            || guest_zygote_build_vectors(&sample, start->exports, start->export_bytes,
                        force_jit, buffer, capacity, &vectors) < 0
            || recheck_final(start, export_fd, &sample, vectors.envp, GUEST_ZYGOTE_ENV_COUNT) < 0) return -1;
    *out = vectors;
    return 0;
}
