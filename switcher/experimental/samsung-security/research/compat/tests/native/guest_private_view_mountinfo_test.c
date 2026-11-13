/* Authored portable grammar fixtures. No kernel/Android namespace simulation. */
#include "guest_private_view_mountinfo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks;
static struct gpv_mount_row rows[4];
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr, "FAIL line %u: %s\n", (unsigned)__LINE__, #x); exit(1); } } while (0)

static void mount_result(const char *s, int expected) {
    size_t count = 999, n = strlen(s);
    char *copy = (char *)malloc(n + 1);
    CHECK(copy != NULL); memcpy(copy, s, n + 1);
    CHECK(gpv_parse_mountinfo(s, n, rows, 4, &count) == expected);
    CHECK(!memcmp(copy, s, n + 1));
    CHECK(expected == GPV_OK ? count > 0 : count == 0);
    free(copy);
}
static void fd_result(const char *s, int expected, uint64_t value) {
    uint64_t id = 999;
    size_t n = strlen(s);
    char *copy = (char *)malloc(n + 1);
    CHECK(copy != NULL); memcpy(copy, s, n + 1);
    CHECK(gpv_parse_fdinfo_mnt_id(s, n, &id) == expected);
    CHECK(id == value);
    CHECK(!memcmp(copy, s, n + 1)); free(copy);
}
int main(void) {
    const char *basic = "41 1 8:2 / /data rw,nosuid shared:48 master:9 propagate_from:9 - ext4 /dev/block/data rw,seclabel\n";
    const char *over = "41 1 8:2 / /data rw shared:48 - ext4 /dev/data rw\n42 1 8:2 / /data rw shared:48 - ext4 /dev/data rw\n";
    const struct gpv_mount_row *old, *fresh;
    uint64_t id;
    size_t n = 99, matches = 99;
    char buffer[1600], path[1025];
    char *large;
    mount_result(basic, GPV_OK);
    CHECK(rows[0].id == 41 && rows[0].parent == 1 && rows[0].major == 8 && rows[0].minor == 2);
    CHECK(rows[0].shared == 48 && rows[0].master == 9 && rows[0].propagate == 9 && !rows[0].unbindable);
    CHECK(!strcmp(rows[0].root, "/") && !strcmp(rows[0].point, "/data") && !strcmp(rows[0].source, "/dev/block/data"));
    CHECK(!strcmp(rows[0].options, "rw,nosuid") && !strcmp(rows[0].super_options, "rw,seclabel"));
    mount_result("1 1 0:0 / /x rw unbindable - tmpfs tmpfs rw\n", GPV_OK);
    CHECK(rows[0].unbindable == 1);
    mount_result("1 1 0:0 /a\\040b /t\\011c\\012d\\134e rw - tmpfs src\\040x rw,context=a\\040b\n", GPV_OK);
    CHECK(!strcmp(rows[0].root, "/a b") && !strcmp(rows[0].point, "/t\tc\nd\\e"));
    CHECK(!strcmp(rows[0].source, "src x") && !strcmp(rows[0].super_options, "rw,context=a\\040b"));
    mount_result("1 1 0:0 / /x rw,key=a\\054b,tag=x\\043y - fuse\\043test dev\\0431 rw\n", GPV_OK);
    CHECK(!strcmp(rows[0].type, "fuse#test") && !strcmp(rows[0].source, "dev#1"));
    CHECK(!strcmp(rows[0].options, "rw,key=a\\054b,tag=x\\043y"));
    mount_result("18446744073709551615 1 4294967295:4294967295 / /x rw - tmpfs none rw\n", GPV_OK);
    CHECK(rows[0].id == UINT64_MAX && rows[0].major == UINT32_MAX && rows[0].minor == UINT32_MAX);
    mount_result(over, GPV_OK);
    CHECK(gpv_mount_path_count(rows, 2, "/data", &matches) == GPV_OK && matches == 2);
    fd_result("pos:\t0\nflags:\t0100000\nmnt_id:\t41\nlock: a\nlock: b\n", GPV_OK, 41);
    CHECK(gpv_parse_fdinfo_mnt_id("mnt_id: 41\n", 11, &id) == GPV_OK);
    old = gpv_mount_by_id(rows, 2, id);
    CHECK(gpv_parse_fdinfo_mnt_id("mnt_id: 42\n", 11, &id) == GPV_OK);
    fresh = gpv_mount_by_id(rows, 2, id);
    CHECK(old == &rows[0] && fresh == &rows[1] && old != fresh);
    CHECK(old->major == fresh->major && old->minor == fresh->minor && !strcmp(old->root, fresh->root) && !strcmp(old->point, fresh->point));
    CHECK(old->shared == fresh->shared); /* Peer overlap diagnostic; not ownership admission. */
    CHECK(gpv_mount_by_id(rows, 2, 999) == NULL);
    mount_result("41 1 8:2 / /x rw - ext4 x rw\n41 1 8:2 / /y rw - ext4 y rw\n", GPV_INVALID);
    mount_result("0 1 0:0 / /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 0 0:0 / /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("18446744073709551616 1 0:0 / /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 4294967296:0 / /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:4294967296 / /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 relative /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x\\000 rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x\\043 rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x\\04 rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw shared:2 shared:3 - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw master:2 master:2 - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw shared:0 - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw propagate_from:3 - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw unbindable shared:3 - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw unknown:3 - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x ro,rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw,key=a,key=b - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw, - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw - tmpfs none rw extra\n", GPV_INVALID);
    mount_result("1  1 0:0 / /x rw - tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw tmpfs none rw\n", GPV_INVALID);
    mount_result("1 1 0:0 / /x rw - tmpfs none rw", GPV_INVALID);
    mount_result("\n", GPV_INVALID);
    memset(path, 'a', 1023); path[0] = '/'; path[1023] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / %s rw - tmpfs none rw\n", path) > 0);
    mount_result(buffer, GPV_OK);
    path[1023] = 'a'; path[1024] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / %s rw - tmpfs none rw\n", path) > 0);
    mount_result(buffer, GPV_LIMIT);
    memset(path, 's', 1023); path[1023] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / /x rw - tmpfs %s rw\n", path) > 0);
    mount_result(buffer, GPV_OK);
    path[1023] = 's'; path[1024] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / /x rw - tmpfs %s rw\n", path) > 0);
    mount_result(buffer, GPV_LIMIT);
    memset(path, 't', 63); path[63] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / /x rw - %s none rw\n", path) > 0);
    mount_result(buffer, GPV_OK);
    path[63] = 't'; path[64] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / /x rw - %s none rw\n", path) > 0);
    mount_result(buffer, GPV_LIMIT);
    memset(path, 'o', 512); path[512] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / /x %s - tmpfs none rw\n", path) > 0);
    mount_result(buffer, GPV_OK);
    path[512] = 'o'; path[513] = 0;
    CHECK(snprintf(buffer, sizeof(buffer), "1 1 0:0 / /x %s - tmpfs none rw\n", path) > 0);
    mount_result(buffer, GPV_LIMIT);
    CHECK(gpv_parse_mountinfo(over, strlen(over), rows, 1, &n) == GPV_LIMIT && n == 0);
    CHECK(gpv_parse_mountinfo(basic, strlen(basic), rows, GPV_MOUNTINFO_MAX_ROWS + 1U, &n) == GPV_LIMIT && n == 0);
    memcpy(buffer, basic, strlen(basic)); buffer[5] = 0;
    CHECK(gpv_parse_mountinfo(buffer, strlen(basic), rows, 4, &n) == GPV_INVALID && n == 0);
    large = (char *)malloc(GPV_MOUNTINFO_MAX_BYTES + 1U); CHECK(large != NULL);
    memset(large, 'a', GPV_MOUNTINFO_MAX_BYTES + 1U);
    CHECK(gpv_parse_mountinfo(large, GPV_MOUNTINFO_MAX_BYTES + 1U, rows, 4, &n) == GPV_LIMIT && n == 0);
    CHECK(gpv_parse_mountinfo(large, GPV_MOUNTINFO_MAX_LINE + 1U, rows, 4, &n) == GPV_LIMIT && n == 0);
    CHECK(gpv_parse_fdinfo_mnt_id(large, GPV_FDINFO_MAX_BYTES + 1U, &id) == GPV_LIMIT && id == 0);
    free(large);
    fd_result("mnt_id: 18446744073709551615\n", GPV_OK, UINT64_MAX);
    fd_result("mnt_id: 18446744073709551616\n", GPV_INVALID, 0);
    fd_result("mnt_id: 0\n", GPV_INVALID, 0);
    fd_result("mnt_id: 1\nmnt_id: 1\n", GPV_INVALID, 0);
    fd_result("pos: 0\n", GPV_INVALID, 0);
    fd_result("mnt_id:1\n", GPV_INVALID, 0);
    fd_result("mnt_id: -1\n", GPV_INVALID, 0);
    fd_result("mnt_id: 1 \n", GPV_INVALID, 0);
    fd_result("mnt_id: 1", GPV_INVALID, 0);
    fd_result("mnt_id : 1\n", GPV_INVALID, 0);
    printf("PASS %u portable-parser checks; grammar only, no kernel/Android ownership acceptance\n", checks);
    return 0;
}
