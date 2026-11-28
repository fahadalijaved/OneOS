#define _GNU_SOURCE
#include "guest_native_early_loader_open.h"

#include "guest_native_exec_profile.h"
#include "guest_readback_identity.h"

#include <unistd.h>

#define COUNT(array) (sizeof(array) / sizeof((array)[0]))
#define DIR_FLAGS (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define FILE_FLAGS (O_RDONLY | O_NOATIME | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC)

enum { MAX_FILES = 33 };
_Static_assert(COUNT(gnx_bootstrap_files) == MAX_FILES && COUNT(gnx_linkerconfig_files) == 8,
        "Unexpected native early-loader roster");

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

static int open_directories(int fds[GNX_DIR_COUNT], int bootstrap) {
    for (int i = GNX_SYSTEM; i < GNX_DIR_COUNT; ++i) {
        if (bootstrap ? i >= GNX_APEX : i == GNX_SYSTEM_BOOTSTRAP_BIN || i == GNX_SYSTEM_BOOTSTRAP_LIB64)
            continue;
        fds[i] = openat(fds[directories[i].parent], directories[i].name, DIR_FLAGS);
        if (fds[i] < 0) return -1;
    }
    return 0;
}

static int open_override(int directory, int *fd) {
    static const char name[] = "com.android.runtime";
    struct statx named, parent, held;
    if (guest_readback_stat(directory, name, &named) < 0) return errno == ENOENT ? 0 : -1;
    if (!S_ISDIR(named.stx_mode)) return guest_readback_refuse(ENOTDIR);
    if (guest_readback_stat(directory, "", &parent) < 0) return -1;
    if (!guest_readback_same_mount(&parent, &named) || parent.stx_ino == named.stx_ino)
        return guest_readback_refuse(EXDEV);
    *fd = openat(directory, name, DIR_FLAGS);
    if (*fd < 0 || guest_readback_stat(*fd, "", &held) < 0) return -1;
    return guest_readback_same_node(&named, &held) ? 0 : guest_readback_refuse(ESTALE);
}

static int open_file(const int dirs[GNX_DIR_COUNT], const struct guest_native_exec_pin *pin, int *fd) {
    int parent_fd = dirs[pin->parent];
    struct statx parent, named, held;
    if (guest_readback_stat(parent_fd, "", &parent) < 0
            || guest_readback_stat(parent_fd, pin->name, &named) < 0) return -1;
    if (!S_ISREG(named.stx_mode) || named.stx_size != pin->bytes
            || !guest_readback_same_mount(&parent, &named)) return guest_readback_refuse(EXDEV);
    *fd = openat(parent_fd, pin->name, FILE_FLAGS);
    if (*fd < 0 || guest_readback_stat(*fd, "", &held) < 0) return -1;
    return guest_readback_same_node(&named, &held) ? 0 : guest_readback_refuse(ESTALE);
}

static int same_node(const struct guest_linkerconfig_generation_node *a,
        const struct guest_linkerconfig_generation_node *b) {
    return a->mount_id == b->mount_id && a->inode == b->inode && a->device_major == b->device_major
            && a->device_minor == b->device_minor && a->mode == b->mode && a->uid == b->uid && a->gid == b->gid;
}

static int same_baseline(const struct guest_linkerconfig_generation_start *a,
        const struct guest_linkerconfig_generation_start *b) {
    return a->root_fd == b->root_fd && a->directory_fd == b->directory_fd && a->base_fd == b->base_fd
            && same_node(&a->root, &b->root) && same_node(&a->directory, &b->directory)
            && same_node(&a->base, &b->base);
}

static void close_owned(int fd, int *primary, int *close_error) {
    if (fd < 0 || close(fd) == 0) return;
    int error = errno ? errno : EIO;
    if (!*close_error) *close_error = error;
    if (!*primary) *primary = error;
}

int guest_native_early_loader_open_readback(enum guest_native_exec_phase phase,
        const struct guest_linkerconfig_generation_start *baseline,
        const struct guest_apex_runtime_sample *runtime, const char *const *envp, size_t env_count,
        struct guest_native_early_loader_sample *out, int *close_error) {
    if (!baseline || !envp || !out || !close_error) return guest_readback_refuse(EINVAL);
    if (*close_error) return guest_readback_refuse(*close_error);
    int bootstrap = phase == GUEST_NATIVE_EXEC_APEXD_BOOTSTRAP;
    if ((!bootstrap && (phase != GUEST_NATIVE_EXEC_LINKERCONFIG_FIRST || !runtime))
            || baseline->root_fd < 0 || baseline->directory_fd < 0 || baseline->base_fd < 0
            || baseline->root_fd == baseline->directory_fd || baseline->root_fd == baseline->base_fd
            || baseline->directory_fd == baseline->base_fd || !baseline->root.mount_id)
        return guest_readback_refuse(EINVAL);
    const int borrowed[] = { baseline->root_fd, baseline->directory_fd, baseline->base_fd };
    for (size_t i = 0; i < COUNT(borrowed); ++i) {
        int flags = fcntl(borrowed[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    }

    const struct guest_native_exec_pin *pins = bootstrap ? gnx_bootstrap_files : gnx_linkerconfig_files;
    size_t count = bootstrap ? COUNT(gnx_bootstrap_files) : COUNT(gnx_linkerconfig_files);
    int files[MAX_FILES];
    for (size_t i = 0; i < count; ++i) files[i] = -1;
    struct guest_native_exec_view placement = {
        .carrier_mount_id = baseline->root.mount_id, .runtime = runtime,
        .file_fds = files, .file_count = count,
    };
    for (int i = GNX_SYSTEM; i < GNX_DIR_COUNT; ++i) placement.dirs[i] = -1;
    placement.dirs[GNX_ROOT] = baseline->root_fd;
    struct guest_native_early_loader_view view = {
        .placement = &placement, .system_etc_fd = -1, .runtime_config_fd = -1,
        .output_directory_fd = baseline->directory_fd, .output_base_fd = baseline->base_fd,
        .envp = envp, .env_count = env_count,
    };
    int primary = 0;
    struct guest_native_early_loader_sample result;
    if (open_directories(placement.dirs, bootstrap) < 0) goto failed;
    view.system_etc_fd = openat(placement.dirs[GNX_SYSTEM], "etc", DIR_FLAGS);
    if (view.system_etc_fd < 0 || (!bootstrap && open_override(baseline->directory_fd, &view.runtime_config_fd) < 0))
        goto failed;
    for (size_t i = 0; i < count; ++i) {
        if (open_file(placement.dirs, &pins[i], &files[i]) < 0) goto failed;
    }
    if (guest_native_early_loader_readback(phase, &view, &result) < 0) goto failed;
    if (!same_baseline(baseline, &result.baseline)) {
        errno = ESTALE;
        goto failed;
    }
    goto done;

failed:
    primary = errno ? errno : EIO;
done:
    for (size_t i = count; i > 0; --i) close_owned(files[i - 1], &primary, close_error);
    close_owned(view.runtime_config_fd, &primary, close_error);
    close_owned(view.system_etc_fd, &primary, close_error);
    for (int i = GNX_DIR_COUNT - 1; i > GNX_ROOT; --i) close_owned(placement.dirs[i], &primary, close_error);
    if (primary) return guest_readback_refuse(primary);
    struct guest_linkerconfig_generation_start after;
    if (guest_linkerconfig_generation_begin(baseline->root_fd, baseline->directory_fd, baseline->base_fd,
            &after) < 0) return -1;
    if (!same_baseline(baseline, &after)) return guest_readback_refuse(ESTALE);
    *out = result;
    return 0;
}
