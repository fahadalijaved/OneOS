#define _GNU_SOURCE
#include "guest_native_exec_placement.h"

#include "guest_native_exec_profile.h"
#include "guest_readback_identity.h"
#include "guest_tree_sha256.h"

#include <linux/magic.h>
#include <string.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#ifndef EROFS_MAGIC
#define EROFS_MAGIC 0xe0f5e1e2UL
#endif

#define COUNT(array) (sizeof(array) / sizeof((array)[0]))
#define DIR_BIT(index) (1u << (index))
enum {
    MAX_OBJECTS = 64,
    MAX_FILE_BYTES = 16 * 1024 * 1024,
    BOOTSTRAP_DIRS = DIR_BIT(GNX_APEX) - 1u,
    LINKERCONFIG_DIRS = (DIR_BIT(GNX_DIR_COUNT) - 1u)
            & ~(DIR_BIT(GNX_SYSTEM_BOOTSTRAP_BIN) | DIR_BIT(GNX_SYSTEM_BOOTSTRAP_LIB64)),
    MOUNT_REQUIRED = ST_RDONLY | ST_NOSUID | ST_NODEV,
};

_Static_assert(COUNT(gnx_bootstrap_files) >= 2 && COUNT(gnx_bootstrap_files) <= MAX_OBJECTS
            && COUNT(gnx_linkerconfig_files) >= 2 && COUNT(gnx_linkerconfig_files) <= MAX_OBJECTS,
        "Each native phase needs an entry, interpreter and at most 64 objects");

static const struct {
    const char *name;
    enum guest_native_exec_dir parent;
} directories[GNX_DIR_COUNT] = {
    [GNX_SYSTEM] = { "system", GNX_ROOT },
    [GNX_SYSTEM_BIN] = { "bin", GNX_SYSTEM },
    [GNX_SYSTEM_BOOTSTRAP_BIN] = { "bootstrap", GNX_SYSTEM_BIN },
    [GNX_SYSTEM_LIB64] = { "lib64", GNX_SYSTEM },
    [GNX_SYSTEM_BOOTSTRAP_LIB64] = { "bootstrap", GNX_SYSTEM_LIB64 },
    [GNX_APEX] = { "apex", GNX_ROOT },
    [GNX_RUNTIME] = { "com.android.runtime", GNX_APEX },
    [GNX_RUNTIME_BIN] = { "bin", GNX_RUNTIME },
    [GNX_RUNTIME_LIB64] = { "lib64", GNX_RUNTIME },
    [GNX_RUNTIME_BIONIC] = { "bionic", GNX_RUNTIME_LIB64 },
};

static int check_fds(const struct guest_native_exec_view *view, unsigned active) {
    int fds[GNX_DIR_COUNT + MAX_OBJECTS];
    size_t count = 0;
    for (unsigned i = 0; i < GNX_DIR_COUNT; ++i) {
        if (active & DIR_BIT(i)) fds[count++] = view->dirs[i];
    }
    memcpy(fds + count, view->file_fds, view->file_count * sizeof(int));
    count += view->file_count;
    for (size_t i = 0; i < count; ++i) {
        if (fds[i] < 0) return guest_readback_refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) {
            if (fds[i] == fds[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fds[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    }
    return 0;
}

static int snapshot_directories(const int *fds, unsigned active, struct statx *nodes) {
    for (unsigned i = 0; i < GNX_DIR_COUNT; ++i) {
        if (!(active & DIR_BIT(i))) continue;
        if (guest_readback_stat(fds[i], "", &nodes[i]) < 0) return -1;
        if (!S_ISDIR(nodes[i].stx_mode)) return guest_readback_refuse(ENOTDIR);
        if (i != GNX_ROOT) {
            struct statx named;
            if (guest_readback_stat(fds[directories[i].parent], directories[i].name, &named) < 0) return -1;
            if (!guest_readback_same_node(&nodes[i], &named)) return guest_readback_refuse(ESTALE);
        }
    }
    return 0;
}

static int check_filesystem(int fd, unsigned long expected) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0) return -1;
    return (unsigned long)fs.f_type == expected ? 0 : guest_readback_refuse(EXDEV);
}

static int check_mounts(const struct guest_native_exec_view *view, unsigned active, const struct statx *dirs) {
    const struct statx *root = &dirs[GNX_ROOT];
    if (root->stx_mnt_id != view->carrier_mount_id) return guest_readback_refuse(EXDEV);
    if (check_filesystem(view->dirs[GNX_ROOT], EROFS_MAGIC) < 0) return -1;
    for (unsigned i = GNX_SYSTEM; i < GNX_APEX; ++i) {
        if ((active & DIR_BIT(i)) && !guest_readback_same_mount(root, &dirs[i]))
            return guest_readback_refuse(EXDEV);
    }
    if (!(active & DIR_BIT(GNX_APEX))) return 0;

    const struct statx *apex = &dirs[GNX_APEX], *runtime = &dirs[GNX_RUNTIME];
    const struct guest_apex_runtime_sample *sample = view->runtime;
    if (check_filesystem(view->dirs[GNX_APEX], TMPFS_MAGIC) < 0
            || check_filesystem(view->dirs[GNX_RUNTIME], EROFS_MAGIC) < 0) return -1;
    if (apex->stx_mnt_id == root->stx_mnt_id || runtime->stx_mnt_id == root->stx_mnt_id
            || apex->stx_mnt_id == runtime->stx_mnt_id) return guest_readback_refuse(EXDEV);
    if (apex->stx_mnt_id != sample->xml.mount_id || apex->stx_ino != sample->xml.directory_inode
            || apex->stx_dev_major != sample->xml.device_major || apex->stx_dev_minor != sample->xml.device_minor
            || runtime->stx_mnt_id != sample->runtime_mount_id || runtime->stx_ino != sample->runtime_inode)
        return guest_readback_refuse(ESTALE);
    for (unsigned i = GNX_RUNTIME_BIN; i < GNX_DIR_COUNT; ++i) {
        if (!guest_readback_same_mount(runtime, &dirs[i])) return guest_readback_refuse(EXDEV);
    }
    return 0;
}

static const struct link_pin {
    enum guest_native_exec_dir parent;
    const char *name, *target;
    unsigned gid;
} linkerconfig_links[] = {
    {GNX_SYSTEM_BIN, "linker64", "/apex/com.android.runtime/bin/linker64", 2000},
    {GNX_SYSTEM_LIB64, "libc.so", "/apex/com.android.runtime/lib64/bionic/libc.so", 0},
    {GNX_SYSTEM_LIB64, "libdl.so", "/apex/com.android.runtime/lib64/bionic/libdl.so", 0},
    {GNX_SYSTEM_LIB64, "libm.so", "/apex/com.android.runtime/lib64/bionic/libm.so", 0},
};

static int sample_link(int fd, const struct statx *parent, const struct link_pin *pin, struct statx *link) {
    char actual[64];
    size_t target_bytes = strlen(pin->target);
    struct statx after;
    if (guest_readback_stat(fd, pin->name, link) < 0) return -1;
    if (!guest_readback_same_mount(parent, link)) return guest_readback_refuse(EXDEV);
    if (link->stx_mode != (S_IFLNK | 0777) || link->stx_uid || link->stx_gid != pin->gid
            || link->stx_nlink != 1 || link->stx_size != target_bytes) return guest_readback_refuse(EPERM);
    ssize_t bytes = readlinkat(fd, pin->name, actual, sizeof(actual));
    if (bytes < 0) return -1;
    if ((size_t)bytes != target_bytes || memcmp(actual, pin->target, target_bytes))
        return guest_readback_refuse(EPROTO);
    if (guest_readback_stat(fd, pin->name, &after) < 0) return -1;
    return guest_readback_same_node(link, &after) ? 0 : guest_readback_refuse(ESTALE);
}

struct file_sample {
    struct statx node;
    unsigned long mount_flags;
};

static int sample_file(const struct guest_native_exec_view *view, const struct statx *dirs,
        const struct guest_native_exec_pin *pin, size_t index, struct file_sample *out) {
    int fd = view->file_fds[index];
    int status = fcntl(fd, F_GETFL);
    if (status < 0) return -1;
    if ((status & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);
    struct statvfs fs;
    if (fstatvfs(fd, &fs) < 0) return -1;
    out->mount_flags = fs.f_flag & (MOUNT_REQUIRED | ST_NOEXEC);
    if ((out->mount_flags & MOUNT_REQUIRED) != MOUNT_REQUIRED) return guest_readback_refuse(EPERM);
    struct statx named;
    if (guest_readback_stat(fd, "", &out->node) < 0
            || guest_readback_stat(view->dirs[pin->parent], pin->name, &named) < 0) return -1;
    if (!guest_readback_same_node(&out->node, &named)) return guest_readback_refuse(ESTALE);
    if (!guest_readback_same_mount(&out->node, &dirs[pin->parent])) return guest_readback_refuse(EXDEV);
    if (!S_ISREG(out->node.stx_mode) || out->node.stx_size != pin->bytes
            || (index < 2 && !(out->node.stx_mode & 0111))) return guest_readback_refuse(EPERM);
    return 0;
}

static int hash_file(int fd, const struct guest_native_exec_pin *pin) {
    struct guest_tree_sha256 hash;
    unsigned char buffer[4096], digest[32];
    guest_tree_sha256_init(&hash);
    size_t bytes = (size_t)pin->bytes;
    for (size_t offset = 0; offset < bytes;) {
        size_t count = bytes - offset;
        if (count > sizeof(buffer)) count = sizeof(buffer);
        ssize_t got = pread(fd, buffer, count, (off_t)offset);
        if (got < 0) return -1;
        if (!got || (size_t)got > count) return guest_readback_refuse(EIO);
        guest_tree_sha256_update(&hash, buffer, (size_t)got);
        offset += (size_t)got;
    }
    ssize_t extra = pread(fd, buffer, 1, (off_t)bytes);
    if (extra < 0) return -1;
    if (extra) return guest_readback_refuse(ESTALE);
    guest_tree_sha256_final(&hash, digest);
    return memcmp(digest, pin->sha256, sizeof(digest)) ? guest_readback_refuse(EPROTO) : 0;
}

int guest_native_exec_placement_readback(enum guest_native_exec_phase phase,
        const struct guest_native_exec_view *view, struct guest_native_exec_sample *out) {
    if (!view || !out || !view->file_fds || !view->carrier_mount_id) return guest_readback_refuse(EINVAL);
    const struct guest_native_exec_pin *pins;
    size_t count;
    unsigned active;
    if (phase == GUEST_NATIVE_EXEC_APEXD_BOOTSTRAP) {
        pins = gnx_bootstrap_files;
        count = COUNT(gnx_bootstrap_files);
        active = BOOTSTRAP_DIRS;
    } else if (phase == GUEST_NATIVE_EXEC_LINKERCONFIG_FIRST && view->runtime) {
        pins = gnx_linkerconfig_files;
        count = COUNT(gnx_linkerconfig_files);
        active = LINKERCONFIG_DIRS;
    } else return guest_readback_refuse(EINVAL);
    if (view->file_count != count) return guest_readback_refuse(EINVAL);
    for (size_t i = 0; i < count; ++i) {
        if (pins[i].parent <= GNX_ROOT || pins[i].parent >= GNX_DIR_COUNT
                || !(active & DIR_BIT(pins[i].parent)) || !pins[i].bytes || pins[i].bytes > MAX_FILE_BYTES)
            return guest_readback_refuse(EPROTO);
    }
    if (check_fds(view, active) < 0) return -1;

    struct statx dirs[GNX_DIR_COUNT], after_dirs[GNX_DIR_COUNT], links[COUNT(linkerconfig_links)];
    struct file_sample files[MAX_OBJECTS];
    size_t link_count = phase == GUEST_NATIVE_EXEC_LINKERCONFIG_FIRST ? COUNT(linkerconfig_links) : 0;
    if (snapshot_directories(view->dirs, active, dirs) < 0 || check_mounts(view, active, dirs) < 0) return -1;
    for (size_t i = 0; i < link_count; ++i) {
        const struct link_pin *pin = &linkerconfig_links[i];
        if (sample_link(view->dirs[pin->parent], &dirs[pin->parent], pin, &links[i]) < 0) return -1;
    }
    unsigned long mount_flags[2] = {0};
    for (size_t i = 0; i < count; ++i) {
        if (sample_file(view, dirs, &pins[i], i, &files[i]) < 0) return -1;
        unsigned role = pins[i].parent >= GNX_RUNTIME;
        if (mount_flags[role] && mount_flags[role] != files[i].mount_flags) return guest_readback_refuse(ESTALE);
        mount_flags[role] = files[i].mount_flags;
    }
    for (size_t i = 0; i < count; ++i) {
        if (hash_file(view->file_fds[i], &pins[i]) < 0) return -1;
    }

    struct guest_native_exec_sample result = { .object_count = count };
    for (size_t i = 0; i < count; ++i) {
        struct file_sample after;
        if (sample_file(view, dirs, &pins[i], i, &after) < 0) return -1;
        if (!guest_readback_same_node(&files[i].node, &after.node) || files[i].mount_flags != after.mount_flags)
            return guest_readback_refuse(ESTALE);
        if (after.mount_flags & ST_NOEXEC) result.noexec_objects |= UINT64_C(1) << i;
    }
    if (snapshot_directories(view->dirs, active, after_dirs) < 0 || check_mounts(view, active, after_dirs) < 0)
        return -1;
    for (unsigned i = 0; i < GNX_DIR_COUNT; ++i) {
        if ((active & DIR_BIT(i)) && !guest_readback_same_node(&dirs[i], &after_dirs[i]))
            return guest_readback_refuse(ESTALE);
    }
    for (size_t i = 0; i < link_count; ++i) {
        const struct link_pin *pin = &linkerconfig_links[i];
        struct statx after;
        if (sample_link(view->dirs[pin->parent], &after_dirs[pin->parent], pin, &after) < 0) return -1;
        if (!guest_readback_same_node(&links[i], &after)) return guest_readback_refuse(ESTALE);
    }
    *out = result;
    return 0;
}
