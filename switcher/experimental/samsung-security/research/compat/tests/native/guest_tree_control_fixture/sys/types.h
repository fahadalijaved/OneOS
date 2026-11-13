#ifndef ONEOS_GTC_TEST_TYPES_H
#define ONEOS_GTC_TEST_TYPES_H
#include_next <sys/types.h>
typedef unsigned uid_t;
typedef unsigned gid_t;
#ifndef _SSIZE_T_DEFINED
#define _SSIZE_T_DEFINED
typedef __int64 ssize_t;
#endif
#endif
