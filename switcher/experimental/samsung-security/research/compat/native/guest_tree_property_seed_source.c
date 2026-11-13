#define _GNU_SOURCE
#include "guest_tree_property_seed_source.h"
#include "guest_tree_sha256.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

/* Linux UAPI. Older build headers may predate these flags. The kernel must
 * support both, with no weaker fallback. */
#ifndef MFD_NOEXEC_SEAL
#define MFD_NOEXEC_SEAL 0x0008U
#endif
#ifndef F_SEAL_EXEC
#define F_SEAL_EXEC 0x0020
#endif
#define SEALS (F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE | F_SEAL_EXEC)

#define BLOB(role) \
    extern const unsigned char oneos_property_seed_##role[], oneos_property_seed_##role##_end[]
BLOB(info);
BLOB(build);
BLOB(default);
BLOB(vndk);
BLOB(serial);

struct seed_profile {
    const unsigned char *first, *end;
    const char *name, *digest;
    size_t bytes;
};
#define SEED(role, label, size, sha) {oneos_property_seed_##role, oneos_property_seed_##role##_end, label, sha, size}
static const struct seed_profile profiles[GTP_SEED_COUNT] = {
    [GTP_SEED_INFO] = SEED(info, "info", 171544U, "a413051d6516719189ea964efaa7d74954f0d1052fedf066cef8c9a1c813d3e4"),
    [GTP_SEED_BUILD] = SEED(build, "build", 262144U, "b8e9550fd09f0eb599c4fad63645ea4e1f9f9a41c0c4fbbbf93c70bb86591594"),
    [GTP_SEED_DEFAULT] = SEED(default, "default", 262144U, "fe488c213c448d04ef155d14fc822625226da9df080c10b62b4495770d656bcb"),
    [GTP_SEED_VNDK] = SEED(vndk, "vndk", 262144U, "4072c0f7a7e141a6e21b6a68c8ce216cf586293286192b467b5e141d316617ca"),
    [GTP_SEED_SERIAL] = SEED(serial, "serial", 262144U, "f03e29e557ca4610dfa875a44cb091ed8f65df21de01250b28b3c21ce06c4f18"),
};
#undef SEED
#undef BLOB

struct guest_tree_property_seed_source {
    pid_t parent;
    int fds[GTP_SEED_COUNT];
    struct stat identities[GTP_SEED_COUNT];
    int ready, taken, closed, close_error;
};

static struct guest_tree_property_seed_source source;

static int refuse(int error) {
    errno = error;
    return -1;
}

static int process_leader(void) {
    return getpid() == gettid() && !getuid() && !geteuid() && !getegid();
}

static int direct_child(const struct guest_tree_property_seed_source *owner) {
    return owner == &source && owner->parent > 1 && process_leader()
        && getpid() != owner->parent && getppid() == owner->parent;
}

static int same_inode(const struct stat *left, const struct stat *right) {
    return left->st_dev == right->st_dev && left->st_ino == right->st_ino;
}

static void close_cell(struct guest_tree_property_seed_source *owner, int *cell) {
    int fd = *cell, saved = errno;
    *cell = -1;
    if (fd >= 0 && close(fd) < 0 && !owner->close_error) owner->close_error = errno ? errno : EIO;
    errno = saved;
}

static int expected_hash(struct guest_tree_sha256 *hash, const char *expected) {
    static const char hex[] = "0123456789abcdef";
    unsigned char digest[32];
    guest_tree_sha256_final(hash, digest);
    for (size_t i = 0; i < sizeof(digest); ++i)
        if (hex[digest[i] >> 4] != expected[2 * i] || hex[digest[i] & 15] != expected[2 * i + 1])
            return refuse(EBADMSG);
    return 0;
}

static int check_linked_bytes(void) {
    struct guest_tree_sha256 hash;
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        const struct seed_profile *profile = &profiles[i];
        uintptr_t first = (uintptr_t)profile->first, end = (uintptr_t)profile->end;
        if (end < first || end - first != profile->bytes) return refuse(EBADMSG);
        guest_tree_sha256_init(&hash);
        guest_tree_sha256_update(&hash, profile->first, profile->bytes);
        if (expected_hash(&hash, profile->digest) < 0) return -1;
    }
    return 0;
}

static int check_sealed(int fd, size_t bytes, int access, struct stat *identity) {
    int status = fcntl(fd, F_GETFL);
    int descriptor = fcntl(fd, F_GETFD);
    int seals = fcntl(fd, F_GET_SEALS);
    if (status < 0 || descriptor < 0 || seals < 0 || fstat(fd, identity) < 0) return -1;
    if ((status & (O_ACCMODE | O_PATH)) != access || !(descriptor & FD_CLOEXEC) || seals != SEALS
            || identity->st_mode != (S_IFREG | 0400) || identity->st_uid || identity->st_gid
            || identity->st_nlink || !identity->st_ino || identity->st_size != (off_t)bytes)
        return refuse(EXDEV);
    return 0;
}

static int check_payload(int fd, const struct seed_profile *profile) {
    struct guest_tree_sha256 hash;
    unsigned char buffer[4096];
    size_t offset = 0;
    guest_tree_sha256_init(&hash);
    while (offset < profile->bytes) {
        size_t chunk = profile->bytes - offset;
        if (chunk > sizeof(buffer)) chunk = sizeof(buffer);
        ssize_t got = pread(fd, buffer, chunk, (off_t)offset);
        if (got < 0) return -1;
        if (!got || (size_t)got > chunk) return refuse(EIO);
        guest_tree_sha256_update(&hash, buffer, (size_t)got);
        offset += (size_t)got;
    }
    ssize_t tail = pread(fd, buffer, 1, (off_t)offset);
    if (tail < 0) return -1;
    return tail == 0 ? expected_hash(&hash, profile->digest) : refuse(EIO);
}

static int seal(int writer, const struct seed_profile *profile) {
    size_t offset = 0;
    while (offset < profile->bytes) {
        ssize_t used = write(writer, profile->first + offset, profile->bytes - offset);
        if (used < 0) return -1;
        if (!used || (size_t)used > profile->bytes - offset) return refuse(EIO);
        offset += (size_t)used;
    }
    if (fchmod(writer, 0400) < 0 || fcntl(writer, F_ADD_SEALS, SEALS) < 0) return -1;
    return 0;
}

static int create_role(struct guest_tree_property_seed_source *owner, int proc_fds, size_t i) {
    const struct seed_profile *profile = &profiles[i];
    struct stat created, reopened;
    int result = -1;
    int writer = memfd_create(profile->name, MFD_CLOEXEC | MFD_ALLOW_SEALING | MFD_NOEXEC_SEAL);
    if (writer < 0) return -1;
    int reader = -1;
    if (seal(writer, profile) < 0 || check_sealed(writer, profile->bytes, O_RDWR, &created) < 0) goto done;
    for (size_t j = 0; j < i; ++j) {
        if (same_inode(&created, &owner->identities[j])) { errno = EXDEV; goto done; }
    }
    char descriptor[16];
    int length = snprintf(descriptor, sizeof(descriptor), "%d", writer);
    if (length <= 0 || (size_t)length >= sizeof(descriptor)) { errno = EOVERFLOW; goto done; }
    /* This exact procfs magic link reopens the file description with O_RDONLY.
     * An ordinary dup would preserve the writable access mode. */
    reader = openat(proc_fds, descriptor, O_RDONLY | O_CLOEXEC);
    if (reader < 0 || check_sealed(reader, profile->bytes, O_RDONLY, &reopened) < 0) goto done;
    if (!same_inode(&created, &reopened)) { errno = EXDEV; goto done; }
    if (check_payload(reader, profile) < 0) goto done;
    owner->identities[i] = reopened;
    owner->fds[i] = reader;
    reader = -1;
    result = 0;
done:
    close_cell(owner, &reader);
    close_cell(owner, &writer);
    return owner->close_error ? refuse(owner->close_error) : result;
}

int guest_tree_property_seed_source_prepare(struct guest_tree_property_seed_source **out) {
    if (!out || *out) return refuse(EINVAL);
    if (!process_leader() || getpid() <= 1) return refuse(EPERM);
    if (source.parent) return refuse(EALREADY);
    source.parent = getpid();
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) source.fds[i] = -1;
    *out = &source;
    if (check_linked_bytes() < 0) return -1;
    struct statfs fs;
    struct stat proc;
    int result = -1;
    int fd = open("/proc/self/fd", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstatfs(fd, &fs) < 0 || fstat(fd, &proc) < 0) goto done;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || !S_ISDIR(proc.st_mode)) { errno = EXDEV; goto done; }
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i)
        if (create_role(&source, fd, i) < 0) goto done;
    result = 0;
done:
    close_cell(&source, &fd);
    if (source.close_error) return refuse(source.close_error);
    source.ready = result == 0;
    return result;
}

int guest_tree_property_seed_source_keep_in_child(struct guest_tree_property_seed_source *owner, int fd) {
    if (!direct_child(owner)) return refuse(EPERM);
    if (!owner->ready || owner->taken || fd < 0) return refuse(EINVAL);
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i)
        if (fd == owner->fds[i]) return 1;
    return 0;
}

int guest_tree_property_seed_source_take_in_child(struct guest_tree_property_seed_source *owner,
        int seeds[GTP_SEED_COUNT]) {
    if (!direct_child(owner)) return refuse(EPERM);
    if (!owner->ready || owner->taken || !seeds) return refuse(EINVAL);
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i)
        if (seeds[i] != -1) return refuse(EINVAL);
    owner->taken = 1;
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        struct stat actual;
        if (check_sealed(owner->fds[i], profiles[i].bytes, O_RDONLY, &actual) < 0) return -1;
        if (!same_inode(&actual, &owner->identities[i])) return refuse(ESTALE);
    }
    for (size_t i = 0; i < GTP_SEED_COUNT; ++i) {
        seeds[i] = owner->fds[i];
        owner->fds[i] = -1;
    }
    return 0;
}

int guest_tree_property_seed_source_close(struct guest_tree_property_seed_source *owner) {
    if (owner != &source || !owner->parent) return refuse(EINVAL);
    if (!(process_leader() && getpid() == owner->parent) && !direct_child(owner)) return refuse(EPERM);
    if (owner->close_error) return refuse(owner->close_error);
    if (owner->closed) return 0;
    owner->ready = 0;
    for (size_t i = GTP_SEED_COUNT; i; --i) {
        int fd = owner->fds[i - 1];
        if (fd < 0) continue;
        struct stat actual;
        if (check_sealed(fd, profiles[i - 1].bytes, O_RDONLY, &actual) < 0
                || !same_inode(&actual, &owner->identities[i - 1])) {
            owner->close_error = ESTALE;
            return refuse(ESTALE);
        }
        close_cell(owner, &owner->fds[i - 1]);
        if (owner->close_error) return refuse(owner->close_error);
    }
    owner->closed = 1;
    return 0;
}
