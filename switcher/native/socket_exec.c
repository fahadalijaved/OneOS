/*
 * socket_exec: start a program with an init-style control socket.
 *
 *   socket_exec [--seqpacket] <name> <program> [args...]
 *
 * Like init's "socket <name> stream 0660 root system" ("seqpacket" with
 * --seqpacket): creates the socket /dev/socket/<name>, listens on it, publishes it to the program as
 * ANDROID_SOCKET_<name>=<fd> (the rest of the environment is passed on) and
 * execs the program. libcutils' android_get_control_socket() takes it from
 * there and checks that the fd is bound to /dev/socket/<name>.
 *
 * The guest shares One UI's init, which has no services from the guest
 * image. HyperOS starts "rust" packages (its launcher among them) through
 * hyos_spawner, a service its own init starts with "socket hyos_spawner";
 * guest_start.sh starts it with this, and (--seqpacket) the image's own
 * zygote_next, which Android 17 starts its native-only processes from
 * (HyperOS run 11: One UI's zygote_next started Chrome's renderers, which
 * crashed reading HyperOS's font map).
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#define AID_SYSTEM 1000

int main(int argc, char **argv) {
    int type = SOCK_STREAM;
    if (argc > 1 && strcmp(argv[1], "--seqpacket") == 0) {
        type = SOCK_SEQPACKET;
        argv++;
        argc--;
    }
    if (argc < 3) {
        fprintf(stderr, "usage: socket_exec [--seqpacket] <name> <program> [args...]\n");
        return 2;
    }
    const char *name = argv[1];
    for (const char *c = name; *c; c++) {
        if (!((*c >= 'a' && *c <= 'z') || (*c >= '0' && *c <= '9') || *c == '_')) {
            fprintf(stderr, "socket_exec: bad socket name %s\n", name);
            return 2;
        }
    }
    struct sockaddr_un addr = {.sun_family = AF_UNIX};
    int n = snprintf(addr.sun_path, sizeof(addr.sun_path), "/dev/socket/%s", name);
    if (n <= 0 || (size_t)n >= sizeof(addr.sun_path)) {
        fprintf(stderr, "socket_exec: socket name too long\n");
        return 2;
    }
    int fd = socket(AF_UNIX, type, 0);
    if (fd < 0) { perror("socket"); return 1; }
    unlink(addr.sun_path);
    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror(addr.sun_path); return 1; }
    if (listen(fd, 10) < 0) { perror("listen"); return 1; }
    if (chmod(addr.sun_path, 0660) < 0) { perror("chmod"); return 1; }
    if (chown(addr.sun_path, 0, AID_SYSTEM) < 0) { perror("chown"); return 1; }

    char env[160];
    snprintf(env, sizeof(env), "ANDROID_SOCKET_%s=%d", name, fd);
    if (putenv(strdup(env)) != 0) { perror("putenv"); return 1; }
    execv(argv[2], &argv[2]);
    fprintf(stderr, "socket_exec: exec %s: %s\n", argv[2], strerror(errno));
    return 1;
}
