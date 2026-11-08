#define _GNU_SOURCE
#include "guest_linkerconfig_output.h"

#include "guest_readback_identity.h"
#include "guest_tree_sha256.h"

#include <linux/magic.h>
#include <string.h>
#include <sys/statfs.h>
#include <unistd.h>

enum slot { ROOT, DIRECTORY, BASE, COMPANION, SLOTS };

static const char *const names[SLOTS] = {
    [DIRECTORY] = "linkerconfig", [BASE] = "ld.config.txt", [COMPANION] = "apex.libraries.config.txt",
};

static int snapshot(const int *fd, struct statx *held, unsigned count) {
    if (guest_readback_stat(fd[ROOT], "", &held[ROOT]) < 0) return -1;
    for (unsigned i = DIRECTORY; i < count; ++i) {
        struct statx named;
        int parent = fd[i == DIRECTORY ? ROOT : DIRECTORY];
        if (guest_readback_stat(fd[i], "", &held[i]) < 0
                || guest_readback_stat(parent, names[i], &named) < 0) return -1;
        if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

static int stable_snapshot(const struct statx *before, const struct statx *after, unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    return 0;
}

static int readback_flags(const int *fd, unsigned count) {
    for (unsigned i = 0; i < count; ++i) {
        if (fd[i] < 0) return guest_readback_refuse(EINVAL);
        for (unsigned j = 0; j < i; ++j) {
            if (fd[i] == fd[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fd[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
        if (i < BASE) continue;
        flags = fcntl(fd[i], F_GETFL);
        if (flags < 0) return -1;
        if ((flags & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);
    }
    return 0;
}

static int output_directory(int fd, const struct statx *root, const struct statx *dir) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    if (fs.f_type != TMPFS_MAGIC || root->stx_mnt_id == dir->stx_mnt_id) return guest_readback_refuse(EXDEV);
    if (!S_ISDIR(root->stx_mode) || dir->stx_mode != (S_IFDIR | 0755) || dir->stx_uid || dir->stx_gid)
        return guest_readback_refuse(EPERM);
    return 0;
}

static int output_profile(const struct statx *file) {
    return file->stx_mode == (S_IFREG | 0644) && !file->stx_uid && !file->stx_gid && file->stx_nlink == 1;
}

static struct guest_linkerconfig_generation_node generation_node(const struct statx *node) {
    return (struct guest_linkerconfig_generation_node) {
        .mount_id = node->stx_mnt_id, .inode = node->stx_ino,
        .device_major = node->stx_dev_major, .device_minor = node->stx_dev_minor,
        .mode = node->stx_mode, .uid = node->stx_uid, .gid = node->stx_gid,
    };
}

static int same_generation_node(const struct guest_linkerconfig_generation_node *before, const struct statx *now) {
    return before->mount_id == now->stx_mnt_id && before->inode == now->stx_ino
            && before->device_major == now->stx_dev_major && before->device_minor == now->stx_dev_minor
            && before->mode == now->stx_mode && before->uid == now->stx_uid && before->gid == now->stx_gid;
}

struct text_span {
    const unsigned char *begin, *end;
};

static int ascii_space(unsigned char byte) {
    return byte == ' ' || (byte >= '\t' && byte <= '\r');
}

static struct text_span trim(struct text_span text) {
    while (text.begin < text.end && ascii_space(*text.begin)) ++text.begin;
    while (text.begin < text.end && ascii_space(text.end[-1])) --text.end;
    return text;
}

static int equals(struct text_span text, const char *literal) {
    size_t length = strlen(literal);
    return (size_t)(text.end - text.begin) == length && !memcmp(text.begin, literal, length);
}

static int valid_name(struct text_span text) {
    if (text.begin == text.end) return 0;
    for (const unsigned char *p = text.begin; p < text.end; ++p) {
        unsigned char byte = *p;
        if (!((byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z')
                || (byte >= '0' && byte <= '9') || byte == '.' || byte == '_' || byte == '-')) return 0;
    }
    return 1;
}

static int system_section(const unsigned char *bytes, size_t size, struct guest_linkerconfig_system_section *out) {
    struct guest_linkerconfig_system_section result = {0};
    const unsigned char *end = bytes + size;
    int in_preamble = 1, in_system = 0;
    uint32_t number = 0;
    while (bytes < end) {
        const unsigned char *lf = memchr(bytes, '\n', (size_t)(end - bytes));
        const unsigned char *limit = lf ? lf : end;
        const unsigned char *comment = memchr(bytes, '#', (size_t)(limit - bytes));
        struct text_span line = trim((struct text_span){ bytes, comment ? comment : limit });
        bytes = lf ? lf + 1 : end;
        ++number;
        if (line.begin == line.end) continue;

        if (*line.begin == '[') {
            if (!result.mapping_line || line.end - line.begin < 3 || line.end[-1] != ']')
                return guest_readback_refuse(EPROTO);
            struct text_span name = { line.begin + 1, line.end - 1 };
            if (!valid_name(name)) return guest_readback_refuse(EPROTO);
            in_system = equals(name, "system");
            if (in_preamble && !in_system) return guest_readback_refuse(EPROTO);
            in_preamble = 0;
            if (in_system) {
                if (result.section_line) return guest_readback_refuse(EPROTO);
                result.section_line = number;
            }
            continue;
        }

        const unsigned char *assign = memchr(line.begin, '=', (size_t)(line.end - line.begin));
        if (!assign || assign == line.begin) return guest_readback_refuse(EPROTO);
        int append = assign[-1] == '+';
        struct text_span key = trim((struct text_span){ line.begin, assign - append });
        struct text_span value = trim((struct text_span){ assign + 1, line.end });
        if (!valid_name(key)) return guest_readback_refuse(EPROTO);
        int mapping = key.end - key.begin > 4 && !memcmp(key.begin, "dir.", 4);
        if (in_preamble) {
            if (append || !mapping || value.begin == value.end || *value.begin != '/') return guest_readback_refuse(EPROTO);
            if (!result.mapping_line) {
                if (!equals(key, "dir.system") || (!equals(value, "/system/bin/") && !equals(value, "/system/bin")))
                    return guest_readback_refuse(EPROTO);
                result.mapping_line = number;
            }
        } else if (mapping) {
            return guest_readback_refuse(EPROTO);
        } else if (in_system && equals(key, "namespace.default.search.paths")) {
            if (value.begin == value.end || append != (result.search_path_lines != 0)
                    || (!append && !equals(value, "/system/${LIB}")))
                return guest_readback_refuse(EPROTO);
            ++result.search_path_lines;
        }
    }
    if (!result.section_line || !result.search_path_lines) return guest_readback_refuse(EPROTO);
    *out = result;
    return 0;
}

static int hash_output(int fd, const struct statx *file, int require_content,
        unsigned char *capture, struct guest_linkerconfig_output_file_sample *out) {
    unsigned char buffer[4096];
    struct guest_tree_sha256 hash;
    size_t used = 0, bytes = (size_t)file->stx_size;
    int comment = 0, content = 0;
    guest_tree_sha256_init(&hash);
    while (used < bytes) {
        size_t remaining = bytes - used;
        unsigned char *chunk = capture ? capture + used : buffer;
        ssize_t got = pread(fd, chunk, remaining < sizeof(buffer) ? remaining : sizeof(buffer), (off_t)used);
        if (got < 0) return -1;
        if (!got) return guest_readback_refuse(EIO);
        if (memchr(chunk, 0, (size_t)got)) return guest_readback_refuse(EPROTO);
        for (size_t i = 0; require_content && !content && i < (size_t)got; ++i) {
            unsigned char byte = chunk[i];
            if (byte == '\n') comment = 0;
            else if (byte == '#') comment = 1;
            else if (!comment && byte != ' ' && (byte < '\t' || byte > '\r')) content = 1;
        }
        guest_tree_sha256_update(&hash, chunk, (size_t)got);
        used += (size_t)got;
    }
    ssize_t tail = pread(fd, buffer, 1, (off_t)bytes);
    if (tail < 0) return -1;
    if (tail) return guest_readback_refuse(EFBIG);
    if (require_content && !content) return guest_readback_refuse(EPROTO);
    out->inode = file->stx_ino;
    out->bytes = bytes;
    guest_tree_sha256_final(&hash, out->sha256);
    return 0;
}

static int output_readback(const struct guest_linkerconfig_output_files *files,
        const struct guest_linkerconfig_generation_start *start, unsigned char *scratch, size_t capacity,
        struct guest_linkerconfig_output_sample *out, struct guest_linkerconfig_system_section *system) {
    if (!files || !out) return guest_readback_refuse(EINVAL);
    const int fd[SLOTS] = { files->root_fd, files->directory_fd, files->base_fd, files->companion_fd };
    if (start && (start->root_fd != fd[ROOT] || start->directory_fd != fd[DIRECTORY] || start->base_fd != fd[BASE]))
        return guest_readback_refuse(ESTALE);

    struct statx before[SLOTS], after[SLOTS];
    if (readback_flags(fd, SLOTS) < 0 || snapshot(fd, before, SLOTS) < 0) return -1;
    const struct statx *root = &before[ROOT], *dir = &before[DIRECTORY];
    if (start && (!same_generation_node(&start->root, root) || !same_generation_node(&start->directory, dir)
            || !same_generation_node(&start->base, &before[BASE]))) return guest_readback_refuse(ESTALE);
    if (output_directory(fd[DIRECTORY], root, dir) < 0) return -1;
    if (!guest_readback_same_mount(dir, &before[BASE])
            || !guest_readback_same_mount(dir, &before[COMPANION])) return guest_readback_refuse(EXDEV);
    if (!output_profile(&before[BASE]) || !output_profile(&before[COMPANION])
            || before[BASE].stx_ino == before[COMPANION].stx_ino) return guest_readback_refuse(EPERM);
    if (before[BASE].stx_size > GUEST_LINKERCONFIG_OUTPUT_MAX_BYTES
            || before[COMPANION].stx_size > GUEST_LINKERCONFIG_OUTPUT_MAX_BYTES) return guest_readback_refuse(EFBIG);
    if (system && before[BASE].stx_size > capacity) return guest_readback_refuse(EFBIG);

    struct guest_linkerconfig_output_sample result = {
        .root_mount_id = root->stx_mnt_id, .root_inode = root->stx_ino,
        .directory_mount_id = dir->stx_mnt_id, .directory_inode = dir->stx_ino,
        .directory_device_major = dir->stx_dev_major, .directory_device_minor = dir->stx_dev_minor,
    };
    struct guest_linkerconfig_system_section selected;
    if (hash_output(fd[BASE], &before[BASE], 1, scratch, &result.base) < 0
            || hash_output(fd[COMPANION], &before[COMPANION], 0, NULL, &result.companion) < 0
            || (system && system_section(scratch, result.base.bytes, &selected) < 0)
            || snapshot(fd, after, SLOTS) < 0 || stable_snapshot(before, after, SLOTS) < 0) return -1;
    *out = result;
    if (system) *system = selected;
    return 0;
}

int guest_linkerconfig_output_readback(const struct guest_linkerconfig_output_files *files,
        struct guest_linkerconfig_output_sample *out) {
    return output_readback(files, NULL, NULL, 0, out, NULL);
}

static int companion_absent(int directory_fd) {
    struct statx entry;
    if (guest_readback_stat(directory_fd, names[COMPANION], &entry) == 0) return guest_readback_refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int read_placeholder(int fd) {
    unsigned char marker;
    ssize_t got = pread(fd, &marker, 1, 0);
    if (got < 0) return -1;
    if (!got) return guest_readback_refuse(EIO);
    if (marker != '#') return guest_readback_refuse(EPROTO);
    got = pread(fd, &marker, 1, 1);
    if (got < 0) return -1;
    return got ? guest_readback_refuse(EFBIG) : 0;
}

int guest_linkerconfig_generation_begin(int root_fd, int directory_fd, int base_fd,
        struct guest_linkerconfig_generation_start *out) {
    if (!out) return guest_readback_refuse(EINVAL);
    const int fd[] = { root_fd, directory_fd, base_fd };
    struct statx before[COMPANION], after[COMPANION];
    if (readback_flags(fd, COMPANION) < 0 || snapshot(fd, before, COMPANION) < 0
            || output_directory(directory_fd, &before[ROOT], &before[DIRECTORY]) < 0) return -1;
    if (!guest_readback_same_mount(&before[DIRECTORY], &before[BASE])) return guest_readback_refuse(EXDEV);
    if (!output_profile(&before[BASE])) return guest_readback_refuse(EPERM);
    if (before[BASE].stx_size != 1) return guest_readback_refuse(EPROTO);
    if (companion_absent(directory_fd) < 0 || read_placeholder(base_fd) < 0 || companion_absent(directory_fd) < 0
            || snapshot(fd, after, COMPANION) < 0 || stable_snapshot(before, after, COMPANION) < 0) return -1;

    *out = (struct guest_linkerconfig_generation_start) {
        .root_fd = root_fd, .directory_fd = directory_fd, .base_fd = base_fd,
        .root = generation_node(&before[ROOT]), .directory = generation_node(&before[DIRECTORY]),
        .base = generation_node(&before[BASE]),
    };
    return 0;
}

int guest_linkerconfig_generation_readback(const struct guest_linkerconfig_generation_start *start,
        const struct guest_linkerconfig_output_files *files, struct guest_linkerconfig_output_sample *out) {
    if (!start) return guest_readback_refuse(EINVAL);
    return output_readback(files, start, NULL, 0, out, NULL);
}

int guest_linkerconfig_generation_readback_system(const struct guest_linkerconfig_generation_start *start,
        const struct guest_linkerconfig_output_files *files, void *scratch, size_t capacity,
        struct guest_linkerconfig_system_output_sample *out) {
    if (!start || !scratch || !capacity || !out) return guest_readback_refuse(EINVAL);
    struct guest_linkerconfig_system_output_sample result;
    if (output_readback(files, start, scratch, capacity, &result.output, &result.system) < 0) return -1;
    *out = result;
    return 0;
}
