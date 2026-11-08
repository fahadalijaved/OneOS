#ifndef ONEOS_GTSP_FIXTURE_STAT_H
#define ONEOS_GTSP_FIXTURE_STAT_H
#include <stdint.h>
#define S_IFDIR 0040000
#define S_IFREG 0100000
#define S_ISDIR(mode) (((mode) & 0170000) == S_IFDIR)
#define S_ISREG(mode) (((mode) & 0170000) == S_IFREG)
#define STATX_TYPE 1
#define STATX_MODE 2
#define STATX_NLINK 4
#define STATX_UID 8
#define STATX_GID 16
#define STATX_MTIME 64
#define STATX_CTIME 128
#define STATX_INO 256
#define STATX_SIZE 512
#define STATX_MNT_ID 4096
struct stat { uint64_t st_dev, st_ino; };
struct statx_timestamp { int64_t tv_sec; uint32_t tv_nsec; };
struct statx {
    unsigned stx_mask, stx_mode, stx_uid, stx_gid, stx_nlink, stx_dev_major, stx_dev_minor;
    uint64_t stx_mnt_id, stx_ino, stx_size;
    struct statx_timestamp stx_mtime, stx_ctime;
};
int fstat(int fd, struct stat *out);
int stat(const char *path, struct stat *out);
int statx(int fd, const char *path, int flags, unsigned mask, struct statx *out);
#endif
