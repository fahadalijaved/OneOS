#ifndef ONEOS_GUEST_ZYGOTE_VECTORS_H
#define ONEOS_GUEST_ZYGOTE_VECTORS_H

#include "guest_classpath_readback.h"

enum { GUEST_ZYGOTE_ENV_COUNT = 16, GUEST_ZYGOTE_ARGV_SLOTS = 8 };

struct guest_zygote_vectors {
    const char *program;
    const char *argv[GUEST_ZYGOTE_ARGV_SLOTS];
    const char *envp[GUEST_ZYGOTE_ENV_COUNT + 1];
};

/* Construct the fixed guest app_process64 vectors. The immutable sample and
 * exports, caller buffer and output are disjoint. The buffer and output are
 * unchanged on refusal. Keep the buffer alive and unchanged while using the
 * result. The owner admits the actual classpath occurrence, guest directories,
 * private listening sockets at FDs 3 and 4, credentials and JIT selection.
 * This only builds vectors and never reads the ambient environment. */
int guest_zygote_build_vectors(const struct guest_classpath_sample *sample,
        const void *exports, size_t export_bytes, int force_jit, char *buffer,
        size_t capacity, struct guest_zygote_vectors *out);

#endif
