#ifndef ONEOS_STDIO_FIXTURE_STAT_H
#define ONEOS_STDIO_FIXTURE_STAT_H

#include <stdint.h>

/* Only the fields read by the validator. This is not a host or Android ABI. */
struct stat {
    uint64_t st_dev;
    uint64_t st_ino;
    uint64_t st_rdev;
    unsigned st_mode;
};

#define S_IFMT 0170000U
#define S_IFCHR 0020000U
#define S_IFBLK 0060000U
#define S_IFREG 0100000U
#define S_IFIFO 0010000U
#define S_ISCHR(mode) (((mode) & S_IFMT) == S_IFCHR)

int fixture_fstat(int fd, struct stat *out);
#define fstat fixture_fstat

#endif
