#ifndef ONEOS_GTC_TEST_SIGNAL_H
#define ONEOS_GTC_TEST_SIGNAL_H
#include <sys/types.h>
#define SIGINT 2
#define SIGHUP 1
#define SIGTERM 15
#define SIGKILL 9
#define SIG_SETMASK 2
#define SIG_DFL ((void (*)(int))0)
typedef unsigned sigset_t;
struct sigaction { void (*sa_handler)(int); sigset_t sa_mask; };
int sigemptyset(sigset_t *set);
int sigaction(int signal, const struct sigaction *action, struct sigaction *old);
int sigprocmask(int how, const sigset_t *set, sigset_t *old);
#endif
