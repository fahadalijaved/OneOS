#define _GNU_SOURCE
#include "guest_tree_install_host_profile.h"
#include "guest_tree_install_stream.h"

#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/system_properties.h>
#include <unistd.h>

extern const unsigned char oneos_verified_host_profile[288];

static int property_is(const char *name, const char *expected) {
    char value[PROP_VALUE_MAX];
    int length = __system_property_get(name, value);
    return length > 0 && (size_t)length == strlen(expected) && !memcmp(value, expected, (size_t)length);
}

static int prepare_reply(void) {
    struct stat info;
    int fd = STDOUT_FILENO;
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0 || (flags & O_PATH) || fstat(fd, &info) < 0) return -1;
    int access = flags & O_ACCMODE;
    if (S_ISFIFO(info.st_mode)) {
        if (access != O_WRONLY) return -1;
    } else if (!S_ISSOCK(info.st_mode) || access != O_RDWR || guest_tree_connected_unix_stream(fd) < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

static int report(enum guest_tree_install_host_profile_result result) {
    const char *frame;
    int status;
    switch (result) {
    case GTHP_PUBLISHED_LOCAL_CLOSED:
        frame = "ONEOS_PROFILE_V1 PUBLISHED_CLOSED\n";
        status = 0;
        break;
    case GTHP_ALREADY_MATCHES_LOCAL_CLOSED:
        frame = "ONEOS_PROFILE_V1 MATCHED_LOCAL_CLOSED\n";
        status = 0;
        break;
    case GTHP_NO_EFFECT_LOCAL_CLOSED:
        frame = "ONEOS_PROFILE_V1 REFUSED_LOCAL_CLOSED\n";
        status = 2;
        break;
    default:
        frame = "ONEOS_PROFILE_V1 HOLD\n";
        status = 3;
        break;
    }
    size_t length = strlen(frame);
    struct pollfd output = {.fd = STDOUT_FILENO, .events = POLLOUT};
    if (poll(&output, 1, 1000) != 1 || output.revents != POLLOUT
            || write(STDOUT_FILENO, frame, length) != (ssize_t)length) return 3;
    return status;
}

int main(int argc, char **argv) {
    if (argc != 2 || strcmp(argv[1], "--publish-verified-host-profile") || getuid() || geteuid()
            || getpid() != gettid() || signal(SIGPIPE, SIG_IGN) == SIG_ERR || prepare_reply() < 0) return 2;
    if (!property_is("ro.product.model", "SM-S948U1")
            || !property_is("ro.build.display.id", "CP2A.260605.016.S948U1UES4BZIG")
            || !property_is("ro.build.version.sdk", "37")) return report(GTHP_NO_EFFECT_LOCAL_CLOSED);
    return report(guest_tree_install_host_profile(oneos_verified_host_profile, sizeof(oneos_verified_host_profile)));
}
