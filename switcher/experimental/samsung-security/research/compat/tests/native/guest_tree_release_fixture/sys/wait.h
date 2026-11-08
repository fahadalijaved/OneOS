#ifndef ONEOS_GTR_FIXTURE_WAIT_H
#define ONEOS_GTR_FIXTURE_WAIT_H
#include <sys/types.h>
#define WNOHANG 1
#define WIFEXITED(status) (((status) & 127) == 0)
#define WIFSIGNALED(status) (((status) & 127) != 0 && ((status) & 127) != 127)
pid_t waitpid(pid_t pid, int *status, int options);
#endif
