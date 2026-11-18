#ifndef ONEOS_GTR_FIXTURE_UNISTD_H
#define ONEOS_GTR_FIXTURE_UNISTD_H
#include <sys/types.h>
pid_t fork(void);
pid_t getpid(void);
pid_t gettid(void);
int close(int fd);
#endif
