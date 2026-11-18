#define _GNU_SOURCE
#include "guest_tree_stop_role_birth.h"

#include "guest_tree_sha256.h"
#include "guest_tree_stop_proc.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <unistd.h>

#define PROC_ROOT "/proc"
#define CONFIG_NAME "config.gz"
#define CONFIG_BYTES 48809U
#define LOOKUP (AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT)
#define ID_MASK (STATX_TYPE | STATX_MODE | STATX_MNT_ID | STATX_INO)

/* Exact captured kernel config with PID_NS and USER_NS compiled out. */
static const unsigned char expected_config_sha256[32] = {
    0xa0, 0xa8, 0x05, 0x28, 0xb7, 0x4a, 0x6d, 0xd7,
    0x2c, 0xd3, 0x70, 0x77, 0xbd, 0x7e, 0xc6, 0x0d,
    0x12, 0x91, 0xff, 0x0a, 0x8f, 0xc6, 0x48, 0x5b,
    0xb0, 0x73, 0x68, 0x7b, 0x46, 0xa4, 0x85, 0x87,
};

static int refuse(int error) {
    errno = error;
    return -1;
}

static int identify(int fd, const char *name, mode_t type, struct statx *out) {
    if (statx(fd, name, LOOKUP | (*name ? 0 : AT_EMPTY_PATH), ID_MASK, out) < 0) return -1;
    return (out->stx_mask & ID_MASK) == ID_MASK && out->stx_mnt_id && out->stx_ino
        && (out->stx_mode & S_IFMT) == type ? 0 : refuse(EXDEV);
}

static int same_mount(const struct statx *a, const struct statx *b) {
    return a->stx_mnt_id == b->stx_mnt_id && a->stx_dev_major == b->stx_dev_major
        && a->stx_dev_minor == b->stx_dev_minor;
}

static int same_node(const struct statx *a, const struct statx *b) {
    return same_mount(a, b) && a->stx_ino == b->stx_ino && a->stx_mode == b->stx_mode;
}

static int current_pair(int fd, int parent, const char *name, mode_t type, const struct statx *initial) {
    struct statx held, named;
    if (identify(fd, "", type, &held) < 0 || identify(parent, name, type, &named) < 0) return -1;
    return same_node(initial, &held) && same_node(initial, &named) ? 0 : refuse(ESTALE);
}

static int current_root(int proc, const struct statx *initial, pid_t own_pid) {
    struct statfs fs;
    struct statx self_id;
    if (fstatfs(proc, &fs) < 0) return -1;
    if ((unsigned long)fs.f_type != PROC_SUPER_MAGIC || initial->stx_ino != 1) return refuse(EXDEV);
    if (current_pair(proc, AT_FDCWD, PROC_ROOT, S_IFDIR, initial) < 0
            || identify(proc, "self", S_IFLNK, &self_id) < 0) return -1;
    if (!same_mount(initial, &self_id)) return refuse(EXDEV);
    char expected[24], self[24];
    int length = snprintf(expected, sizeof(expected), "%ld", (long)own_pid);
    if (length <= 0 || (size_t)length >= sizeof(expected)) return refuse(EOVERFLOW);
    ssize_t count = readlinkat(proc, "self", self, sizeof(self));
    if (count < 0) return -1;
    return count == length && !memcmp(self, expected, (size_t)length) ? 0 : refuse(EXDEV);
}

static int pin_config(int fd) {
    struct guest_tree_sha256 hash;
    unsigned char block[4096], digest[32];
    size_t total = 0;
    guest_tree_sha256_init(&hash);
    for (;;) {
        ssize_t count = read(fd, block, sizeof(block));
        if (count < 0) return -1;
        if (!count) break;
        if ((size_t)count > CONFIG_BYTES - total) return refuse(EOVERFLOW);
        guest_tree_sha256_update(&hash, block, (size_t)count);
        total += (size_t)count;
    }
    guest_tree_sha256_final(&hash, digest);
    return total == CONFIG_BYTES && !memcmp(digest, expected_config_sha256, sizeof(digest)) ? 0 : refuse(ESTALE);
}

int guest_tree_stop_role_birth(pid_t child, uint64_t *start_ticks) {
    if (!start_ticks) return refuse(EINVAL);
    *start_ticks = 0;
    pid_t own_pid = getpid();
    if (child <= 0 || child == own_pid || (uint64_t)child > INT32_MAX) return refuse(EINVAL);
    int proc = open(PROC_ROOT, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (proc < 0) return -1;
    int config = -1, error = 0;
    struct statx proc_id, config_id;
    struct guest_tree_stop_proc_birth birth = {0};
    if (identify(proc, "", S_IFDIR, &proc_id) < 0 || current_root(proc, &proc_id, own_pid) < 0
            || identify(proc, CONFIG_NAME, S_IFREG, &config_id) < 0) { error = errno; goto done; }
    if (!same_mount(&proc_id, &config_id)) { error = EXDEV; goto done; }
    config = openat(proc, CONFIG_NAME, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (config < 0 || current_pair(config, proc, CONFIG_NAME, S_IFREG, &config_id) < 0
            || pin_config(config) < 0 || current_pair(config, proc, CONFIG_NAME, S_IFREG, &config_id) < 0
            || current_root(proc, &proc_id, own_pid) < 0) { error = errno; goto done; }
    enum guest_tree_stop_proc_result result = guest_tree_stop_proc_read(proc, child, 1, &birth);
    if (result != GUEST_TREE_STOP_PROC_LIVE) { error = errno ? errno : EIO; goto done; }
    if (birth.pid != child || !birth.start_ticks || birth.pid_ns_dev || birth.pid_ns_ino) { error = ESTALE; goto done; }
    if (current_pair(config, proc, CONFIG_NAME, S_IFREG, &config_id) < 0
            || current_root(proc, &proc_id, own_pid) < 0) error = errno;
done:
    if (config >= 0 && close(config) < 0 && !error) error = errno;
    if (close(proc) < 0 && !error) error = errno;
    if (error) return refuse(error);
    *start_ticks = birth.start_ticks;
    return 0;
}
