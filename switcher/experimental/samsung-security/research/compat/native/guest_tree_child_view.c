#define _GNU_SOURCE
#include "guest_tree_child_view.h"

#include "guest_tree_prepare_root.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define PRIVATE_DATA GUEST_TREE_DATA_PATH
#define ROOT_PATH GUEST_TREE_TARGET_PATH
#define TREE_PATH GUEST_TREE_SOURCE_PATH
#define O_DIR (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define TMPFS_FLAGS (MS_NOSUID | MS_NODEV | MS_NOEXEC)
#define ROOT_TMPFS "mode=0700,uid=0,gid=0,size=1048576,nr_inodes=64"
#define DEV_TMPFS "mode=0755,uid=0,gid=0,size=1048576,nr_inodes=64"

struct mount_sample {
    struct guest_tree_mount_scratch scratch;
    size_t count;
};

struct peer_groups {
    uint64_t *ids;
    size_t count;
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int current_parent(const struct gtc_child_inputs *input) {
    return getppid() == input->parent ? 0 : refuse(ECHILD);
}

static int directory_stat(int fd, struct stat *stat) {
    if (fd < 0) return refuse(EBADF);
    if (fstat(fd, stat) < 0) return -1;
    return S_ISDIR(stat->st_mode) ? 0 : refuse(ENOTDIR);
}

static int same_node(const struct stat *a, const struct stat *b) {
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino;
}

static int same_directory(int left, int right) {
    struct stat a, b;
    if (directory_stat(left, &a) < 0 || directory_stat(right, &b) < 0) return -1;
    return same_node(&a, &b) ? 0 : refuse(EXDEV);
}

static int namespace_identity(int fd, struct stat *identity) {
    struct statfs fs;
    if (fd < 0) return refuse(EBADF);
    if (fstat(fd, identity) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int named_namespace(int fd, struct stat *identity) {
    struct stat current;
    if (namespace_identity(fd, identity) < 0 || stat("/proc/self/ns/mnt", &current) < 0) return -1;
    return same_node(identity, &current) ? 0 : refuse(EXDEV);
}

static int walk(int base, const char *relative) {
    int current = fcntl(base, F_DUPFD_CLOEXEC, 3);
    if (current < 0) return -1;
    while (*relative) {
        char component[64];
        size_t length = strcspn(relative, "/");
        if (!length || length >= sizeof(component)) return refuse(EINVAL);
        memcpy(component, relative, length);
        component[length] = '\0';
        if (!strcmp(component, ".") || !strcmp(component, "..")) return refuse(EINVAL);
        int next = openat(current, component, O_DIR);
        int primary = errno;
        if (close(current) < 0 && next >= 0) return -1;
        if (next < 0) return refuse(primary);
        current = next;
        relative += length;
        if (*relative) ++relative;
    }
    return current;
}

static int fd_path(int fd, char path[64]) {
    if (fd < 0) return refuse(EBADF);
    int used = snprintf(path, 64, "/proc/self/fd/%d", fd);
    return used > 0 && used < 64 ? 0 : refuse(EOVERFLOW);
}

static int bind_fds(int source, int target) {
    char src[64], dst[64];
    if (fd_path(source, src) < 0 || fd_path(target, dst) < 0) return -1;
    return mount(src, dst, NULL, MS_BIND, NULL);
}

static int share_fd(int fd) {
    char path[64];
    if (fd_path(fd, path) < 0) return -1;
    return mount(NULL, path, NULL, MS_SHARED, NULL);
}

static int mount_tmpfs(int fd, const char *label, const char *options) {
    char path[64];
    if (fd_path(fd, path) < 0) return -1;
    return mount(label, path, "tmpfs", TMPFS_FLAGS, options);
}

static int sample_mounts(struct mount_sample *sample) {
    const unsigned mask = STATX_TYPE | STATX_MNT_ID;
    const int flags = AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT;
    struct statx proc, file;
    struct statfs fs;
    size_t used = 0;
    int error = 0;
    int fd = open("/proc/self/mountinfo", O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0 || statx(AT_FDCWD, "/proc", flags, mask, &proc) < 0
            || statx(fd, "", flags | AT_EMPTY_PATH, mask, &file) < 0) error = errno;
    else if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || (proc.stx_mask & mask) != mask
            || (file.stx_mask & mask) != mask || !proc.stx_mnt_id || proc.stx_mnt_id != file.stx_mnt_id
            || !S_ISDIR(proc.stx_mode) || !S_ISREG(file.stx_mode)) error = EXDEV;
    while (!error && used < sample->scratch.text_capacity) {
        ssize_t count = read(fd, sample->scratch.text + used, sample->scratch.text_capacity - used);
        if (count < 0) error = errno;
        else if (count == 0) break;
        else used += (size_t)count;
    }
    if (close(fd) < 0 && !error) error = errno;
    if (error) return refuse(error);
    if (!used || used == sample->scratch.text_capacity
            || gpv_parse_mountinfo(sample->scratch.text, used, sample->scratch.rows,
                                   sample->scratch.row_capacity, &sample->count) != GPV_OK) return refuse(EPROTO);
    return 0;
}

static int sample_open(struct mount_sample *sample) {
    sample->scratch.text_capacity = GPV_MOUNTINFO_MAX_BYTES + 1U;
    sample->scratch.row_capacity = GPV_MOUNTINFO_MAX_ROWS;
    sample->scratch.text = malloc(sample->scratch.text_capacity);
    sample->scratch.rows = calloc(sample->scratch.row_capacity, sizeof(*sample->scratch.rows));
    if (!sample->scratch.text || !sample->scratch.rows) return -1;
    return 0;
}

static void sample_free(struct mount_sample *sample) {
    free(sample->scratch.text);
    free(sample->scratch.rows);
}

static int fd_mount(int fd, struct statx *identity) {
    const unsigned mask = STATX_TYPE | STATX_INO | STATX_MNT_ID;
    if (fd < 0) return refuse(EBADF);
    if (statx(fd, "", AT_EMPTY_PATH | AT_NO_AUTOMOUNT | AT_SYMLINK_NOFOLLOW, mask, identity) < 0) return -1;
    if ((identity->stx_mask & mask) != mask || !identity->stx_mnt_id || !S_ISDIR(identity->stx_mode))
        return refuse(EXDEV);
    return 0;
}

static const struct gpv_mount_row *member(const struct mount_sample *sample, int fd) {
    struct statx stat;
    if (fd_mount(fd, &stat) < 0) return NULL;
    const struct gpv_mount_row *row = gpv_mount_by_id(sample->scratch.rows, sample->count, stat.stx_mnt_id);
    if (!row || row->major != stat.stx_dev_major || row->minor != stat.stx_dev_minor) {
        errno = EXDEV;
        return NULL;
    }
    return row;
}

static int same_mount(int left, int right) {
    struct statx a, b;
    if (fd_mount(left, &a) < 0 || fd_mount(right, &b) < 0) return -1;
    return a.stx_mnt_id == b.stx_mnt_id ? 0 : refuse(EXDEV);
}

static int option(const char *options, const char *wanted) {
    size_t length = strlen(wanted);
    while (*options) {
        size_t current = strcspn(options, ",");
        if (current == length && !memcmp(options, wanted, length)) return 1;
        options += current;
        if (*options) ++options;
    }
    return 0;
}

static int private_row(const struct gpv_mount_row *row) {
    return row && !row->shared && !row->master && !row->propagate && !row->unbindable;
}

static int tmpfs_options(const struct gpv_mount_row *row) {
    return row && !strcmp(row->type, "tmpfs") && !strcmp(row->root, "/")
        && option(row->options, "rw") && option(row->options, "nosuid") && option(row->options, "nodev")
        && option(row->options, "noexec") && option(row->super_options, "rw");
}

static int path_at_or_below(const char *path, const char *base) {
    size_t length = strlen(base);
    return !strncmp(path, base, length) && (!path[length] || path[length] == '/');
}

static int absent_submounts(const struct mount_sample *sample, const char *path) {
    for (size_t i = 0; i < sample->count; ++i) {
        if (path_at_or_below(sample->scratch.rows[i].point, path)) return refuse(EXDEV);
    }
    return 0;
}

static int retain_groups(const struct mount_sample *sample, struct peer_groups *groups) {
    groups->ids = malloc(3U * sample->count * sizeof(*groups->ids));
    if (!groups->ids) return -1;
    for (size_t i = 0; i < sample->count; ++i) {
        const struct gpv_mount_row *row = &sample->scratch.rows[i];
        if (row->shared) groups->ids[groups->count++] = row->shared;
        if (row->master) groups->ids[groups->count++] = row->master;
        if (row->propagate) groups->ids[groups->count++] = row->propagate;
    }
    return 0;
}

static int forbidden(const struct peer_groups *original, uint64_t group) {
    for (size_t i = 0; group && i < original->count; ++i) {
        if (original->ids[i] == group) return 1;
    }
    return 0;
}

static int peer_pair(const struct peer_groups *original, const struct mount_sample *current,
                     int native, int guest, const char *native_path, const char *guest_path, uint64_t *group) {
    const struct gpv_mount_row *a = member(current, native);
    const struct gpv_mount_row *b = member(current, guest);
    if (same_directory(native, guest) < 0 || !a || !b || a->id == b->id || !a->shared || a->shared != b->shared
            || a->master || b->master || a->propagate || b->propagate || a->unbindable || b->unbindable
            || forbidden(original, a->shared) || strcmp(a->root, b->root)
            || a->major != b->major || a->minor != b->minor
            || strcmp(a->point, native_path) || strcmp(b->point, guest_path)) return refuse(EXDEV);
    *group = a->shared;
    return 0;
}

static int tmpfs_profile(const struct mount_sample *sample, int fd, int covered, const char *point) {
    struct statfs fs;
    struct statx previous;
    const struct gpv_mount_row *row = member(sample, fd);
    if (!private_row(row)) return refuse(EXDEV);
    if (fd_mount(covered, &previous) < 0 || fstatfs(fd, &fs) < 0) return -1;
    if (row->id == previous.stx_mnt_id || strcmp(row->point, point)
            || (unsigned long)fs.f_type != TMPFS_MAGIC || !tmpfs_options(row)) return refuse(EXDEV);
    return 0;
}

static int mode_0755(int fd) {
    struct stat stat;
    if (directory_stat(fd, &stat) < 0) return -1;
    if (stat.st_uid || stat.st_gid || (stat.st_mode & 07777) != 0755) return refuse(EPERM);
    return 0;
}

static int dev_shape(int fd, int has_socket) {
    int readable = openat(fd, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (readable < 0 || same_directory(fd, readable) < 0 || same_mount(fd, readable) < 0) return -1;
    DIR *directory = fdopendir(readable);
    if (!directory) return -1;
    int error = 0;
    unsigned seen = 0;
    while (!error) {
        errno = 0;
        struct dirent *entry = readdir(directory);
        if (!entry) { error = errno; break; }
        unsigned bit;
        if (!strcmp(entry->d_name, ".")) bit = 1;
        else if (!strcmp(entry->d_name, "..")) bit = 2;
        else if (has_socket && !strcmp(entry->d_name, "socket")) bit = 4;
        else { error = ENOTEMPTY; break; }
        if (seen & bit) { error = EPROTO; break; }
        seen |= bit;
    }
    if (!error && seen != (has_socket ? 7U : 3U)) error = EPROTO;
    if (closedir(directory) < 0 && !error) error = errno;
    return error ? refuse(error) : 0;
}

static int scaffold_root(int inherited_root, struct mount_sample *sample, int *scaffold, int *target) {
    int old_mnt = openat(inherited_root, "mnt", O_DIR);
    if (mount_tmpfs(old_mnt, "gvo-v2-scaffold", ROOT_TMPFS) < 0) return -1;
    int fresh_mnt = openat(inherited_root, "mnt", O_DIR);
    if (sample_mounts(sample) < 0 || tmpfs_profile(sample, fresh_mnt, old_mnt, "/mnt") < 0) return -1;
    int writable_mnt = openat(fresh_mnt, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (writable_mnt < 0 || same_directory(fresh_mnt, writable_mnt) < 0
            || same_mount(fresh_mnt, writable_mnt) < 0 || mkdirat(writable_mnt, "gvi", 0700) < 0) return -1;
    *scaffold = openat(writable_mnt, "gvi", O_DIR);
    if (*scaffold < 0 || same_mount(fresh_mnt, *scaffold) < 0 || mkdirat(*scaffold, "root", 0700) < 0) return -1;
    *target = openat(*scaffold, "root", O_DIR);
    return same_mount(*scaffold, *target);
}

struct peer_view {
    int native, guest;
};

static int make_data_peers(int inherited_root, int tree_root, int source_data, int covered_data,
                           struct peer_view *data) {
    int target = openat(tree_root, "data", O_DIR);
    if (same_mount(tree_root, target) < 0 || bind_fds(source_data, covered_data) < 0) return -1;
    data->native = openat(inherited_root, "data", O_DIR);
    if (same_directory(data->native, source_data) < 0
            || share_fd(data->native) < 0 || bind_fds(data->native, target) < 0) return -1;
    data->guest = openat(tree_root, "data", O_DIR);
    return same_directory(data->native, data->guest);
}

struct alias_view {
    int source, native, guest;
};

static int make_aliases(const struct peer_view *data, struct alias_view *alias) {
    alias->source = walk(data->native, "user/0");
    int target = openat(data->native, "data", O_DIR);
    if (same_mount(data->native, alias->source) < 0 || same_mount(data->native, target) < 0
            || bind_fds(alias->source, target) < 0) return -1;
    alias->native = openat(data->native, "data", O_DIR);
    alias->guest = openat(data->guest, "data", O_DIR);
    if (same_directory(alias->source, alias->native) < 0 || same_directory(alias->source, alias->guest) < 0) return -1;
    return 0;
}

static int make_mirror_peers(int inherited_root, int tree_root, int covered, struct mount_sample *sample,
                             struct peer_view *mirror) {
    int target = openat(tree_root, "data_mirror", O_DIR);
    if (same_mount(tree_root, target) < 0 || mount_tmpfs(covered, "gvo-owned-mirror", ROOT_TMPFS) < 0) return -1;
    mirror->native = openat(inherited_root, "data_mirror", O_DIR);
    if (sample_mounts(sample) < 0 || tmpfs_profile(sample, mirror->native, covered, "/data_mirror") < 0) return -1;
    int writable = openat(mirror->native, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (writable < 0 || same_directory(writable, mirror->native) < 0 || same_mount(writable, mirror->native) < 0
            || mkdirat(writable, "data_ce", 0700) < 0 || mkdirat(writable, "data_de", 0700) < 0
            || share_fd(mirror->native) < 0 || bind_fds(mirror->native, target) < 0) return -1;
    mirror->guest = openat(tree_root, "data_mirror", O_DIR);
    return same_directory(mirror->native, mirror->guest);
}

static int make_dev(int inherited_root, int tree_root, struct mount_sample *sample, int *dev, int *socket) {
    int inherited = openat(inherited_root, "dev", O_DIR);
    int target = openat(tree_root, "dev", O_DIR);
    if (inherited < 0 || mode_0755(target) < 0 || same_mount(tree_root, target) < 0 || dev_shape(target, 0) < 0
            || sample_mounts(sample) < 0 || absent_submounts(sample, ROOT_PATH "/dev") < 0
            || mount_tmpfs(target, "gvo-v3-owned-dev", DEV_TMPFS) < 0) return -1;
    *dev = openat(tree_root, "dev", O_DIR);
    if (mode_0755(*dev) < 0 || sample_mounts(sample) < 0 || tmpfs_profile(sample, *dev, target, ROOT_PATH "/dev") < 0
            || dev_shape(*dev, 0) < 0) return -1;
    int writable = openat(*dev, ".", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (writable < 0 || same_directory(writable, *dev) < 0 || same_mount(writable, *dev) < 0
            || mkdirat(writable, "socket", 0755) < 0) return -1;
    int socket_write = openat(writable, "socket", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (same_mount(socket_write, *dev) < 0 || fchown(socket_write, 0, 0) < 0 || fchmod(socket_write, 0755) < 0) return -1;
    *socket = openat(*dev, "socket", O_DIR);
    int inherited_after = openat(inherited_root, "dev", O_DIR);
    if (same_directory(*socket, socket_write) < 0 || same_mount(*dev, *socket) < 0
            || same_directory(inherited, inherited_after) < 0 || same_mount(inherited, inherited_after) < 0
            || mode_0755(*socket) < 0 || dev_shape(*dev, 1) < 0 || dev_shape(*socket, 0) < 0) return -1;
    struct stat dev_stat, socket_stat;
    if (directory_stat(*dev, &dev_stat) < 0 || directory_stat(*socket, &socket_stat) < 0) return -1;
    if (same_node(&dev_stat, &socket_stat) || dev_stat.st_nlink != 3 || socket_stat.st_nlink != 2) return refuse(EXDEV);
    return 0;
}

static int observe_aliases(const struct peer_groups *original, const struct mount_sample *current,
                           const struct peer_view *data, const struct alias_view *alias,
                           struct gtc_observation *observation) {
    const struct gpv_mount_row *native_data = member(current, data->native);
    const struct gpv_mount_row *guest_data = member(current, data->guest);
    const struct gpv_mount_row *native_alias = member(current, alias->native);
    const struct gpv_mount_row *guest_alias = member(current, alias->guest);
    if (!native_data || !guest_data || !native_alias || !guest_alias
            || same_directory(alias->source, alias->native) < 0 || same_directory(alias->source, alias->guest) < 0
            || native_alias->id == guest_alias->id || native_alias->parent != native_data->id
            || guest_alias->parent != guest_data->id || native_alias->master || guest_alias->master
            || native_alias->propagate || guest_alias->propagate || native_alias->unbindable || guest_alias->unbindable
            || forbidden(original, native_alias->shared) || forbidden(original, guest_alias->shared)
            || strcmp(native_alias->root, guest_alias->root) || native_alias->major != guest_alias->major
            || native_alias->minor != guest_alias->minor || strcmp(native_alias->point, "/data/data")
            || strcmp(guest_alias->point, ROOT_PATH "/data/data")) return refuse(EXDEV);
    observation->alias_native = native_alias->id;
    observation->alias_guest = guest_alias->id;
    observation->guest_data_mount = guest_data->id;
    return 0;
}

static int observe_view(const struct gtc_child_inputs *input, const struct peer_groups *original,
                        struct mount_sample *current, const struct guest_tree_root_preparation *root,
                        const struct peer_view *data, const struct peer_view *mirror,
                        const struct alias_view *alias, struct gtc_child_view *result) {
    struct stat identity;
    int tree = result->rights[GTC_GUEST_ROOT];
    int dev = result->rights[GTC_DEV];
    int socket = result->rights[GTC_SOCKET];
    if (current_parent(input) < 0 || named_namespace(result->rights[GTC_NAMESPACE], &identity) < 0
            || sample_mounts(current) < 0) return -1;
    const struct gpv_mount_row *tree_mount = member(current, tree);
    const struct gpv_mount_row *data_mount = member(current, data->guest);
    const struct gpv_mount_row *mirror_mount = member(current, mirror->guest);
    const struct gpv_mount_row *native_mirror = member(current, mirror->native);
    const struct gpv_mount_row *dev_mount = member(current, dev);
    const struct gpv_mount_row *socket_mount = member(current, socket);
    struct gtc_observation *observation = &result->observation;
    if (!private_row(tree_mount) || tree_mount->id != root->readback.attached.id || strcmp(tree_mount->point, ROOT_PATH)
            || !option(tree_mount->options, "ro") || !option(tree_mount->options, "nosuid")
            || !option(tree_mount->options, "nodev") || same_directory(tree, input->witnesses[GTC_TREE]) < 0
            || same_directory(data->native, input->witnesses[GTC_PRIVATE_DATA]) < 0
            || !data_mount || data_mount->parent != tree_mount->id || !mirror_mount
            || mirror_mount->parent != tree_mount->id || !tmpfs_options(native_mirror)
            || strcmp(native_mirror->source, "gvo-owned-mirror") || !tmpfs_options(dev_mount) || !socket_mount
            || dev_mount->parent != tree_mount->id || dev_mount->id != socket_mount->id
            || dev_mount->id == tree_mount->id || dev_mount->id == data_mount->id || dev_mount->id == mirror_mount->id
            || !private_row(dev_mount) || strcmp(dev_mount->point, ROOT_PATH "/dev")
            || strcmp(dev_mount->source, "gvo-v3-owned-dev")) return refuse(EXDEV);
    if (peer_pair(original, current, data->native, data->guest, "/data", ROOT_PATH "/data",
                  &observation->data_group) < 0
            || peer_pair(original, current, mirror->native, mirror->guest, "/data_mirror", ROOT_PATH "/data_mirror",
                         &observation->mirror_group) < 0
            || observation->data_group == observation->mirror_group
            || observe_aliases(original, current, data, alias, observation) < 0) return refuse(EXDEV);
    observation->guest_mirror_mount = mirror_mount->id;
    observation->namespace_dev = (uint64_t)identity.st_dev;
    observation->namespace_inode = (uint64_t)identity.st_ino;
    for (size_t n = 1; n < GTR_VIEW_RIGHTS; ++n) {
        const struct gpv_mount_row *row = member(current, result->rights[n]);
        if (!row) return -1;
        observation->mounts[n] = row->id;
    }
    return current_parent(input);
}

int guest_tree_prepare_child_view(const struct gtc_child_inputs *input,
                                  struct gtc_child_view *view, void *context) {
    if (!input || !input->witnesses || !view || context || input->parent <= 1) return refuse(EINVAL);
    for (size_t n = 0; n < GTR_VIEW_RIGHTS; ++n) if (view->rights[n] != -1) return refuse(EINVAL);
    struct mount_sample before = {0}, after = {0};
    struct peer_groups inherited = {0};
    struct gtc_child_view actual = {0};
    struct guest_tree_root_preparation prepared = {.attachment = {.clone_fd = -1}, .readback = {.root_fd = -1}};
    struct peer_view data, mirror;
    struct alias_view alias;
    struct stat parent_ns, child_ns, data_stat, host_stat;
    int scaffold, target;
    int result = -1;
    if (current_parent(input) < 0 || named_namespace(input->witnesses[GTC_PARENT_NAMESPACE], &parent_ns) < 0
            || sample_open(&before) < 0 || sample_open(&after) < 0 || sample_mounts(&before) < 0
            || retain_groups(&before, &inherited) < 0 || unshare(CLONE_NEWNS) < 0) goto done;
    actual.rights[GTC_NAMESPACE] = open("/proc/self/ns/mnt", O_RDONLY | O_CLOEXEC);
    if (named_namespace(actual.rights[GTC_NAMESPACE], &child_ns) < 0) goto done;
    if (same_node(&parent_ns, &child_ns)) { errno = EXDEV; goto done; }
    if (current_parent(input) < 0 || mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0
            || sample_mounts(&after) < 0) goto done;
    for (size_t n = 0; n < after.count; ++n) {
        if (!private_row(&after.scratch.rows[n])) { errno = EXDEV; goto done; }
    }
    int root = actual.rights[GTC_INHERITED_ROOT] = open("/", O_DIR);
    if (root < 0) goto done;
    int tree = walk(root, &TREE_PATH[1]);
    int source_data = walk(root, &PRIVATE_DATA[1]);
    int covered_data = openat(root, "data", O_DIR);
    int covered_mirror = openat(root, "data_mirror", O_DIR);
    if (covered_mirror < 0 || same_directory(tree, input->witnesses[GTC_TREE]) < 0
            || same_directory(source_data, input->witnesses[GTC_PRIVATE_DATA]) < 0
            || directory_stat(source_data, &data_stat) < 0 || directory_stat(covered_data, &host_stat) < 0
            || absent_submounts(&after, PRIVATE_DATA) < 0) goto done;
    if (data_stat.st_uid != 1000 || data_stat.st_gid != 1000 || (data_stat.st_mode & 07777) != 0771
            || same_node(&data_stat, &host_stat)) { errno = EXDEV; goto done; }
    if (current_parent(input) < 0 || scaffold_root(root, &after, &scaffold, &target) < 0) goto done;
    struct guest_tree_root_inputs root_input = {.parent_pid = input->parent,
        .parent_namespace_fd = input->witnesses[GTC_PARENT_NAMESPACE], .child_namespace_fd = actual.rights[GTC_NAMESPACE],
        .source_fd = tree, .scaffold_parent_fd = scaffold, .target_fd = target};
    if (guest_tree_prepare_root(&root_input, before.scratch, after.scratch, &prepared) < 0) goto done;
    int guest = actual.rights[GTC_GUEST_ROOT] = prepared.readback.root_fd;
    if (current_parent(input) < 0 || make_data_peers(root, guest, source_data, covered_data, &data) < 0
            || sample_mounts(&after) < 0) goto done;
    uint64_t data_group;
    if (peer_pair(&inherited, &after, data.native, data.guest, "/data", ROOT_PATH "/data", &data_group) < 0
            || current_parent(input) < 0 || make_aliases(&data, &alias) < 0
            || current_parent(input) < 0 || make_mirror_peers(root, guest, covered_mirror, &after, &mirror) < 0
            || current_parent(input) < 0 || make_dev(root, guest, &after, &actual.rights[GTC_DEV],
                                                      &actual.rights[GTC_SOCKET]) < 0) goto done;
    actual.rights[GTC_DATA] = data.native;
    actual.rights[GTC_MIRROR] = mirror.native;
    if (observe_view(input, &inherited, &after, &prepared, &data, &mirror, &alias, &actual) < 0) goto done;
    if (actual.observation.data_group != data_group) { errno = ESTALE; goto done; }
    *view = actual;
    result = 0;
done:
    /* The private child owns even failure-path mount references until GTC's
     * actual process exit. No parent receives incomplete right ownership. */
    sample_free(&after);
    sample_free(&before);
    free(inherited.ids);
    return result;
}
