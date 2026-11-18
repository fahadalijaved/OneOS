#ifndef ONEOS_GTSP_FIXTURE_FCNTL_H
#define ONEOS_GTSP_FIXTURE_FCNTL_H
#define O_RDONLY 0
#define O_PATH 0x200000
#define O_DIRECTORY 0x10000
#define O_NOFOLLOW 0x20000
#define O_CLOEXEC 0x80000
#define O_NONBLOCK 0x800
#define F_DUPFD_CLOEXEC 1030
#define AT_FDCWD (-100)
#define AT_SYMLINK_NOFOLLOW 0x100
#define AT_NO_AUTOMOUNT 0x800
#define AT_EMPTY_PATH 0x1000
int open(const char *path, int flags, ...);
int openat(int base, const char *path, int flags, ...);
int fcntl(int fd, int command, ...);
#endif
