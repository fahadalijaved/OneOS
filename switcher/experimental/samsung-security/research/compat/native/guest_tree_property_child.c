#define _GNU_SOURCE
#include "guest_tree_property_child.h"
#include "guest_tree_property_view.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define PROPERTY_NAME "__properties__"
#define TEMPORARY_NAME ".oneos-property-seed"
#define REQUIRED_DEV_FLAGS 0x0eU /* Linux NOSUID | NODEV | NOEXEC */

static int option(const char *list, const char *name) {
    size_t length = strlen(name);
    while (*list) {
        size_t token = strcspn(list, ",");
        if (token == length && !memcmp(list, name, length)) return 1;
        list += token;
        if (*list) ++list;
    }
    return 0;
}

static int same_mount(struct guest_tree_mount_identity a, struct guest_tree_mount_identity b) {
    return a.id == b.id && a.major == b.major && a.minor == b.minor;
}

static int dev_profile(const struct guest_tree_dev_identity *held,
        const struct guest_tree_dev_identity *named, unsigned mode, unsigned links) {
    return held->mount.id && held->ino && same_mount(held->mount, named->mount)
            && held->ino == named->ino && held->mode == mode && named->mode == mode
            && !held->uid && !held->gid && !named->uid && !named->gid
            && held->nlink == links && named->nlink == links
            && held->fs_type == 0x01021994U && named->fs_type == held->fs_type
            && (held->fs_flags & 0x0fU) == REQUIRED_DEV_FLAGS && named->fs_flags == held->fs_flags;
}

int guest_tree_dev_roles_check_seeded(const struct gpv_mount_row *rows, size_t count,
        uint64_t root_mount_id, const struct guest_tree_seeded_dev_sample *sample) {
    if (!rows || !count || count > GPV_MOUNTINFO_MAX_ROWS || !root_mount_id || !sample) return -1;
    const struct guest_tree_dev_sample *skel = &sample->skeleton;
    const struct guest_tree_dev_identity *dev = &skel->dev, *socket = &skel->socket_dir;
    const struct guest_tree_dev_identity *property = &sample->property;
    if (!dev_profile(dev, &skel->reopened_dev, 0040755U, 4)
            || !dev_profile(socket, &skel->reopened_socket, 0040755U, 2)
            || !dev_profile(property, &sample->reopened_property, 0040500U, 2)
            || !same_mount(dev->mount, socket->mount) || !same_mount(dev->mount, property->mount)
            || dev->fs_flags != socket->fs_flags || dev->fs_flags != property->fs_flags
            || dev->ino == socket->ino || dev->ino == property->ino || socket->ino == property->ino) return -1;
    const struct gpv_mount_row *root = gpv_mount_by_id(rows, count, root_mount_id);
    const struct gpv_mount_row *row = gpv_mount_by_id(rows, count, dev->mount.id);
    if (!root || !row || root == row || strcmp(root->point, GUEST_TREE_TARGET_PATH)
            || root->shared || root->master || root->propagate || root->unbindable
            || !option(root->options, "ro") || !option(root->options, "nosuid") || !option(root->options, "nodev")
            || row->parent != root_mount_id || row->major != dev->mount.major || row->minor != dev->mount.minor
            || strcmp(row->point, GUEST_TREE_DEV_PATH) || strcmp(row->root, "/")
            || strcmp(row->type, "tmpfs") || strcmp(row->source, GUEST_TREE_DEV_SOURCE)
            || row->shared || row->master || row->propagate || row->unbindable
            || !option(row->options, "rw") || !option(row->super_options, "rw")
            || !option(row->options, "nosuid") || !option(row->options, "nodev") || !option(row->options, "noexec"))
        return -1;
    const size_t prefix = sizeof(GUEST_TREE_DEV_PATH) - 1;
    for (size_t i = 0; i < count; ++i) {
        const struct gpv_mount_row *other = &rows[i];
        if (other == row) continue;
        if (other->parent == row->id || (other->major == row->major && other->minor == row->minor)
            || (!strncmp(other->point, GUEST_TREE_DEV_PATH, prefix)
                && (other->point[prefix] == '\0' || other->point[prefix] == '/'))) return -1;
    }
    return 0;
}

#define DIRECTORY (O_PATH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
#define READING (O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC)
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define MASK (STATX_TYPE | STATX_MODE | STATX_UID | STATX_GID | STATX_NLINK | STATX_INO \
              | STATX_MNT_ID | STATX_SIZE | STATX_MTIME | STATX_CTIME)

static const char *const property_files[GTP_SEED_COUNT] = {
    "property_info", "u:object_r:build_prop:s0", "u:object_r:default_prop:s0", "u:object_r:vndk_prop:s0", "properties_serial",
};

struct guest_tree_property_child {
    pid_t child;
    struct gtc_child_inputs input;
    struct gtc_child_view view;
    int witnesses[GTR_WITNESSES], seeds[GTP_SEED_COUNT], property_fd;
    struct statx root, dev, socket, property, files[GTP_SEED_COUNT];
    int ready, closed, error;
};

static struct guest_tree_property_child one;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int hold(struct guest_tree_property_child *owner, int error) {
    if (!owner->error) owner->error = error ? error : EIO;
    owner->ready = 0;
    return refuse(owner->error);
}

static void close_local(struct guest_tree_property_child *owner, int fd) {
    int saved = errno;
    if (fd >= 0 && close(fd) < 0) (void)hold(owner, errno);
    errno = saved;
}

static int sample(int fd, const char *name, struct statx *out) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), MASK, out) < 0) return -1;
    return (out->stx_mask & MASK) == MASK && out->stx_ino && out->stx_mnt_id ? 0 : refuse(EXDEV);
}

static struct guest_tree_mount_identity mount_of(const struct statx *out) {
    return (struct guest_tree_mount_identity){out->stx_mnt_id, out->stx_dev_major, out->stx_dev_minor};
}

static int same_inode(const struct statx *a, const struct statx *b) {
    return a->stx_dev_major == b->stx_dev_major && a->stx_dev_minor == b->stx_dev_minor && a->stx_ino == b->stx_ino;
}

static int same_object(const struct statx *a, const struct statx *b) {
    return same_inode(a, b) && a->stx_mnt_id == b->stx_mnt_id;
}

static int stable(const struct statx *a, const struct statx *b) {
    return same_object(a, b) && a->stx_mode == b->stx_mode && a->stx_uid == b->stx_uid
        && a->stx_gid == b->stx_gid && a->stx_size == b->stx_size && a->stx_nlink == b->stx_nlink
        && a->stx_mtime.tv_sec == b->stx_mtime.tv_sec && a->stx_mtime.tv_nsec == b->stx_mtime.tv_nsec
        && a->stx_ctime.tv_sec == b->stx_ctime.tv_sec && a->stx_ctime.tv_nsec == b->stx_ctime.tv_nsec;
}

static int root_process(pid_t parent) {
    return parent > 1 && getpid() != parent && getpid() == gettid() && getppid() == parent
        && !getuid() && !geteuid() && !getegid();
}

static int namespace_id(int fd, struct stat *id) {
    struct statfs fs;
    if (fstatfs(fd, &fs) < 0 || fstat(fd, id) < 0) return -1;
    if ((unsigned long)fs.f_type != NSFS_MAGIC || !id->st_ino) return refuse(EXDEV);
    int type = ioctl(fd, NS_GET_NSTYPE);
    if (type < 0) return -1;
    return type == CLONE_NEWNS ? 0 : refuse(EXDEV);
}

static int proc_type(const char *path, struct statx *proc) {
    struct statfs fs;
    if (statfs(path, &fs) < 0 || sample(AT_FDCWD, path, proc) < 0) return -1;
    return (unsigned long)fs.f_type == PROC_SUPER_MAGIC && S_ISDIR(proc->stx_mode) ? 0 : refuse(EXDEV);
}

static int current_namespace(struct guest_tree_property_child *owner) {
    struct statx proc, link;
    struct stat initial, actual, named;
    if (!root_process(owner->input.parent)) return refuse(EPERM);
    if (proc_type("/proc", &proc) < 0 || sample(AT_FDCWD, "/proc/self/ns/mnt", &link) < 0
        || namespace_id(owner->witnesses[GTC_PARENT_NAMESPACE], &initial) < 0
        || namespace_id(owner->view.rights[GTC_NAMESPACE], &actual) < 0) return -1;
    if (!S_ISLNK(link.stx_mode) || !same_mount(mount_of(&proc), mount_of(&link))
        || (initial.st_dev == actual.st_dev && initial.st_ino == actual.st_ino)
        || owner->view.observation.namespace_dev != (uint64_t)actual.st_dev
        || owner->view.observation.namespace_inode != (uint64_t)actual.st_ino) return refuse(EXDEV);
    int fd = open("/proc/self/ns/mnt", O_RDONLY | O_CLOEXEC);
    if (fd < 0) return -1;
    int result = namespace_id(fd, &named);
    if (!result && (actual.st_dev != named.st_dev || actual.st_ino != named.st_ino)) result = refuse(EXDEV);
    close_local(owner, fd);
    return owner->error ? refuse(owner->error) : result;
}

static int disjoint_view(const struct gtc_child_inputs *input, const struct gtc_child_view *view) {
    for (size_t i = 0; i < GTR_VIEW_RIGHTS; ++i) {
        int fd = view->rights[i];
        int flags = fd < 0 ? -1 : fcntl(fd, F_GETFD);
        if (flags < 0 || !(flags & FD_CLOEXEC)) return refuse(EBADF);
        for (size_t j = 0; j < i; ++j)
            if (fd == view->rights[j]) return refuse(EINVAL);
        for (size_t j = 0; j < GTR_WITNESSES; ++j)
            if (fd == input->witnesses[j]) return refuse(EINVAL);
    }
    return 0;
}

static int claim_seeds(struct guest_tree_property_child *owner, int seeds[GTP_SEED_COUNT]) {
    struct stat files[GTP_SEED_COUNT];
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        if (seeds[i] < 0) return refuse(EBADF);
        for (size_t j = 0; j < GTR_VIEW_RIGHTS; ++j)
            if (seeds[i] == owner->view.rights[j]) return refuse(EINVAL);
        for (size_t j = 0; j < GTR_WITNESSES; ++j)
            if (seeds[i] == owner->witnesses[j]) return refuse(EINVAL);
        int descriptor = fcntl(seeds[i], F_GETFD), flags = fcntl(seeds[i], F_GETFL);
        if (descriptor < 0 || flags < 0 || fstat(seeds[i], &files[i]) < 0) return -1;
        if (!(descriptor & FD_CLOEXEC) || (flags & (O_ACCMODE | O_PATH)) != O_RDONLY
            || !S_ISREG(files[i].st_mode) || !files[i].st_ino) return refuse(EXDEV);
        for (size_t j = 0; j < i; ++j)
            if (files[i].st_dev == files[j].st_dev && files[i].st_ino == files[j].st_ino) return refuse(EINVAL);
    }
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        owner->seeds[i] = seeds[i];
        seeds[i] = -1;
    }
    return 0;
}

static int root_device(struct guest_tree_property_child *owner, int initial) {
    const int *rights = owner->view.rights;
    struct statx root, named, source, dev, socket;
    if (sample(rights[GTC_GUEST_ROOT], "", &root) < 0 || sample(AT_FDCWD, GUEST_TREE_TARGET_PATH, &named) < 0
        || sample(owner->witnesses[GTC_TREE], "", &source) < 0
        || sample(rights[GTC_DEV], "", &dev) < 0 || sample(rights[GTC_SOCKET], "", &socket) < 0) return -1;
    if (!S_ISDIR(root.stx_mode) || !S_ISDIR(source.stx_mode) || !S_ISDIR(dev.stx_mode) || !S_ISDIR(socket.stx_mode)
        || !same_object(&root, &named) || !same_inode(&root, &source) || root.stx_mnt_id == source.stx_mnt_id
        || owner->view.observation.mounts[GTC_GUEST_ROOT] != root.stx_mnt_id
        || owner->view.observation.mounts[GTC_DEV] != dev.stx_mnt_id
        || owner->view.observation.mounts[GTC_SOCKET] != socket.stx_mnt_id
        || !same_mount(mount_of(&dev), mount_of(&socket)) || same_inode(&dev, &socket)) return refuse(EXDEV);
    if (initial) { owner->root = root; owner->dev = dev; owner->socket = socket; }
    else if (!same_object(&root, &owner->root) || !same_object(&dev, &owner->dev)
             || !same_object(&socket, &owner->socket)) return refuse(ESTALE);
    return 0;
}

static int dev_identity(int fd, struct guest_tree_dev_identity *out) {
    struct statx id;
    struct statfs fs;
    if (sample(fd, "", &id) < 0 || fstatfs(fd, &fs) < 0) return -1;
    *out = (struct guest_tree_dev_identity){mount_of(&id), id.stx_ino, id.stx_nlink,
        (unsigned long)fs.f_type, fs.f_flags, id.stx_mode, id.stx_uid, id.stx_gid};
    return 0;
}

static int mount_rows(struct guest_tree_property_child *owner, struct gpv_mount_row *rows, size_t *count) {
    size_t used = 0;
    int result = -1;
    const size_t limit = GPV_MOUNTINFO_MAX_BYTES + 1U;
    char *text = malloc(limit);
    if (!text) return -1;
    struct statx proc, file;
    struct statfs fs;
    int fd = open("/proc/self/mountinfo", READING);
    if (fd < 0 || fstatfs(fd, &fs) < 0 || proc_type("/proc", &proc) < 0 || sample(fd, "", &file) < 0) goto done;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || !S_ISREG(file.stx_mode)
        || !same_mount(mount_of(&proc), mount_of(&file))) { errno = EXDEV; goto done; }
    while (used < limit) {
        ssize_t length = read(fd, text + used, limit - used);
        if (length < 0) goto done;
        if (!length) break;
        used += (size_t)length;
    }
    result = gpv_parse_mountinfo(text, used, rows, GPV_MOUNTINFO_MAX_ROWS, count) == GPV_OK ? 0 : refuse(EPROTO);
done:
    close_local(owner, fd);
    free(text);
    return owner->error ? refuse(owner->error) : result;
}

static int shape(struct guest_tree_property_child *owner, int base, const char *const *names, size_t count) {
    struct statx held, reopened;
    int result = -1;
    int fd = openat(base, ".", READING | O_DIRECTORY);
    if (fd < 0 || sample(base, "", &held) < 0 || sample(fd, "", &reopened) < 0) goto done;
    if (!same_object(&held, &reopened)) { errno = ESTALE; goto done; }
    DIR *dir = fdopendir(fd);
    if (!dir) goto done;
    fd = -1;
    unsigned seen = 0;
    for (;;) {
        errno = 0;
        const struct dirent *entry = readdir(dir);
        if (!entry) {
            if (!errno) result = seen == ((1U << (count + 2)) - 1U) ? 0 : refuse(ESTALE);
            break;
        }
        unsigned bit = 0;
        if (!strcmp(entry->d_name, ".")) bit = 1U;
        else if (!strcmp(entry->d_name, "..")) bit = 2U;
        else for (size_t i = 0; i < count; ++i)
            if (!strcmp(entry->d_name, names[i])) { bit = 1U << (i + 2); break; }
        if (!bit || (seen & bit)) { errno = ESTALE; break; }
        seen |= bit;
    }
    int saved = errno;
    if (closedir(dir) < 0) (void)hold(owner, errno);
    errno = saved;
done:
    close_local(owner, fd);
    return owner->error ? refuse(owner->error) : result;
}

static int property_objects(struct guest_tree_property_child *owner, int dir, int initial) {
    struct statx property, named;
    if (sample(owner->property_fd, "", &property) < 0 || sample(dir, "", &named) < 0) return -1;
    if (!stable(&property, &named) || (!initial && !stable(&property, &owner->property))) return refuse(ESTALE);
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        struct statx value;
        if (sample(dir, property_files[i], &value) < 0) return -1;
        const uint64_t bytes = i == GTP_SEED_INFO ? 171544U : GUEST_TREE_PROP_AREA_BYTES;
        if (value.stx_mode != (S_IFREG | 0444) || value.stx_uid || value.stx_gid || value.stx_nlink != 1
            || value.stx_size != bytes || !same_mount(mount_of(&property), mount_of(&value))
            || (!initial && !stable(&value, &owner->files[i]))) return refuse(ESTALE);
        for (size_t j = 0; j < i; ++j)
            if (same_inode(&value, &owner->files[j])) return refuse(EXDEV);
        if (initial) owner->files[i] = value;
    }
    if (initial) owner->property = property;
    return 0;
}

static int named_object(int base, const char *name, const struct statx *expected) {
    struct statx actual;
    if (sample(base, name, &actual) < 0) return -1;
    return same_object(&actual, expected) ? 0 : refuse(ESTALE);
}

static int current_property(struct guest_tree_property_child *owner, int initial) {
    const int *rights = owner->view.rights;
    static const char *const dev_names[] = {"socket", PROPERTY_NAME};
    struct guest_tree_seeded_dev_sample view;
    struct statx inherited, absent;
    struct gpv_mount_row *rows = NULL;
    int dev = -1, socket = -1, property = -1, result = -1;
    if (current_namespace(owner) < 0 || root_device(owner, 0) < 0) return -1;
    dev = openat(rights[GTC_GUEST_ROOT], "dev", DIRECTORY);
    if (dev < 0) goto done;
    socket = openat(dev, "socket", DIRECTORY);
    property = openat(dev, PROPERTY_NAME, DIRECTORY);
    if (socket < 0 || property < 0 || sample(rights[GTC_INHERITED_ROOT], "dev", &inherited) < 0) goto done;
    if (!S_ISDIR(inherited.stx_mode) || (inherited.stx_dev_major == owner->dev.stx_dev_major
        && inherited.stx_dev_minor == owner->dev.stx_dev_minor)) { errno = EXDEV; goto done; }
    if (statx(dev, TEMPORARY_NAME, LOOKUP, STATX_TYPE, &absent) == 0) { errno = EEXIST; goto done; }
    if (errno != ENOENT) goto done;
    if (dev_identity(rights[GTC_DEV], &view.skeleton.dev) < 0 || dev_identity(rights[GTC_SOCKET], &view.skeleton.socket_dir) < 0
        || dev_identity(dev, &view.skeleton.reopened_dev) < 0 || dev_identity(socket, &view.skeleton.reopened_socket) < 0
        || dev_identity(owner->property_fd, &view.property) < 0 || dev_identity(property, &view.reopened_property) < 0) goto done;
    size_t count;
    rows = malloc(GPV_MOUNTINFO_MAX_ROWS * sizeof(*rows));
    if (!rows || mount_rows(owner, rows, &count) < 0) goto done;
    if (guest_tree_dev_roles_check_seeded(rows, count, owner->root.stx_mnt_id, &view) < 0) { errno = EXDEV; goto done; }
    const struct gpv_mount_row *root = gpv_mount_by_id(rows, count, owner->root.stx_mnt_id);
    if (root->major != owner->root.stx_dev_major || root->minor != owner->root.stx_dev_minor) {
        errno = EXDEV;
        goto done;
    }
    if (shape(owner, dev, dev_names, 2) < 0 || shape(owner, socket, NULL, 0) < 0
        || shape(owner, property, property_files, GTP_SEED_COUNT) < 0 || property_objects(owner, property, initial) < 0
        || named_object(rights[GTC_GUEST_ROOT], "dev", &owner->dev) < 0
        || named_object(dev, "socket", &owner->socket) < 0
        || named_object(dev, PROPERTY_NAME, &owner->property) < 0
        || current_namespace(owner) < 0 || root_device(owner, 0) < 0) goto done;
    result = 0;
done:
    free(rows);
    close_local(owner, property);
    close_local(owner, socket);
    close_local(owner, dev);
    return owner->error ? refuse(owner->error) : result;
}

int guest_tree_property_child_begin(const struct gtc_child_inputs *input, const struct gtc_child_view *view,
        int seeds[GTP_SEED_COUNT], struct guest_tree_property_child **out) {
    if (!input || !input->witnesses || !view || !seeds || !out || *out) return refuse(EINVAL);
    if (!root_process(input->parent)) return refuse(EPERM);
    if (one.child) return refuse(EALREADY);
    one.child = getpid();
    one.input = *input;
    one.view = *view;
    memcpy(one.witnesses, input->witnesses, sizeof(one.witnesses));
    one.input.witnesses = one.witnesses;
    one.property_fd = -1;
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) one.seeds[i] = -1;
    *out = &one;
    if (disjoint_view(input, view) < 0 || current_namespace(&one) < 0 || root_device(&one, 1) < 0
        || claim_seeds(&one, seeds) < 0) return -1;
    int result = guest_tree_stage_property_seed(&one.input, &one.view, one.seeds, &one.property_fd);
    if (result != 0) return hold(&one, result > 0 ? EPROTO : errno);
    if (one.property_fd < 0) return hold(&one, EPROTO);
    for (size_t i = 0; i < GTR_VIEW_RIGHTS; ++i)
        if (one.property_fd == one.view.rights[i]) return hold(&one, EPROTO);
    for (size_t i = 0; i < GTR_WITNESSES; ++i)
        if (one.property_fd == one.witnesses[i]) return hold(&one, EPROTO);
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i)
        if (one.property_fd == one.seeds[i]) return hold(&one, EPROTO);
    int descriptor = fcntl(one.property_fd, F_GETFD), flags = fcntl(one.property_fd, F_GETFL);
    if (descriptor < 0 || flags < 0) return hold(&one, errno);
    if (!(descriptor & FD_CLOEXEC) || !(flags & O_PATH)) return hold(&one, EPROTO);
    if (current_property(&one, 1) < 0) return hold(&one, errno);
    one.ready = 1;
    return 0;
}

int guest_tree_property_child_borrow(struct guest_tree_property_child *owner, int *directory_fd) {
    if (owner != &one || owner->child != getpid() || !directory_fd || *directory_fd != -1) return refuse(EINVAL);
    if (!root_process(owner->input.parent)) return refuse(EPERM);
    if (!owner->ready) return refuse(owner->error ? owner->error : EBUSY);
    if (current_property(owner, 0) < 0) return hold(owner, errno);
    *directory_fd = owner->property_fd;
    return 0;
}

int guest_tree_property_child_close(struct guest_tree_property_child *owner) {
    if (owner != &one || owner->child != getpid()) return refuse(EINVAL);
    if (!root_process(owner->input.parent)) return refuse(EPERM);
    if (owner->error) return refuse(owner->error);
    if (owner->closed) return 0;
    if (owner->ready && current_property(owner, 0) < 0) return hold(owner, errno);
    owner->ready = 0;
    close_local(owner, owner->property_fd);
    owner->property_fd = -1;
    if (owner->error) return refuse(owner->error);
    for (size_t i = GTP_SEED_COUNT; i; --i) {
        close_local(owner, owner->seeds[i - 1]);
        owner->seeds[i - 1] = -1;
        if (owner->error) return refuse(owner->error);
    }
    owner->closed = 1;
    return 0;
}
