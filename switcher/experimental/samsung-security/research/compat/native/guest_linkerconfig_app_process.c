#define _GNU_SOURCE
#include "guest_linkerconfig_app_process.h"

#include "guest_readback_identity.h"
#include "guest_tree_sha256.h"

#include <linux/magic.h>
#include <string.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <unistd.h>

#define EROFS_MAGIC 0xe0f5e1e2UL

enum slot { ROOT, SYSTEM, SYSTEM_BIN, SYSTEM_ETC, APP, APEX, RUNTIME, RUNTIME_BIN, LINKER, SLOTS };

static const struct {
    const char *name;
    enum slot parent;
    unsigned mode, uid, gid;
} nodes[SLOTS] = {
    [ROOT] = { "", ROOT, S_IFDIR | 0755, 0, 0 },
    [SYSTEM] = { "system", ROOT, S_IFDIR | 0755, 0, 0 },
    [SYSTEM_BIN] = { "bin", SYSTEM, S_IFDIR | 0751, 0, 2000 },
    [SYSTEM_ETC] = { "etc", SYSTEM, S_IFDIR | 0755, 0, 0 },
    [APP] = { "app_process64", SYSTEM_BIN, S_IFREG | 0755, 0, 2000 },
    [APEX] = { "apex", ROOT, S_IFDIR | 0755, 0, 0 },
    [RUNTIME] = { "com.android.runtime", APEX, S_IFDIR | 0755, 1000, 1000 },
    [RUNTIME_BIN] = { "bin", RUNTIME, S_IFDIR | 0755, 0, 2000 },
    [LINKER] = { "linker64", RUNTIME_BIN, S_IFREG | 0755, 0, 2000 },
};

static const char link_target[] = "/apex/com.android.runtime/bin/linker64";
static const unsigned char app_sha256[32] = {
    0x78, 0xd3, 0xbf, 0x52, 0x33, 0x3a, 0x15, 0x1a, 0x6f, 0x48, 0x59, 0xf5, 0x14, 0x4d, 0xe5, 0x57,
    0x8a, 0xdf, 0x00, 0x95, 0x03, 0xb7, 0x92, 0xa9, 0x1d, 0xb3, 0x07, 0x43, 0x5a, 0x0f, 0x21, 0xdc,
};
static const unsigned char linker_sha256[32] = {
    0x97, 0xf3, 0x10, 0x18, 0x81, 0x79, 0x26, 0xc4, 0x99, 0x7b, 0x77, 0xbd, 0x7f, 0x91, 0x37, 0x2e,
    0xcb, 0xe8, 0x34, 0x59, 0x76, 0xcc, 0x20, 0x19, 0xd4, 0x16, 0x8b, 0x00, 0x58, 0x64, 0x30, 0xc8,
};

static int check_arch_absent(int etc_fd) {
    struct statx override;
    if (guest_readback_stat(etc_fd, "ld.config.arm64.txt", &override) == 0) return guest_readback_refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int check_link(int bin_fd, const struct statx *bin, struct statx *link) {
    static const char name[] = "linker64";
    struct statx after;
    char target[sizeof(link_target)];
    if (guest_readback_stat(bin_fd, name, link) < 0) return -1;
    if (!guest_readback_same_mount(bin, link)) return guest_readback_refuse(EXDEV);
    if (link->stx_mode != (S_IFLNK | 0777) || link->stx_uid || link->stx_gid != 2000 || link->stx_nlink != 1
            || link->stx_size != sizeof(link_target) - 1) return guest_readback_refuse(EPERM);
    ssize_t length = readlinkat(bin_fd, name, target, sizeof(target));
    if (length < 0) return -1;
    if ((size_t)length != sizeof(link_target) - 1 || memcmp(target, link_target, sizeof(link_target) - 1))
        return guest_readback_refuse(EPROTO);
    if (guest_readback_stat(bin_fd, name, &after) < 0) return -1;
    return guest_readback_same_node(link, &after) ? 0 : guest_readback_refuse(ESTALE);
}

static int snapshot(const int fd[SLOTS], struct statx held[SLOTS], struct statx *link) {
    for (unsigned i = 0; i < SLOTS; ++i) {
        if (guest_readback_stat(fd[i], "", &held[i]) < 0) return -1;
        if (held[i].stx_mode != nodes[i].mode || held[i].stx_uid != nodes[i].uid || held[i].stx_gid != nodes[i].gid)
            return guest_readback_refuse(EPERM);
        if (i == ROOT) continue;
        struct statx named;
        if (guest_readback_stat(fd[nodes[i].parent], nodes[i].name, &named) < 0) return -1;
        if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
    }
    if (check_arch_absent(fd[SYSTEM_ETC]) < 0) return -1;
    return check_link(fd[SYSTEM_BIN], &held[SYSTEM_BIN], link);
}

static int check_filesystems(const int fd[SLOTS], const struct statx held[SLOTS],
        const struct guest_apex_runtime_sample *runtime) {
    const struct statx *root = &held[ROOT], *apex = &held[APEX], *module = &held[RUNTIME];
    struct statfs root_fs, apex_fs, runtime_fs;
    if (fstatfs(fd[ROOT], &root_fs) < 0 || fstatfs(fd[APEX], &apex_fs) < 0 || fstatfs(fd[RUNTIME], &runtime_fs) < 0)
        return -1;
    if ((unsigned long)root_fs.f_type != EROFS_MAGIC || apex_fs.f_type != TMPFS_MAGIC
            || (unsigned long)runtime_fs.f_type != EROFS_MAGIC
            || root->stx_mnt_id == apex->stx_mnt_id || root->stx_mnt_id == module->stx_mnt_id
            || apex->stx_mnt_id == module->stx_mnt_id) return guest_readback_refuse(EXDEV);
    for (unsigned i = SYSTEM; i <= APP; ++i) {
        if (!guest_readback_same_mount(root, &held[i])) return guest_readback_refuse(EXDEV);
    }
    if (!guest_readback_same_mount(module, &held[RUNTIME_BIN]) || !guest_readback_same_mount(module, &held[LINKER]))
        return guest_readback_refuse(EXDEV);
    if (apex->stx_mnt_id != runtime->xml.mount_id || apex->stx_ino != runtime->xml.directory_inode
            || apex->stx_dev_major != runtime->xml.device_major || apex->stx_dev_minor != runtime->xml.device_minor
            || module->stx_mnt_id != runtime->runtime_mount_id || module->stx_ino != runtime->runtime_inode)
        return guest_readback_refuse(ESTALE);
    return 0;
}

static int check_elf(int fd, const struct statx *file, size_t bytes, const unsigned char expected[32]) {
    if (file->stx_nlink != 1 || file->stx_size != bytes) return guest_readback_refuse(EPROTO);
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0) return -1;
    if ((flags & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);

    unsigned char buffer[4096], digest[32];
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    for (size_t used = 0; used < bytes;) {
        size_t remaining = bytes - used;
        ssize_t got = pread(fd, buffer, remaining < sizeof(buffer) ? remaining : sizeof(buffer), (off_t)used);
        if (got < 0) return -1;
        if (!got) return guest_readback_refuse(EIO);
        guest_tree_sha256_update(&hash, buffer, (size_t)got);
        used += (size_t)got;
    }
    ssize_t tail = pread(fd, buffer, 1, (off_t)bytes);
    if (tail < 0) return -1;
    if (tail) return guest_readback_refuse(EFBIG);
    guest_tree_sha256_final(&hash, digest);
    return memcmp(digest, expected, sizeof(digest)) ? guest_readback_refuse(EPROTO) : 0;
}

enum { REQUIRED_MOUNT_FLAGS = ST_RDONLY | ST_NOSUID | ST_NODEV };

struct exec_mount_flags {
    unsigned long app, interpreter;
};

static int read_mount_flags(const int fd[SLOTS], struct exec_mount_flags *flags) {
    struct statvfs app, interpreter;
    const unsigned long mask = REQUIRED_MOUNT_FLAGS | ST_NOEXEC;
    if (fstatvfs(fd[APP], &app) < 0 || fstatvfs(fd[LINKER], &interpreter) < 0) return -1;
    *flags = (struct exec_mount_flags){ .app = app.f_flag & mask, .interpreter = interpreter.f_flag & mask };
    return 0;
}

static int app_process_readback(const struct guest_linkerconfig_generation_start *start,
        const struct guest_apex_runtime_sample *runtime, const struct guest_linkerconfig_app_process_files *files,
        void *scratch, size_t capacity, struct guest_linkerconfig_app_process_sample *out,
        struct guest_linkerconfig_system_section *system) {
    if (!start || !runtime || !files || !out) return guest_readback_refuse(EINVAL);
    if (start->root_fd != files->output.root_fd || start->directory_fd != files->output.directory_fd
            || start->base_fd != files->output.base_fd) return guest_readback_refuse(ESTALE);
    const int fd[] = { files->output.root_fd, files->system_fd, files->system_bin_fd, files->system_etc_fd,
        files->app_process_fd, files->apex_fd, files->runtime_fd, files->runtime_bin_fd, files->linker_fd,
        files->output.directory_fd, files->output.base_fd, files->output.companion_fd };
    for (size_t i = 0; i < sizeof(fd) / sizeof(fd[0]); ++i) {
        if (fd[i] < 0) return guest_readback_refuse(EINVAL);
        for (size_t j = 0; j < i; ++j) {
            if (fd[i] == fd[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fd[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    }

    struct statx before[SLOTS], after[SLOTS], link, after_link;
    struct exec_mount_flags before_flags, after_flags;
    if (snapshot(fd, before, &link) < 0 || check_filesystems(fd, before, runtime) < 0
            || read_mount_flags(fd, &before_flags) < 0) return -1;
    if ((before_flags.app & REQUIRED_MOUNT_FLAGS) != REQUIRED_MOUNT_FLAGS
            || (before_flags.interpreter & REQUIRED_MOUNT_FLAGS) != REQUIRED_MOUNT_FLAGS)
        return guest_readback_refuse(EPERM);
    if (check_elf(fd[APP], &before[APP], 51880, app_sha256) < 0
            || check_elf(fd[LINKER], &before[LINKER], 2640432, linker_sha256) < 0) return -1;
    struct guest_linkerconfig_app_process_sample result = {
        .app_process_inode = before[APP].stx_ino, .linker_inode = before[LINKER].stx_ino,
        .runtime_mount_id = before[RUNTIME].stx_mnt_id,
    };
    struct guest_linkerconfig_system_output_sample generated;
    if (system) {
        if (guest_linkerconfig_generation_readback_system(start, &files->output, scratch, capacity, &generated) < 0)
            return -1;
        result.output = generated.output;
    } else if (guest_linkerconfig_generation_readback(start, &files->output, &result.output) < 0) {
        return -1;
    }
    if (snapshot(fd, after, &after_link) < 0 || read_mount_flags(fd, &after_flags) < 0) return -1;
    if (before_flags.app != after_flags.app || before_flags.interpreter != after_flags.interpreter)
        return guest_readback_refuse(ESTALE);
    for (unsigned i = 0; i < SLOTS; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    if (!guest_readback_same_node(&link, &after_link)) return guest_readback_refuse(ESTALE);
    if (!(before_flags.app & ST_NOEXEC)) result.executable_mounts |= GUEST_LINKERCONFIG_EXEC_APP;
    if (!(before_flags.interpreter & ST_NOEXEC)) result.executable_mounts |= GUEST_LINKERCONFIG_EXEC_INTERPRETER;
    *out = result;
    if (system) *system = generated.system;
    return 0;
}

int guest_linkerconfig_app_process_readback(const struct guest_linkerconfig_generation_start *start,
        const struct guest_apex_runtime_sample *runtime, const struct guest_linkerconfig_app_process_files *files,
        struct guest_linkerconfig_app_process_sample *out) {
    return app_process_readback(start, runtime, files, NULL, 0, out, NULL);
}

int guest_linkerconfig_app_process_readback_system(const struct guest_linkerconfig_generation_start *start,
        const struct guest_apex_runtime_sample *runtime, const struct guest_linkerconfig_app_process_files *files,
        void *scratch, size_t capacity, struct guest_linkerconfig_app_process_system_sample *out) {
    if (!scratch || !capacity || !out) return guest_readback_refuse(EINVAL);
    struct guest_linkerconfig_app_process_system_sample result;
    if (app_process_readback(start, runtime, files, scratch, capacity, &result.entry, &result.system) < 0) return -1;
    *out = result;
    return 0;
}
