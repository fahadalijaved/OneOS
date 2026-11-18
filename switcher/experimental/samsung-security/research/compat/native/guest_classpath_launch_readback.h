#ifndef ONEOS_GUEST_CLASSPATH_LAUNCH_READBACK_H
#define ONEOS_GUEST_CLASSPATH_LAUNCH_READBACK_H

#include "guest_classpath_jar_readback.h"
#include "guest_classpath_readback.h"
#include "guest_zygote_vectors.h"

struct guest_classpath_launch_jar {
    const char *path;
    const int *ancestors;
    size_t ancestor_count;
    int fd;
    struct guest_classpath_jar_pin pin;
};

struct guest_classpath_launch_start {
    struct guest_classpath_start file;
    const struct guest_classpath_launch_jar *jars;
    const struct guest_classpath_jar_sample *samples;
    size_t jar_count;
    const void *exports;
    size_t export_bytes;
    unsigned char export_sha256[32];
};

/* Verify the selected JARs and observe the fresh publication baseline. Supply
 * JARs in strict ASCII pathname order, with each ancestor chain starting at
 * directories->root_fd. The expected exports and independent JAR pins come
 * from the same admitted fragment, mount and effective property view. Borrow
 * all FDs and immutable input arrays, paths and bytes through finish. The
 * sample array is disjoint scratch of sample_capacity entries and can change
 * on refusal. Keep it immutable after success. The disjoint out changes only
 * on success. */
int guest_classpath_launch_begin(const struct guest_classpath_directories *directories,
        const struct guest_classpath_launch_jar *jars, size_t jar_count,
        const void *exports, size_t export_bytes, struct guest_classpath_jar_sample *samples,
        size_t sample_capacity, struct guest_classpath_launch_start *out);

/* After the owner settles the exact producer, verify the final file, proposed
 * environment and retained JAR identities. Borrow the original start, final
 * file FD and immutable envp (env_count entries plus a NULL terminator).
 * The disjoint out changes only on success. The owner excludes other writers,
 * namespace changes and FD substitution through use. No FD or environment
 * ownership changes. The result is readback evidence only. */
int guest_classpath_launch_finish(const struct guest_classpath_launch_start *start,
        int export_fd, const char *const envp[], size_t env_count,
        struct guest_classpath_sample *out);

/* Build the fixed direct-entry profile from the checked file. The buffer is
 * disjoint scratch for classpath strings and can change on refusal. Retain
 * it with the returned vectors. Only out is published after the final join.
 * The owner admits the fixed paths and private socket slots separately. */
int guest_classpath_launch_finish_zygote(const struct guest_classpath_launch_start *start,
        int export_fd, int force_jit, char *buffer, size_t capacity,
        struct guest_zygote_vectors *out);

#endif
