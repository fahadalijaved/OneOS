#ifndef ONEOS_GTR_FIXTURE_FCNTL_H
#define ONEOS_GTR_FIXTURE_FCNTL_H
#define F_GETFD 1
#define FD_CLOEXEC 1
int fcntl(int fd, int command, ...);
#endif
