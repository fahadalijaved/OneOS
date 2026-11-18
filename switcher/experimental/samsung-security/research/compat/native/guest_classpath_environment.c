#include "guest_classpath_environment.h"

#include "guest_tree_sha256.h"

#include <errno.h>
#include <string.h>

static const char *const names[GUEST_CLASSPATH_ENV_KEYS] = {
    "BOOTCLASSPATH", "DEX2OATBOOTCLASSPATH", "SYSTEMSERVERCLASSPATH", "STANDALONE_SYSTEMSERVER_JARS",
};
static const char export_prefix[] = "export ";

struct value {
    const unsigned char *bytes;
    size_t length;
};

enum { MAX_JAR_PATH_BYTES = 240 };

static int refuse(int error) {
    errno = error;
    return -1;
}

static int check_export_span(const void *exports, size_t export_bytes) {
    if (!exports || !export_bytes) return refuse(EINVAL);
    return export_bytes > GUEST_CLASSPATH_MAX_BYTES ? refuse(EFBIG) : 0;
}

static int parse_values(const void *exports, size_t export_bytes, struct value values[GUEST_CLASSPATH_ENV_KEYS]) {
    const unsigned char *cursor = exports, *end = cursor + export_bytes;
    const size_t prefix_length = sizeof(export_prefix) - 1;
    for (unsigned i = 0; i < GUEST_CLASSPATH_ENV_KEYS; ++i) {
        size_t name_length = strlen(names[i]);
        size_t header_length = prefix_length + name_length + 1;
        if ((size_t)(end - cursor) <= header_length || memcmp(cursor, export_prefix, prefix_length)
                || memcmp(cursor + prefix_length, names[i], name_length) || cursor[header_length - 1] != ' ')
            return refuse(EPROTO);
        cursor += header_length;
        const unsigned char *lf = memchr(cursor, '\n', (size_t)(end - cursor));
        if (!lf) return refuse(EPROTO);
        for (const unsigned char *p = cursor; p < lf; ++p) {
            if (*p <= ' ' || *p > '~') return refuse(EPROTO);
        }
        values[i] = (struct value) { .bytes = cursor, .length = (size_t)(lf - cursor) };
        cursor = lf + 1;
    }
    return cursor == end ? 0 : refuse(EPROTO);
}

static int checked_values(const struct guest_classpath_sample *sample, const void *exports,
        size_t export_bytes, struct value values[GUEST_CLASSPATH_ENV_KEYS]) {
    if (!sample) return refuse(EINVAL);
    if (check_export_span(exports, export_bytes) < 0) return -1;
    if (!sample->mount_id || !sample->inode || sample->bytes != export_bytes) return refuse(ESTALE);

    struct guest_tree_sha256 hash;
    unsigned char digest[32];
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, exports, export_bytes);
    guest_tree_sha256_final(&hash, digest);
    if (memcmp(digest, sample->sha256, sizeof(digest))) return refuse(ESTALE);

    return parse_values(exports, export_bytes, values);
}

int guest_classpath_copy_environment(const struct guest_classpath_sample *sample,
        const void *exports, size_t export_bytes, char *buffer, size_t capacity,
        struct guest_classpath_environment *out) {
    if (!buffer || !out) return refuse(EINVAL);
    struct value values[GUEST_CLASSPATH_ENV_KEYS];
    if (checked_values(sample, exports, export_bytes, values) < 0) return -1;
    size_t required = export_bytes - GUEST_CLASSPATH_ENV_KEYS * (sizeof(export_prefix) - 1);
    if (capacity < required) return refuse(ENOBUFS);

    struct guest_classpath_environment result = {0};
    for (unsigned i = 0; i < GUEST_CLASSPATH_ENV_KEYS; ++i) {
        size_t name_length = strlen(names[i]);
        result.entries[i] = buffer;
        memcpy(buffer, names[i], name_length);
        buffer[name_length] = '=';
        buffer += name_length + 1;
        memcpy(buffer, values[i].bytes, values[i].length);
        buffer += values[i].length;
        *buffer++ = '\0';
    }
    *out = result;
    return 0;
}

int guest_classpath_verify_environment(const struct guest_classpath_sample *sample,
        const void *exports, size_t export_bytes, const char *const envp[], size_t env_count) {
    if (!envp) return refuse(EINVAL);
    if (env_count > GUEST_CLASSPATH_ENV_MAX_ENTRIES) return refuse(EFBIG);
    if (envp[env_count]) return refuse(EINVAL);
    struct value values[GUEST_CLASSPATH_ENV_KEYS];
    if (checked_values(sample, exports, export_bytes, values) < 0) return -1;

    unsigned seen = 0;
    size_t budget = GUEST_CLASSPATH_ENV_MAX_BYTES;
    for (size_t j = 0; j < env_count; ++j) {
        const char *entry = envp[j];
        if (!entry) return refuse(EINVAL);
        size_t length = 0;
        while (length < budget && entry[length]) ++length;
        if (length == budget) return refuse(EFBIG);
        budget -= length + 1;
        const char *equal = memchr(entry, '=', length);
        if (!equal || equal == entry) return refuse(EPROTO);
        size_t name_length = (size_t)(equal - entry);
        for (unsigned i = 0; i < GUEST_CLASSPATH_ENV_KEYS; ++i) {
            if (name_length != strlen(names[i]) || memcmp(entry, names[i], name_length)) continue;
            unsigned bit = 1u << i;
            if (seen & bit) return refuse(EEXIST);
            if (length - name_length - 1 != values[i].length
                    || memcmp(equal + 1, values[i].bytes, values[i].length)) return refuse(EPROTO);
            seen |= bit;
            break;
        }
    }
    return seen == (1u << GUEST_CLASSPATH_ENV_KEYS) - 1 ? 0 : refuse(ENOENT);
}

static size_t find_jar_path(const char *const *paths, const size_t *lengths, size_t count,
        const unsigned char *path, size_t length) {
    size_t lo = 0, hi = count;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        size_t stored = lengths[mid];
        int order = memcmp(path, paths[mid], length < stored ? length : stored);
        if (!order) {
            if (length == stored) return mid;
            order = length < stored ? -1 : 1;
        }
        if (order < 0) hi = mid;
        else lo = mid + 1;
    }
    return count;
}

int guest_classpath_verify_jar_paths(const void *exports, size_t export_bytes,
        const char *const *paths, size_t count) {
    if (!paths && count) return refuse(EINVAL);
    if (count > GUEST_CLASSPATH_MAX_JARS) return refuse(EFBIG);
    if (check_export_span(exports, export_bytes) < 0) return -1;
    struct value values[GUEST_CLASSPATH_ENV_KEYS];
    if (parse_values(exports, export_bytes, values) < 0) return -1;

    size_t lengths[GUEST_CLASSPATH_MAX_JARS];
    for (size_t i = 0; i < count; ++i) {
        if (!paths[i] || !paths[i][0]) return refuse(EINVAL);
        size_t length = 0;
        while (length <= MAX_JAR_PATH_BYTES && paths[i][length]) {
            unsigned char byte = (unsigned char)paths[i][length++];
            if (byte <= ' ' || byte > '~') return refuse(EPROTO);
        }
        if (length > MAX_JAR_PATH_BYTES) return refuse(EFBIG);
        lengths[i] = length;
        if (i) {
            int order = strcmp(paths[i - 1], paths[i]);
            if (order >= 0) return refuse(order == 0 ? EEXIST : EPROTO);
        }
    }

    unsigned char seen[GUEST_CLASSPATH_MAX_JARS] = {0};
    size_t matched = 0;
    for (unsigned i = 0; i < GUEST_CLASSPATH_ENV_KEYS; ++i) {
        if (!values[i].length) continue;
        const unsigned char *cursor = values[i].bytes, *end = cursor + values[i].length;
        unsigned bit = 1u << i;
        for (;;) {
            const unsigned char *separator = memchr(cursor, ':', (size_t)(end - cursor));
            size_t length = (size_t)((separator ? separator : end) - cursor);
            if (!length) return refuse(EPROTO);
            if (length > MAX_JAR_PATH_BYTES) return refuse(EFBIG);
            size_t index = find_jar_path(paths, lengths, count, cursor, length);
            if (index == count) return refuse(ENOENT);
            if (seen[index] & bit) return refuse(EEXIST);
            if (!seen[index]) ++matched;
            seen[index] |= bit;
            if (!separator) break;
            cursor = separator + 1;
        }
    }
    return matched == count ? 0 : refuse(EPROTO);
}
