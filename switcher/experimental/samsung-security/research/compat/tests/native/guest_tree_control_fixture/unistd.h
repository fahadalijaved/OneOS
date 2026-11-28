#ifndef ONEOS_GTC_TEST_UNISTD_H
#define ONEOS_GTC_TEST_UNISTD_H
#include <sys/types.h>
pid_t getpid(void);
pid_t gettid(void);
pid_t getppid(void);
uid_t geteuid(void);
gid_t getegid(void);
int getresuid(uid_t *real, uid_t *effective, uid_t *saved);
int getresgid(gid_t *real, gid_t *effective, gid_t *saved);
int close(int fd);
_Noreturn void _exit(int status);
#endif
