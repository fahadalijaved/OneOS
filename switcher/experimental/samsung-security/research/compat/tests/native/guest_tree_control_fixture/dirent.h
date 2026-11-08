#ifndef ONEOS_GTC_TEST_DIRENT_H
#define ONEOS_GTC_TEST_DIRENT_H
typedef struct fixture_directory DIR;
struct dirent { char d_name[64]; };
DIR *opendir(const char *path);
struct dirent *readdir(DIR *directory);
int dirfd(DIR *directory);
int closedir(DIR *directory);
#endif
