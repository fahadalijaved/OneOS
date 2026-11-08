#ifndef ONEOS_GTSP_FIXTURE_UNISTD_H
#define ONEOS_GTSP_FIXTURE_UNISTD_H
#include <sys/types.h>
#include <stddef.h>
typedef unsigned uid_t;
pid_t getpid(void);
pid_t gettid(void);
uid_t getuid(void);
uid_t geteuid(void);
int close(int fd);
ssize_t read(int fd, void *buffer, size_t count);
#endif
