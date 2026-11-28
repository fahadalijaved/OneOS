/* Authored observation model. It never operates on the process's real FDs. */
#include "guest_zygote_stdio.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

struct slot {
    struct stat identity;
    int status;
    int flags;
    int stat_error;
    int status_error;
    int flags_error;
};

enum query { STAT, STATUS, FLAGS };
static struct slot slots[3];
static unsigned checks, cases, calls;
static int replace_after_stat;

#define CHECK(condition) do { \
    ++checks; \
    if (!(condition)) { \
        fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); \
        exit(1); \
    } \
} while (0)

static void record_query(int fd, enum query query) {
    CHECK(calls < 9);
    CHECK(fd == (int)(calls / 3));
    CHECK(query == (enum query)(calls % 3));
    ++calls;
}

static int fail_with(int error) {
    errno = error;
    return -1;
}

int fixture_fstat(int fd, struct stat *out) {
    record_query(fd, STAT);
    if (slots[fd].stat_error) return fail_with(slots[fd].stat_error);
    *out = slots[fd].identity;
    if (fd == replace_after_stat) slots[fd].identity.st_mode = S_IFREG;
    return 0;
}

int fixture_fcntl(int fd, int command) {
    CHECK(command == F_GETFL || command == F_GETFD);
    record_query(fd, command == F_GETFL ? STATUS : FLAGS);
    if (command == F_GETFL) {
        if (slots[fd].status_error) return fail_with(slots[fd].status_error);
        return slots[fd].status;
    }
    if (slots[fd].flags_error) return fail_with(slots[fd].flags_error);
    return slots[fd].flags;
}

static void reset(void) {
    const struct slot null_slot = {
        .identity = { .st_dev = UINT64_C(0x1200000001), .st_ino = UINT64_C(0x2300000002),
                      .st_rdev = 0x103, .st_mode = S_IFCHR | 0666 },
        .status = O_RDWR,
    };
    for (unsigned i = 0; i < 3; ++i) slots[i] = null_slot;
    calls = 0;
    replace_after_stat = -1;
}

static void expect(int expected, int error, unsigned expected_calls) {
    errno = EDOM;
    int result = oneos_guest_zygote_stdio_validate();
    int actual_error = errno;
    CHECK(result == expected);
    CHECK(actual_error == error);
    CHECK(calls == expected_calls);
    ++cases;
}

int main(void) {
    reset();
    expect(0, EDOM, 9);

    for (unsigned fd = 0; fd < 3; ++fd) {
        unsigned base = fd * 3;
        const unsigned wrong_modes[] = {S_IFREG, S_IFBLK, S_IFIFO};
        const uint64_t wrong_devices[] = {0x203, 0x105, 0x100103, UINT64_C(0x100000000103)};
        const int wrong_access[] = {O_RDONLY, O_WRONLY, O_ACCMODE, O_PATH, O_PATH | O_RDWR};

        for (unsigned i = 0; i < sizeof(wrong_modes) / sizeof(*wrong_modes); ++i) {
            reset();
            slots[fd].identity.st_mode = wrong_modes[i] | 0666;
            expect(-1, ENODEV, base + 1);
        }
        for (unsigned i = 0; i < sizeof(wrong_devices) / sizeof(*wrong_devices); ++i) {
            reset();
            slots[fd].identity.st_rdev = wrong_devices[i];
            expect(-1, ENODEV, base + 1);
        }
        for (unsigned i = 0; i < sizeof(wrong_access) / sizeof(*wrong_access); ++i) {
            reset();
            slots[fd].status = wrong_access[i];
            expect(-1, EINVAL, base + 3);
        }
        reset();
        slots[fd].flags = FD_CLOEXEC;
        expect(-1, EINVAL, base + 3);

        reset();
        slots[fd].stat_error = EBADF;
        expect(-1, EBADF, base + 1);
        reset();
        slots[fd].status_error = EINTR;
        expect(-1, EINTR, base + 2);
        reset();
        slots[fd].flags_error = EIO;
        expect(-1, EIO, base + 3);
    }

    for (unsigned fd = 1; fd < 3; ++fd) {
        reset();
        slots[fd].identity.st_dev ^= UINT64_C(1) << 40;
        expect(-1, EXDEV, fd * 3 + 3);
        reset();
        slots[fd].identity.st_ino ^= UINT64_C(1) << 40;
        expect(-1, EXDEV, fd * 3 + 3);
    }

    /* Explicitly violate custody: identity changes between fstat and fcntl. */
    reset();
    replace_after_stat = 1;
    int observation = oneos_guest_zygote_stdio_validate();
    CHECK(observation == 0 && calls == 9);
    CHECK(slots[1].identity.st_mode == S_IFREG);
    puts("LIMIT: unchanged flags can hide synthetic FD replacement after fstat");
    printf("PASS %u stable-custody scenarios, %u checks\n", cases, checks);
    return 0;
}
