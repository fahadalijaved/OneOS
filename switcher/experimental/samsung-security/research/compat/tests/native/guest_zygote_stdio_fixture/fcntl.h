#ifndef ONEOS_STDIO_FIXTURE_FCNTL_H
#define ONEOS_STDIO_FIXTURE_FCNTL_H

/* Linux flag values for the host metadata model. */
#define O_RDONLY 0
#define O_WRONLY 1
#define O_RDWR 2
#define O_ACCMODE 3
#define O_PATH 010000000
#define F_GETFD 1
#define F_GETFL 3
#define FD_CLOEXEC 1

int fixture_fcntl(int fd, int command);
#define fcntl fixture_fcntl

#endif
