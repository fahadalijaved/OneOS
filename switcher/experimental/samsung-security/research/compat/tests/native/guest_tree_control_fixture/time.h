#ifndef ONEOS_GTC_TEST_TIME_H
#define ONEOS_GTC_TEST_TIME_H
#include <sys/types.h>
#define CLOCK_MONOTONIC 1
int clock_gettime(int clock, struct timespec *out);
#endif
