#ifndef ONEOS_GTC_TEST_POLL_H
#define ONEOS_GTC_TEST_POLL_H
#define POLLIN 1
struct pollfd { int fd; short events, revents; };
int poll(struct pollfd *fds, unsigned long count, int timeout);
#endif
