#ifndef ONEOS_GTSP_FIXTURE_STATFS_H
#define ONEOS_GTSP_FIXTURE_STATFS_H
struct statfs { long f_type; };
int fstatfs(int fd, struct statfs *out);
#endif
