#define _GNU_SOURCE

#include "guest_tree_sha256.h"
#include "guest_tree_stop_proc.h"

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int parse_pid(const char *text, pid_t *pid) {
    unsigned value = 0;
    if (*text < '1' || *text > '9') return -1;
    for (; *text; ++text) {
        if (*text < '0' || *text > '9') return -1;
        unsigned digit = (unsigned)(*text - '0');
        if (value > ((unsigned)INT_MAX - digit) / 10U) return -1;
        value = 10U * value + digit;
    }
    *pid = (pid_t)value;
    return 0;
}

/* Exact observed Samsung kernel configuration with PID_NS and USER_NS off. */
static int pinned_global_config(int proc_fd) {
    static const unsigned char expected[32] = {
        0xa0, 0xa8, 0x05, 0x28, 0xb7, 0x4a, 0x6d, 0xd7, 0x2c, 0xd3, 0x70, 0x77, 0xbd, 0x7e, 0xc6, 0x0d,
        0x12, 0x91, 0xff, 0x0a, 0x8f, 0xc6, 0x48, 0x5b, 0xb0, 0x73, 0x68, 0x7b, 0x46, 0xa4, 0x85, 0x87,
    };
    enum { EXPECTED_BYTES = 48809 };
    int fd = openat(proc_fd, "config.gz", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return -1;
    struct guest_tree_sha256 hash;
    unsigned char block[4096], digest[32];
    size_t total = 0;
    ssize_t count;
    guest_tree_sha256_init(&hash);
    for (;;) {
        count = read(fd, block, sizeof(block));
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0 || (size_t)count > EXPECTED_BYTES - total) break;
        guest_tree_sha256_update(&hash, block, (size_t)count);
        total += (size_t)count;
    }
    int closed = close(fd);
    guest_tree_sha256_final(&hash, digest);
    return count == 0 && closed == 0 && total == EXPECTED_BYTES
        && !memcmp(digest, expected, sizeof(digest)) ? 0 : -1;
}

int main(int argc, char **argv) {
    pid_t pid;
    if (argc != 3 || parse_pid(argv[2], &pid) < 0) return 2;
    int global = !strcmp(argv[1], "--pinned-global-pid-view");
    if (!global && strcmp(argv[1], "--pid-namespace-view")) return 2;
    int proc_fd = open("/proc", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (proc_fd < 0) return 3;
    struct guest_tree_stop_proc_birth birth = {0};
    enum guest_tree_stop_proc_result result = GUEST_TREE_STOP_PROC_ERROR;
    if (!global || pinned_global_config(proc_fd) == 0)
        result = guest_tree_stop_proc_read(proc_fd, pid, global, &birth);
    if (close(proc_fd) < 0 || result == GUEST_TREE_STOP_PROC_ERROR) return 3;
    const char *view = global ? "PINNED_GLOBAL" : "PID_NAMESPACE";
    if (result == GUEST_TREE_STOP_PROC_ABSENT) {
        if (printf("ONEOS_STOP_PROC_V1 %s DIRECT_ENOENT %d\n", view, (int)pid) < 0) return 3;
    } else if (printf("ONEOS_STOP_PROC_V1 %s LIVE %d %" PRIu64 " %" PRIu64 " %" PRIu64 "\n",
               view, (int)birth.pid, birth.start_ticks, birth.pid_ns_dev, birth.pid_ns_ino) < 0) {
        return 3;
    }
    return fflush(stdout) == 0 ? 0 : 3;
}
