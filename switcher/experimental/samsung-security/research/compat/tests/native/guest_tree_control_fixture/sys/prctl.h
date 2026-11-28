#ifndef ONEOS_GTC_TEST_PRCTL_H
#define ONEOS_GTC_TEST_PRCTL_H
#define PR_SET_PDEATHSIG 1
int prctl(int option, ...);
#endif
