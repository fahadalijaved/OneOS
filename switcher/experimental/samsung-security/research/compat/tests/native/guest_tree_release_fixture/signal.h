#ifndef ONEOS_GTR_FIXTURE_SIGNAL_H
#define ONEOS_GTR_FIXTURE_SIGNAL_H
#include <sys/types.h>
#define SIGCHLD 17
#define SIGTERM 15
#define SIGKILL 9
#define SA_NOCLDWAIT 2
#define SIG_DFL ((void (*)(int))0)
struct sigaction { void (*sa_handler)(int); int sa_flags; };
int sigaction(int signal_number, const struct sigaction *input, struct sigaction *output);
int kill(pid_t pid, int signal_number);
#endif
