#define _GNU_SOURCE
#include "guest_native_early_loader.h"

#include "guest_native_exec_profile.h"
#include "guest_readback_identity.h"

#include <string.h>

enum { ENV_MAX_ENTRIES = 128, ENV_MAX_BYTES = 128 * 1024 };

struct path_sample {
    struct statx directories[4];
    size_t count;
    struct statx output_directory, base;
};

static int check_environment(const char *const *envp, size_t count) {
    if (!envp) return guest_readback_refuse(EINVAL);
    if (count > ENV_MAX_ENTRIES) return guest_readback_refuse(EFBIG);
    if (envp[count]) return guest_readback_refuse(EINVAL);
    size_t budget = ENV_MAX_BYTES;
    for (size_t i = 0; i < count; ++i) {
        const char *entry = envp[i];
        if (!entry) return guest_readback_refuse(EINVAL);
        size_t length = 0;
        while (length < budget && entry[length]) ++length;
        if (length == budget) return guest_readback_refuse(EFBIG);
        budget -= length + 1;
        const char *separator = memchr(entry, '=', length);
        if (!separator || separator == entry) return guest_readback_refuse(EPROTO);
        if (separator - entry >= 3 && !memcmp(entry, "LD_", 3)) return guest_readback_refuse(EPERM);
    }
    return 0;
}

static int absent(int parent, const char *name) {
    struct statx entry;
    if (guest_readback_stat(parent, name, &entry) == 0) return guest_readback_refuse(EEXIST);
    return errno == ENOENT ? 0 : -1;
}

static int joined_directory(int parent, const char *name, int fd, struct statx *directory) {
    if (fd < 0) return guest_readback_refuse(EINVAL);
    int flags = fcntl(fd, F_GETFD);
    if (flags < 0) return -1;
    if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    struct statx named;
    if (guest_readback_stat(fd, "", directory) < 0 || guest_readback_stat(parent, name, &named) < 0) return -1;
    if (!guest_readback_same_node(directory, &named)) return guest_readback_refuse(ESTALE);
    return S_ISDIR(directory->stx_mode) ? 0 : guest_readback_refuse(ENOTDIR);
}

static int same_generation_mount(const struct guest_linkerconfig_generation_node *start, const struct statx *now) {
    return start->mount_id == now->stx_mnt_id && start->device_major == now->stx_dev_major
            && start->device_minor == now->stx_dev_minor;
}

static int same_generation_object(const struct guest_linkerconfig_generation_node *start, const struct statx *now) {
    return same_generation_mount(start, now) && start->inode == now->stx_ino && start->mode == now->stx_mode
            && start->uid == now->stx_uid && start->gid == now->stx_gid;
}

static int sample_base(const struct guest_linkerconfig_generation_start *start, struct statx *base) {
    struct statx named;
    if (guest_readback_stat(start->base_fd, "", base) < 0
            || guest_readback_stat(start->directory_fd, "ld.config.txt", &named) < 0) return -1;
    if (!guest_readback_same_node(base, &named) || !same_generation_object(&start->base, base)
            || base->stx_size != 1 || base->stx_nlink != 1) return guest_readback_refuse(ESTALE);
    return 0;
}

static int sample_bootstrap(const int *fd, struct path_sample *paths) {
    struct statx *lib64 = &paths->directories[2], *bootstrap = &paths->directories[3];
    if (joined_directory(fd[GNX_SYSTEM], "lib64", fd[GNX_SYSTEM_LIB64], lib64) < 0
            || joined_directory(fd[GNX_SYSTEM_LIB64], "bootstrap", fd[GNX_SYSTEM_BOOTSTRAP_LIB64], bootstrap) < 0)
        return -1;
    if (!guest_readback_same_mount(&paths->directories[0], lib64) || !guest_readback_same_mount(lib64, bootstrap))
        return guest_readback_refuse(EXDEV);
    for (size_t i = 0; i < sizeof(gnx_bootstrap_files) / sizeof(gnx_bootstrap_files[0]); ++i) {
        const struct guest_native_exec_pin *pin = &gnx_bootstrap_files[i];
        if (pin->parent == GNX_SYSTEM_LIB64 && absent(fd[GNX_SYSTEM_BOOTSTRAP_LIB64], pin->name) < 0) return -1;
    }
    paths->count = 4;
    return 0;
}

static int sample_runtime_override(const struct guest_native_early_loader_view *view,
        const struct guest_linkerconfig_generation_start *start, struct path_sample *paths) {
    static const char name[] = "com.android.runtime";
    if (view->runtime_config_fd == -1) return absent(start->directory_fd, name);
    struct statx *runtime = &paths->directories[2];
    if (joined_directory(start->directory_fd, name, view->runtime_config_fd, runtime) < 0) return -1;
    if (!same_generation_mount(&start->directory, runtime) || start->directory.inode == runtime->stx_ino)
        return guest_readback_refuse(EXDEV);
    if (absent(view->runtime_config_fd, "ld.config.txt") < 0) return -1;
    paths->count = 3;
    return 0;
}

static int sample_paths(enum guest_native_exec_phase phase, const struct guest_native_early_loader_view *view,
        const struct guest_linkerconfig_generation_start *start, struct path_sample *paths) {
    const int *fd = view->placement->dirs;
    struct statx *system = &paths->directories[0], *etc = &paths->directories[1];
    if (start->root.mount_id != view->placement->carrier_mount_id) return guest_readback_refuse(EXDEV);
    if (joined_directory(fd[GNX_ROOT], "system", fd[GNX_SYSTEM], system) < 0
            || joined_directory(fd[GNX_SYSTEM], "etc", view->system_etc_fd, etc) < 0
            || joined_directory(fd[GNX_ROOT], "linkerconfig", start->directory_fd, &paths->output_directory) < 0)
        return -1;
    if (!same_generation_mount(&start->root, system) || !guest_readback_same_mount(system, etc))
        return guest_readback_refuse(EXDEV);
    if (!same_generation_object(&start->directory, &paths->output_directory)) return guest_readback_refuse(ESTALE);
    if (absent(view->system_etc_fd, "ld.config.arm64.txt") < 0) return -1;
    paths->count = 2;
    int result = phase == GUEST_NATIVE_EXEC_APEXD_BOOTSTRAP ? sample_bootstrap(fd, paths)
            : sample_runtime_override(view, start, paths);
    return result < 0 ? -1 : sample_base(start, &paths->base);
}

static int same_generation_node(const struct guest_linkerconfig_generation_node *a,
        const struct guest_linkerconfig_generation_node *b) {
    return a->mount_id == b->mount_id && a->inode == b->inode && a->device_major == b->device_major
            && a->device_minor == b->device_minor && a->mode == b->mode && a->uid == b->uid && a->gid == b->gid;
}

static int same_baseline(const struct guest_linkerconfig_generation_start *a,
        const struct guest_linkerconfig_generation_start *b) {
    return a->root_fd == b->root_fd && a->directory_fd == b->directory_fd && a->base_fd == b->base_fd
            && same_generation_node(&a->root, &b->root) && same_generation_node(&a->directory, &b->directory)
            && same_generation_node(&a->base, &b->base);
}

int guest_native_early_loader_readback(enum guest_native_exec_phase phase,
        const struct guest_native_early_loader_view *view, struct guest_native_early_loader_sample *out) {
    if (!view || !view->placement || !out) return guest_readback_refuse(EINVAL);
    if (phase != GUEST_NATIVE_EXEC_APEXD_BOOTSTRAP && phase != GUEST_NATIVE_EXEC_LINKERCONFIG_FIRST)
        return guest_readback_refuse(EINVAL);
    if (phase == GUEST_NATIVE_EXEC_LINKERCONFIG_FIRST && view->runtime_config_fd < -1)
        return guest_readback_refuse(EINVAL);
    if (check_environment(view->envp, view->env_count) < 0) return -1;

    int root = view->placement->dirs[GNX_ROOT];
    int directory = view->output_directory_fd, base = view->output_base_fd;
    struct guest_native_early_loader_sample result;
    struct guest_linkerconfig_generation_start after;
    struct path_sample before_paths, after_paths;
    if (guest_linkerconfig_generation_begin(root, directory, base, &result.baseline) < 0
            || sample_paths(phase, view, &result.baseline, &before_paths) < 0
            || guest_native_exec_placement_readback(phase, view->placement, &result.placement) < 0
            || guest_linkerconfig_generation_begin(root, directory, base, &after) < 0
            || sample_paths(phase, view, &after, &after_paths) < 0) return -1;
    if (!same_baseline(&result.baseline, &after) || before_paths.count != after_paths.count
            || !guest_readback_same_node(&before_paths.output_directory, &after_paths.output_directory)
            || !guest_readback_same_node(&before_paths.base, &after_paths.base)) return guest_readback_refuse(ESTALE);
    for (size_t i = 0; i < before_paths.count; ++i) {
        if (!guest_readback_same_node(&before_paths.directories[i], &after_paths.directories[i]))
            return guest_readback_refuse(ESTALE);
    }
    *out = result;
    return 0;
}
