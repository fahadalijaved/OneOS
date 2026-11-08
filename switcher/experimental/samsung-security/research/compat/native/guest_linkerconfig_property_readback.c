#define _GNU_SOURCE
#include "guest_linkerconfig_property_readback.h"

#include "guest_readback_identity.h"
#include "guest_tree_sha256.h"

#include <linux/magic.h>
#include <string.h>
#include <sys/statfs.h>
#include <sys/statvfs.h>
#include <sys/xattr.h>
#include <unistd.h>

#define EROFS_MAGIC 0xe0f5e1e2UL

enum slot { ROOT, DEV, DIRECTORY, INFO, VNDK, DEBUG, SERIAL, SLOTS };
enum { PROPERTY_INFO_BYTES = 171544 };

static const struct {
    enum slot parent;
    const char *name, *label;
    unsigned mode;
    size_t bytes;
} nodes[SLOTS] = {
    [ROOT] = { ROOT, "", NULL, S_IFDIR | 0755, 0 },
    [DEV] = { ROOT, "dev", NULL, S_IFDIR | 0755, 0 },
    [DIRECTORY] = { DEV, "__properties__", NULL, S_IFDIR | 0711, 0 },
    [INFO] = { DIRECTORY, "property_info", "u:object_r:property_info:s0", S_IFREG | 0444, PROPERTY_INFO_BYTES },
    [VNDK] = { DIRECTORY, GUEST_TREE_VNDK_PROP_AREA, GUEST_TREE_VNDK_PROP_AREA, S_IFREG | 0444, GUEST_TREE_PROP_AREA_BYTES },
    [DEBUG] = { DIRECTORY, GUEST_TREE_DEBUG_PROP_AREA, GUEST_TREE_DEBUG_PROP_AREA, S_IFREG | 0444, GUEST_TREE_PROP_AREA_BYTES },
    [SERIAL] = { DIRECTORY, "properties_serial", "u:object_r:properties_serial:s0", S_IFREG | 0444, GUEST_TREE_PROP_AREA_BYTES },
};

static const unsigned char property_info_sha256[32] = {
    0xa4, 0x13, 0x05, 0x1d, 0x65, 0x16, 0x71, 0x91, 0x89, 0xea, 0x96, 0x4e, 0xfa, 0xa7, 0xd7, 0x49,
    0x54, 0xf0, 0xd1, 0x05, 0x2f, 0xed, 0xf0, 0x66, 0xce, 0xf8, 0xc9, 0xa1, 0xc8, 0x13, 0xd3, 0xe4,
};

static int label_matches(int fd, const char *expected) {
    char label[64];
    ssize_t bytes = fgetxattr(fd, "security.selinux", label, sizeof(label));
    if (bytes < 0) return -1;
    size_t length = strlen(expected) + 1;
    if ((size_t)bytes != length || memcmp(label, expected, length)) return guest_readback_refuse(EACCES);
    return 0;
}

static int snapshot(const int fd[SLOTS], struct statx held[SLOTS]) {
    for (unsigned i = 0; i < SLOTS; ++i) {
        if (guest_readback_stat(fd[i], "", &held[i]) < 0) return -1;
        if (held[i].stx_mode != nodes[i].mode || held[i].stx_uid || held[i].stx_gid
                || (i == DIRECTORY && held[i].stx_nlink != 2)
                || (i >= INFO && (held[i].stx_nlink != 1 || held[i].stx_size != nodes[i].bytes)))
            return guest_readback_refuse(EPERM);
        if (i == ROOT) continue;
        struct statx named;
        if (guest_readback_stat(fd[nodes[i].parent], nodes[i].name, &named) < 0) return -1;
        if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
        if (i >= DIRECTORY && !guest_readback_same_mount(&held[DEV], &held[i])) return guest_readback_refuse(EXDEV);
        for (unsigned j = DEV; j < i; ++j) {
            if (held[i].stx_ino == held[j].stx_ino) return guest_readback_refuse(EPERM);
        }
        if (nodes[i].label && label_matches(fd[i], nodes[i].label) < 0) return -1;
    }
    struct statfs root_fs, dev_fs;
    struct statvfs dev_flags;
    if (fstatfs(fd[ROOT], &root_fs) < 0 || fstatfs(fd[DEV], &dev_fs) < 0 || fstatvfs(fd[DEV], &dev_flags) < 0)
        return -1;
    const unsigned long required = ST_NOSUID | ST_NODEV | ST_NOEXEC;
    if ((unsigned long)root_fs.f_type != EROFS_MAGIC || dev_fs.f_type != TMPFS_MAGIC
            || held[ROOT].stx_mnt_id == held[DEV].stx_mnt_id || (dev_flags.f_flag & required) != required)
        return guest_readback_refuse(EXDEV);
    return 0;
}

static int digest_file(int fd, size_t size, unsigned char *capture, unsigned char digest[32]) {
    unsigned char buffer[4096];
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    for (size_t used = 0; used < size;) {
        size_t remaining = size - used;
        unsigned char *chunk = capture ? capture + used : buffer;
        ssize_t got = pread(fd, chunk, remaining < sizeof(buffer) ? remaining : sizeof(buffer), (off_t)used);
        if (got < 0) return -1;
        if (!got) return guest_readback_refuse(EIO);
        guest_tree_sha256_update(&hash, chunk, (size_t)got);
        used += (size_t)got;
    }
    ssize_t tail = pread(fd, buffer, 1, (off_t)size);
    if (tail < 0) return -1;
    if (tail) return guest_readback_refuse(EFBIG);
    guest_tree_sha256_final(&hash, digest);
    return 0;
}

static int serial_area_profile(const unsigned char *bytes) {
    static const unsigned char used[] = { 0x70, 0, 0, 0 };
    static const unsigned char magic_version[] = { 0x50, 0x52, 0x4f, 0x50, 0xab, 0xd0, 0x6e, 0xfc };
    /* This area carries the global serial at offset four and no records. */
    if (memcmp(bytes, used, sizeof(used)) || memcmp(bytes + 8, magic_version, sizeof(magic_version))) return 0;
    for (size_t i = 16; i < GUEST_TREE_PROP_AREA_BYTES; ++i) {
        if (bytes[i]) return 0;
    }
    return 1;
}

int guest_linkerconfig_property_readback(const struct guest_linkerconfig_property_files *files,
        void *scratch, size_t capacity, struct guest_linkerconfig_property_sample *out) {
    if (!files || !scratch || !out) return guest_readback_refuse(EINVAL);
    if (capacity < GUEST_LINKERCONFIG_PROPERTY_SCRATCH_BYTES) return guest_readback_refuse(EFBIG);
    const int fd[] = { files->root_fd, files->dev_fd, files->directory_fd, files->info_fd,
                       files->vndk_fd, files->debug_fd, files->serial_fd };
    for (unsigned i = 0; i < SLOTS; ++i) {
        if (fd[i] < 0) return guest_readback_refuse(EINVAL);
        for (unsigned j = 0; j < i; ++j) {
            if (fd[i] == fd[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fd[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
        if (i < INFO) continue;
        flags = fcntl(fd[i], F_GETFL);
        if (flags < 0) return -1;
        if ((flags & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);
    }

    struct statx before[SLOTS], after[SLOTS];
    if (snapshot(fd, before) < 0) return -1;
    struct guest_linkerconfig_property_sample result = {
        .root_mount_id = before[ROOT].stx_mnt_id, .root_inode = before[ROOT].stx_ino,
        .dev_mount_id = before[DEV].stx_mnt_id, .directory_inode = before[DIRECTORY].stx_ino,
    };
    unsigned char digest[32];
    unsigned char *vndk = scratch, *debug = vndk + GUEST_TREE_PROP_AREA_BYTES;
    if (digest_file(fd[SERIAL], nodes[SERIAL].bytes, vndk, result.serial_sha256) < 0) return -1;
    if (!serial_area_profile(vndk)) return guest_readback_refuse(EPROTO);
    if (digest_file(fd[INFO], nodes[INFO].bytes, NULL, digest) < 0) return -1;
    if (memcmp(digest, property_info_sha256, sizeof(digest))) return guest_readback_refuse(EBADMSG);
    if (digest_file(fd[VNDK], nodes[VNDK].bytes, vndk, result.vndk_sha256) < 0
            || digest_file(fd[DEBUG], nodes[DEBUG].bytes, debug, result.debug_sha256) < 0) return -1;
    enum guest_tree_prop_result parsed = guest_tree_property_read_linkerconfig(vndk, nodes[VNDK].bytes,
            debug, nodes[DEBUG].bytes, &result.properties);
    if (parsed != GUEST_TREE_PROP_STORED_LINKERCONFIG)
        return guest_readback_refuse(parsed == GUEST_TREE_PROP_UNSUPPORTED ? EOPNOTSUPP : EPROTO);
    if (digest_file(fd[SERIAL], nodes[SERIAL].bytes, NULL, digest) < 0 || snapshot(fd, after) < 0) return -1;
    if (memcmp(digest, result.serial_sha256, sizeof(digest))) return guest_readback_refuse(ESTALE);
    for (unsigned i = 0; i < SLOTS; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    *out = result;
    return 0;
}
