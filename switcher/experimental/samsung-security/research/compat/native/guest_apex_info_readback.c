#define _GNU_SOURCE
#include "guest_apex_info_readback.h"

#include "guest_readback_identity.h"
#include "guest_tree_sha256.h"

#include <linux/magic.h>
#include <string.h>
#include <sys/statfs.h>
#include <unistd.h>

static const char xml_name[] = "apex-info-list.xml";
enum { ANDROID_SYSTEM_GID = 1000 };
#define EROFS_MAGIC 0xe0f5e1e2UL

static const unsigned char runtime_manifest_sha256[32] = {
    0x48, 0xe7, 0x4b, 0xbf, 0x3d, 0xea, 0xd7, 0x38, 0x6e, 0x9a, 0x16, 0xba, 0x8f, 0xf5, 0x1c, 0xd9,
    0x98, 0x3c, 0x5d, 0x5a, 0xb6, 0x97, 0x3b, 0xb7, 0xfb, 0x8c, 0x44, 0x5a, 0x96, 0x53, 0xd0, 0xd9,
};
static const unsigned char runtime_config[] = { 0x10, 0x01 };
enum { RUNTIME_MANIFEST_BYTES = 143 };

static int read_exact(int fd, unsigned char *bytes, size_t size) {
    size_t used = 0;
    while (used < size) {
        ssize_t count = pread(fd, bytes + used, size - used, (off_t)used);
        if (count < 0) return -1;
        if (count == 0) return guest_readback_refuse(EIO);
        used += (size_t)count;
    }
    unsigned char extra;
    ssize_t tail = pread(fd, &extra, 1, (off_t)size);
    if (tail < 0) return -1;
    return tail == 0 ? 0 : guest_readback_refuse(EFBIG);
}

static void digest_bytes(const void *bytes, size_t count, unsigned char out[32]) {
    struct guest_tree_sha256 hash;
    guest_tree_sha256_init(&hash);
    guest_tree_sha256_update(&hash, bytes, count);
    guest_tree_sha256_final(&hash, out);
}

static int readback(int apex_fd, int xml_fd, void *scratch, size_t capacity,
        struct guest_apex_info_sample *out, unsigned expected_gid,
        const struct statx *initial_directory, const struct statx *initial_file) {
    if (apex_fd < 0 || xml_fd < 0 || apex_fd == xml_fd || !scratch || !out || !capacity) return guest_readback_refuse(EINVAL);
    int apex_flags = fcntl(apex_fd, F_GETFD);
    if (apex_flags < 0) return -1;
    int xml_flags = fcntl(xml_fd, F_GETFD);
    if (xml_flags < 0) return -1;
    int access = fcntl(xml_fd, F_GETFL);
    if (access < 0) return -1;
    if (!(apex_flags & xml_flags & FD_CLOEXEC) || (access & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME)
        return guest_readback_refuse(EPERM);

    struct statx directory, file, named, after;
    struct statfs filesystem;
    if (guest_readback_stat(apex_fd, "", &directory) < 0 || fstatfs(apex_fd, &filesystem) < 0
            || guest_readback_stat(xml_fd, "", &file) < 0 || guest_readback_stat(apex_fd, xml_name, &named) < 0) return -1;
    if (initial_directory && (!guest_readback_same_node(initial_directory, &directory) || !guest_readback_same_node(initial_file, &file)))
        return guest_readback_refuse(ESTALE);
    if (directory.stx_mode != (S_IFDIR | 0755) || directory.stx_uid || directory.stx_gid
            || filesystem.f_type != TMPFS_MAGIC || !guest_readback_same_mount(&directory, &file)) return guest_readback_refuse(EXDEV);
    int mode_matches = file.stx_mode == (S_IFREG | 0644)
            || (expected_gid == 0 && file.stx_mode == (S_IFREG | 0444));
    if (!mode_matches || file.stx_uid || file.stx_gid != expected_gid || file.stx_nlink != 1 || !file.stx_size)
        return guest_readback_refuse(EPERM);
    if (file.stx_size > GUEST_APEX_INFO_MAX_BYTES || file.stx_size > capacity) return guest_readback_refuse(EFBIG);
    if (!guest_readback_same_node(&file, &named)) return guest_readback_refuse(ESTALE);

    size_t bytes = (size_t)file.stx_size;
    if (read_exact(xml_fd, scratch, bytes) < 0 || guest_readback_stat(xml_fd, "", &after) < 0
            || guest_readback_stat(apex_fd, xml_name, &named) < 0) return -1;
    if (!guest_readback_same_node(&file, &after) || !guest_readback_same_node(&file, &named)) return guest_readback_refuse(ESTALE);
    if (guest_readback_stat(apex_fd, "", &after) < 0) return -1;
    if (!guest_readback_same_node(&directory, &after)) return guest_readback_refuse(ESTALE);

    struct guest_apex_info_sample result = {
        .mount_id = directory.stx_mnt_id, .directory_inode = directory.stx_ino, .file_inode = file.stx_ino,
        .device_major = directory.stx_dev_major, .device_minor = directory.stx_dev_minor, .bytes = bytes,
    };
    digest_bytes(scratch, bytes, result.sha256);
    *out = result;
    return 0;
}

int guest_apex_info_readback(int apex_fd, int xml_fd, void *scratch, size_t capacity,
        struct guest_apex_info_sample *out) {
    return readback(apex_fd, xml_fd, scratch, capacity, out, 0, NULL, NULL);
}

int guest_apex_info_readback_donor(int apex_fd, int xml_fd, void *scratch, size_t capacity,
        struct guest_apex_info_sample *out) {
    return readback(apex_fd, xml_fd, scratch, capacity, out, ANDROID_SYSTEM_GID, NULL, NULL);
}

enum runtime_slot { APEX, XML, RUNTIME, MANIFEST, ETC, CONFIG, RUNTIME_SLOTS };

static int runtime_snapshot(const int fd[RUNTIME_SLOTS], struct statx held[RUNTIME_SLOTS]) {
    static const struct {
        enum runtime_slot parent;
        const char *name;
    } names[RUNTIME_SLOTS] = {
        [XML] = { APEX, xml_name }, [RUNTIME] = { APEX, "com.android.runtime" },
        [MANIFEST] = { RUNTIME, "apex_manifest.pb" }, [ETC] = { RUNTIME, "etc" },
        [CONFIG] = { ETC, "linker.config.pb" },
    };
    for (unsigned i = 0; i < RUNTIME_SLOTS; ++i) {
        if (guest_readback_stat(fd[i], "", &held[i]) < 0) return -1;
        if (names[i].name) {
            struct statx named;
            if (guest_readback_stat(fd[names[i].parent], names[i].name, &named) < 0) return -1;
            if (!guest_readback_same_node(&held[i], &named)) return guest_readback_refuse(ESTALE);
        }
    }
    return 0;
}

static int runtime_file_profile(const struct statx *file, size_t bytes) {
    return file->stx_mode == (S_IFREG | 0644) && file->stx_uid == 1000 && file->stx_gid == 1000
            && file->stx_nlink == 1 && file->stx_size == bytes;
}

int guest_apex_info_readback_runtime(const struct guest_apex_runtime_files *files,
        void *scratch, size_t capacity, struct guest_apex_runtime_sample *out) {
    if (!files || !scratch || !capacity || !out) return guest_readback_refuse(EINVAL);
    const int fd[RUNTIME_SLOTS] = { files->apex_fd, files->xml_fd, files->runtime_fd,
                                  files->manifest_fd, files->etc_fd, files->config_fd };
    for (unsigned i = 0; i < RUNTIME_SLOTS; ++i) {
        if (fd[i] < 0) return guest_readback_refuse(EINVAL);
        for (unsigned j = 0; j < i; ++j) {
            if (fd[i] == fd[j]) return guest_readback_refuse(EINVAL);
        }
        int flags = fcntl(fd[i], F_GETFD);
        if (flags < 0) return -1;
        if (!(flags & FD_CLOEXEC)) return guest_readback_refuse(EPERM);
    }
    const enum runtime_slot leaves[] = { MANIFEST, CONFIG };
    for (size_t i = 0; i < sizeof(leaves) / sizeof(leaves[0]); ++i) {
        int flags = fcntl(fd[leaves[i]], F_GETFL);
        if (flags < 0) return -1;
        if ((flags & (O_ACCMODE | O_PATH | O_NOATIME)) != O_NOATIME) return guest_readback_refuse(EPERM);
    }

    struct statx before[RUNTIME_SLOTS], after[RUNTIME_SLOTS];
    struct statfs fs;
    if (runtime_snapshot(fd, before) < 0 || fstatfs(fd[RUNTIME], &fs) < 0) return -1;
    const struct statx *runtime = &before[RUNTIME], *etc = &before[ETC];
    if ((unsigned long)fs.f_type != EROFS_MAGIC || runtime->stx_mnt_id == before[APEX].stx_mnt_id
            || !guest_readback_same_mount(runtime, etc) || !guest_readback_same_mount(runtime, &before[MANIFEST])
            || !guest_readback_same_mount(runtime, &before[CONFIG])) return guest_readback_refuse(EXDEV);
    if (runtime->stx_mode != (S_IFDIR | 0755) || runtime->stx_uid != 1000 || runtime->stx_gid != 1000
            || etc->stx_mode != (S_IFDIR | 0755) || etc->stx_uid || etc->stx_gid != 2000
            || !runtime_file_profile(&before[MANIFEST], RUNTIME_MANIFEST_BYTES)
            || !runtime_file_profile(&before[CONFIG], sizeof(runtime_config))) return guest_readback_refuse(EPERM);

    struct guest_apex_runtime_sample result = {
        .runtime_mount_id = runtime->stx_mnt_id, .runtime_inode = runtime->stx_ino,
        .manifest_inode = before[MANIFEST].stx_ino, .etc_inode = etc->stx_ino,
        .config_inode = before[CONFIG].stx_ino,
    };
    unsigned char manifest[RUNTIME_MANIFEST_BYTES], config[sizeof(runtime_config)], digest[32];
    if (readback(fd[APEX], fd[XML], scratch, capacity, &result.xml, ANDROID_SYSTEM_GID, &before[APEX], &before[XML]) < 0
            || read_exact(fd[MANIFEST], manifest, sizeof(manifest)) < 0
            || read_exact(fd[CONFIG], config, sizeof(config)) < 0) return -1;
    digest_bytes(manifest, sizeof(manifest), digest);
    if (memcmp(digest, runtime_manifest_sha256, sizeof(digest))
            || memcmp(config, runtime_config, sizeof(config))) return guest_readback_refuse(EPROTO);
    if (runtime_snapshot(fd, after) < 0) return -1;
    for (unsigned i = 0; i < RUNTIME_SLOTS; ++i) {
        if (!guest_readback_same_node(&before[i], &after[i])) return guest_readback_refuse(ESTALE);
    }
    *out = result;
    return 0;
}
