#ifndef ONEOS_GUEST_CLASSPATH_ENVIRONMENT_H
#define ONEOS_GUEST_CLASSPATH_ENVIRONMENT_H

#include "guest_classpath_readback.h"

enum {
    GUEST_CLASSPATH_ENV_KEYS = 4,
    GUEST_CLASSPATH_ENV_MAX_ENTRIES = 128,
    GUEST_CLASSPATH_ENV_MAX_BYTES = 128 * 1024,
    GUEST_CLASSPATH_MAX_JARS = 128,
};

struct guest_classpath_environment {
    const char *entries[GUEST_CLASSPATH_ENV_KEYS + 1];
};

/* Project the same canonical export bytes verified by the file observer into
 * four KEY=value strings and a NULL terminator. A present empty value stays
 * KEY=. Borrow immutable exports and a disjoint caller buffer and result.
 * Both buffer and result remain untouched on failure. */
int guest_classpath_copy_environment(const struct guest_classpath_sample *sample,
        const void *exports, size_t export_bytes, char *buffer, size_t capacity,
        struct guest_classpath_environment *out);

/* Compare the four keys against the proposed final child vector. The owner
 * supplies env_count readable string pointers followed by one readable NULL
 * slot, and retains the entire vector and its strings through exec. The owner
 * independently admits the sample occurrence, file custody, JARs, properties
 * and all other environment keys. Neither function imports the file or changes
 * any process environment. */
int guest_classpath_verify_environment(const struct guest_classpath_sample *sample,
        const void *exports, size_t export_bytes, const char *const envp[], size_t env_count);

/* Compare the complete JAR set in the four canonical exports with count
 * readable pointers to immutable, NUL-terminated paths of at most 240 bytes.
 * Paths are in strict ASCII order. A path can occur in more than one export,
 * once per export. A NULL paths pointer is allowed for an empty set only.
 * The caller independently verifies the export bytes and each JAR. */
int guest_classpath_verify_jar_paths(const void *exports, size_t export_bytes,
        const char *const *paths, size_t count);

#endif
